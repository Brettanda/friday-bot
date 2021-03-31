import asyncio
import datetime
# import json
import logging
import random
# import time
# import typing

import discord
import validators
import wavelink
# import youtube_dl
from discord.ext import commands, tasks
from discord.ext.menus import ListPageSource, MenuPages

from cogs.cleanup import get_delete_time
from functions import MessageColors, embed, exceptions, relay_info


def can_play(ctx:commands.Context):
  connect_perms = ["connect","speak"]
  missing = []
  voice = ctx.author.voice
  if voice is None or voice.channel is None:
    raise exceptions.UserNotInVoiceChannel("You must be in a voice channel to play music.")
  for perm,value in voice.channel.permissions_for(ctx.me):
    if value == False and perm.lower() in connect_perms:
      missing.append(perm)
  if len(missing) > 0:
    raise commands.BotMissingPermissions(missing)
  return True

import os
import sys

from cogs.help import cmd_help
from index import dead_nodes_sent, songqueue

SEARCHOPTIONS = {
  "1️⃣":0,
  "2️⃣":1,
  "3️⃣":2,
  "4️⃣":3,
  "5️⃣":4,
  "6️⃣":5,
  "7️⃣":6,
  "8️⃣":7
}


class Music(commands.Cog, wavelink.WavelinkMixin):
  def __init__(self,bot):
    self.bot = bot
    self.loop = bot.loop
    if not hasattr(bot, 'wavelink'):
      self.bot.wavelink = wavelink.Client(bot=self.bot)
    # self.bot.loop.create_task(self.start_nodes())
    self.start_nodes.start()
    self.fucking_check_for_dead_nodes.start()
    
    # self.songqueue = {}

  class LavaPlayer(wavelink.Player):
    def __init__(self,*args,**kwargs):
      super().__init__(*args,**kwargs)
      if not hasattr(self,"text_channel"):
        self.text_channel = None
      if not hasattr(self,"voice_channel"):
        self.voice_channel = None

    async def connect(self,ctx:commands.Context=None,channel:discord.VoiceChannel=None):
      if not hasattr(self,"voice_channel"):
        self.voice_channel = channel
      if self.is_connected and ctx is not None and self.bot.user in ctx.guild.voice.channel.members:
        await ctx.reply(embed=embed(title=f"I am already connected to `{self.bot.get_channel(self.channel_id)}`",color=MessageColors.ERROR))
        return channel

      if ctx is not None and (channel := getattr(ctx.author.voice, "channel", channel)) is None:
        await ctx.reply(embed=embed(title=f"Could not find voice channel `{channel}`",color=MessageColors.ERROR))
        return channel

      if not isinstance(channel,int):
        await super().connect(channel.id)
        await ctx.guild.change_voice_state(channel=channel,self_mute=False,self_deaf=True)

      return channel

    async def add_tracks(self,ctx,tracks):
      global songqueue
      serverQueueId = str(ctx.guild.id)
      # if not hasattr(tracks,"tracks") and isinstance(tracks,list) and len(tracks) == 1:
      #   track = tracks[0]
      if not hasattr(tracks,"tracks") and isinstance(tracks,wavelink.Track):
        track = tracks
      elif not hasattr(tracks,"tracks") and not isinstance(tracks,wavelink.Track):
        track = tracks[0]
      else:
        track = tracks.tracks[0]
      if not hasattr(self,"text_channel") or self.text_channel is None:
        self.text_channel = ctx.channel
      if not hasattr(self,"voice_channel") or self.voice_channel is None:
        self.voice_channel = discord.utils.get(ctx.guild.voice_channels,id=ctx.author.voice.channel.id)
      if isinstance(tracks,wavelink.TrackPlaylist):
        try:
          for trak in tracks.tracks:
            songqueue[serverQueueId].append({"track":trak,"requested":ctx.author})
        except KeyError:
          songqueue[serverQueueId] = []
          for trak in tracks.tracks:
            songqueue[serverQueueId].append({"track":trak,"requested":ctx.author})
      elif tracks == None:
        await ctx.reply(embed=embed(title="Failed to load this song/playlist please try another one",color=MessageColors.ERROR))
        return
      else:
        try:
          songqueue[serverQueueId].append({"track":track if track is not None else tracks[0],"requested":ctx.author})
        except KeyError:
          songqueue[serverQueueId] = []
          songqueue[serverQueueId].append({"track":track if track is not None else tracks[0],"requested":ctx.author})

      thumbnail = track.thumb if track.thumb is not None else None

      try:
        duration = str(datetime.timedelta(milliseconds=int(track.duration))).split(".")[0]
      except KeyError:
        duration = "??:??:??"
        
      songsinqueue = len(songqueue[serverQueueId])

      # voiceChannel = discord.utils.get(ctx.guild.voice_channels,id=ctx.author.voice.channel.id)

      if not self.is_connected:
        await self.connect(ctx,self.voice_channel.id)

      if not self.is_playing:
        await self.play(track)
        await ctx.reply(embed=embed(
            title='Now playing: **{}**'.format(track.title),
            url=track.uri,
            description=f"Connected to `{ctx.bot.get_channel(self.channel_id)}` and bound to {self.text_channel.mention}",
            color=MessageColors.MUSIC,
            thumbnail=thumbnail,
            fieldstitle=["Duration","Total songs in queue"],
            fieldsval=[duration,songsinqueue]
          ),delete_after=await get_delete_time(ctx)
        )
        
      elif self.is_playing:
        if hasattr(tracks,"tracks") and len(tracks.tracks) > 1:
          await ctx.reply(embed=embed(title=f"Added `{len(tracks.tracks)}` songs to queue",color=MessageColors.MUSIC))
        else:
          await ctx.reply(embed=embed(title=f"Added to queue: **{track.title if track is not None else tracks[0].title}**",color=MessageColors.MUSIC))

        # await self.play(songqueue[serverQueueId][0]["track"])

    async def choose_track(self,ctx,tracks):
      def _check(r,u):
        return (
          r.emoji in SEARCHOPTIONS.keys()
          and u == ctx.author
          and r.message.id == msg.id
        )

      msg = await ctx.reply(embed=embed(
        "Choose a song",
        description=(
          "\n".join(
            f"`{i+1}.` {t.title} ({t.length//60000}:{str(t.length%60).zfill(2)})"
            for i,t in enumerate(tracks[:8])
          )
        ),
        color=MessageColors.MUSIC
      ))
      for emoji in list(SEARCHOPTIONS.keys())[:min(len(tracks),len(SEARCHOPTIONS))]:
        await msg.add_reaction(emoji)

      try:
        reaction, _ = await self.bot.wait_for("reaction_add",timeout=60.0,check=_check)
      except asyncio.TimeoutError:
        try:
          await asyncio.gather(
            msg.delete(),
            ctx.message.delete()
          )
        except discord.NotFound:
          pass
      else:
        try:
          await msg.delete()
        except discord.NotFound:
          pass
        return tracks[SEARCHOPTIONS[reaction.emoji]]
      

    async def reconnect(self):
      global songqueue
      if str(self.guild_id) not in songqueue or len(songqueue[str(self.guild_id)]) == 0:
        raise commands.CommandInvokeError("No songs to resume from")
      new_node = self.bot.wavelink.get_best_node()
      if new_node is None or new_node.identifier == self.node.identifier:
        raise commands.CommandInvokeError("All nodes are down")
      await self.change_node(new_node.identifier)
      await self.play(songqueue[str(self.guild_id)][0])
      await self.seek(self.last_position)
      await self.voice_channel.guild.change_voice_state(channel=self.voice_channel,self_mute=False,self_deaf=True)

    async def advance(self):
      global songqueue
      serverQueueId = "{}".format(self.guild_id)
      songqueue[serverQueueId].pop(0)
      if len(songqueue[serverQueueId]) > 0:
        new_node = self.bot.wavelink.get_best_node()
        if new_node.identifier != self.node.identifier:
          await self.change_node(new_node.identifier)
        await self.play(songqueue[serverQueueId][0]["track"])
        if self.text_channel is not None:
          try:
            duration = str(datetime.timedelta(milliseconds=int(songqueue[serverQueueId][0]["track"].duration)))
          except KeyError:
            duration = "??:??:??"
            
          songsinqueue = len(songqueue[serverQueueId])
          await self.text_channel.send(
            embed=embed(
              title='Now playing: **{}**'.format(songqueue[serverQueueId][0]["track"].title),
              url=songqueue[serverQueueId][0]["track"].uri,
              color=MessageColors.MUSIC,
              thumbnail=songqueue[serverQueueId][0]["track"].thumb,
              fieldstitle=["Duration","Total songs in queue"],
              fieldsval=[duration,songsinqueue]
            )
          )
      else:
        delete = await get_delete_time(guild_id=self.guild_id)
        await asyncio.gather(
          self.destroy(force=True),
          self.text_channel.send(embed=embed(title="Finished the queue",color=MessageColors.MUSIC),delete_after=delete) if self.text_channel is not None else None
        )

  class Menu(MenuPages):
    async def send_initial_message(self,ctx,channel):
      page = await self._source.get_page(0)
      kwargs = await self._get_kwargs_from_page(page)
      return await ctx.reply(**kwargs)

  class QueueMenu(ListPageSource):
    def __init__(self,ctx,data,player=None):
      self.ctx = ctx
      self.player = player
      super().__init__(data,per_page=10)

    async def write_page(self,menu,fields=[]):
      offset = (menu.current_page*self.per_page) + 1
      len_data = len(self.entries)

      fieldstitles = []
      fieldsvals = []
      fieldsin = []
      for name,value in fields:
        fieldstitles.append(name)
        fieldsvals.append(value)
        fieldsin.append(False)

      reply = embed(
        title=f"Queue for {self.ctx.guild.name}",
        description=f"Currently Playing: `1.`[{self.player.current.title}]({self.player.current.uri})\n`{datetime.timedelta(milliseconds=self.player.position)}` - `{datetime.timedelta(milliseconds=self.player.current.duration)}`" if offset == 1 else None,
        color=MessageColors.MUSIC,
        fieldstitle=fieldstitles[1:] if offset == 1 else fieldstitles,
        fieldsval=fieldsvals[1:] if offset == 1 else fieldsvals,
        fieldsin=fieldsin[1:] if offset == 1 else fieldsin,
        footer=f"{offset:,} - {min(len_data, offset+self.per_page-1):,} of {len_data:,} songs."
      )
      return reply

    async def format_page(self,menu,entries):
      offset = (menu.current_page*self.per_page) + 1
      # len_data = len(self.entries)
      fields = []
      x = 0
      for entry in entries:
        fields.append((f"`{offset+x}.` Requested by: {entry['requested'].name}",f"[{entry['track'].title}]({entry['track'].uri}) `{str(datetime.timedelta(milliseconds=entry['track'].duration)).split('.')[0]}`"))
        x = x + 1

      return await self.write_page(menu,fields)
      
  async def tryagain(self,ctx):
    await ctx.reply(embed=embed(title="Something went wrong, please try again later",color=MessageColors.ERROR))

  @wavelink.WavelinkMixin.listener()
  async def on_node_ready(self,node):
    await self.bot.wait_until_ready()
    global songqueue
    await relay_info(f"Wavelink node `{node.identifier}` ready.",self.bot,channel=808594696904769546,logger=logger)
    if len(node.players) <= 0:
      return
    new_node = self.bot.wavelink.get_best_node()
    if new_node is None:
      await relay_info(f"Some how the node `{node.identifier}` has died right after ready",self.bot,channel=713270561840824361)
      return
    for player in node.players.values():
      await player.reconnect()
      # await player.change_node(new_node.identifier)
      # await player.connect(channel=player.channel_id)
      # await player.play(songqueue[str(player.guild_id)][0])
      # await player.seek(player.position)

  @wavelink.WavelinkMixin.listener()
  async def on_websocket_closed(self,node,payload):
    string = f"Websocket Closed `{node.identifier}` - {payload.code} - {payload.reason}"
    print(string)
    logger.warning(string)

  @tasks.loop(seconds=1)
  async def start_nodes(self):
    await self.bot.wait_until_ready()

    nodes = {
      "USEAST": {
        "host": os.getenv("LAVALINKUSEASTHOST"),
        "port": os.getenv("LAVALINKUSEASTPORT"),
        "rest_uri": os.getenv("LAVALINKUSEASTREST"),
        "password": os.getenv("LAVALINKUSEASTPASS"),
        "identifier": "USEAST",
        "region": "us_east",
      },
      "USCENTRAL": {
        "host": os.getenv("LAVALINKUSCENTRALHOST"),
        "port": os.getenv("LAVALINKUSCENTRALPORT"),
        "rest_uri": os.getenv("LAVALINKUSCENTRALREST"),
        "password": os.getenv("LAVALINKUSCENTRALPASS"),
        "identifier": "USCENTRAL",
        "region": "us_central",
      }
    }

    if self.bot.wavelink.nodes:
      previous = self.bot.wavelink.nodes.copy()
      difference = list(set(nodes).symmetric_difference(set(previous)))
      if len(previous) > len(nodes):
        for diff in difference:
          try:
            await self.bot.wavelink.destroy_node(identifier=str(diff))
          except:
            raise
          else:
            print(f"Removed `{diff}` from the nodes")
            logger.warning(f"Removed `{diff}` from the nodes")
      elif len(previous) < len(nodes):
        for diff in difference:
          try:
            await self.bot.wavelink.initiate_node(**nodes[diff])
          except:
            raise
          else:
            print(f"Added `{diff}` to nodes")
            logger.info(f"Added `{diff}` to nodes")
    else:
      to_launch = []
      for node in nodes.values():
        to_launch.append(self.bot.wavelink.initiate_node(**node))
      await asyncio.gather(*to_launch)

  def cog_unload(self):
    self.fucking_check_for_dead_nodes.cancel()
    self.start_nodes.cancel()
    
  @tasks.loop(seconds=0.1)
  async def fucking_check_for_dead_nodes(self):
    global songqueue
    global dead_nodes_sent
    if self.bot.wavelink.nodes:
      current = self.bot.wavelink.nodes
      for node in current.values():
        if node.is_available == False:
          node.close()
          node.open()
        for player in node.players.values():
          if player.last_position == 0 and len(songqueue[str(player.guild_id)]) > 0:
            await player.connect(channel=player.channel_id)
        if not node.is_available == True and len(node.players) > 0 and dead_nodes_sent == False:
          await relay_info(f"Something happened to `{node.identifier}`",self.bot,channel=713270561840824361)
          players = node.players.copy()
          new_node = self.bot.wavelink.get_best_node()
          print(new_node)
          for player in players.values():
            if new_node is None:
              await relay_info("I think all Lavalink nodes have stoped",self.bot,channel=713270561840824361)
              if player.text_channel is not None:
                await player.text_channel.send(embed=embed(title="Something has gone wrong on the server side, I will re-try connecting again in a bit.",color=MessageColors.ERROR)) if player.text_channel is not None else None
              dead_nodes_sent = True
              return
            await player.change_node(new_node.identifier)
            if str(player.guild_id) in songqueue and len(songqueue[str(player.guild_id)]) == 0:
              print("no songs in queue to resume")
              logger.info("no songs in queue to resume")
              return await player.destroy(force=True)
            if str(player.guild_id) in songqueue and len(songqueue[str(player.guild_id)]) > 0:
              await player.reconnect()
              # position = player.position
              # await player.connect(channel=player.channel_id)
              # await asyncio.sleep(0.5)
              # await player.set_pause(True)
              # await asyncio.sleep(0.5)
              # guild = self.bot.get_guild(player.guild_id)
              # await asyncio.gather(
              #   player.set_pause(False),
              #   player.play(songqueue[str(player.guild_id)][0]),
              #   player.seek(position),
              #   guild.change_voice_state(channel=guild.get_channel(player.channel_id),self_mute=False,self_deaf=True)
              # )
              
  @wavelink.WavelinkMixin.listener("on_track_end")
  async def on_player_stop(self,node,payload):
    print("Next song")
    logger.debug("Next song")
    await payload.player.advance()

  @wavelink.WavelinkMixin.listener("on_track_stuck")
  async def on_track_stuck(self,node,payload):
    print("track stuck")
    logger.warning("track stuck")

  # @wavelink.WavelinkMixin.listener()
  # async def on_track_exception(self,node,payload):
  #   if payload.error == 'The track was unexpectedly terminated.':
  #     new_node = self.bot.wavelink.get_best_node()
  #     for player in node.players.values():
  #       print(player)
  #       # if player.node != new_node:
  #       await player.change_node(new_node.identifier)
  #       print(f"Player moved to node `{new_node.identifier}`")
  #       logger.info(f"Player moved to node `{new_node.identifier}`")
  #       # else:
  #       #   print(f"No need to move to node `{new_node.identifier}`")
  #       #   logger.info(f"No need to move to node `{new_node.identifier}`")
  #   else:
  #     print("Exception: ",payload.error)
  #     logger.error(f"Exception: {payload.error}")
      
  @wavelink.WavelinkMixin.listener()
  async def on_track_exception(self,node,payload):
    print("Exception")
    await payload.player.reconnect()

  @wavelink.WavelinkMixin.listener()
  async def on_wavelink_error(self,error):
    if isinstance(error,wavelink.ZeroConnectedNodes):
      print("No connected Lavalink nodes")
      logger.warning("No connected Lavalink nodes")
    else:
      print(error)
      logger.error(error)

  async def cog_before_invoke(self,ctx):
    if self.bot.intents.members and ctx.guild.chunked != True:
      await ctx.guild.chunk(cache=False)

  def get_player(self,obj):
    if isinstance(obj,commands.Context):
      return self.bot.wavelink.get_player(obj.guild.id, cls=self.LavaPlayer,context=obj)
    elif isinstance(obj,discord.Guild):
      return self.bot.wavelink.get_player(obj.id, cls=self.LavaPlayer)
    else:
      return None

  @commands.command(name="join",aliases=["connect","summon"])
  @commands.guild_only()
  @commands.check(can_play)
  async def connect(self,ctx):
    global songqueue
    voicechannel = ctx.author.voice.channel

    try:
      player = self.get_player(ctx)
      await player.connect(ctx,voicechannel.id)
    except:
      raise
    else:
      await ctx.reply(embed=embed(title=f"Joined `{voicechannel}`",color=MessageColors.MUSIC))

  @commands.command(name="play",aliases=['p','add'],usage="<Song url/Song title>",description="Follow this command with the title of a song to search for it or just paste the Youtube/SoundCloud url if the search gives and undesirable result")
  @commands.guild_only()
  @commands.check(can_play)
  @commands.max_concurrency(1,commands.BucketType.channel,wait=True)
  async def play(self,ctx, *, url: str):
    url = url.strip("<>")
    global songqueue
    try:
      player = self.get_player(ctx)
      # best_node = self.bot.wavelink.get_best_node()
      if player.node is None:
        await ctx.reply(embed=embed(title=f"There are no availble nodes to play from, please try again later",color=MessageColors.ERROR))
        return
      # if player.node.identifier != best_node.identifier:
      #   await player.change_node(best_node.identifier)
      # if ctx.author.voice is None and not player.is_connected:
      #   await ctx.reply(embed=embed(title="You must be in a voice channel to play music.",color=MessageColors.MUSIC))
      #   return

      if "open.spotify.com" in ctx.message.content.lower() or "spotify:track:" in ctx.message.content.lower():
        return await ctx.reply(embed=embed(title="At the moment Spotify links are not supported.",color=MessageColors.ERROR))

      # voiceChannel = discord.utils.get(ctx.guild.voice_channels,id=ctx.author.voice.channel.id)

      async with ctx.typing():
        try:
          # if not player.text_channel:
          #   player.text_channel = ctx.channel          

          # if not player.is_connected:
          #   await player.connect(ctx,voiceChannel.id)
          #   await ctx.guild.change_voice_state(channel=voiceChannel,self_mute=False,self_deaf=True)

          valid = validators.url(url)
          if not valid:
            url = f"ytsearch:{url}"
          await player.add_tracks(ctx,await self.bot.wavelink.get_tracks(url))
        except BaseException as e:
          try:
            # e = "".join(f"{e}".split("ERROR: "))
            e = f"{e}".strip("ERROR: ")
          except:
            pass
          await ctx.reply(embed=embed(title=f"{e}",color=MessageColors.ERROR))
          raise
    except wavelink.ZeroConnectedNodes:
      await ctx.reply(embed=embed(title=f"Failed to get a node to play from, please try again later",color=MessageColors.ERROR))

  # @play.error
  # async def error_play(self,ctx,error):
  #   if isinstance(error,ConnectionResetError):
  #     print("fuck")
  #   elif isinstance(error,wavelink.errors.ZeroConnectedNodes):
  #   else:
  #     raise

  @commands.command(name="search",description="Search for songs from YouTube. To search with soundcloud user the `soundcloud` command")
  @commands.guild_only()
  @commands.check(can_play)
  async def search(self,ctx,*,query:str):
    query = query.strip("<>")
    if validators.url(query):
      return await ctx.invoke(self.play,url=query)
    player = self.get_player(ctx)
    tracks = await self.bot.wavelink.get_tracks(f"ytsearch:{query}")
    track = await player.choose_track(ctx,tracks)
    await player.add_tracks(ctx,track)

  @commands.command(name="soundcloud",description="Search for songs through Soundcloud instead of YouTube")
  @commands.guild_only()
  @commands.check(can_play)
  async def soundcloud_search(self,ctx,*,query:str):
    query = query.strip("<>")
    if validators.url(query):
      return await ctx.invoke(self.play,url=query)
    player = self.get_player(ctx)
    tracks = await self.bot.wavelink.get_tracks(f"scsearch:{query}")
    track = await player.choose_track(ctx,tracks)
    await player.add_tracks(ctx,track)

  @commands.command(name="node")
  async def node(self,ctx):
    player = self.get_player(ctx)
    await ctx.reply(embed=embed(title=f"Node - {player.node.identifier}",description=f"Region: {player.node.region}\nPlayers: {len(player.node.players)}\nIs available: {player.node.is_available}",color=MessageColors.MUSIC))

  @commands.command(name="nodes")
  async def nodes(self,ctx):
    if self.bot.wavelink.nodes:
      current = self.bot.wavelink.nodes.copy()
      title = []
      descriptions = []
      for node in current.values():
        title.append(node.identifier)
        descriptions.append(f"Region: {node.region}\nPlayers: {len(node.players)}\nIs available: {node.is_available}")
      await ctx.reply(embed=embed(title="Nodes",fieldstitle=[*title],fieldsval=[*descriptions],color=MessageColors.MUSIC))
    else:
      await ctx.reply(embed=embed(title="Failed to get information on the available nodes",color=MessageColors.ERROR))

  @commands.command(name="seek",description="Accepted time formats are 1h20m30s, 20m30s, 30(s)")
  @commands.guild_only()
  @commands.check(can_play)
  async def seek(self,ctx,time:str):
    time = time.lower()
    if "h" not in time and "m" not in time:
      await cmd_help(ctx,ctx.command,"That time is not supported")
      return
    global songqueue
    player = self.get_player(ctx)
    if player.is_connected:
      try:
        hours = time.split("h")
        minutes = hours[1].split("m") if len(hours) > 1 else hours[0].split("m")
        seconds = minutes[1].split("s") if len(minutes) > 1 else minutes[0].split("s")
        hours = int(hours[0]) if hours[0] != "" and len(hours) > 1 else 0
        minutes = int(minutes[0]) if minutes[0] != "" and len(minutes) > 1 else 0
        seconds = int(seconds[0]) if seconds[0] != "" and len(seconds) > 1 else 0
        seek = datetime.timedelta(hours=hours,minutes=minutes,seconds=seconds)
        milliseconds = seek.seconds*1000
        if player.current.duration < milliseconds:
          reply = dict(embed=embed(title="Please choose a time within the duration of the current track",color=MessageColors.ERROR))
          await ctx.reply(**reply)
          return
        await player.seek(milliseconds)
      except BaseException as e:
        await cmd_help(ctx,ctx.command,"Something has gone wrong with the time format you gave")
        print(e)
        logger.error(e)
      else:
        reply = dict(embed=embed(title=f"Playing from {seek}",color=MessageColors.MUSIC))
        await ctx.reply(**reply)
    else:
      reply = dict(embed=embed(title="I am not connected to a voice channel",color=MessageColors.MUSIC))
      await ctx.reply(**reply)

  @commands.command(name="stop",aliases=["leave","disconnect"])
  @commands.guild_only()
  async def stop(self,ctx):
    global songqueue
    try:
      player = self.get_player(ctx)
      if player.is_connected:
        try:
          async with ctx.typing():
            if str(ctx.guild.id) in songqueue and len(songqueue["{}".format(ctx.guild.id)]) > 0:
              del songqueue["{}".format(ctx.guild.id)]
            await player.destroy()
        except:
          raise
        else:
          await ctx.reply(embed=embed(title="Finished",color=MessageColors.MUSIC))
      else:
        await ctx.reply(embed=embed(title="I am not connected to a voice channel",color=MessageColors.MUSIC))
    except:
      # await self.tryagain(ctx)
      raise

  @commands.command(name="skip")
  @commands.guild_only()
  @commands.check(can_play)
  async def skip(self,ctx,num_tracks:int=1):
    global songqueue
    player = self.get_player(ctx)
    for i in range(num_tracks-1):
      songqueue[str(ctx.guild.id)].pop(i)
    await player.stop()

  @commands.command(name="del",aliases=["delete","remove"])
  @commands.guild_only()
  async def delete(self,ctx,index:int):
    global songqueue
    index = index - 1
    song = songqueue[str(ctx.guild.id)][index]["track"]
    try:
      songqueue[str(ctx.guild.id)].pop(index)
    except:
      raise
    else:
      reply = dict(embed=embed(title=f"Removed [{index+1}]`{song.title}` from the queue"))
      await ctx.reply(**reply)


  @commands.command(name="shuffle")
  @commands.guild_only()
  @commands.check(can_play)
  async def shuffle(self,ctx):
    global songqueue
    upcoming = songqueue[str(ctx.guild.id)][1:]
    random.shuffle(upcoming)
    songqueue[str(ctx.guild.id)] = songqueue[str(ctx.guild.id)][:1]
    songqueue[str(ctx.guild.id)].extend(upcoming)
    await ctx.reply(embed=embed(title="The queue has been shuffled",color=MessageColors.MUSIC))

  # TODO: Check for queue length so discord message is less than max message character count
  @commands.command(name="queue")
  @commands.guild_only()
  @commands.bot_has_permissions(add_reactions=True)
  async def queue(self,ctx):
    global songqueue
    if len(songqueue) > 0 and len(songqueue[str(ctx.guild.id)]) > 0:
      delay = await get_delete_time(ctx)
      menu = self.Menu(
        source=self.QueueMenu(ctx,songqueue[str(ctx.guild.id)],self.get_player(ctx)),
        delete_message_after=True,
        clear_reactions_after=True,
        timeout=delay
      )
      await menu.start(ctx)
    else:
      await ctx.reply(embed=embed(title="Nothing is playing right now"))

  @commands.command(name="pause")
  @commands.guild_only()
  @commands.check(can_play)
  async def pause(self,ctx):
    player = self.get_player(ctx)
    if player is not None and player.is_paused:
      await ctx.reply(embed=embed(title="I have already been paused",color=MessageColors.MUSIC))
    elif player is not None and player.is_playing: 
      await player.set_pause(True)
      await ctx.reply(embed=embed(title="Paused",color=MessageColors.MUSIC))
    else:
      await ctx.reply(embed=embed(title="Failed to pause",color=MessageColors.ERROR))

  @commands.command(name="resume")
  @commands.guild_only()
  @commands.check(can_play)
  async def resume(self,ctx):
    player = self.get_player(ctx)
    if player is not None and not player.is_connected:
      await player.reconnect()
    if player is not None and player.is_paused:
      await player.set_pause(False)
      await ctx.reply(embed=embed(title="Resumed",color=MessageColors.MUSIC))
    elif player is not None and player.is_playing: 
      await ctx.reply(embed=embed(title="I was never paused",color=MessageColors.MUSIC))
    else:
      await ctx.reply(embed=embed(title="Failed to resume",color=MessageColors.ERROR))

  # @commands.command(name="listen",hidden=True)
  # @commands.is_owner()
  # @commands.guild_only()
  # async def listen(self,ctx):
  #   # TODO: the title from spotify doesn't always play the correct song
  #   # TODO: won't keep up if the user skips the current song
  #   # await ctx.guild.chunk(cache=False)
  #   if await self.can_play(ctx) == True:
  #     return
  #   toplay = ctx.author.activities or None
  #   if toplay is not None:
  #     for act in toplay:
  #       if isinstance(act,discord.Spotify):
  #         toplay = act or None
  #   else:
  #     return
  #   voice = discord.utils.get(self.bot.voice_clients,guild=ctx.guild)
  #   try:
  #     await ctx.author.voice.channel.connect(reconnect=False)
  #     await ctx.guild.change_voice_state(channel=ctx.author.voice.channel,self_mute=False,self_deaf=True)
  #   except:
  #     pass

  #   try:
  #     now = datetime.datetime.now(datetime.timezone.utc)
  #     start = toplay.start
  #     now = now.replace(tzinfo=None)
  #     currentplay = (now - start)
  #     secs = currentplay.seconds
  #     player = await YTDLSource.from_url(f"{toplay.title} {toplay.artist}", loop=self.bot.loop, stream=True,start=secs)
  #     # player = await YTDLSource.from_url(f"spotify:track:{toplay.track_id}", loop=self.bot.loop, stream=True,start=secs)
  #     # ctx.voice_client.play(player)
  #     ctx.voice_client.play(player,after=lambda e: asyncio.run_coroutine_threadsafe(self.listen(ctx),self.bot.loop))
  #     duration = toplay.duration - datetime.timedelta(microseconds=toplay.duration.microseconds)
  #     await ctx.channel.send(
  #       embed=embed(
  #         title=f'Now playing: **{player.title}**',
  #         color=MessageColors.MUSIC,
  #         thumbnail=player.data['thumbnails'][0]['url'],
  #         # fieldstitle=["Started at","Duration"],
  #         # fieldsval=[secs,duration]
  #         fieldstitle=["Duration"],
  #         fieldsval=[duration]
  #       )
  #     )
  #   except BaseException as e:
  #     print(e)
  #     if "Already playing audio." in str(e):
  #       await ctx.channel.send(embed=embed(title=f"I'm unable to listen along with you because I am already listening along with someone else",color=MessageColors.ERROR))
  #   # else:
  #   #   while voice.is_playing():
  #   #     print()

  @commands.Cog.listener()
  async def on_voice_state_update(self,member,before,after):
    global songqueue
    # TODO: when moved to another voice channel, Friday will some times just stop playing music until !pause and !resume are executed
    try:
      player = self.get_player(member.guild)
      if member == self.bot.user:
        try:
          if after.channel == None and len(songqueue["{}".format(member.guild.id)]) > 0:
            try:
              await player.text_channel.send(embed=embed(title="Finished",color=MessageColors.MUSIC))
            except discord.Forbidden:
              pass
            del songqueue["{}".format(member.guild.id)]
            await player.destroy()
            # print("{} queue cleared".format(member.guild.id))
        except KeyError:
          pass

        # if after.channel != None and player.is_playing:
        #   await asyncio.sleep(1)
        #   await player.set_pause(True)
        #   await asyncio.sleep(0.3)
        #   await player.set_pause(False)

      if before.channel is None:
        return
      if self.bot.user not in before.channel.members:
        return

      try:
        await asyncio.sleep(3)
        if len(self.bot.get_channel(player.channel_id).members) == 1:
          await player.destroy()
          del songqueue["{}".format(member.guild.id)] 
      except KeyError:
        pass
      except AttributeError:
        pass
    except wavelink.ZeroConnectedNodes:
      pass

def setup(bot):
  global logger
  logger = logging.getLogger(__name__)
  bot.add_cog(Music(bot))
