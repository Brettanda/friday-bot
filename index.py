import asyncio
import logging
import os
import sys
import aiohttp
from importlib import reload

from dotenv import load_dotenv
import nextcord as discord
from typing import Optional
from typing_extensions import TYPE_CHECKING
from collections import defaultdict
# import interactions
from nextcord.ext import commands

import cogs
import functions

if TYPE_CHECKING:
  from .cogs.log import Log
  from .cogs.database import Database

load_dotenv()

TOKEN = os.environ.get('TOKENTEST')

dead_nodes_sent = False
formatter = logging.Formatter("%(levelname)s:%(name)s: %(message)s")


async def get_prefix(bot: "Friday", message: discord.Message):
  if message.guild is not None:
    return commands.when_mentioned_or(bot.prefixes[message.guild.id])(bot, message)
  return commands.when_mentioned_or(functions.config.defaultPrefix)(bot, message)


class Friday(commands.AutoShardedBot):
  """Friday is a discord bot that is designed to be a flexible and easy to use bot."""

  def __init__(self, loop=None, **kwargs):
    self.cluster_name = kwargs.pop("cluster_name", None)
    self.cluster_idx = kwargs.pop("cluster_idx", 0)
    self.should_start = kwargs.pop("start", False)
    self._logger = kwargs.pop("logger")

    if loop is None:
      self.loop = asyncio.new_event_loop()
      asyncio.set_event_loop(self.loop)
    else:
      self.loop = loop
    super().__init__(
        command_prefix=get_prefix,
        strip_after_prefix=True,
        case_insensitive=True,
        intents=functions.config.intents,
        status=discord.Status.idle,
        owner_id=215227961048170496,
        description=functions.config.description,
        member_cache_flags=functions.config.member_cache,
        chunk_guilds_at_startup=False,
        allowed_mentions=functions.config.allowed_mentions,
        enable_debug_events=True,
        # heartbeat_timeout=150.0,
        loop=self.loop, **kwargs
    )

    self.session = None
    self.restartPending = False
    self.views_loaded = False

    # guild_id: str("!")
    self.prefixes = defaultdict(lambda: str("!"))
    self.prod = True if len(sys.argv) > 1 and (sys.argv[1] == "--prod" or sys.argv[1] == "--production") else False
    self.canary = True if len(sys.argv) > 1 and (sys.argv[1] == "--canary") else False
    self.ready = False

    self.load_extension("cogs.database")
    self.load_extension("cogs.log")
    self.loop.run_until_complete(self.setup(True))
    self.logger.info(f"Cluster Starting {kwargs.get('shard_ids', None)}, {kwargs.get('shard_count', 1)}")
    if self.should_start:
      self.run(kwargs["token"])

  def __repr__(self):
    return "<Friday>"

  @property
  def log(self) -> Optional["Log"]:
    return self.get_cog("Log")

  @property
  def logger(self) -> logging.Logger:
    return self._logger

  @property
  def db(self) -> Optional["Database"]:
    return self.get_cog("Database")

  async def get_context(self, message, *, cls=None) -> functions.MyContext:
    return await super().get_context(message, cls=functions.MyContext)

  async def setup(self, load_extentions: bool = False):
    self.session: aiohttp.ClientSession() = aiohttp.ClientSession(loop=self.loop)

    for guild_id, prefix in await self.db.query("SELECT id,prefix FROM servers"):
      self.prefixes[int(guild_id, base=10)] = prefix

    if load_extentions:
      for cog in cogs.default:
        try:
          self.load_extension(f"cogs.{cog}")
        except Exception as e:
          self.logger.error(f"Failed to load extenstion {cog} with \n {e}")

  async def reload_cogs(self):
    self.ready = False
    reload(cogs)
    reload(functions)

    for i in functions.modules:
      if not i.startswith("_"):
        reload(getattr(functions, i))

    self.reload_extension("cogs.log")
    for i in cogs.default:
      self.reload_extension(f"cogs.{i}")
    self.ready = True

  async def on_message(self, ctx):
    if not self.ready:
      return

    if ctx.author.bot and not ctx.author.id == 892865928520413245:
      return

    await self.process_commands(ctx)

  async def get_or_fetch_member(self, guild: discord.Guild, member_id: int) -> Optional[discord.Member]:
    member = guild.get_member(member_id)
    if member is not None:
      return member

    shard = self.get_shard(guild.shard_id)
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

  async def on_error(self, event_method, *args, **kwargs):
    return await self.log.on_error(event_method, *args, **kwargs)

  async def close(self):
    await super().close()
    await self.session.close()


if __name__ == "__main__":
  print(f"Python version: {sys.version}")
  handler = logging.StreamHandler(sys.stdout)
  handler.setFormatter(formatter)
  filehandler = logging.FileHandler("logging.log", encoding="utf-8")
  filehandler.setFormatter(logging.Formatter("%(asctime)s:%(name)s:%(levelname)-8s%(message)s"))

  logger = logging.getLogger("Friday")
  logger.handlers = [handler, filehandler]
  logger.setLevel(logging.INFO)
  bot = Friday(logger=logger)
  if len(sys.argv) > 1:
    if sys.argv[1] == "--prod" or sys.argv[1] == "--production":
      TOKEN = os.environ.get("TOKEN")
    elif sys.argv[1] == "--canary":
      TOKEN = os.environ.get("TOKENCANARY")
  loop = asyncio.get_event_loop()
  try:
    loop.run_until_complete(bot.start(TOKEN, reconnect=True))
  except KeyboardInterrupt:
    logging.info("STOPED")
    loop.run_until_complete(bot.close())
  finally:
    loop.close()
