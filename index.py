import asyncio
import logging
import os
import sys
import aiohttp
from importlib import reload

import discord
from typing import TYPE_CHECKING, Optional
from discord.ext import commands
from dotenv import load_dotenv

import cogs
import functions

if TYPE_CHECKING:
  from .cogs.log import Log
  from .cogs.database import Database

load_dotenv()

TOKEN = os.environ.get('TOKENTEST')

dead_nodes_sent = False


async def get_prefix(bot: "Friday", message: discord.Message):
  if message.guild is not None:
    if str(message.guild.id) in bot.prefixes:
      return commands.when_mentioned_or(bot.prefixes[str(message.guild.id)])(bot, message)
    else:
      current = await bot.db.query("SELECT prefix FROM servers WHERE id=$1", str(message.guild.id))
      bot.prefixes[message.guild.id] = str(current)
      bot.logger.warning(f"{message.guild.id}'s prefix was {bot.prefixes.get(str(message.guild.id), None)} and is now {current}")
      return commands.when_mentioned_or(bot.prefixes[str(message.guild.id)])(bot, message)
  return commands.when_mentioned_or(functions.config.defaultPrefix)(bot, message)


class Friday(commands.AutoShardedBot):
  def __init__(self, **kwargs):
    self.cluster_name = kwargs.pop("cluster_name", None)
    self.cluster_idx = kwargs.pop("cluster_idx", 0)
    self.should_start = kwargs.pop("start", False)

    self.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(self.loop)
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
        # heartbeat_timeout=150.0,
        loop=self.loop, **kwargs
    )

    self.session = None
    self.restartPending = False
    self.views_loaded = False
    self.saved_guilds = {}
    self.songqueue = {}
    self.prod = True if len(sys.argv) > 1 and (sys.argv[1] == "--prod" or sys.argv[1] == "--production") else False
    self.canary = True if len(sys.argv) > 1 and (sys.argv[1] == "--canary") else False
    self.ready = False

    self.prefixes = {}
    self.load_extension("cogs.database")
    self.load_extension("cogs.log")
    self.loop.run_until_complete(self.setup(True))
    self.logger.info(f"Cluster Starting {kwargs.get('shard_ids', None)}, {kwargs.get('shard_count', 1)}")
    if self.should_start:
      self.run(kwargs["token"])

  @property
  def log(self) -> "Log":
    return self.get_cog("Log")

  @property
  def logger(self):
    return self.log.logger

  @property
  def db(self) -> "Database":
    return self.get_cog("Database")

  async def get_context(self, message, *, cls=None) -> functions.MyContext:
    return await super().get_context(message, cls=functions.MyContext)

  async def setup(self, load_extentions: bool = False):
    self.session: aiohttp.ClientSession() = aiohttp.ClientSession()

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

    if ctx.author.bot:
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
  bot = Friday()
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
