import asyncio
import logging
import os
import sys
from importlib import reload

import discord
from typing import TYPE_CHECKING
from discord.ext import commands
from dotenv import load_dotenv

import cogs
import functions

if TYPE_CHECKING:
  from .cogs.log import Log

load_dotenv()

TOKEN = os.environ.get('TOKENTEST')

songqueue = {}
dead_nodes_sent = False


async def get_prefix(bot, message):
  if hasattr(bot.log, "get_guild_prefix"):
    return await bot.log.get_guild_prefix(bot, message)
  return functions.config.defaultPrefix


class Friday(commands.AutoShardedBot):
  def __init__(self, **kwargs):
    self.cluster_name = kwargs.get("cluster_name", None)
    self.cluster_idx = kwargs.get("cluster_idx", 0)
    self.should_start = kwargs.get("start", False)

    self.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(self.loop)
    super().__init__(
        command_prefix=get_prefix or functions.config.defaultPrefix,
        strip_after_prefix=True,
        case_insensitive=True,
        intents=functions.config.intents,
        status=discord.Status.idle,
        owner_id=215227961048170496,
        description=functions.config.description,
        member_cache_flags=functions.config.member_cache,
        fetch_offline_members=False,
        allowed_mentions=functions.config.allowed_mentions,
        # heartbeat_timeout=150.0,
        loop=self.loop, **kwargs
    )

    self.restartPending = False
    self.saved_guilds = {}
    self.songqueue = {}
    self.prod = True if len(sys.argv) > 1 and (sys.argv[1] == "--prod" or sys.argv[1] == "--production") else False
    self.canary = True if len(sys.argv) > 1 and (sys.argv[1] == "--canary") else False
    self.ready = False

    self.load_extension("cogs.log")
    self.load_cogs()
    self.logger.info(f"Cluster Starting {kwargs.get('shard_ids', None)}, {kwargs.get('shard_count', 1)}")
    if self.should_start:
      self.run(kwargs["token"])

  @property
  def log(self) -> "Log":
    return self.get_cog(functions.config.reloadable_bot)

  @property
  def logger(self):
    return self.log.logger

  async def get_context(self, message, *, cls=None) -> functions.MyContext:
    return await super().get_context(message, cls=functions.MyContext)

  def load_cogs(self):
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

    for i in cogs.default:
      self.reload_extension(f"cogs.{i}")
    self.ready = True

  async def on_message(self, ctx):
    if not self.ready:
      return

    if ctx.author.bot:
      return

    await self.process_commands(ctx)

  async def on_error(self, event_method, *args, **kwargs):
    return await self.log.on_error(event_method, *args, **kwargs)

  async def close(self):
    self.logger.info("Shutting down")
    await super().close()


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
    # mydb.close()
    logging.info("STOPED")
    loop.run_until_complete(bot.close())
  finally:
    loop.close()
