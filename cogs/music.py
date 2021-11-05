import asyncio
import datetime
import json
import math
import os
import re
from typing import List, Literal, Optional, Union

import async_timeout
import nextcord as discord
import validators
import wavelink
from nextcord.ext import commands, menus
from numpy import random

from functions import MessageColors, MyContext, checks, config, embed, exceptions

URL_REG = re.compile(r'https?://(?:www\.)?.+')


def can_play():
  async def predicate(ctx: MyContext) -> bool:
    # connect_perms = ["connect", "speak"]
    # missing = []
    # if ctx.author.voice is None or ctx.author.voice.channel is None:
    #   raise NoChannelProvided()
    # for perm, value in ctx.author.voice.channel.permissions_for(ctx.me):
    #   if value is False and perm.lower() in connect_perms:
    #     missing.append(perm)
    # if len(missing) > 0:
    #   raise commands.BotMissingPermissions(missing)
    # return True
    player: Player = ctx.bot.wavelink.get_player(ctx.guild.id, cls=Player, ctx=ctx)

    if player.ctx and player.ctx.channel != ctx.channel:
      raise IncorrectChannelError(f"You must be in `{player.ctx.channel}` for this session.")
    if ctx.command.name == "connect" and not player.ctx:
      return True
    elif ctx.cog.is_privileged(ctx):
      return True

    if not player.channel_id:
      raise IncorrectChannelError("Failed to load the channel to play music.")

    channel = ctx.bot.get_channel(player.channel_id)
    if not channel:
      raise IncorrectChannelError("Failed to load the channel to play music.")

    if player.is_connected:
      if ctx.author not in channel.members:
        raise IncorrectChannelError(f"You must be in `{channel}` to use voice commands.")

    return True
  return commands.check(predicate)


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


class Track(wavelink.Track):
  __slots__ = ("requester", "thumbnail",)

  def __init__(self, *args, **kwargs):
    super().__init__(*args)
    self.requester = kwargs.get("requester")
    self.thumbnail = kwargs.get("thumbnail")


class Player(wavelink.Player):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.ctx: Optional[MyContext] = kwargs.get("ctx", None)
    self.dj: Optional[discord.Member] = self.ctx.author if self.ctx else None

    self.current_title = None
    self.queue = asyncio.Queue()

    self.waiting = False

    self.pause_votes = set()
    self.resume_votes = set()
    self.skip_votes = set()
    self.shuffle_votes = set()
    self.stop_votes = set()

  async def connect(self, channel: Union[discord.VoiceChannel, discord.StageChannel], self_deaf: bool = True, *, ctx: MyContext = None) -> Union[discord.VoiceChannel, discord.StageChannel]:
    if not self.ctx:
      self.ctx = ctx
      self.dj = ctx.author
    guild = self.bot.get_guild(self.guild_id)
    if not guild:
      raise wavelink.errors.InvalidIDProvided(f'No guild found for id <{self.guild_id}>')
    self.channel_id = channel.id
    await self._get_shard_socket(guild.shard_id).voice_state(self.guild_id, str(channel.id), self_deaf=self_deaf)

    return channel

  async def disconnect(self, *, force: bool = False):
    guild = self.bot.get_guild(self.guild_id)
    if not guild and force is True:
      self.channel_id = None
      return
    if not guild:
      raise wavelink.errors.InvalidIDProvided(f'No guild found for id <{self.guild_id}>')

    self.channel_id = None
    await self._get_shard_socket(guild.shard_id).voice_state(self.guild_id, None)

  async def do_next(self):
    if self.is_playing or self.waiting:
      return

    self.pause_votes.clear()
    self.resume_votes.clear()
    self.skip_votes.clear()
    self.shuffle_votes.clear()
    self.stop_votes.clear()

    try:
      self.waiting = True
      with async_timeout.timeout(60):
        track = await self.queue.get()
    except asyncio.TimeoutError:
      # No music has been played for 5 minutes, cleanup and disconnect...
      return await self.teardown()

    channel = self.bot.get_channel(self.channel_id)
    if channel and channel.type == discord.ChannelType.stage_voice and not channel.instance:
      await channel.create_instance(topic=track.title, reason="Music time!")
    elif channel and channel.type == discord.ChannelType.stage_voice and channel.instance is not None and self.current_title and channel.instance.topic == self.current_title:
      await channel.instance.edit(topic=track.title, reason="Next track!")

    self.current_title = track.title
    await self.play(track)
    self.waiting = False

    await self.ctx.reply(embed=self.build_embed())

  def build_embed(self) -> Optional[discord.Embed]:
    track = self.current
    if not track:
      return

    channel = self.bot.get_channel(self.channel_id)
    qsize = self.queue.qsize()

    try:
      duration = str(datetime.timedelta(milliseconds=int(track.length)))
    except OverflowError:
      duration = "??:??:??"

    return embed(
        title=f"Now playing: **{track.title}**",
        thumbnail=track.thumbnail,
        url=track.uri,
        fieldstitle=["Duration", "Queue Length", "Volume", "Requested By", "DJ", "Channel"],
        fieldsval=[duration, str(qsize), f"**`{self.volume}%`**", f"{track.requester.mention}", f"{self.dj.mention if self.dj else None}", f"{channel.mention if channel else None}"],
        color=MessageColors.MUSIC)

  async def teardown(self):
    try:
      await self.destroy()
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


class QueueMenu(menus.ButtonMenuPages):
  def __init__(self, source, *, title="Commands", description=""):
    super().__init__(source=source, timeout=30.0)
    self._source = source
    self.current_page = 0
    self.ctx = None
    self.message = None

  async def start(self, ctx, *, channel: discord.TextChannel = None, wait=False) -> None:
    await self._source._prepare_once()
    self.ctx = ctx
    self.message = await self.send_initial_message(ctx, ctx.channel)

  async def send_initial_message(self, ctx: "MyContext", channel: discord.TextChannel):
    page = await self._source.get_page(0)
    kwargs = await self._get_kwargs_from_page(page)
    return await ctx.send(**kwargs)

  async def _get_kwargs_from_page(self, page):
    value = await super()._get_kwargs_from_page(page)
    if "view" not in value:
      value.update({"view": self})
    return value

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if interaction.user and interaction.user == self.ctx.author:
      return True
    else:
      await interaction.response.send_message('This help menu is not for you.', ephemeral=True)
      return False

  def stop(self):
    try:
      self.ctx.bot.loop.create_task(self.message.delete())
    except discord.NotFound:
      pass
    super().stop()

  async def on_timeout(self) -> None:
    self.stop()


class Music(commands.Cog, wavelink.WavelinkMixin):
  """Listen to your favourite music and audio clips with Friday's music commands"""

  def __init__(self, bot):
    self.bot = bot

    if not hasattr(self.bot, "wavelink"):
      self.bot.wavelink = wavelink.Client(bot=bot, session=bot.session)

    bot.loop.create_task(self.start_nodes())

  async def start_nodes(self):
    await self.bot.wait_until_ready()

    nodes = {
        "MAIN": {
            "host": os.environ.get("LAVALINKUSHOST"),
            "port": os.environ.get("LAVALINKUSPORT"),
            "rest_uri": f"http://{os.environ.get('LAVALINKUSHOST')}:{os.environ.get('LAVALINKUSPORT')}/",
            "password": os.environ.get("LAVALINKUSPASS"),
            "identifier": "MAIN",
            "region": "us_central",
        },
    }

    if self.bot.wavelink.nodes:
      previous: List[wavelink.Node] = self.bot.wavelink.nodes.copy()

      for node in previous.values():
        if not node.is_available:
          await node.destroy()

    for n in nodes.values():
      try:
        await self.bot.wavelink.initiate_node(**n)
      except wavelink.errors.NodeOccupied:
        pass

  def cog_check(self, ctx: MyContext) -> bool:
    if not ctx.guild:
      raise commands.NoPrivateMessage()

    return True

  async def cog_command_error(self, ctx: MyContext, error: Exception):
    if isinstance(error, (IncorrectChannelError, NoChannelProvided, NoCustomSoundsFound, VoiceConnectionError)):
      return await ctx.send(embed=embed(title=error, color=MessageColors.ERROR))
    elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
      return await ctx.send_help(ctx.command)
    elif isinstance(error, commands.BadLiteralArgument):
      return await ctx.send(embed=embed(title=f"`{error.param.name}` must be one of `{', '.join(error.literals)}.`", color=MessageColors.ERROR))
    elif isinstance(error, (exceptions.RequiredTier, exceptions.NotSupporter, exceptions.NotInSupportServer)):
      return await ctx.send(embed=embed(title=error, color=MessageColors.ERROR))
    else:
      print(f"Error in {ctx.command.qualified_name}: {type(error).__name__}: {error}")

  @wavelink.WavelinkMixin.listener()
  async def on_node_ready(self, node: wavelink.Node):
    print(f"Node {node.identifier} is ready!")

  @wavelink.WavelinkMixin.listener('on_track_stuck')
  @wavelink.WavelinkMixin.listener('on_track_end')
  @wavelink.WavelinkMixin.listener('on_track_exception')
  async def on_player_stop(self, node: wavelink.Node, payload):
    await payload.player.do_next()

  @commands.Cog.listener()
  async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    # TODO: when moved to another voice channel, Friday will some times just stop playing music until !pause and !resume are executed
    if member == self.bot.user:
      if before.channel != after.channel and after.channel is not None and after.channel.type == discord.ChannelType.stage_voice:
        await member.edit(suppress=False)

    # TODO: Check if node has been made yet

    # if not player:
    player: Player = self.bot.wavelink.get_player(member.guild.id, cls=Player)

    if member.bot:
      return

    if not player.channel_id or not player.ctx:
      player.node.players.pop(member.guild.id)
      return

    channel = self.bot.get_channel(int(player.channel_id))

    if member == player.dj and after.channel is None:
      for m in channel.members:
        if m.bot:
          continue
        else:
          player.dj = m
          return
    elif after.channel == channel and player.dj not in channel.members:
      player.dj = member

  def required(self, ctx: MyContext):
    player: Player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player, ctx=ctx)
    channel = self.bot.get_channel(player.channel_id)
    required = math.ceil((len(channel.members) - 1) / 2.5)

    if ctx.command.name == "stop":
      if len(channel.members) == 3:
        required = 2

    return required

  def is_privileged(self, ctx: MyContext):
    player: Player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player, ctx=ctx)

    return player.dj == ctx.author or ctx.author.guild_permissions.kick_members

  async def join(self, ctx: MyContext, channel: Union[discord.VoiceChannel, discord.StageChannel] = None) -> Optional[Union[discord.VoiceChannel, discord.StageChannel]]:
    player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, ctx=ctx)

    if player.is_connected:
      return

    channel = getattr(ctx.author.voice, 'channel', channel) if channel is None else channel
    if channel is None:
      raise NoChannelProvided

    return await player.connect(channel, ctx=ctx)

  @commands.command(name="connect", aliases=["join"], help="Join a voice channel")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def connect(self, ctx: MyContext, *, channel: Optional[Union[discord.VoiceChannel, discord.StageChannel]] = None):
    """Connect to a voice channel."""
    ch = await self.join(ctx, channel)
    if ch:
      return await ctx.send(f"{ch.mention}", embed=embed(title="Connected to voice channel", color=MessageColors.MUSIC))
    return await ctx.send(embed=embed(title="Failed to connect to voice channel.", color=MessageColors.ERROR))

  @commands.command(name="play", aliases=["p", "add"], extras={"examples": ["https://youtu.be/dQw4w9WgXcQ"]}, usage="<url/title>", help="Follow this command with the title of a song to search for it or just paste the Youtube/SoundCloud url if the search gives and undesirable result")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def play(self, ctx: MyContext, *, query: str):
    """Play or queue a song with the given query."""
    player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, ctx=ctx)

    await ctx.trigger_typing()
    if not player.is_connected:
      await self.join(ctx)

    query = query.strip('<>')
    if not URL_REG.match(query):
      query = f'ytsearch:{query}'

    tracks = await self.bot.wavelink.get_tracks(query)
    if not tracks:
      return await ctx.send(embed=embed(title='No songs were found with that query. Please try again.', color=MessageColors.ERROR))

    if isinstance(tracks, wavelink.TrackPlaylist):
      for track in tracks.tracks:
        track = Track(track.id, track.info, thumbnail=track.thumb, requester=ctx.author)
        await player.queue.put(track)
      if player.is_playing or player.is_paused:
        await ctx.send(embed=embed(
            title=f"Added the playlist {tracks.data['playlistInfo']['name']}",
            description=f" with {len(tracks.tracks)} songs to the queue.",
            color=MessageColors.MUSIC))
    else:
      track = Track(tracks[0].id, tracks[0].info, thumbnail=tracks[0].thumb, requester=ctx.author)
      await player.queue.put(track)
      if player.is_playing or player.is_paused:
        await ctx.send(embed=embed(title=f"Added **{track.title}** to the Queue", color=MessageColors.MUSIC))

    if not player.is_playing:
      await player.do_next()

  @commands.command(name="pause")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def pause(self, ctx: MyContext):
    """Pause the currently playing song."""
    player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, ctx=ctx)

    if player.is_paused or not player.is_connected:
      return await ctx.send(embed=embed(title='Nothing is playing right now', color=MessageColors.ERROR))

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
    player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, ctx=ctx)

    if not player.is_paused or not player.is_connected:
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
    player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, ctx=ctx)

    if not player.is_connected:
      return await ctx.send(embed=embed(title='Nothing is playing right now', color=MessageColors.ERROR))

    if self.is_privileged(ctx):
      await ctx.send(embed=embed(title='An admin or DJ has skipped the song.', color=MessageColors.MUSIC))
      player.skip_votes.clear()

      return await player.stop()

    if ctx.author == player.current.requester:
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
      await ctx.send(embed=embed(title=f'{ctx.author} has voted to skip the song.', color=MessageColors.MUSIC))

  @commands.command(name="stop", aliases=["disconnect"], help="Stops the currently playing music")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  # @can_play()
  async def stop(self, ctx: MyContext):
    """Stop the player and clear all internal states."""
    player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, ctx=ctx)

    if not player.is_connected:
      return await ctx.send(embed=embed(title='Nothing is playing right now', color=MessageColors.ERROR))

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
    player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, ctx=ctx)

    if not player.is_connected:
      return await ctx.send(embed=embed(title='Nothing is playing right now', color=MessageColors.ERROR))

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
    player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, ctx=ctx)

    if not player.is_connected:
      return await ctx.send(embed=embed(title='Nothing is playing right now', color=MessageColors.ERROR))

    if player.queue.qsize() < 3:
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

  @commands.command(name="equalizer", aliases=['eq'])
  @checks.is_min_tier(list(config.premium_tiers)[1])
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def equalizer(self, ctx: MyContext, *, equalizer: Literal["flat", "boost", "metal", "piano"]):
    """Change the players equalizer."""
    player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, ctx=ctx)

    if not player.is_connected:
      return await ctx.send(embed=embed(title='Nothing is playing right now', color=MessageColors.ERROR))

    if not self.is_privileged(ctx):
      return await ctx.send(embed=embed(title='Only the DJ or admins may change the equalizer.', color=MessageColors.ERROR))

    eqs = {'flat': wavelink.Equalizer.flat(),
           'boost': wavelink.Equalizer.boost(),
           'metal': wavelink.Equalizer.metal(),
           'piano': wavelink.Equalizer.piano()}

    eq = eqs.get(equalizer.lower(), None)

    if not eq:
      joined = "\n".join(eqs.keys())
      return await ctx.send(embed=embed(title=f'Invalid EQ provided. Valid EQs:\n\n{joined}', color=MessageColors.ERROR))

    await ctx.send(embed=embed(title=f'Successfully changed equalizer to {equalizer}', color=MessageColors.MUSIC))
    await player.set_eq(eq)

  @commands.command(name="queue", aliases=['que'], help="shows the song queue")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
  @can_play()
  async def queue(self, ctx: MyContext):
    """Display the players queued songs."""
    player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, ctx=ctx)

    if not player.is_connected:
      return await ctx.send(embed=embed(title='Nothing is playing right now', color=MessageColors.ERROR))

    if player.queue.qsize() == 0:
      return await ctx.send(embed=embed(title='There are no more songs in the queue.', color=MessageColors.ERROR))

    entries = [track.title for track in player.queue._queue]
    pages = PaginatorSource(entries=entries)
    paginator = QueueMenu(source=pages)

    await paginator.start(ctx)

  @commands.command(name="nowplaying", aliases=['np', 'now_playing', 'current'])
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
  @can_play()
  async def nowplaying(self, ctx: MyContext):
    """Update the player controller."""
    player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, ctx=ctx)

    if not player.is_connected:
      return await ctx.send(embed=embed(title='Nothing is playing right now', color=MessageColors.ERROR))

    await ctx.send(embed=player.build_embed())

  @commands.command(name="swap_dj", aliases=['swap'], help="Swap who has control over the music. (Admins always have control)")
  @commands.guild_only()
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  @can_play()
  async def swap_dj(self, ctx: MyContext, *, member: discord.Member = None):
    """Swap the current DJ to another member in the voice channel."""
    player: Player = self.bot.wavelink.get_player(guild_id=ctx.guild.id, cls=Player, ctx=ctx)

    if not player.is_connected:
      return await ctx.send(embed=embed(title='Nothing is playing right now', color=MessageColors.ERROR))

    if not self.is_privileged(ctx):
      return await ctx.send(embed=embed(title='Only admins and the DJ may use this command.', color=MessageColors.ERROR))

    members = self.bot.get_channel(int(player.channel_id)).members

    if member and member not in members:
      return await ctx.send(embed=embed(title=f'{member} is not currently in voice, so can not be a DJ.'))

    if member and member == player.dj:
      return await ctx.send(embed=embed(title='Cannot swap DJ to the current DJ... :)'))

    if len(members) <= 2:
      return await ctx.send(embed=embed(title='No more members to swap to.', color=MessageColors.MUSIC))

    if member:
      player.dj = member
      return await ctx.send(embed=embed(title=f'{member.mention} is now the DJ.', color=MessageColors.MUSIC))

    for m in members:
      if m == player.dj or m.bot:
        continue
      else:
        player.dj = m
        return await ctx.send(embed=embed(title=f'{member.mention} is now the DJ.', color=MessageColors.MUSIC))

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


def setup(bot):
  bot.add_cog(Music(bot))
