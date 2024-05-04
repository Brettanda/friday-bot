from __future__ import annotations

import collections
import datetime
import logging
import math
import os
import re
from typing import TYPE_CHECKING, List, Literal, Optional, Union, TypeVar
from enum import Enum

import discord
import validators
import wavelink
from discord.ext import commands, menus
import copy as co
from yarl import URL
from typing_extensions import Annotated

from functions import (MessageColors, checks, config, embed, exceptions,
                       paginator)

if TYPE_CHECKING:
  from typing_extensions import Self

  from functions.custom_contexts import GuildContext, MyContext
  from index import Friday

ST = TypeVar("ST", bound="wavelink.Playable")

log = logging.getLogger(__name__)

MISSING = discord.utils.MISSING
URL_REG = re.compile(r'https?://(?:www\.)?.+')
VoiceChannel = Union[discord.VoiceChannel, discord.StageChannel]


def can_play():
  async def predicate(ctx: GuildContext) -> bool:
    cog: Music = ctx.bot.get_cog('Music')  # type: ignore
    player: Player | None = ctx.voice_client  # type: ignore

    if player is None:
      return True

    if hasattr(player, "text_channel") and player.text_channel and player.text_channel != ctx.channel:
      assert player.ctx is not None
      raise IncorrectChannelError(f"You must be in `{player.ctx.channel}` for this session.", channel=player.ctx.channel)
    if ctx.command.name == "connect" and (not hasattr(player, "ctx") or not player.ctx):
      return True
    elif cog.is_privileged(ctx):
      return True

    if not player.channel or not player.channel.id:
      raise IncorrectChannelError("Failed to load the channel to play music.")

    if ctx.author not in player.channel.members:
      raise IncorrectChannelError(f"You must be in `{player.channel}` to use voice commands.", channel=player.channel)

    return True
  return commands.check(predicate)


class NothingPlaying(exceptions.Base):
  def __init__(self, message: str = "Nothing is playing right now."):
    super().__init__(message=message)


class NoChannelProvided(exceptions.Base):
  def __init__(self, message="You must be in a voice channel or provide one to connect to."):
    super().__init__(message=message)


class IncorrectChannelError(exceptions.Base):
  def __init__(self, message="You must be in the same voice channel as the bot.", channel=None):
    self.channel = channel
    super().__init__(message=message)


class NoCustomSoundsFound(exceptions.Base):
  def __init__(self, message="There are no custom sounds for this server (yet)"):
    super().__init__(message=message)


class VoiceConnectionError(exceptions.Base):
  def __init__(self, message="An error occured while connecting to a voice channel."):
    super().__init__(message=message)


class TrackNotFound(exceptions.Base):
  def __init__(self, message="Failed to find the requested track."):
    super().__init__(message=message)


class Equalizer(wavelink.Equalizer):
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
  def options(cls) -> List[str]:
    return ["flat", "boost", "metal", "piano"]

  @classmethod
  def lit_options(cls):
    return Literal["flat", "boost", "metal", "piano"]

  @staticmethod
  def _factory(levels: list):
    _dict = collections.defaultdict(int)

    _dict.update(levels)
    _dict = [{"band": i, "gain": _dict[i]} for i in range(15)]

    return _dict

  @classmethod
  def build(cls, *, levels: list, name: str = 'CustomEqualizer') -> Self:
    return cls(levels=levels, name=name)

  @classmethod
  def flat(cls) -> Self:
    levels = [(0, .0), (1, .0), (2, .0), (3, .0), (4, .0),
              (5, .0), (6, .0), (7, .0), (8, .0), (9, .0),
              (10, .0), (11, .0), (12, .0), (13, .0), (14, .0)]

    return cls(levels=levels, name='Flat')

  @classmethod
  def boost(cls) -> Self:
    levels = [(0, -0.075), (1, .125), (2, .125), (3, .1), (4, .1),
              (5, .05), (6, 0.075), (7, .0), (8, .0), (9, .0),
              (10, .0), (11, .0), (12, .125), (13, .15), (14, .05)]

    return cls(levels=levels, name='Boost')

  @classmethod
  def metal(cls) -> Self:
    levels = [(0, .0), (1, .1), (2, .1), (3, .15), (4, .13),
              (5, .1), (6, .0), (7, .125), (8, .175), (9, .175),
              (10, .125), (11, .125), (12, .1), (13, .075), (14, .0)]

    return cls(levels=levels, name='Metal')

  @classmethod
  def piano(cls) -> Self:
    levels = [(0, -0.25), (1, -0.25), (2, -0.125), (3, 0.0),
              (4, 0.25), (5, 0.25), (6, 0.0), (7, -0.25), (8, -0.25),
              (9, 0.0), (10, 0.0), (11, 0.5), (12, 0.25), (13, -0.025)]

    return cls(levels=levels, name='Piano')


class Track(wavelink.Playable):
  requester: discord.Member


class CustomSearch(discord.app_commands.Transformer):
  @staticmethod
  def get_platform(value: str) -> str:
    if value.startswith("http"):
      link = URL(value)
      log.info(link.host)
      log.info(link.path)
      log.info(link.query)
      if link.host and ("youtube.com" in link.host or "youtu.be" in link.host):
        if link.path == "/playlist" or link.query.get("list") is not None:
          return "youtubeplaylist"
        return "youtube"
      elif link.host and "soundcloud.com" in link.host:
        return "soundcloud"
      elif link.host and "spotify.com" in link.host:
        return "spotify"
    return "youtube"

  # @classmethod
  # async def transform(cls, interaction: discord.Interaction, value: str, /) -> list[Track]:
  #   platform = cls.get_platform(value)
  #   value = value.strip("<>")
  #   log.info(platform)
  #   if platform is SearchType.Spotify:
  #     decoded = spotify.decode_url(value)
  #     if decoded:
  #       if decoded['type'] is spotify.SpotifySearchType.playlist:
  #         tracks = []
  #         async for t in spotify.SpotifyTrack.iterator(query=value):
  #           t.requester = interaction.user
  #           tracks.append(t)
  #         return tracks
  #   tracks = await platform.value.search(value)
  #   if platform == SearchType.YouTubePlaylist and isinstance(tracks, wavelink.YouTubePlaylist):
  #     tracks = tracks.tracks
  #     for t in tracks:
  #       t.requester = interaction.user
  #   return tracks

  async def convert(self, ctx: MyContext, value: str) -> list[Track]:
    platform = self.get_platform(value)
    value = value.strip("<>")
    tracks = await wavelink.Playable.search(value)
    if isinstance(tracks, list):
      for t in tracks:
        t.requester = ctx.author
    return tracks

  async def autocomplete(self, interaction: discord.Interaction, value: str, /) -> List[discord.app_commands.Choice[str]]:
    search = await wavelink.Playable.search(value)
    return [discord.app_commands.Choice(name=track.title, value=track.uri or track.title) for track in search[:25]]


class Player(wavelink.Player):
  current: Track

  def __init__(
      self,
      *args,
      dj: discord.Member = None,
      text_channel: discord.TextChannel = None,
      ctx: MyContext = None,
      shuffle_votes: set[discord.Member] = set(),
      skip_votes: set[discord.Member] = set(),
      pause_votes: set[discord.Member] = set(),
      resume_votes: set[discord.Member] = set(),
      remove_votes: dict[int, set[discord.Member]] = collections.defaultdict(lambda: set()),
      stop_votes: set[discord.Member] = set(),
      loop_votes: set[discord.Member] = set(),
      **kwargs,
  ):
    self.dj = dj
    self.text_channel = text_channel
    self.ctx = ctx
    self.shuffle_votes = shuffle_votes
    self.skip_votes = skip_votes
    self.pause_votes = pause_votes
    self.resume_votes = resume_votes
    self.remove_votes = remove_votes
    self.stop_votes = stop_votes
    self.loop_votes = loop_votes
    super().__init__(*args, **kwargs)


# class TrackEventPayload(wavelink.TrackEventPayload):
#   player: Player
#   track: Track
#   ctx: GuildContext
#   original: Track | None


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
        color=MessageColors.music())

  def is_paginating(self) -> bool:
    return True


class Music(commands.Cog):
  """Listen to your favourite music and audio clips with Friday's music commands"""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def cog_load(self):
    nodes = [
        wavelink.Node(
            identifier=f"{os.environ.get('LAVALINKUSID','MAIN')}",
            uri=f"http://{os.environ['LAVALINKUSHOST']}:{os.environ['LAVALINKUSPORT']}",
            password=os.environ["LAVALINK_SERVER_PASSWORD"],
        )
    ]

    await wavelink.Pool.connect(client=self.bot, nodes=nodes)#, spotify=spotify_client)

  def cog_check(self, ctx: MyContext) -> bool:
    if not ctx.guild:
      raise commands.NoPrivateMessage()

    return True

  async def cog_command_error(self, ctx: MyContext, error: commands.CommandError):
    error = getattr(error, "original", error)
    wavelink_errors = (wavelink.exceptions.WavelinkException,)
    # TODO: Test this shit
    if isinstance(error, IncorrectChannelError):
      return await ctx.send(error.channel and error.channel.mention, embed=embed(title=error, color=MessageColors.error()))
    elif isinstance(error, (NoChannelProvided, NoCustomSoundsFound, VoiceConnectionError, NothingPlaying, *wavelink_errors)):
      return await ctx.send(embed=embed(title=error, color=MessageColors.error()))
    elif isinstance(error, commands.BadLiteralArgument):
      return await ctx.send(embed=embed(title=f"`{error.param.name}` must be one of `{', '.join(error.literals)}.`", color=MessageColors.error()))
    elif isinstance(error, commands.BadUnionArgument):
      return await ctx.send(embed=embed(title="Failed to get the requested track", color=MessageColors.error()))
    elif isinstance(error, (exceptions.RequiredTier, exceptions.NotSupporter, exceptions.NotInSupportServer)):
      return await ctx.send(embed=embed(title=error, color=MessageColors.error()))
    else:
      log.error(f"Error in {ctx.command.qualified_name}: {type(error).__name__}: {error}")

  @commands.Cog.listener()
  async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
    log.info(f"Node {payload.node.identifier} is ready!")

  @commands.Cog.listener()
  async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload) -> None:
    print(payload.exception)

  @commands.Cog.listener()
  async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload): # TrackEventPayload
    if payload.player.channel is None:
      return

    assert payload.player.ctx is not None
    await payload.player.ctx.send(embed=self.now_playing_embed(payload.player.ctx, payload.player))

    if not isinstance(payload.player.channel, discord.StageChannel):
      return

    if payload.original is None:  # and payload.player.channel.topic is not None:
      return

    if payload.player.channel.topic is not None and not payload.player.channel.topic.startswith(f"🎵 {payload.original.title}"):
      return

    stage_instance = await payload.player.channel.fetch_instance()
    assert stage_instance is not None
    await stage_instance.edit(topic=f"🎵 {payload.player.current.title}{' by ' + str(payload.player.current.requester) if payload.player.current.requester is not None else ''}", reason="Next track started.")
    # if payload.player.channel.instance:
    #   stage_instance = await payload.player.channel.fetch_instance()
    #   await stage_instance.edit(topic=f"🎵 {payload.track.title}{' by ' + payload.track.requester if payload.track.requester is not None else ''}", reason="Next track started.")
    # else:
    #   await payload.player.channel.create_instance(topic=f"🎵 {payload.track.title}{' by ' + payload.track.requester if payload.track.requester is not None else ''}", reason="Next track started.")

  @commands.Cog.listener()
  async def on_wavelink_inactive_player(self, player: wavelink.Player): #TrackEventPayload):
    if not player.queue.is_empty:
      return

    await player.disconnect()

  def required(self, ctx: GuildContext, player: Player) -> int:
    channel = player.channel
    assert channel is not None
    required = math.ceil((len(channel.members) - 1) / 2.5)

    if ctx.command.name == "stop":
      if len(channel.members) == 3:
        required = 2

    return required

  def is_privileged(self, ctx: GuildContext) -> bool:
    player: Player | None = ctx.voice_client  # type: ignore
    if player is None:
      return False

    return bool(player.dj == ctx.author or ctx.author.guild_permissions.kick_members)

  def now_playing_embed(self, ctx: MyContext, player: Player) -> embed:
    assert not isinstance(ctx.channel, discord.DMChannel)
    qsize = player.queue.count

    try:
      duration = str(datetime.timedelta(milliseconds=player.current and int(player.current.length) or 0))
    except (OverflowError, AttributeError):
      duration = "??:??:??"
    return embed(
        title=f"Now playing: **{player.current and player.current.title}**",
        thumbnail=player.current and getattr(player.current.source, "thumbnail", None),
        url=player.current and player.current.uri or None,
        fieldstitle=["Duration", "Queue Length", "Volume", "DJ", "Requested By", "Channel"],
        fieldsval=[
            duration,
            str(qsize),
            f"**`{player.volume}%`**",
            f"{player.dj.mention if player.dj else None}",
            f"{player.current and player.current.requester.mention}",
            f"{ctx.channel.mention if ctx.channel else None}"
        ],
        color=MessageColors.music())

  @commands.command(name="connect", aliases=["join"])
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def connect(self, ctx: GuildContext, *, channel: Optional[VoiceChannel] = None):
    """Connect to a voice channel."""
    if not ctx.voice_client:
      if ctx.author.voice is None or ctx.author.voice.channel is None:
        raise NoChannelProvided
      player: Player = await ctx.author.voice.channel.connect(cls=Player, self_deaf=True)
    else:
      player = ctx.voice_client  # type: ignore
    # ch = await self.join(ctx, channel)
    if player.channel:
      return await ctx.send(f"{player.channel.mention}", embed=embed(title="Connected to voice channel", color=MessageColors.music()))
    return await ctx.send(embed=embed(title="Failed to connect to voice channel.", color=MessageColors.error()))

  @commands.command(name="play", aliases=["p", "add"], extras={"examples": ["https://youtu.be/dQw4w9WgXcQ"]}, usage="<url/title>")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def play(self, ctx: GuildContext, *, query: discord.app_commands.Transform[list[Track], CustomSearch]):
    """Play or queue a song with the given query."""
    if not ctx.voice_client:
      if ctx.author.voice is None or ctx.author.voice.channel is None:
        raise NoChannelProvided
      if ctx.author.voice.channel.permissions_for(ctx.guild.me) < discord.Permissions.stage_moderator():
        raise commands.BotMissingPermissions(["stage_moderator"])
      player: Player = await ctx.author.voice.channel.connect(cls=Player, self_deaf=True)
      player.dj = ctx.author
      player.ctx = ctx
    else:
      player: Player = ctx.voice_client  # type: ignore

    # if player.channel.instance is None:
    #   await player.channel.create_instance(topic=track.title, reason="Music time!")
    if isinstance(player.channel, discord.StageChannel) and player.channel is not None and getattr(player.channel, "instance", None) is None:
      log.info(query[0].title)
      await player.channel.create_instance(topic=f"🎵 {query[0].title}{' by ' + str(query[0].requester) if query[0].requester is not None else ''}", reason="Next track started.")
      if ctx.guild.me.voice and ctx.guild.me.voice.suppress and player.channel:
        if player.channel.permissions_for(ctx.guild.me) >= discord.Permissions.stage_moderator():
          await ctx.guild.me.edit(suppress=False, reason="Music started.")
        else:
          await ctx.guild.me.request_to_speak()

    new_tracks = []

    async def _play(track):
      track.requester = ctx.author
      # log.info(track)
      new_tracks.append(track)
      await player.queue.put_wait(track)

    for track in query:
      try:
        await _play(track)
      except BaseException:
        raise TrackNotFound()

    if not player.playing:
      await player.play(query[0])

    if player.playing:
      if len(new_tracks) == 1:
        await ctx.send(embed=embed(title=f"Added **{new_tracks[0].title}** to the queue.", color=MessageColors.music()))
      else:
        await ctx.send(embed=embed(title=f"Added **{len(new_tracks)}** tracks to the queue.", color=MessageColors.music()))

  @commands.command(name="pause")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def pause(self, ctx: GuildContext):
    """Pause the currently playing song."""
    player: Player | None = ctx.voice_client  # type: ignore

    if player is None or player.paused or player.current is None:
      raise NothingPlaying()

    if self.is_privileged(ctx):
      await ctx.send(embed=embed(title='An admin or DJ has paused the player.', color=MessageColors.music()))
      player.pause_votes.clear()

      return await player.pause(True)

    required = self.required(ctx, player=player)
    player.pause_votes.add(ctx.author)

    if len(player.pause_votes) >= required:
      await ctx.send(embed=embed(title='Vote to pause passed. Pausing player.', color=MessageColors.music()))
      player.pause_votes.clear()
      await player.pause(True)
    else:
      await ctx.send(embed=embed(title=f'{ctx.author} has voted to pause the player.', color=MessageColors.music()))

  @commands.command(name="resume")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def resume(self, ctx: GuildContext):
    """Resume a currently paused player."""
    player: Player | None = ctx.voice_client  # type: ignore

    if player is None or not player.paused or player.current is None:
      raise NothingPlaying()

    if self.is_privileged(ctx):
      await ctx.send(embed=embed(title='An admin or DJ has resumed the player.', color=MessageColors.music()))
      player.resume_votes.clear()

      return await player.pause(False)

    required = self.required(ctx, player)
    player.resume_votes.add(ctx.author)

    if len(player.resume_votes) >= required:
      await ctx.send(embed=embed(title='Vote to resume passed. Resuming player.', color=MessageColors.music()))
      player.resume_votes.clear()
      await player.pause(False)
    else:
      await ctx.send(embed=embed(title=f'{ctx.author.mention} has voted to resume the player.', color=MessageColors.music()))

  @commands.command(name="loop")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def loop(self, ctx: GuildContext, type: Literal['all', 'one'] = None) -> None:
    """Loop the current song or the queue."""
    player: Player | None = ctx.voice_client  # type: ignore

    if not player:
      raise NothingPlaying()

    def set_loop(type):
      if type == "one":
        player.queue.mode = wavelink.QueueMode.loop
      elif type == "all":
        player.queue.mode = wavelink.QueueMode.loop_all
      else:
        player.queue.mode = wavelink.QueueMode.normal

    if self.is_privileged(ctx):
      await ctx.send(embed=embed(title=f'An admin or DJ has set the loop to {type}.', color=MessageColors.music()))
      player.loop_votes.clear()

      set_loop(type)
      return

  @commands.command(name="skip")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def skip(self, ctx: GuildContext):
    """Skip the currently playing song."""
    player: Player | None = ctx.voice_client  # type: ignore

    if player is None or not player.current:
      raise NothingPlaying()

    if self.is_privileged(ctx):
      await ctx.send(embed=embed(title='An admin or DJ has skipped the song.', color=MessageColors.music()))
      player.skip_votes.clear()

      return await player.skip(force=False)

    if hasattr(player.current, "requester") and ctx.author == player.current.requester:
      await ctx.send(embed=embed(title='The song requester has skipped the song.', color=MessageColors.music()))
      player.skip_votes.clear()

      return await player.skip(force=False)

    required = self.required(ctx, player)
    player.skip_votes.add(ctx.author)

    if len(player.skip_votes) >= required:
      await ctx.send(embed=embed(title='Vote to skip passed. Skipping song.', color=MessageColors.music()))
      player.skip_votes.clear()
      await player.skip(force=False)
    else:
      await ctx.send(embed=embed(title=f'{ctx.author} has voted to skip the song. {len(player.skip_votes)}/{required}', color=MessageColors.music()))

  @commands.command(name="stop", aliases=["disconnect"])
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  # @can_play()
  async def stop(self, ctx: GuildContext):
    """Stops the currently playing music."""
    player: Player | None = ctx.voice_client  # type: ignore

    if player is None:
      raise NothingPlaying()

    if self.is_privileged(ctx):
      await ctx.send(embed=embed(title='An admin or DJ has stopped the player.', color=MessageColors.music()))
      return await player.disconnect()

    required = self.required(ctx, player)
    player.stop_votes.add(ctx.author)

    if len(player.stop_votes) >= required:
      await ctx.send(embed=embed(title='Vote to stop passed. Stopping the player.', color=MessageColors.music()))
      return await player.disconnect()
    else:
      await ctx.send(embed=embed(title=f'{ctx.author} has voted to stop the player.', color=MessageColors.music()))

  @commands.command(name="volume", aliases=['v', 'vol'])
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def volume(self, ctx: GuildContext, *, vol: int):
    """Change the players volume, between 1 and 100."""
    player: Player | None = ctx.voice_client  # type: ignore

    if player is None:
      raise NothingPlaying()

    if not self.is_privileged(ctx):
      return await ctx.send(embed=embed(title='Only the DJ or admins may change the volume.', color=MessageColors.music()))

    if not 0 < vol <= 100:
      return await ctx.send(embed=embed(title='Please enter a value between 1 and 100.', color=MessageColors.music()))

    await player.set_volume(vol)
    await ctx.send(embed=embed(title=f'Set the volume to **{vol}**%'))

  @commands.command(name="shuffle", aliases=['mix'])
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def shuffle(self, ctx: GuildContext):
    """Shuffle the players queue."""
    player: Player | None = ctx.voice_client  # type: ignore

    if player is None:
      raise NothingPlaying()

    if player.queue.count < 3:
      return await ctx.send(embed=embed(title='Add more songs to the queue before shuffling.', color=MessageColors.music()))

    if self.is_privileged(ctx):
      await ctx.send(embed=embed(title='An admin or DJ has shuffled the playlist.', color=MessageColors.music()))
      player.shuffle_votes.clear()
      return player.queue.shuffle()

    required = self.required(ctx, player)
    player.shuffle_votes.add(ctx.author)

    if len(player.shuffle_votes) >= required:
      await ctx.send(embed=embed(title='Vote to shuffle passed. Shuffling the playlist.', color=MessageColors.music()))
      player.shuffle_votes.clear()
      player.queue.shuffle()
    else:
      await ctx.send(embed=embed(title=f'{ctx.author.mention} has voted to shuffle the playlist.', color=MessageColors.music()))

  @commands.command(name="equalizer", aliases=['eq', 'filter'], extras={"examples": Equalizer.options(), "params": Equalizer.options()})
  @checks.is_min_tier(config.PremiumTiersNew.tier_2)
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def equalizer(self, ctx: GuildContext, *, equalizer: Annotated[str, Equalizer.lit_options()]):
    """Change the players equalizer."""
    player: Player | None = ctx.voice_client  # type: ignore

    if not player:
      raise NothingPlaying()

    if not self.is_privileged(ctx):
      return await ctx.send(embed=embed(title='Only the DJ or admins may change the equalizer.', color=MessageColors.error()))

    eqs = {'flat': Equalizer.flat(),
           'boost': Equalizer.boost(),
           'metal': Equalizer.metal(),
           'piano': Equalizer.piano()}

    eq = eqs.get(equalizer.lower(), None)

    if not eq:
      joined = "\n".join(eqs.keys())
      return await ctx.send(embed=embed(title=f'Invalid EQ provided. Valid EQs:\n\n{joined}', color=MessageColors.error()))

    filters = player.filters
    filters.equalizer.set(bands=eq.eq)
    await player.set_filters(filters)
    await ctx.send(embed=embed(title=f'Successfully changed equalizer to {equalizer}', color=MessageColors.music()))

  @commands.group(name="queue", aliases=['que'], invoke_without_command=True)
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
  @can_play()
  async def queue(self, ctx: GuildContext):
    """Display the players queued songs."""
    player: Player | None = ctx.voice_client  # type: ignore

    if not player or not player.current:
      raise NothingPlaying()

    if player.queue.is_empty:
      return await ctx.send(embed=embed(title='There are no more songs in the queue.', color=MessageColors.error()))

    entries = [track.title for track in player.queue]
    source = PaginatorSource(entries=entries)
    pages = paginator.RoboPages(source=source, ctx=ctx, compact=True)

    await pages.start()

  @queue.command(name="remove", aliases=['rm'])
  @commands.guild_only()
  @can_play()
  async def queue_remove(self, ctx: GuildContext, *, index: int):
    """Remove a song from the queue by index."""
    player: Player | None = ctx.voice_client  # type: ignore

    if not player or not player.current:
      raise NothingPlaying()

    if index < 1 or index > player.queue.count:
      return await ctx.send(embed=embed(title='Invalid index provided.', color=MessageColors.error()))
    entry = player.queue[index - 1]

    if self.is_privileged(ctx):
      del player.queue[index - 1]
      player.remove_votes.clear()
      return await ctx.send(embed=embed(title=f'An admin or DJ has removed **{entry.title}** from the queue', color=MessageColors.music()))

    if hasattr(player.current, "requester") and ctx.author == player.current.requester:
      del player.queue[index - 1]
      player.remove_votes.clear()
      return await ctx.send(embed=embed(title=f'The song requester has removed **{entry.title}** from the queue.', color=MessageColors.music()))

    required = self.required(ctx, player)
    player.remove_votes[index - 1].add(ctx.author)

    if len(player.remove_votes) >= required:
      player.remove_votes.clear()
      del player.queue[index - 1]
      await ctx.send(embed=embed(title=f'Queue removal passed, removed **{entry.title}** from the queue.', color=MessageColors.music()))
    else:
      await ctx.send(embed=embed(title=f'{ctx.author} has voted to remove **{entry.title}** from the queue. {len(player.remove_votes)}/{required}', color=MessageColors.music()))

  @commands.command(name="nowplaying", aliases=['np', 'now_playing', 'current'])
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
  @can_play()
  async def nowplaying(self, ctx: GuildContext):
    """Update the player controller."""
    player: Player | None = ctx.voice_client  # type: ignore

    if not player or player.current is None:
      raise NothingPlaying()

    await ctx.send(embed=self.now_playing_embed(ctx, player))

  @commands.command(name="swap_dj", aliases=['swap'], help="Swap who has control over the music. (Admins always have control)")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def swap_dj(self, ctx: GuildContext, *, member: discord.Member = None):
    """Swap the current DJ to another member in the voice channel."""
    player: Player | None = ctx.voice_client  # type: ignore

    if not player:
      raise NothingPlaying()

    if not self.is_privileged(ctx):
      return await ctx.send(embed=embed(title='Only admins and the DJ may use this command.', color=MessageColors.error()))

    assert player.channel is not None
    members = player.channel.members

    if member and member not in members:
      return await ctx.send(embed=embed(title=f'{member} is not currently in voice, so can not be a DJ.'))

    if member and member == player.dj:
      return await ctx.send(embed=embed(title='Cannot swap DJ to the current DJ... :)'))

    if len(members) <= 2:
      return await ctx.send(embed=embed(title='No more members to swap to.', color=MessageColors.music()))

    if member:
      player.dj = member
      return await ctx.send(embed=embed(title=f'{member.display_name} is now the DJ.', color=MessageColors.music()))

    for m in members:
      if m == player.dj or m.bot:
        continue
      else:
        player.dj = m
        return await ctx.send(embed=embed(title=f'{m.display_name} is now the DJ.', color=MessageColors.music()))

  @commands.group(name="custom", aliases=["c"], invoke_without_command=True, case_insensitive=True, help="Play sounds/songs without looking for the url everytime")
  @commands.guild_only()
  # @commands.cooldown(1,4, commands.BucketType.channel)
  @can_play()
  @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
  async def custom(self, ctx: GuildContext, name: str = None):
    if name is None:
      return await ctx.invoke(self.custom_list)  # type: ignore
    try:
      async with ctx.typing():
        sounds: list[dict] = await ctx.db.fetchval("SELECT customSounds FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))  # type: ignore
    except Exception:
      await ctx.reply(embed=embed(title=f"The custom sound `{name}` has not been set, please add it with `{ctx.prefix}custom|c add <name> <url>`", color=MessageColors.error()))
    else:
      i = next((index for (index, d) in enumerate(sounds) if d["name"] == name), None)
      if sounds is not None and i is not None:
        sound = sounds[i]
        await ctx.invoke(self.bot.get_command("play"), query=sound["url"])  # type: ignore
      else:
        await ctx.reply(embed=embed(title=f"The sound `{name}` has not been added, please check the `custom list` command", color=MessageColors.error()))

  @custom.command(name="add")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def custom_add(self, ctx: GuildContext, name: str, url: str):
    url = url.strip("<>")
    valid = validators.url(url)  # type: ignore
    if valid is not True:
      await ctx.reply(embed=embed(title=f"Failed to recognize the url `{url}`", color=MessageColors.error()))
      return

    if name in ["add", "change", "replace", "list", "remove", "del"]:
      await ctx.reply(embed=embed(title=f"`{name}`is not an acceptable name for a command as it is a sub-command of custom", color=MessageColors.error()))
      return

    async with ctx.typing():
      name = "".join(name.split(" ")).lower()
      sounds: list[dict] = await ctx.db.fetchval("SELECT customSounds FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))  # type: ignore
      if sounds == "" or not sounds:
        sounds = []
      if name in [x["name"] for x in sounds]:
        return await ctx.reply(embed=embed(title=f"`{name}` was already added, please choose another", color=MessageColors.error()))
      sounds.append({"name": name, "url": url})
      await ctx.db.execute("UPDATE servers SET customSounds=$1::jsonb[] WHERE id=$2::text", sounds, str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"I will now play `{url}` for the command `{ctx.prefix}{ctx.command.parent} {name}`"))

  @custom.command(name="list")
  @commands.guild_only()
  async def custom_list(self, ctx: GuildContext):
    async with ctx.typing():
      sounds: list[dict] = await ctx.db.fetchval("SELECT customSounds FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))  # type: ignore
      if not sounds:
        raise NoCustomSoundsFound("There are no custom sounds for this server (yet)")
      result = ""
      for sound in sounds:
        result += f"```{sound['name']} -> {sound['url']}```"
      if result == "":
        result = "There are no custom sounds for this server (yet)"
    await ctx.reply(embed=embed(title="The list of custom sounds", description=result))

  @custom.command(name="change", aliases=["replace"])
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def custom_change(self, ctx: GuildContext, name: str, url: str):
    try:
      async with ctx.typing():
        name = "".join(name.split(" ")).lower()
        sounds: list[dict] = await ctx.db.fetchval("SELECT customSounds FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))  # type: ignore
        index = next((i for (i, d) in enumerate(sounds) if d["name"] == name), 10000000000000000000)
        old = sounds[index]
        sounds[index]["url"] = url
        await ctx.db.execute("UPDATE servers SET customSounds=$1 WHERE id=$2", sounds, str(ctx.guild.id))
    except KeyError:
      await ctx.reply(embed=embed(title=f"Could not find the custom command `{name}`", color=MessageColors.error()))
    else:
      await ctx.reply(embed=embed(title=f"Changed `{name}` from `{old}` to `{url}`"))

  @custom.command(name="remove", aliases=["del"])
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def custom_del(self, ctx: GuildContext, name: str):
    try:
      async with ctx.typing():
        name = "".join(name.split(" ")).lower()
        sounds: list[dict] = await ctx.db.fetchval("SELECT customSounds FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))  # type: ignore
        sounds.pop(next((index for (index, d) in enumerate(sounds) if d["name"] == name), 100000000000000000))
        await ctx.db.execute("UPDATE servers SET customSounds=$1::jsonb[] WHERE id=$2", sounds, str(ctx.guild.id))
    except KeyError:
      await ctx.reply(embed=embed(title=f"Could not find the custom command `{name}`", color=MessageColors.error()))
    else:
      await ctx.reply(embed=embed(title=f"Removed the custom sound `{name}`"))

  @custom.command(name="clear")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def custom_clear(self, ctx: GuildContext):
    async with ctx.typing():
      await ctx.db.execute("UPDATE servers SET customsounds=array[]::jsonb[] WHERE id=$1", str(ctx.guild.id))
    await ctx.send(embed=embed(title="Cleared this servers custom commands"))


async def setup(bot):
  await bot.add_cog(Music(bot))
