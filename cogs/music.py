# import sys
# import os
from index import songqueue
import discord
from discord.ext.commands import Cog
from discord.ext import commands

from discord_slash import cog_ext  # , SlashContext
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


import youtube_dl
import json
import validators
import asyncio
import datetime
import time
# from cogs.cleanup import get_delete_time

from functions import embed, MessageColors, exceptions, checks, query  # , relay_info


def can_play(ctx: commands.Context):
  connect_perms = ["connect", "speak"]
  missing = []
  if ctx.author.voice is None or ctx.author.voice.channel is None:
    raise exceptions.UserNotInVoiceChannel("You must be in a voice channel to play music.")
  for perm, value in ctx.author.voice.channel.permissions_for(ctx.me):
    if value is False and perm.lower() in connect_perms:
      missing.append(perm)
  if len(missing) > 0:
    raise commands.BotMissingPermissions(missing)
  return True


ytdl_format_options = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '64',
    }],
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class Music(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.bot = bot

  async def tryagain(self, ctx):
    # if isinstance(ctx, SlashContext):
      # await ctx.send(embed=embed(title="Something went wrong, please try again later", color=MessageColors.ERROR))
    # await ctx.reply(embed=embed(title="Something went wrong, please try again later", color=MessageColors.ERROR))
    return dict(embed=embed(title="Something went wrong, please try again later", color=MessageColors.ERROR))

  async def can_play(self, ctx):
    connect_perms = ["connect", "speak"]
    missing = []

    if not hasattr(ctx.author, "voice"):
      raise exceptions.OnlySlashCommands()

    if ctx.author.voice is None:
      raise exceptions.UserNotInVoiceChannel("You must be in a voice channel to play music.")

    if ctx.author.voice.channel is None:
      raise exceptions.CantSeeNewVoiceChannelType("I believe you are in a new type of voice channel that I can't join yet")

    if ctx.author.voice.channel.type == discord.ChannelType.stage_voice:
      return dict(embed=embed(title="I cannot play in stage channels, yet ;)", color=MessageColors.ERROR))

    voiceChannel = ctx.author.voice.channel
    for perm, value in voiceChannel.permissions_for(ctx.guild.me):
      if value is False and perm.lower() in connect_perms:
        missing.append(perm)
    if missing:
      return dict(embed=embed(title=f"{commands.BotMissingPermissions(missing)}", color=MessageColors.ERROR))
      # await ctx.reply(embed=embed(title=f"{commands.BotMissingPermissions(missing)}", color=MessageColors.ERROR))
    return True

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

      # if 'entries' in data:
      #   # take first item from a playlist
      #   data = data['entries'][0]
      #   # TODO: Play the full playlists not just the first item

      if start != 0:
        new_time = time.time()
        start = start + (new_time - now)
        print(start)
        ffmpeg_options["options"] = f"-vn -ss {start}"
      # filename = data['url'] if stream else ytdl.prepare_filename(data)
      dataa = []
      if "entries" in data:
        for d in data["entries"]:
          filename = d['url'] if stream else ytdl.prepare_filename(d)
          dataa.append(cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=d))
      else:
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        dataa = [cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)]
      return (*dataa,)
      # return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

  async def start_playing(self, ctx, pop=False, slash=False):
    # global songqueue
    serverQueueId = "{}".format(ctx.guild.id)

    if pop is True:
      if ctx.guild.voice_client.channel.type == discord.ChannelType.stage_voice and ctx.guild.voice_client.channel.topic == songqueue[serverQueueId][0].title:
        await ctx.guild.voice_client.channel.edit(topic=songqueue[serverQueueId][1].title)
      songqueue[serverQueueId].pop(0)

    if len(songqueue[serverQueueId]) > 0:
      ctx.guild.voice_client.play(songqueue[serverQueueId][0], after=lambda e: asyncio.run_coroutine_threadsafe(self.start_playing(ctx, pop=True), self.bot.loop))

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
      # if not looping:
      #   return dict(
      #       embed=embed(
      #           title='Now playing: **{}**'.format(songqueue[serverQueueId][0].title),
      #           color=MessageColors.MUSIC,
      #           thumbnail=thumbnail,
      #           fieldstitle=["Duration", "Total songs in queue"],
      #           fieldsval=[duration, songsinqueue]
      #       ), delete_after=self.bot.log.get_guild_delete_commands(ctx.guild)
      #   )
      if pop is True or slash:
        await ctx.send(
            embed=embed(
                title='Now playing: **{}**'.format(songqueue[serverQueueId][0].title),
                color=MessageColors.MUSIC,
                thumbnail=thumbnail,
                fieldstitle=["Duration", "Total songs in queue"],
                fieldsval=[duration, songsinqueue]
            ), delete_after=self.bot.log.get_guild_delete_commands(ctx.guild)
        )
      else:
        await ctx.reply(
            embed=embed(
                title='Now playing: **{}**'.format(songqueue[serverQueueId][0].title),
                color=MessageColors.MUSIC,
                thumbnail=thumbnail,
                fieldstitle=["Duration", "Total songs in queue"],
                fieldsval=[duration, songsinqueue]
            ), delete_after=self.bot.log.get_guild_delete_commands(ctx.guild)
        )
    else:
      await ctx.guild.voice_client.disconnect()
      # if looping:
      return await ctx.send(embed=embed(title="Finished the queue", color=MessageColors.MUSIC), delete_after=self.bot.log.get_guild_delete_commands(ctx.guild))

  @commands.command(name="play", aliases=['p', 'add'], usage="<url/title>", help="Follow this command with the title of a song to search for it or just paste the Youtube/SoundCloud url if the search gives and undesirable result")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @commands.bot_has_permissions(send_messages=True, embed_links=True, read_messages=True)
  async def norm_play(self, ctx, *, query: str):
    await self.play(ctx, query)

  @cog_ext.cog_slash(name="play", description="Play some epic music")
  @checks.slash(user=True, private=False)
  async def slash_play(self, ctx, query: str):
    await self.play(ctx, query, True)

  async def play(self, ctx, query: str, slash=False):
    # await ctx.guild.chunk(cache=False)
    global songqueue
    can_play = await self.can_play(ctx)
    if can_play is not True:
      if slash:
        return await ctx.send(**can_play)
      return await ctx.reply(**can_play)

    if "open.spotify.com" in query or "spotify:track:" in query:  # ) or ("open.spotify.com" in ctx.message.content or "spotify:track:" in ctx.message.content):
      if slash:
        return await ctx.send(embed=embed(title="At the moment Spotify links are not supported.", color=MessageColors.ERROR))
      return await ctx.reply(embed=embed(title="At the moment Spotify links are not supported.", color=MessageColors.ERROR))

    if slash:
      await ctx.defer()

    voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

    serverQueueId = "{}".format(ctx.guild.id)
    if voice is not None:  # voice.is_playing() is not None or voice.is_paused() is not None:
      try:
        # async with ctx.typing():
        players = await self.YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
        print(players)
        for player in players:
          if not hasattr(player, "title"):
            print("nothing")
          songqueue[serverQueueId].append(player)
        if len(players) > 1:
          if slash:
            return await ctx.send(embed=embed(title=f"Added `{len(players)}` songs to queue", color=MessageColors.MUSIC))
          return await ctx.reply(embed=embed(title=f"Added `{len(players)}` songs to queue", color=MessageColors.MUSIC))
          # await ctx.reply(embed=embed(title=f"Added `{len(players)}` songs to queue", color=MessageColors.MUSIC))
        else:
          if slash:
            return await ctx.send(embed=embed(title=f"Added to queue: **{players[0].title}**", color=MessageColors.MUSIC))
          return await ctx.reply(embed=embed(title=f"Added to queue: **{players[0].title}**", color=MessageColors.MUSIC))
          # await ctx.reply(embed=embed(title=f"Added to queue: **{players[0].title}**", color=MessageColors.MUSIC))
        return
      except BaseException as e:
        try:
          e = "".join(f"{e}".split("ERROR: "))
        except BaseException:
          pass
        if slash:
          return await ctx.send(embed=embed(title=f"{e}", color=MessageColors.ERROR))
        return await ctx.reply(embed=embed(title=f"{e}", color=MessageColors.ERROR))
        # return await ctx.reply(embed=embed(title=f"{e}", color=MessageColors.ERROR))
    # async with ctx.typing():
    try:
      players = await self.YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
      print(players)
      songqueue[serverQueueId] = []
      for player in players:
        songqueue[serverQueueId].append(player)
      vc = await ctx.author.voice.channel.connect(reconnect=True)
      # if vc.channel.type.name == "stage_voice" and vc.channel.topic is None:
      #   vc.pause()
      if vc.channel.type == discord.ChannelType.stage_voice:
        if vc.channel.topic is None:
          await vc.channel.edit(topic=player.title)
          # await vc.channel.edit(topic="Beats with Friday")
        await ctx.guild.me.edit(suppress=False)
        # await ctx.guild.me.request_to_speak()
      await ctx.guild.change_voice_state(channel=vc.channel, self_mute=False, self_deaf=True)
    except BaseException as e:
      try:
        e = "".join(f"{e}".split("ERROR: "))
      except BaseException:
        pass
      if slash:
        return await ctx.send(embed=embed(title=f"{e}", color=MessageColors.ERROR))
      return await ctx.reply(embed=embed(title=f"{e}", color=MessageColors.ERROR))
      # return await ctx.reply(embed=embed(title=f"{e}", color=MessageColors.ERROR))
    # try:
    await self.start_playing(ctx, slash=slash)
    # except:
    # await self.tryagain(ctx)

  @commands.command(name="stop", aliases=["disconnect"], help="Stops the currently playing music", brief="Stops the music")
  @commands.guild_only()
  async def norm_stop(self, ctx):
    await self.stop(ctx)

  @cog_ext.cog_slash(name="stop", description="Stops the music")
  @checks.slash(user=True, private=False)
  async def slash_stop(self, ctx):
    await self.stop(ctx, True)

  async def stop(self, ctx, slash=False):
    global songqueue
    can_play = await self.can_play(ctx)
    if can_play is not True:
      if slash:
        return await ctx.send(**can_play)
      return await ctx.reply(**can_play)
    try:
      # voice = discord.utils.get(self.bot.voice_clients,guild=ctx.guild)
      voice = ctx.guild.voice_client
      if voice is not None:
        try:
          # async with ctx.typing():
          if len(songqueue["{}".format(ctx.guild.id)]) > 0:
            del songqueue["{}".format(ctx.guild.id)]
          voice.stop()
        except BaseException:
          pass
        await voice.disconnect()
        if slash:
          return await ctx.send(embed=embed(title="Finished"))
        return await ctx.reply(embed=embed(title="Finished"))
      else:
        if slash:
          return await ctx.send(embed=embed(title="I am not connected to a voice channel"))
        return await ctx.reply(embed=embed(title="I am not connected to a voice channel"))
        # await ctx.reply(embed=embed(title="I am not connected to a voice channel"))
    except BaseException:
      if slash:
        return await ctx.send(**await self.tryagain(ctx))
      return await ctx.reply(**await self.tryagain(ctx))

  @commands.command(name="skip", help="Skips the current song")
  @commands.guild_only()
  @commands.bot_has_permissions(send_messages=True, embed_links=True, read_messages=True)
  async def norm_skip(self, ctx):
    try:
      await ctx.message.delete(delay=self.bot.log.get_guild_delete_commands(ctx.guild))
    except discord.NotFound:
      pass
    await self.skip(ctx)

  @cog_ext.cog_slash(name="skip", description="Skips the current song")
  @checks.slash(user=True, private=False)
  async def slash_skip(self, ctx):
    await self.skip(ctx, True)

  async def skip(self, ctx, slash=False):
    global songqueue
    can_play = await self.can_play(ctx)
    if can_play is not True:
      if slash:
        return await ctx.send(**can_play)
      return await ctx.reply(**can_play)
    try:
      serverQueueId = "{}".format(ctx.guild.id)
      if len(songqueue[serverQueueId]) > 1:
        ctx.guild.voice_client.stop()
        ctx.guild.voice_client.play(songqueue[serverQueueId][0], after=lambda e: asyncio.run_coroutine_threadsafe(self.start_playing(ctx), self.bot.loop))
        if slash:
          try:
            thumbnail = songqueue[serverQueueId][1].data['thumbnails'][0]['url']
          except KeyError:
            thumbnail = None

          try:
            duration = str(datetime.timedelta(seconds=int(songqueue[serverQueueId][1].data['duration'])))
          except KeyError:
            duration = "??:??:??"

          songsinqueue = len(songqueue[serverQueueId]) - 1
          return await ctx.send(
              embed=embed(
                  title='Now playing: **{}**'.format(songqueue[serverQueueId][1].title),
                  color=MessageColors.MUSIC,
                  thumbnail=thumbnail,
                  fieldstitle=["Duration", "Total songs in queue"],
                  fieldsval=[duration, songsinqueue]
              ), delete_after=self.bot.log.get_guild_delete_commands(ctx.guild)
          )
      else:
        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        if voice is not None:
          # async with ctx.typing():
          await voice.disconnect()
          if slash:
            return await ctx.send(embed=embed(title="Finished", color=MessageColors.MUSIC))
          return await ctx.reply(embed=embed(title="Finished", color=MessageColors.MUSIC))
        else:
          if slash:
            return await ctx.send(embed=embed(title="I am not connected to a voice channel", color=MessageColors.MUSIC))
          return await ctx.reply(embed=embed(title="I am not connected to a voice channel", color=MessageColors.MUSIC))
    except BaseException:
      if slash:
        return await ctx.send(**await self.tryagain(ctx))
      return await ctx.reply(**await self.tryagain(ctx))

  # @commands.command(name="shuffle")
  # @commands.guild_only()
  # @commands.bot_has_permissions(send_messages = True, embed_links = True, read_messages = True)
  # async def shuffle(self,ctx):

  # TODO: Check for queue length so discord message is less than max message character count
  @commands.command(name="queue", help="shows the song queue")
  @commands.guild_only()
  async def norm_queue(self, ctx):
    await self.queue(ctx)

  @cog_ext.cog_slash(name="queue", description="Shows the current queue of music")
  @checks.slash(user=True, private=False)
  async def slash_queue(self, ctx):
    await self.queue(ctx, True)

  async def queue(self, ctx, slash=False):
    global songqueue
    can_play = await self.can_play(ctx)
    if can_play is not True:
      if slash:
        return await ctx.send(**can_play)
      return await ctx.reply(**can_play)
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
          queueList = queueList + "\t{}: {}\n".format(x, i.title)
        if slash:
          return await ctx.send(embed=embed(title=title, description=queueList, color=MessageColors.MUSIC))
        return await ctx.reply(embed=embed(title=title, description=queueList, color=MessageColors.MUSIC))
        # await ctx.reply(embed=embed(title=title, description=queueList, color=MessageColors.MUSIC))
      else:
        if slash:
          return await ctx.send(embed=embed(title="Nothing is playing right now"))
        return await ctx.reply(embed=embed(title="Nothing is playing right now"))
        # await ctx.reply(embed=embed(title="Nothing is playing right now"))
    except BaseException:
      if slash:
        return await ctx.send(**await self.tryagain(ctx))
      return await ctx.reply(**await self.tryagain(ctx))

  @commands.command(name="pause", help="Pause the current track")
  @commands.guild_only()
  async def norm_pause(self, ctx):
    await self.pause(ctx)

  @cog_ext.cog_slash(name="pause", description="Pause the current track")
  @checks.slash(user=True, private=False)
  async def slash_pause(self, ctx):
    await self.pause(ctx, True)

  async def pause(self, ctx, slash=False):
    can_play = await self.can_play(ctx)
    if can_play is not True:
      if slash:
        return await ctx.send(**can_play)
      return await ctx.reply(**can_play)
    try:
      voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
      if voice is not None:
        if voice.is_paused():
          if slash:
            return await ctx.send(embed=embed(title="I have already been paused", color=MessageColors.MUSIC))
          return await ctx.reply(embed=embed(title="I have already been paused", color=MessageColors.MUSIC))
        elif voice.is_playing():
          voice.pause()
          if slash:
            return await ctx.send(embed=embed(title="Paused", color=MessageColors.MUSIC))
          return await ctx.reply(embed=embed(title="Paused", color=MessageColors.MUSIC))
    except BaseException:
      if slash:
        return await ctx.send(**await self.tryagain(ctx))
      return await ctx.reply(**await self.tryagain(ctx))

  @commands.command(name="resume", help="Resume the current track")
  @commands.guild_only()
  async def norm_resume(self, ctx):
    await self.resume(ctx)

  @cog_ext.cog_slash(name="resume", description="Resume the current track")
  @checks.slash(user=True, private=False)
  async def slash_resume(self, ctx):
    await self.resume(ctx, True)

  async def resume(self, ctx, slash=False):
    can_play = await self.can_play(ctx)
    if can_play is not True:
      if slash:
        return await ctx.send(**can_play)
      return await ctx.reply(**can_play)
    try:
      voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
      if voice is not None:
        if voice.is_paused():
          voice.resume()
          if slash:
            return await ctx.send(embed=embed(title="Resumed", color=MessageColors.MUSIC))
          return await ctx.reply(embed=embed(title="Resumed", color=MessageColors.MUSIC))
        elif voice.is_playing():
          if slash:
            return await ctx.send(embed=embed(title="I was never paused", color=MessageColors.MUSIC))
          return await ctx.reply(embed=embed(title="I was never paused", color=MessageColors.MUSIC))
      else:
        if slash:
          return await ctx.send(embed=embed(title="Failed to resume", color=MessageColors.ERROR))
        return await ctx.reply(embed=embed(title="Failed to resume", color=MessageColors.ERROR))
    except BaseException:
      if slash:
        return await ctx.send(**await self.tryagain(ctx))
      return await ctx.reply(**await self.tryagain(ctx))

  # @commands.command(name="listen", hidden=True)
  # @commands.is_owner()
  # @commands.guild_only()
  # @commands.bot_has_permissions(send_messages=True, embed_links=True, read_messages=True)
  # async def listen(self, ctx):
  #   # TODO: the title from spotify doesn't always play the correct song
  #   # TODO: won't keep up if the user skips the current song
  #   # await ctx.guild.chunk(cache=False)
  #   if await self.can_play(ctx) is True:
  #     return
  #   toplay = ctx.author.activities or None
  #   if toplay is not None:
  #     for act in toplay:
  #       if isinstance(act, discord.Spotify):
  #         toplay = act or None
  #   else:
  #     return
  #   # voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
  #   try:
  #     await ctx.author.voice.channel.connect(reconnect=False)
  #     await ctx.guild.change_voice_state(channel=ctx.author.voice.channel, self_mute=False, self_deaf=True)
  #   except BaseException:
  #     pass

  #   try:
  #     now = datetime.datetime.now(datetime.timezone.utc)
  #     start = toplay.start
  #     now = now.replace(tzinfo=None)
  #     currentplay = (now - start)
  #     secs = currentplay.seconds
  #     player = await self.YTDLSource.from_url(f"{toplay.title} {toplay.artist}", loop=self.bot.loop, stream=True, start=secs)
  #     # player = await self.YTDLSource.from_url(f"spotify:track:{toplay.track_id}", loop=self.bot.loop, stream=True,start=secs)
  #     # ctx.voice_client.play(player)
  #     ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(self.listen(ctx), self.bot.loop))
  #     duration = toplay.duration - datetime.timedelta(microseconds=toplay.duration.microseconds)
  #     await ctx.reply(
  #         embed=embed(
  #             title=f'Now playing: **{player.title}**',
  #             color=MessageColors.MUSIC,
  #             thumbnail=player.data['thumbnails'][0]['url'],
  #             # fieldstitle=["Started at","Duration"],
  #             # fieldsval=[secs,duration]
  #             fieldstitle=["Duration"],
  #             fieldsval=[duration]
  #         )
  #     )
  #   except BaseException as e:
  #     print(e)
  #     if "Already playing audio." in str(e):
  #       await ctx.reply(embed=embed(title="I'm unable to listen along with you because I am already listening along with someone else", color=MessageColors.ERROR))
  #   # else:
  #   #   while voice.is_playing():
  #   #     print()

  @Cog.listener()
  async def on_voice_state_update(self, member, before, after):
    global songqueue
    # TODO: when moved to another voice channel, Friday will some times just stop playing music until !pause and !resume are executed
    if member == self.bot.user:
      try:
        if after.channel is None and len(songqueue["{}".format(member.guild.id)]) > 0:
          del songqueue["{}".format(member.guild.id)]
          # print("{} queue cleared".format(member.guild.id))
      except KeyError:
        pass

    try:
      await asyncio.sleep(3)
      if len(member.guild.voice_client.channel.voice_states) == 1:
        if member.guild.voice_client.channel.type == discord.ChannelType.stage_voice:
          await member.guild.voice_client.channel.edit(topic="")
        await member.guild.voice_client.disconnect()
        del songqueue["{}".format(member.guild.id)]
    except KeyError:
      pass
    except AttributeError:
      pass

  @commands.group(name="custom", aliases=["c"], invoke_without_command=True, help="Play sounds/songs without looking for the url everytime")
  @commands.guild_only()
  # @commands.cooldown(1,4, commands.BucketType.channel)
  @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
  async def custom(self, ctx, name: str):
    if not can_play(ctx):
      return
    try:
      async with ctx.typing():
        sounds = await query(self.bot.log.mydb, "SELECT customSounds FROM servers WHERE id=?", ctx.guild.id)
        sounds = json.loads(sounds)
    except Exception:
      await ctx.reply(embed=embed(title=f"The custom sound `{name}` has not been set, please add it with `{ctx.prefix}custom|c add <name> <url>`", color=MessageColors.ERROR))
    else:
      if sounds is not None and name in sounds:
        await ctx.invoke(self.bot.get_command("play"), query=sounds[name])
      else:
        await ctx.reply(embed=embed(title=f"The sound `{name}` has not been added, please check the `custom list` command", color=MessageColors.ERROR))

  @custom.command(name="add")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def custom_add(self, ctx, name: str, url: str):
    url = url.strip("<>")
    valid = validators.url(url)
    if valid is not True:
      await ctx.reply(embed=embed(title=f"Failed to recognize the url `{url}`", color=MessageColors.ERROR))
      return

    if name in ["add", "change", "replace", "list", "remove", "del"]:
      await ctx.reply(embed=embed(title=f"`{name}`is not an acceptable name for a command as it is a sub-command of custom", color=MessageColors.ERROR))
      return

    async with ctx.typing():
      name = "".join(name.split(" ")).lower()
      sounds = (await query(self.bot.log.mydb, "SELECT customSounds FROM servers WHERE id=?", ctx.guild.id))
      if sounds == "" or sounds is None:
        sounds = r"{}"
      sounds = json.loads(sounds)
      if name in sounds:
        await ctx.reply(embed=embed(title=f"`{name}` was already added, please choose another", color=MessageColors.ERROR))
        return
      sounds.update({name: url})
      await query(self.bot.log.mydb, "UPDATE servers SET customSounds=? WHERE id=?", json.dumps(sounds), ctx.guild.id)
    await ctx.reply(embed=embed(title=f"I will now play `{url}` for the command `{ctx.prefix}{ctx.command.parent} {name}`"))

  @custom.command(name="list")
  @commands.guild_only()
  async def custom_list(self, ctx):
    async with ctx.typing():
      sounds = await query(self.bot.log.mydb, "SELECT customSounds FROM servers WHERE id=?", ctx.guild.id)
      if sounds is None:
        raise exceptions.NoCustomSoundsFound("There are no custom sounds for this server (yet)")
      sounds = json.loads(sounds)
      result = ""
      for sound in sounds:
        result += f"```{sound} -> {sounds[sound]}```"
      if result == "":
        result = "There are no custom sounds for this server (yet)"
    await ctx.reply(embed=embed(title="The list of custom sounds", description=result))

  @custom.command(name="change", aliases=["replace"])
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def custom_change(self, ctx, name: str, url: str):
    try:
      async with ctx.typing():
        name = "".join(name.split(" ")).lower()
        sounds = await query(self.bot.log.mydb, "SELECT customSounds FROM servers WHERE id=?", ctx.guild.id)
        sounds = json.loads(sounds)
        old = sounds[name]
        sounds[name] = url
        await query(self.bot.log.mydb, "UPDATE servers SET customSounds=? WHERE id=?", json.dumps(sounds), ctx.guild.id)
    except KeyError:
      await ctx.reply(embed=embed(title=f"Could not find the custom command `{name}`", color=MessageColors.ERROR))
    else:
      await ctx.reply(embed=embed(title=f"Changed `{name}` from `{old}` to `{url}`"))

  @custom.command(name="remove", aliases=["del"])
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def custom_del(self, ctx, name: str):
    try:
      async with ctx.typing():
        name = "".join(name.split(" ")).lower()
        sounds = await query(self.bot.log.mydb, "SELECT customSounds FROM servers WHERE id=?", ctx.guild.id)
        sounds = json.loads(sounds)
        del sounds[name]
        await query(self.bot.log.mydb, "UPDATE servers SET customSounds=? WHERE id=?", json.dumps(sounds), ctx.guild.id)
    except KeyError:
      await ctx.reply(embed=embed(title=f"Could not find the custom command `{name}`", color=MessageColors.ERROR))
    else:
      await ctx.reply(embed=embed(title=f"Removed the custom sound `{name}`"))


def setup(bot):
  bot.add_cog(Music(bot))
