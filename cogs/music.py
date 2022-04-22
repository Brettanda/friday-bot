import asyncio
import collections
import datetime
import functools
import itertools
import json
import math
import os
import re
from typing import List, Literal, Optional, Union

import async_timeout
import discord
import validators
import wavelink
from wavelink.ext import spotify
from discord.ext import commands, menus
from numpy import random

from functions import (MessageColors, MyContext, checks, config, embed, time,
                       exceptions, paginator)

MISSING = discord.utils.MISSING
URL_REG = re.compile(r'https?://(?:www\.)?.+')
VoiceChannel = Union[
    discord.VoiceChannel, discord.StageChannel
]


def can_play():
  async def predicate(ctx: MyContext) -> bool:
    player = ctx.cog.get_player(ctx.guild, ctx=ctx)

    if player is None:
      return True

    if hasattr(player, "text_channel") and player.text_channel and player.text_channel != ctx.channel:
      raise IncorrectChannelError(f"You must be in `{player.ctx.channel}` for this session.")
    if ctx.command.name == "connect" and (not hasattr(player, "ctx") or not player.ctx):
      return True
    elif ctx.cog.is_privileged(ctx):
      return True

    if not player.channel or not player.channel.id:
      raise IncorrectChannelError("Failed to load the channel to play music.")

    if player.is_connected():
      if ctx.author not in player.channel.members:
        raise IncorrectChannelError(f"You must be in `{player.channel}` to use voice commands.")

    return True
  return commands.check(predicate)


class NothingPlaying(exceptions.Base):
  def __init__(self, message: str = "Nothing is playing right now."):
    super().__init__(message=message)


class NoChannelProvided(exceptions.Base):
  def __init__(self, message="You must be in a voice channel or provide one to connect to."):
    super().__init__(message=message)


class IncorrectChannelError(exceptions.Base):
  def __init__(self, message="You must be in the same voice channel as the bot."):
    super().__init__(message=message)


class NoCustomSoundsFound(exceptions.Base):
  def __init__(self, message="There are no custom sounds for this server (yet)"):
    super().__init__(message=message)


class VoiceConnectionError(exceptions.Base):
  def __init__(self, message="An error occured while connecting to a voice channel."):
    super().__init__(message=message)


class Equalizer:
  def __init__(self, *, levels: list, name: str = 'CustomEqualizer'):
    self.eq = self._factory(levels)
    self.raw = levels

    self._name = name

  def __str__(self):
    return self._name

  def __repr__(self):
    return f'<cogs.music.Equalizer: {self._name}, Raw: {self.eq}>'

  @property
  def name(self):
    return self._name

  @classmethod
  def options(cls) -> [str]:
    return ["flat", "boost", "metal", "piano"]

  @classmethod
  def lit_options(cls) -> [str]:
    return Literal["flat", "boost", "metal", "piano"]

  @staticmethod
  def _factory(levels: list):
    _dict = collections.defaultdict(int)

    _dict.update(levels)
    _dict = [{"band": i, "gain": _dict[i]} for i in range(15)]

    return _dict

  @classmethod
  def build(cls, *, levels: list, name: str = 'CustomEqualizer'):
    return cls(levels=levels, name=name)

  @classmethod
  def flat(cls):
    levels = [(0, .0), (1, .0), (2, .0), (3, .0), (4, .0),
              (5, .0), (6, .0), (7, .0), (8, .0), (9, .0),
              (10, .0), (11, .0), (12, .0), (13, .0), (14, .0)]

    return cls(levels=levels, name='Flat')

  @classmethod
  def boost(cls):
    levels = [(0, -0.075), (1, .125), (2, .125), (3, .1), (4, .1),
              (5, .05), (6, 0.075), (7, .0), (8, .0), (9, .0),
              (10, .0), (11, .0), (12, .125), (13, .15), (14, .05)]

    return cls(levels=levels, name='Boost')

  @classmethod
  def metal(cls):
    levels = [(0, .0), (1, .1), (2, .1), (3, .15), (4, .13),
              (5, .1), (6, .0), (7, .125), (8, .175), (9, .175),
              (10, .125), (11, .125), (12, .1), (13, .075), (14, .0)]

    return cls(levels=levels, name='Metal')

  @classmethod
  def piano(cls):
    levels = [(0, -0.25), (1, -0.25), (2, -0.125), (3, 0.0),
              (4, 0.25), (5, 0.25), (6, 0.0), (7, -0.25), (8, -0.25),
              (9, 0.0), (10, 0.0), (11, 0.5), (12, 0.25), (13, -0.025)]

    return cls(levels=levels, name='Piano')


class Track(wavelink.YouTubeTrack):
  __slots__ = ("requester", )

  def __init__(self, *args, **kwargs):
    super().__init__(*args)
    self.requester = kwargs.get("requester", None)


class Player(wavelink.Player):
  def __call__(self, client: MISSING, channel: VoiceChannel = MISSING, *, ctx: MyContext = MISSING):
    self = super().__call__(client, channel)
    self.ctx: MyContext = self.ctx if hasattr(self, "ctx") else ctx
    self.text_channel: discord.TextChannel = self.text_channel if hasattr(self, "text_channel") else self.ctx.channel if self.ctx else None
    self.dj = self.dj if hasattr(self, "dj") else self.ctx.author if self.ctx else None

    self.volume = self.volume if hasattr(self, "volume") else 100

    self._equalizer = Equalizer.flat()
    self.waiting = self.waiting if hasattr(self, "waiting") else False
    self.queue = self.queue if hasattr(self, "queue") else wavelink.WaitQueue(max_size=500, history_max_size=500)

    self.pause_votes = self.pause_votes if hasattr(self, "pause_votes") else set()
    self.resume_votes = self.resume_votes if hasattr(self, "resume_votes") else set()
    self.skip_votes = self.skip_votes if hasattr(self, "skip_votes") else set()
    self.shuffle_votes = self.shuffle_votes if hasattr(self, "shuffle_votes") else set()
    # queue position: votes
    self.remove_votes = self.remove_votes if hasattr(self, "remove_votes") else collections.defaultdict(lambda: set())
    self.stop_votes = self.stop_votes if hasattr(self, "stop_votes") else set()
    return self

  def __init__(self, client=MISSING, channel: VoiceChannel = MISSING, *args, **kwargs):
    # if len(args) > 2 and isinstance(args[1], tuple) and isinstance(args[1][0], self.__class__):
    #   client = args[1][0].client
    #   channel = args[1][0].channel
    # else:
    #   client = kwargs.get("client", discord.utils.MISSING)
    #   channel = kwargs.get("channel", discord.utils.MISSING)
    super().__init__(client, channel)
    if len(args) > 2 and isinstance(args[1], tuple) and isinstance(args[1][0], self.__class__):
      self = args[1][0]

    self._connected = self._connected if hasattr(self, "_connected") else False

    self.bot = self.client
    self.ctx: MyContext = self.ctx if hasattr(self, "ctx") else kwargs.get("ctx")
    self.text_channel = self.text_channel if hasattr(self, "text_channel") else self.ctx.channel
    self.dj: Optional[discord.Member] = self.dj if hasattr(self, "dj") else self.ctx.author if self.ctx else None

    self._equalizer = Equalizer.flat()
    self.waiting = self.waiting if hasattr(self, "waiting") else False

    self.pause_votes = self.pause_votes if hasattr(self, "pause_votes") else set()
    self.resume_votes = self.resume_votes if hasattr(self, "resume_votes") else set()
    self.skip_votes = self.skip_votes if hasattr(self, "skip_votes") else set()
    self.shuffle_votes = self.shuffle_votes if hasattr(self, "shuffle_votes") else set()
    # queue position: votes
    self.remove_votes = self.remove_votes if hasattr(self, "remove_votes") else collections.defaultdict(lambda: set())
    self.stop_votes = self.stop_votes if hasattr(self, "stop_votes") else set()

  @property
  def equalizer(self):
    return self._equalizer

  eq = equalizer

  @property
  def queue_duration(self) -> float:
    return sum(track.length for track in [self.track, *self.queue._queue])

  def duration_to_track(self, track: Track) -> str:
    total = sum(t.length for t in [self.track, *list(itertools.islice(self.queue._queue, 0, self.queue._queue.index(track)))])
    retry_after = discord.utils.utcnow() + datetime.timedelta(seconds=total)
    return time.human_timedelta(retry_after)

  async def set_equalizer(self, eq: Equalizer):
    await self.node._websocket.send(op='equalizer', guildId=str(self.guild.id), bands=eq.eq)
    self._equalizer = eq

  set_eq = set_equalizer

  def is_connected(self):
    if hasattr(self, "_connected"):
      return self._connected
    return False

  async def connect(self, *, ctx: MyContext = None, timeout: float = 60.0, reconnect: bool = True, self_deaf: bool = True, self_mute: bool = False) -> Union[discord.VoiceChannel, discord.StageChannel]:
    if not self.guild:
      raise wavelink.errors.InvalidIDProvided(f'No guild found for id <{self.guild.id}>')
    await self.guild.change_voice_state(channel=self.channel, self_deaf=self_deaf, self_mute=self_mute)
    self._connected = True

    return self.channel

  async def do_next(self, *, force: bool = False):
    if not force and (self.is_playing() or self.waiting):
      return

    self.pause_votes.clear()
    self.resume_votes.clear()
    self.skip_votes.clear()
    self.shuffle_votes.clear()
    self.remove_votes.clear()
    self.stop_votes.clear()

    try:
      self.waiting = True
      self._source = None
      with async_timeout.timeout(60):
        track = await self.queue.get_wait()
    except asyncio.TimeoutError:
      # No music has been played for 1 minute, cleanup and disconnect...
      return await self.teardown()

    # if isinstance(track, wavelink.PartialTrack):
    #   track = await self.node.build_track(cls=Track, identifier=track.id)

    track = await self.play(track)
    track.requester = self.ctx.author

    channel = self.channel
    if channel and channel.type == discord.ChannelType.stage_voice and not channel.instance:
      await channel.create_instance(topic=track.title, reason="Music time!")
    elif channel and channel.type == discord.ChannelType.stage_voice and channel.instance is not None and self.current_title and channel.instance.topic == self.current_title:
      await channel.instance.edit(topic=track.title, reason="Next track!")

    self._source = track
    self.waiting = False

    await self.ctx.reply(embed=self.build_embed())

  def build_embed(self) -> Optional[discord.Embed]:
    if not self.source:
      raise NothingPlaying()

    qsize = self.queue.count

    try:
      duration = str(datetime.timedelta(seconds=int(self.source.length)))
    except (OverflowError, AttributeError):
      duration = "??:??:??"

    return embed(
        title=f"Now playing: **{self.track.title}**",
        thumbnail=getattr(self.source, "thumbnail", MISSING),
        url=self.source.uri,
        fieldstitle=["Duration", "Queue Length", "Volume", "Requested By", "DJ", "Channel"],
        fieldsval=[duration, str(qsize), f"**`{self.volume}%`**", f"{self.source.requester.mention}", f"{self.dj.mention if self.dj else None}", f"{self.channel.mention if self.channel else None}"],
        color=MessageColors.MUSIC)

  async def destroy(self, *, force: bool = False):
    await self.stop()
    try:
      await self.disconnect(force=force)
    except ValueError:
      pass
    await self.node._websocket.send(op='destroy', guildId=str(self.guild.id))
    self._connected = False

  async def teardown(self):
    try:
      self.queue.reset()
      await self.destroy()
      self.cleanup()
    except KeyError:
      pass


NUMTOEMOTES = {
    0: "0️⃣",
    1: "1️⃣",
    2: "2️⃣",
    3: "3️⃣",
    4: "4️⃣",
    5: "5️⃣",
    6: "6️⃣",
    7: "7️⃣",
    8: "8️⃣",
    9: "9️⃣",
    10: "🔟",
}


class PaginatorSource(menus.ListPageSource):
  def __init__(self, entries: List[str], *, per_page: int = 10):
    super().__init__(entries, per_page=per_page)

  async def format_page(self, menu: menus.MenuPages, page: List[str]) -> discord.Embed:
    return embed(
        title="Coming up...",
        description='\n'.join(f'{NUMTOEMOTES[index]} - {title}' for index, title in enumerate(page, 1)),
        color=MessageColors.MUSIC)

  def is_paginating(self) -> bool:
    return True


class Music(commands.Cog):
  """Listen to your favourite music and audio clips with Friday's music commands"""

  def __init__(self, bot):
    self.bot = bot

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  @commands.Cog.listener()
  async def on_ready(self):
    nodes = [
        {
            "bot": self.bot,
            "host": os.environ.get("LAVALINKUSHOST"),
            "port": os.environ.get("LAVALINKUSPORT"),
            "password": os.environ.get("LAVALINKUSPASS"),
            "identifier": "MAIN",
        }
    ]

    spotify_client = spotify.SpotifyClient(
        client_id=os.environ.get("SPOTIFYID"),
        client_secret=os.environ.get("SPOTIFYSECRET"),
    )

    for n in nodes:
      try:
        await wavelink.NodePool.create_node(**n, spotify_client=spotify_client)
      except wavelink.NodeOccupied:
        pass

  def cog_check(self, ctx: MyContext) -> bool:
    if not ctx.guild:
      raise commands.NoPrivateMessage()

    return True

  def get_player(self, guild: discord.Guild, *, ctx: Optional[MyContext] = None) -> Optional[Player]:
    player = ctx.voice_client if ctx else None
    if not player:
      node = wavelink.NodePool.get_node()
      player = node.get_player(guild)
    return player

  async def cog_command_error(self, ctx: MyContext, error: Exception):
    error = getattr(error, "original", error)
    wavelink_errors = (wavelink.errors.LoadTrackError, wavelink.errors.WavelinkError, wavelink.errors.LavalinkException, wavelink.errors.NodeOccupied, wavelink.errors.QueueException,)
    if isinstance(error, (IncorrectChannelError, NoChannelProvided, NoCustomSoundsFound, VoiceConnectionError, NothingPlaying, *wavelink_errors)):
      return await ctx.send(embed=embed(title=error, color=MessageColors.ERROR))
    elif isinstance(error, commands.BadLiteralArgument):
      return await ctx.send(embed=embed(title=f"`{error.param.name}` must be one of `{', '.join(error.literals)}.`", color=MessageColors.ERROR))
    elif isinstance(error, (exceptions.RequiredTier, exceptions.NotSupporter, exceptions.NotInSupportServer)):
      return await ctx.send(embed=embed(title=error, color=MessageColors.ERROR))
    else:
      self.bot.logger.error(f"Error in {ctx.command.qualified_name}: {type(error).__name__}: {error}")

  @commands.Cog.listener()
  async def on_wavelink_node_ready(self, node: wavelink.Node):
    self.bot.logger.info(f"Node {node.identifier} is ready!")

  @commands.Cog.listener('on_wavelink_track_stuck')
  @commands.Cog.listener('on_wavelink_track_end')
  async def on_player_stop(self, player: Player, track: Track, *args, **kwargs):
    await player.do_next(force=True)

  @commands.Cog.listener()
  async def on_wavelink_track_exception(self, player: Player, track: Track, error: Exception):
    await player.do_next()
    await self.cog_command_error(player.ctx, error)

  @commands.Cog.listener()
  async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    await self.bot.wait_until_ready()
    # TODO: when moved to another voice channel, Friday will some times just stop playing music until !pause and !resume are executed
    if member == self.bot.user:
      if before.channel and not after.channel:
        player = self.get_player(before.channel.guild)
        if player:
          await player.destroy()
      if before.channel != after.channel and after.channel is not None and after.channel.type == discord.ChannelType.stage_voice:
        await member.edit(suppress=False)

    player = self.get_player(member.guild)
    if player is None:
      return

    if member.bot:
      return

    if not player.channel.id or not player.ctx:
      player.node.players.pop(member.guild.id)
      return

    channel = player.channel

    if member == player.dj and after.channel is None:
      for m in channel.members:
        if m.bot:
          continue
        else:
          player.dj = m
          return
    elif after.channel == channel and player.dj not in channel.members:
      player.dj = member

  def required(self, ctx: MyContext) -> int:
    player = self.get_player(ctx.guild)
    channel = player.channel
    required = math.ceil((len(channel.members) - 1) / 2.5)

    if ctx.command.name == "stop":
      if len(channel.members) == 3:
        required = 2

    return required

  def is_privileged(self, ctx: MyContext) -> bool:
    player = self.get_player(ctx.guild, ctx=ctx)
    if player is None:
      return False

    return player.dj == ctx.author or ctx.author.guild_permissions.kick_members

  async def join(self, ctx: MyContext, channel: Union[VoiceChannel] = None) -> Player:
    player = self.get_player(ctx.guild, ctx=ctx)

    channel = getattr(ctx.author.voice, 'channel', channel) if channel is None else channel
    if channel is None:
      raise NoChannelProvided

    player = Player(client=self.bot, channel=channel, ctx=ctx)
    return ctx.voice_client or await ctx.author.voice.channel.connect(cls=player, self_deaf=True)

  @commands.command(name="connect", aliases=["join"], help="Join a voice channel")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def connect(self, ctx: MyContext, *, channel: Optional[VoiceChannel] = None):
    """Connect to a voice channel."""
    ch = await self.join(ctx, channel)
    if ch.channel:
      return await ctx.send(f"{ch.channel.mention}", embed=embed(title="Connected to voice channel", color=MessageColors.MUSIC))
    return await ctx.send(embed=embed(title="Failed to connect to voice channel.", color=MessageColors.ERROR))

  @commands.command(name="play", aliases=["p", "add"], extras={"examples": ["https://youtu.be/dQw4w9WgXcQ"]}, usage="<url/title>", help="Follow this command with the title of a song to search for it or just paste the Youtube/SoundCloud url if the search gives and undesirable result")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def play(self, ctx: MyContext, *, query: str):
    """Play or queue a song with the given query."""
    player = self.get_player(ctx.guild, ctx=ctx)

    await ctx.trigger_typing()
    if not player:
      player = await self.join(ctx)

    query = query.strip('<>')
    PartTrack = functools.partial(Track)
    spot_link = spotify.decode_url(query)
    tracks = []
    if spot_link:
      if spot_link["type"].name == "playlist":
        async for t in spotify.SpotifyTrack.iterator(query=spot_link["id"], type=spot_link["type"], partial_tracks=True):
          tracks.append(t)
        # self.bot.loop.create_task(self.build_spotify_tracks(spot_link["id"], player=player, _type=spot_link["type"]))
      else:
        tracks = await spotify.SpotifyTrack.search(spot_link["id"], type=spot_link["type"])
        tracks = tracks[:1]
      if not tracks:
        spot_link = None
    if not spot_link:
      try:
        tracks = await player.node.get_tracks(cls=PartTrack, query=query)
      except wavelink.errors.LavalinkException:
        tracks = await player.node.get_playlist(cls=wavelink.abc.Playlist, identifier=query)
      if not tracks:
        tracks = await wavelink.YouTubeTrack.search(query)
        if not tracks:
          return await ctx.send(embed=embed(title='No songs were found with that query. Please try again.', color=MessageColors.ERROR))
        tracks = await player.node.build_track(cls=PartTrack, identifier=tracks[0].id)
        tracks = [tracks]

    if not tracks:
      return await ctx.send(embed=embed(title='No songs were found with that query. Please try again.', color=MessageColors.ERROR))

    tracks[0].requester = ctx.author
    if isinstance(tracks, wavelink.abc.Playlist):
      for track in tracks.data["tracks"]:
        await player.queue.put_wait(Track(track["track"], track["info"], requester=ctx.author))
      if player.is_playing() or player.is_paused():
        await ctx.send(embed=embed(
            title=f"Added the playlist {tracks.data['playlistInfo']['name']}",
            description=f" with {len(tracks.data['tracks'])} songs to the queue.",
            color=MessageColors.MUSIC))
    elif isinstance(tracks, list):
      for track in tracks:
        await player.queue.put_wait(track)
      if player.is_playing() or player.is_paused():
        await ctx.send(embed=embed(
            title=f"Added {tracks[0].title} by {tracks[0].author} to the queue.",
            color=MessageColors.MUSIC))
    else:
      await player.queue.put_wait(tracks[0])
      if (player.is_playing() or player.is_paused()) and player.source is not None and not player.queue.is_empty:
        await ctx.send(embed=embed(title=f"Added **{tracks[0].title}** to the Queue", description=f"About {player.duration_to_track(tracks[0])} until played", color=MessageColors.MUSIC))

    if not player.is_playing():
      await player.do_next()

  @commands.command(name="pause")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def pause(self, ctx: MyContext):
    """Pause the currently playing song."""
    player = self.get_player(ctx.guild, ctx=ctx)

    if not player or (player.is_paused() or not player.is_connected()) or not player.source:
      raise NothingPlaying()

    if self.is_privileged(ctx):
      await ctx.send(embed=embed(title='An admin or DJ has paused the player.', color=MessageColors.MUSIC))
      player.pause_votes.clear()

      return await player.set_pause(True)

    required = self.required(ctx)
    player.pause_votes.add(ctx.author)

    if len(player.pause_votes) >= required:
      await ctx.send(embed=embed(title='Vote to pause passed. Pausing player.', color=MessageColors.MUSIC))
      player.pause_votes.clear()
      await player.set_pause(True)
    else:
      await ctx.send(embed=embed(title=f'{ctx.author} has voted to pause the player.', color=MessageColors.MUSIC))

  @commands.command(name="resume")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def resume(self, ctx: MyContext):
    """Resume a currently paused player."""
    player = self.get_player(ctx.guild, ctx=ctx)

    if not player or (not player.is_paused() or not player.is_connected()) or not player.source:
      return await ctx.send(embed=embed(title='Nothing is playing right now', color=MessageColors.ERROR))

    if self.is_privileged(ctx):
      await ctx.send(embed=embed(title='An admin or DJ has resumed the player.', color=MessageColors.MUSIC))
      player.resume_votes.clear()

      return await player.set_pause(False)

    required = self.required(ctx)
    player.resume_votes.add(ctx.author)

    if len(player.resume_votes) >= required:
      await ctx.send(embed=embed(title='Vote to resume passed. Resuming player.', color=MessageColors.MUSIC))
      player.resume_votes.clear()
      await player.set_pause(False)
    else:
      await ctx.send(embed=embed(title=f'{ctx.author.mention} has voted to resume the player.', color=MessageColors.MUSIC))

  @commands.command(name="skip", help="Skips the current song")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def skip(self, ctx: MyContext):
    """Skip the currently playing song."""
    player = self.get_player(ctx.guild, ctx=ctx)

    if not player or not player.is_connected() or not player.source:
      raise NothingPlaying()

    if self.is_privileged(ctx):
      await ctx.send(embed=embed(title='An admin or DJ has skipped the song.', color=MessageColors.MUSIC))
      player.skip_votes.clear()

      return await player.stop()

    if hasattr(player.source, "requester") and ctx.author == player.source.requester:
      await ctx.send(embed=embed(title='The song requester has skipped the song.', color=MessageColors.MUSIC))
      player.skip_votes.clear()

      return await player.stop()

    required = self.required(ctx)
    player.skip_votes.add(ctx.author)

    if len(player.skip_votes) >= required:
      await ctx.send(embed=embed(title='Vote to skip passed. Skipping song.', color=MessageColors.MUSIC))
      player.skip_votes.clear()
      await player.stop()
    else:
      await ctx.send(embed=embed(title=f'{ctx.author} has voted to skip the song. {len(player.skip_votes)}/{required}', color=MessageColors.MUSIC))

  @commands.command(name="stop", aliases=["disconnect"], help="Stops the currently playing music")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  # @can_play()
  async def stop(self, ctx: MyContext):
    """Stop the player and clear all internal states."""
    player = self.get_player(ctx.guild, ctx=ctx)

    if not player or not player.is_connected():
      raise NothingPlaying()

    if self.is_privileged(ctx):
      await ctx.send(embed=embed(title='An admin or DJ has stopped the player.', color=MessageColors.MUSIC))
      return await player.teardown()

    required = self.required(ctx)
    player.stop_votes.add(ctx.author)

    if len(player.stop_votes) >= required:
      await ctx.send(embed=embed(title='Vote to stop passed. Stopping the player.', color=MessageColors.MUSIC))
      await player.teardown()
    else:
      await ctx.send(embed=embed(title=f'{ctx.author} has voted to stop the player.', color=MessageColors.MUSIC))

  @commands.command(name="volume", aliases=['v', 'vol'])
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def volume(self, ctx: MyContext, *, vol: int):
    """Change the players volume, between 1 and 100."""
    player = self.get_player(ctx.guild, ctx=ctx)

    if not player or not player.is_connected():
      raise NothingPlaying()

    if not self.is_privileged(ctx):
      return await ctx.send(embed=embed(title='Only the DJ or admins may change the volume.', color=MessageColors.MUSIC))

    if not 0 < vol <= 100:
      return await ctx.send(embed=embed(title='Please enter a value between 1 and 100.', color=MessageColors.MUSIC))

    await player.set_volume(vol)
    await ctx.send(embed=embed(title=f'Set the volume to **{vol}**%'))

  @commands.command(name="shuffle", aliases=['mix'])
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def shuffle(self, ctx: MyContext):
    """Shuffle the players queue."""
    player = self.get_player(ctx.guild, ctx=ctx)

    if not player or not player.is_connected():
      raise NothingPlaying()

    if player.queue.count < 3:
      return await ctx.send(embed=embed(title='Add more songs to the queue before shuffling.', color=MessageColors.MUSIC))

    if self.is_privileged(ctx):
      await ctx.send(embed=embed(title='An admin or DJ has shuffled the playlist.', color=MessageColors.MUSIC))
      player.shuffle_votes.clear()
      return random.shuffle(player.queue._queue)

    required = self.required(ctx)
    player.shuffle_votes.add(ctx.author)

    if len(player.shuffle_votes) >= required:
      await ctx.send(embed=embed(title='Vote to shuffle passed. Shuffling the playlist.', color=MessageColors.MUSIC))
      player.shuffle_votes.clear()
      random.shuffle(player.queue._queue)
    else:
      await ctx.send(embed=embed(title=f'{ctx.author.mention} has voted to shuffle the playlist.', color=MessageColors.MUSIC))

  @commands.command(name="equalizer", aliases=['eq'], extras={"examples": Equalizer.options(), "params": Equalizer.options()})
  @checks.is_min_tier(config.PremiumTiersNew.tier_1.value)
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def equalizer(self, ctx: MyContext, *, equalizer: Equalizer.lit_options()):
    """Change the players equalizer."""
    player = self.get_player(ctx.guild, ctx=ctx)

    if not player or not player.is_connected():
      return await ctx.send(embed=embed(title='Nothing is playing right now', color=MessageColors.ERROR))

    if not self.is_privileged(ctx):
      return await ctx.send(embed=embed(title='Only the DJ or admins may change the equalizer.', color=MessageColors.ERROR))

    eqs = {'flat': Equalizer.flat(),
           'boost': Equalizer.boost(),
           'metal': Equalizer.metal(),
           'piano': Equalizer.piano()}

    eq = eqs.get(equalizer.lower(), None)

    if not eq:
      joined = "\n".join(eqs.keys())
      return await ctx.send(embed=embed(title=f'Invalid EQ provided. Valid EQs:\n\n{joined}', color=MessageColors.ERROR))

    await ctx.send(embed=embed(title=f'Successfully changed equalizer to {equalizer}', color=MessageColors.MUSIC))
    await player.set_eq(eq)

  @commands.group(name="queue", aliases=['que'], help="shows the song queue", invoke_without_command=True)
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
  @can_play()
  async def queue(self, ctx: MyContext):
    """Display the players queued songs."""
    player = self.get_player(ctx.guild, ctx=ctx)

    if not player or not player.is_connected():
      raise NothingPlaying()

    if player.queue.is_empty:
      return await ctx.send(embed=embed(title='There are no more songs in the queue.', color=MessageColors.ERROR))

    entries = [track.title for track in player.queue._queue]
    source = PaginatorSource(entries=entries)
    pages = paginator.RoboPages(source=source, ctx=ctx, compact=True)

    await pages.start()

  @queue.command(name="remove", aliases=['rm'], help="Remove an item from the queue")
  @commands.guild_only()
  @can_play()
  async def queue_remove(self, ctx: MyContext, *, index: int):
    """Remove a song from the queue by index."""
    player = self.get_player(ctx.guild, ctx=ctx)

    if not player or not player.is_connected():
      raise NothingPlaying()

    if index < 1 or index > len(player.queue._queue):
      return await ctx.send(embed=embed(title='Invalid index provided.', color=MessageColors.ERROR))
    entry = player.queue._queue[index - 1]

    if self.is_privileged(ctx):
      player.queue.__delitem__(index - 1)
      player.remove_votes.clear()
      return await ctx.send(embed=embed(title=f'An admin or DJ has removed **{entry.title}** from the queue', color=MessageColors.MUSIC))

    if hasattr(player.source, "requester") and ctx.author == player.source.requester:
      player.queue.__delitem__(index - 1)
      player.remove_votes.clear()
      return await ctx.send(embed=embed(title=f'The song requester has removed **{entry.title}** from the queue.', color=MessageColors.MUSIC))

    required = self.required(ctx)
    player.remove_votes[index - 1].add(ctx.author)

    if len(player.remove_votes) >= required:
      player.remove_votes.clear()
      player.queue.__delitem__(index - 1)
      await ctx.send(embed=embed(title=f'Queue removal passed, removed **{entry.title}** from the queue.', color=MessageColors.MUSIC))
    else:
      await ctx.send(embed=embed(title=f'{ctx.author} has voted to remove **{entry.title}** from the queue. {len(player.remove_votes)}/{required}', color=MessageColors.MUSIC))

  @commands.command(name="nowplaying", aliases=['np', 'now_playing', 'current'])
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
  @can_play()
  async def nowplaying(self, ctx: MyContext):
    """Update the player controller."""
    player = self.get_player(ctx.guild, ctx=ctx)

    if not player or not player.is_connected() or player.source is None:
      raise NothingPlaying()

    await ctx.send(embed=player.build_embed())

  @commands.command(name="swap_dj", aliases=['swap'], help="Swap who has control over the music. (Admins always have control)")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def swap_dj(self, ctx: MyContext, *, member: discord.Member = None):
    """Swap the current DJ to another member in the voice channel."""
    player = self.get_player(ctx.guild, ctx=ctx)

    if not player or not player.is_connected():
      raise NothingPlaying()

    if not self.is_privileged(ctx):
      return await ctx.send(embed=embed(title='Only admins and the DJ may use this command.', color=MessageColors.ERROR))

    members = player.channel.members

    if member and member not in members:
      return await ctx.send(embed=embed(title=f'{member} is not currently in voice, so can not be a DJ.'))

    if member and member == player.dj:
      return await ctx.send(embed=embed(title='Cannot swap DJ to the current DJ... :)'))

    if len(members) <= 2:
      return await ctx.send(embed=embed(title='No more members to swap to.', color=MessageColors.MUSIC))

    if member:
      player.dj = member
      return await ctx.send(embed=embed(title=f'{member.display_name} is now the DJ.', color=MessageColors.MUSIC))

    for m in members:
      if m == player.dj or m.bot:
        continue
      else:
        player.dj = m
        return await ctx.send(embed=embed(title=f'{member.display_name} is now the DJ.', color=MessageColors.MUSIC))

  @commands.group(name="custom", aliases=["c"], invoke_without_command=True, case_insensitive=True, help="Play sounds/songs without looking for the url everytime")
  @commands.guild_only()
  # @commands.cooldown(1,4, commands.BucketType.channel)
  @can_play()
  @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
  async def custom(self, ctx, name: str = None):
    if name is None:
      return await ctx.invoke(self.custom_list)
    try:
      async with ctx.typing():
        sounds = await self.bot.db.query("SELECT customSounds FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
        sounds = [json.loads(x) for x in sounds]
    except Exception:
      await ctx.reply(embed=embed(title=f"The custom sound `{name}` has not been set, please add it with `{ctx.prefix}custom|c add <name> <url>`", color=MessageColors.ERROR))
    else:
      i = next((index for (index, d) in enumerate(sounds) if d["name"] == name), None)
      if sounds is not None and i is not None:
        sound = sounds[i]
        await ctx.invoke(self.bot.get_command("play"), query=sound["url"])
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
      name: str = "".join(name.split(" ")).lower()
      sounds: list = (await self.bot.db.query("SELECT customSounds FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id)))
      if sounds == "" or sounds is None:
        sounds = []
      if name in [json.loads(x)["name"] for x in sounds]:
        return await ctx.reply(embed=embed(title=f"`{name}` was already added, please choose another", color=MessageColors.ERROR))
      sounds.append(json.dumps({"name": name, "url": url}))
      await self.bot.db.query("UPDATE servers SET customSounds=$1::json[] WHERE id=$2::text", sounds, str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"I will now play `{url}` for the command `{ctx.prefix}{ctx.command.parent} {name}`"))

  @custom.command(name="list")
  @commands.guild_only()
  async def custom_list(self, ctx):
    async with ctx.typing():
      sounds = await self.bot.db.query("SELECT customSounds FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
      if sounds is None:
        raise NoCustomSoundsFound("There are no custom sounds for this server (yet)")
      sounds = [json.loads(x) for x in sounds]
      result = ""
      for sound in sounds:
        result += f"```{sound['name']} -> {sound['url']}```"
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
        sounds = await self.bot.db.query("SELECT customSounds FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
        sounds = json.loads(sounds)
        old = sounds[name]
        sounds[name] = url
        await self.bot.db.query("UPDATE servers SET customSounds=$1 WHERE id=$2", json.dumps(sounds), str(ctx.guild.id))
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
        sounds = await self.bot.db.query("SELECT customSounds FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
        sounds = [json.loads(x) for x in sounds]
        sounds.pop(next((index for (index, d) in enumerate(sounds) if d["name"] == name), None))
        await self.bot.db.query("UPDATE servers SET customSounds=$1::json[] WHERE id=$2", [json.dumps(x) for x in sounds], str(ctx.guild.id))
    except KeyError:
      await ctx.reply(embed=embed(title=f"Could not find the custom command `{name}`", color=MessageColors.ERROR))
    else:
      await ctx.reply(embed=embed(title=f"Removed the custom sound `{name}`"))

  @custom.command(name="clear")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def custom_clear(self, ctx):
    async with ctx.typing():
      await self.bot.db.query("UPDATE servers SET customsounds=array[]::json[] WHERE id=$1", str(ctx.guild.id))
    await ctx.send(embed=embed(title="Cleared this servers custom commands"))


async def setup(bot):
  await bot.add_cog(Music(bot))
