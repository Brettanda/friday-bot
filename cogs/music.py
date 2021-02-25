import discord
from discord.ext.commands import Cog
from discord.ext import commands

import youtube_dl,ffmpeg,json,asyncio,datetime,time
from cogs.cleanup import get_delete_time

import os,sys
from functions import is_pm,embed,MessageColors

from index import songqueue

ytdl_format_options = {
  'format': 'bestaudio/best',
  'extractaudio': True,
  'audioformat': 'mp3',
  'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
  'postprocessors': [{
    'key': 'FFmpegExtractAudio',
    'preferredcodec': 'mp3',
    'preferredquality': '192',
  }],
  'restrictfilenames': True,
  'noplaylist': True,
  'nocheckcertificate': True,
  'ignoreerrors': False,
  'logtostderr': False,
  'quiet': True,
  'no_warnings': True,
  'default_search': 'auto',
  'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}
ffmpeg_options = {
  'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
  'options': '-vn'
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class Music(Cog):
  """description goes here"""

  def __init__(self,bot):
    self.bot = bot
    self.loop = bot.loop
    # self.songqueue = {}

  async def tryagain(self,ctx):
    await ctx.reply(embed=embed(title="Something went wrong, please try again later",color=MessageColors.ERROR))

  async def can_play(self,ctx):
    # await ctx.guild.chunk(cache=False)
    connect_perms = ["connect","speak"]
    missing = []
    # voiceChannel = discord.utils.get(ctx.guild.voice_channels,id=ctx.author.voice.channel.id)
    # print(ctx.author.voice)
    # print(ctx.author.voice.channel)
    voiceChannel = None
    try:
      voiceChannel = ctx.author.voice.channel
    except:
      return False
    for perm,value in voiceChannel.permissions_for(ctx.me):
      if value == False and perm.lower() in connect_perms:
        missing.append(perm)
    if len(missing) > 0:
      await ctx.reply(embed=embed(title=f"{commands.BotMissingPermissions(missing)}",color=MessageColors.ERROR))
      return True
    return False

  class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
      super().__init__(source, volume)

      self.data = data

      self.title = data.get('title')
      self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, start=0):
      if start != 0:
        now = time.time()
      loop = loop or asyncio.get_event_loop()
      data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

      if 'entries' in data:
        # take first item from a playlist
        data = data['entries'][0]
        # TODO: Play the full playlists not just the first item

      filename = data['url'] if stream else ytdl.prepare_filename(data)
      if start != 0:
        new_time = time.time()
        start = start + (new_time - now)
        print(start)
        ffmpeg_options["options"] = f"-vn -ss {start}"
      return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

  async def start_playing(self,ctx,pop = False):
    global songqueue
    serverQueueId = "{}".format(ctx.guild.id)

    if pop == True:
      songqueue[serverQueueId].pop(0)
      
    if len(songqueue[serverQueueId]) > 0:
      ctx.voice_client.play(songqueue[serverQueueId][0],after=lambda e: asyncio.run_coroutine_threadsafe(self.start_playing(ctx,pop = True),self.bot.loop))

      try:
        thumbnail = songqueue[serverQueueId][0].data['thumbnails'][0]['url']
      except KeyError:
        thumbnail = None

      try:
        duration = str(datetime.timedelta(seconds=int(songqueue[serverQueueId][0].data['duration'])))
      except KeyError:
        duration = "??:??:??"
        
      songsinqueue = len(songqueue[serverQueueId])

      # print(songsinqueue)

      if pop == True:
        await ctx.send(
          embed=embed(
            title='Now playing: **{}**'.format(songqueue[serverQueueId][0].title),
            color=MessageColors.MUSIC,
            thumbnail=thumbnail,
            fieldstitle=["Duration","Total songs in queue"],
            fieldsval=[duration,songsinqueue]
          ),delete_after=await get_delete_time()
        )
      else:
        await ctx.reply(
          embed=embed(
            title='Now playing: **{}**'.format(songqueue[serverQueueId][0].title),
            color=MessageColors.MUSIC,
            thumbnail=thumbnail,
            fieldstitle=["Duration","Total songs in queue"],
            fieldsval=[duration,songsinqueue]
        )
        )
    else:
      async with ctx.typing():
        await ctx.voice_client.disconnect()
      await ctx.send(embed=embed(title="Finished the queue",color=MessageColors.MUSIC),delete_after=await get_delete_time())
      
  @commands.command(name="play",aliases=['p','add'],usage="<url/title>",description="Follow this command with the title of a song to search for it or just paste the Youtube/SoundCloud url if the search gives and undesirable result")
  @commands.guild_only()
  @commands.cooldown(1,4, commands.BucketType.channel)
  @commands.bot_has_permissions(send_messages = True, embed_links = True, read_messages = True)
  async def play(self,ctx, *, url: str):
    # await ctx.guild.chunk(cache=False)
    global songqueue
    if await self.can_play(ctx) == True:
      return
    if ctx.author.voice is None:
      await ctx.reply(embed=embed(title="You must be in a voice channel to play music.",color=MessageColors.MUSIC))
      return

    if "open.spotify.com" in ctx.message.content or "spotify:track:" in ctx.message.content:
      await ctx.reply(embed=embed(title="At the moment Spotify links are not supported.",color=MessageColors.ERROR))
      return

    voice = discord.utils.get(self.bot.voice_clients,guild=ctx.guild)
    voiceChannel = discord.utils.get(ctx.guild.voice_channels,id=ctx.author.voice.channel.id)

    serverQueueId = "{}".format(ctx.guild.id)
    if voice is not None:#voice.is_playing() is not None or voice.is_paused() is not None:
      async with ctx.typing():
        player = await self.YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
        songqueue[serverQueueId].append(player)

      await ctx.reply(embed=embed(title="Added to queue: **{}**".format(player.title),color=MessageColors.MUSIC))
      return

    async with ctx.typing():
      player = await self.YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
      songqueue[serverQueueId] = [player]
      await voiceChannel.connect(reconnect=False)
      await ctx.guild.change_voice_state(channel=voiceChannel,self_mute=False,self_deaf=True)

    # try:
    await self.start_playing(ctx)
    # except:
      # await self.tryagain(ctx)

  @commands.command(name="stop")
  @commands.guild_only()
  @commands.bot_has_permissions(send_messages = True, embed_links = True, read_messages = True)
  async def stop(self,ctx):
    # await ctx.guild.chunk(cache=False)
    global songqueue
    if await self.can_play(ctx) == True:
      return
    try:
      # voice = discord.utils.get(self.bot.voice_clients,guild=ctx.guild)
      voice = ctx.guild.voice_client
      if voice is not None:
        try:
          async with ctx.typing():
            if len(songqueue["{}".format(ctx.guild.id)]) > 0:
              del songqueue["{}".format(ctx.guild.id)]
            voice.stop()
        except:
          pass
        finally:
          await voice.disconnect()
          await ctx.reply(embed=embed(title="Finished"))
      else:
        await ctx.reply(embed=embed(title="I am not connected to a voice channel"))
    except:
      await self.tryagain(ctx)

  @commands.command(name="skip")
  @commands.guild_only()
  @commands.bot_has_permissions(send_messages = True, embed_links = True, read_messages = True)
  async def skip(self,ctx):
    # await ctx.guild.chunk(cache=False)
    global songqueue
    if await self.can_play(ctx) == True:
      return
    try:
      serverQueueId = "{}".format(ctx.guild.id)
      if len(songqueue[serverQueueId]) > 1:
        ctx.voice_client.stop()
        ctx.voice_client.play(songqueue[serverQueueId][0], after=lambda e: asyncio.run_coroutine_threadsafe(self.start_playing(ctx),self.bot.loop))
      else:
        voice = discord.utils.get(self.bot.voice_clients,guild=ctx.guild)
        if voice is not None:
          async with ctx.typing():
            await voice.disconnect()
          await ctx.reply(embed=embed(title="Finished",color=MessageColors.MUSIC))
        else:
          await ctx.reply(embed=embed(title="I am not connected to a voice channel",color=MessageColors.MUSIC))
    except:
      await self.tryagain(ctx)

  # @commands.command(name="shuffle")
  # @commands.guild_only()
  # @commands.bot_has_permissions(send_messages = True, embed_links = True, read_messages = True)
  # async def shuffle(self,ctx):

  # TODO: Check for queue length so discord message is less than max message character count
  @commands.command(name="queue")
  @commands.guild_only()
  @commands.bot_has_permissions(send_messages = True, embed_links = True, read_messages = True)
  async def queue(self,ctx):
    # await ctx.guild.chunk(cache=False)
    global songqueue
    if await self.can_play(ctx) == True:
      return
    try:
      if len(songqueue) > 0 and len(songqueue["{}".format(ctx.guild.id)]) > 0:
        q = songqueue["{}".format(ctx.guild.id)]
        queueList = ""
        title = "Now playing: **{}**".format(q[0].title)
        x = 0
        for i in q[1:]:
          x = x + 1
          if x == 1:
            queueList = "Up Next: \n"
          queueList = queueList + "\t{}: {}\n".format(x,i.title)

        await ctx.reply(embed=embed(title=title,description=queueList,color=MessageColors.MUSIC))
      else:
        await ctx.reply(embed=embed(title="Nothing is playing right now"))
    except:
      await self.tryagain(ctx)

  @commands.command(name="pause")
  @commands.guild_only()
  @commands.bot_has_permissions(send_messages = True, embed_links = True, read_messages = True)
  async def pause(self,ctx):
    # await ctx.guild.chunk(cache=False)
    if await self.can_play(ctx) == True:
      return
    try:
      voice = discord.utils.get(self.bot.voice_clients,guild=ctx.guild)
      if voice is not None:
        if voice.is_paused():
          await ctx.reply(embed=embed(title="I have already been paused",color=MessageColors.MUSIC))
        elif voice.is_playing(): 
          voice.pause()
          await ctx.reply(embed=embed(title="Paused",color=MessageColors.MUSIC))
    except:
      await self.tryagain(ctx)

  @commands.command(name="resume")
  @commands.guild_only()
  @commands.bot_has_permissions(send_messages = True, embed_links = True, read_messages = True)
  async def resume(self,ctx):
    # await ctx.guild.chunk(cache=False)
    if await self.can_play(ctx) == True:
      return
    try:
      voice = discord.utils.get(self.bot.voice_clients,guild=ctx.guild)
      if voice is not None:
        if voice.is_paused():
          voice.resume()
          await ctx.reply(embed=embed(title="Resumed",color=MessageColors.MUSIC))
        elif voice.is_playing(): 
          await ctx.reply(embed=embed(title="I was never paused",color=MessageColors.MUSIC))
      else:
        await ctx.reply(embed=embed(title="Failed to resume",color=MessageColors.ERROR))
    except:
      await self.tryagain(ctx)

  @commands.command(name="listen",hidden=True)
  @commands.is_owner()
  @commands.guild_only()
  @commands.bot_has_permissions(send_messages = True, embed_links = True, read_messages = True)
  async def listen(self,ctx):
    # TODO: the title from spotify doesn't always play the correct song
    # TODO: won't keep up if the user skips the current song
    # await ctx.guild.chunk(cache=False)
    if await self.can_play(ctx) == True:
      return
    toplay = ctx.author.activities or None
    if toplay is not None:
      for act in toplay:
        if isinstance(act,discord.Spotify):
          toplay = act or None
    else:
      return
    voice = discord.utils.get(self.bot.voice_clients,guild=ctx.guild)
    try:
      await ctx.author.voice.channel.connect(reconnect=False)
      await ctx.guild.change_voice_state(channel=ctx.author.voice.channel,self_mute=False,self_deaf=True)
    except:
      pass

    try:
      now = datetime.datetime.now(datetime.timezone.utc)
      start = toplay.start
      now = now.replace(tzinfo=None)
      currentplay = (now - start)
      secs = currentplay.seconds
      player = await self.YTDLSource.from_url(f"{toplay.title} {toplay.artist}", loop=self.bot.loop, stream=True,start=secs)
      # player = await self.YTDLSource.from_url(f"spotify:track:{toplay.track_id}", loop=self.bot.loop, stream=True,start=secs)
      # ctx.voice_client.play(player)
      ctx.voice_client.play(player,after=lambda e: asyncio.run_coroutine_threadsafe(self.listen(ctx),self.bot.loop))
      duration = toplay.duration - datetime.timedelta(microseconds=toplay.duration.microseconds)
      await ctx.reply(
        embed=embed(
          title=f'Now playing: **{player.title}**',
          color=MessageColors.MUSIC,
          thumbnail=player.data['thumbnails'][0]['url'],
          # fieldstitle=["Started at","Duration"],
          # fieldsval=[secs,duration]
          fieldstitle=["Duration"],
          fieldsval=[duration]
      )
      )
    except BaseException as e:
      print(e)
      if "Already playing audio." in str(e):
        await ctx.reply(embed=embed(title=f"I'm unable to listen along with you because I am already listening along with someone else",color=MessageColors.ERROR))
    # else:
    #   while voice.is_playing():
    #     print()

  @Cog.listener()
  async def on_voice_state_update(self,member,before,after):
    global songqueue
    # TODO: when moved to another voice channel, Friday will some times just stop playing music until !pause and !resume are executed
    if member == self.bot.user:
      try:
        if after.channel == None and len(songqueue["{}".format(member.guild.id)]) > 0:
          del songqueue["{}".format(member.guild.id)]
          # print("{} queue cleared".format(member.guild.id))
      except KeyError:
        pass

    try:
      await asyncio.sleep(3)
      if len(member.guild.voice_client.channel.members) == 1:
        await member.guild.voice_client.disconnect()
        del songqueue["{}".format(member.guild.id)]
    except KeyError:
      pass
    except AttributeError:
      pass


def setup(bot):
  bot.add_cog(Music(bot))