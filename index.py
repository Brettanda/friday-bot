from __future__ import annotations

import asyncio
import datetime
import logging
import os
import sys
from collections import Counter, defaultdict
from typing import Any, AsyncIterator, Dict, Iterable, Optional

import aiohttp
import asyncpg
import discord
from discord.ext import commands
from dotenv import load_dotenv
from topgg.webhook import WebhookManager
from typing_extensions import TYPE_CHECKING

import cogs
import functions
from functions.config import Config, ReadOnly

if TYPE_CHECKING:
  from .cogs.database import Database
  from .cogs.reminder import Reminder
  from .cogs.log import Log

load_dotenv()

TOKEN = os.environ.get('TOKENTEST')


async def get_prefix(bot: Friday, message: discord.Message):
  if message.guild is not None:
    return commands.when_mentioned_or(bot.prefixes[message.guild.id])(bot, message)
  return commands.when_mentioned_or(functions.config.defaultPrefix)(bot, message)


class Friday(commands.AutoShardedBot):
  """Friday is a discord bot that is designed to be a flexible and easy to use bot."""

  user: discord.ClientUser
  pool: asyncpg.Pool
  topgg_webhook: WebhookManager
  command_stats: Counter[str]
  socket_stats: Counter[str]
  chat_stats: Counter[str]
  gateway_handler: Any
  bot_app_info: discord.AppInfo
  uptime: datetime.datetime

  def __init__(self, **kwargs):
    self.cluster = kwargs.pop("cluster", None)
    self.cluster_name = kwargs.pop("cluster_name", None)
    self.cluster_idx = kwargs.pop("cluster_idx", 0)
    self.should_start = kwargs.pop("start", False)
    self._logger = kwargs.pop("logger")

    super().__init__(
        command_prefix=get_prefix,
        strip_after_prefix=True,
        case_insensitive=True,
        intents=discord.Intents(
            guilds=True,
            voice_states=True,
            messages=True,
            reactions=True,
            members=True,
            bans=True,
            guild_scheduled_events=True,
            message_content=True,
            # invites=True,
        ),
        status=discord.Status.idle,
        owner_id=215227961048170496,
        description=functions.config.description,
        member_cache_flags=discord.MemberCacheFlags.all(),
        chunk_guilds_at_startup=False,
        allowed_mentions=discord.AllowedMentions(roles=False, everyone=False, users=True),
        enable_debug_events=True,
        **kwargs
    )

    self.views_loaded = False

    # guild_id: str("!")
    self.prefixes = defaultdict(lambda: str("!"))
    self.prod = kwargs.pop("prod", None) or True if len(sys.argv) > 1 and (sys.argv[1] == "--prod" or sys.argv[1] == "--production") else False
    self.canary = kwargs.pop("canary", None) or True if len(sys.argv) > 1 and (sys.argv[1] == "--canary") else False
    self.ready = False

    # shard_id: List[datetime.datetime]
    # shows the last attempted IDENTIFYs and RESUMEs
    self.resumes = defaultdict(list)
    self.identifies = defaultdict(list)

    self.logger.info(f"Cluster Starting {kwargs.get('shard_ids', None)}, {kwargs.get('shard_count', 1)}")
    if self.should_start:
      self.run(kwargs["token"], reconnect=True)

  def __repr__(self) -> str:
    return f"<Friday username=\"{self.user.display_name if self.user else None}\" id={self.user.id if self.user else None}>"

  @property
  def logger(self) -> logging.Logger:
    return self._logger

  async def get_lang(self, msg: discord.Message):
    if msg.guild is None:
      return self.langs["en"]
    if not self.log:
      return self.langs.get(msg.guild.preferred_locale.value[:2], "en")
    return self.langs.get((await self.log.get_guild_config(msg.guild.id)).lang)

  async def get_context(self, message, *, cls=None) -> functions.MyContext:
    return await super().get_context(message, cls=cls or functions.MyContext)

  async def setup_hook(self) -> None:
    self.session = aiohttp.ClientSession()

    self.blacklist: Config[bool] = Config("blacklist.json", loop=self.loop)

    self.langs: Dict[str, ReadOnly[dict[dict, str | dict]]] = {
        "en": ReadOnly("i18n/source/commands.json", loop=self.loop),
        **{name: ReadOnly(f"i18n/translations/{name}/commands.json", loop=self.loop) for name in os.listdir("./i18n/translations")}
    }
    self.languages = self.langs

    self.pool = await functions.db.Table.create_pool(prod=self.prod, canary=self.canary)
    await self.load_extension("cogs.database")
    await self.load_extension("cogs.log")

    self.bot_app_info = await self.application_info()
    self.owner_id = self.bot_app_info.team and self.bot_app_info.team.owner_id or self.bot_app_info.owner.id
    self.owner = self.get_user(self.owner_id) or await self.fetch_user(self.owner_id)

    # Should replace with a json file at some point
    for guild_id, prefix in await self.pool.fetch("SELECT id,prefix FROM servers WHERE prefix!=$1::text", "!"):
      self.prefixes[int(guild_id, base=10)] = prefix

    for cog in [*cogs.default, *cogs.spice]:
      path = "spice.cogs." if cog.lower() in cogs.spice else "cogs."
      try:
        await self.load_extension(f"{path}{cog}")
      except Exception as e:
        self.logger.error(f"Failed to load extenstion {cog} with \n {e}")

  async def on_ready(self):
    DIARY = discord.Object(id=243159711237537802)
    await self.tree.sync(guild=DIARY)
    await self.tree.sync()

  def _clear_gateway_data(self) -> None:
    one_week_ago = discord.utils.utcnow() - datetime.timedelta(days=7)
    for shard_id, dates in self.identifies.items():
      to_remove = [index for index, dt in enumerate(dates) if dt < one_week_ago]
      for index in reversed(to_remove):
        del dates[index]

    for shard_id, dates in self.resumes.items():
      to_remove = [index for index, dt in enumerate(dates) if dt < one_week_ago]
      for index in reversed(to_remove):
        del dates[index]

  async def before_identify_hook(self, shard_id: int, *, initial: bool):
    self._clear_gateway_data()
    self.identifies[shard_id].append(discord.utils.utcnow())
    await super().before_identify_hook(shard_id, initial=initial)

  async def on_message(self, ctx):
    if not self.ready:
      return

    if ctx.author.bot and not ctx.author.id == 892865928520413245 and not ctx.author.id == 968261189828231308:
      return

    await self.process_commands(ctx)

  async def get_or_fetch_member(self, guild: discord.Guild, member_id: int) -> Optional[discord.Member]:
    member = guild.get_member(member_id)
    if member is not None:
      return member

    shard: discord.ShardInfo = self.get_shard(guild.shard_id)   # type: ignore  # will never be None
    if shard.is_ws_ratelimited():
      try:
        member = await guild.fetch_member(member_id)
      except discord.HTTPException:
        return None
      else:
        return member

    members = await guild.query_members(limit=1, user_ids=[member_id], cache=True)
    if not members:
      return None
    return members[0]

  async def resolve_member_ids(self, guild: discord.Guild, member_ids: Iterable[int]) -> AsyncIterator[discord.Member]:
    """Bulk resolves member IDs to member instances, if possible.
    Members that can't be resolved are discarded from the list.
    This is done lazily using an asynchronous iterator.
    Note that the order of the resolved members is not the same as the input.
    Parameters
    -----------
    guild: Guild
        The guild to resolve from.
    member_ids: Iterable[int]
        An iterable of member IDs.
    Yields
    --------
    Member
        The resolved members.
    """

    needs_resolution = []
    for member_id in member_ids:
      member = guild.get_member(member_id)
      if member is not None:
        yield member
      else:
        needs_resolution.append(member_id)

    total_need_resolution = len(needs_resolution)
    if total_need_resolution == 1:
      shard: discord.ShardInfo = self.get_shard(guild.shard_id)   # type: ignore  # will never be None
      if shard.is_ws_ratelimited():
        try:
          member = await guild.fetch_member(needs_resolution[0])
        except discord.HTTPException:
          pass
        else:
          yield member
      else:
        members = await guild.query_members(limit=1, user_ids=needs_resolution, cache=True)
        if members:
          yield members[0]
    elif 0 < total_need_resolution <= 100:
      # Only a single resolution call needed here
      resolved = await guild.query_members(limit=100, user_ids=needs_resolution, cache=True)
      for member in resolved:
        yield member
    elif total_need_resolution > 0:
      # We need to chunk these in bits of 100...
      for index in range(0, total_need_resolution, 100):
        to_resolve = needs_resolution[index: index + 100]
        members = await guild.query_members(limit=100, user_ids=to_resolve, cache=True)
        for member in members:
          yield member

  async def on_error(self, event_method, *args, **kwargs):
    return await self.log.on_error(event_method, *args, **kwargs)

  async def close(self) -> None:
    await super().close()
    await self.session.close()

  @property
  def log(self) -> Log:
    return self.get_cog("Log")  # type: ignore

  @property
  def db(self) -> Optional[Database]:
    return self.get_cog("Database")  # type: ignore

  @property
  def reminder(self) -> Optional[Reminder]:
    return self.get_cog("Reminder")  # type: ignore


async def main(bot):
  async with bot:
    await bot.start(TOKEN, reconnect=True)

if __name__ == "__main__":
  from launcher import get_logger
  print(f"Python version: {sys.version}")
  log = get_logger("Friday")

  bot = Friday(logger=log)
  if len(sys.argv) > 1:
    if sys.argv[1] == "--prod" or sys.argv[1] == "--production":
      TOKEN = os.environ.get("TOKEN")
    elif sys.argv[1] == "--canary":
      TOKEN = os.environ.get("TOKENCANARY")
  try:
    asyncio.run(main(bot))
  except KeyboardInterrupt:
    logging.info("STOPED")
    asyncio.run(bot.close())
