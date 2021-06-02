import asyncio
import logging
import os
import sys
from importlib import reload

import discord
from discord.ext import commands
from dotenv import load_dotenv

import cogs
import functions

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(name)s:%(levelname)-8s%(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
    filename="logging.log"
)

TOKEN = os.environ.get('TOKENTEST')

songqueue = {}
dead_nodes_sent = False


async def get_prefix(bot, message):
  if hasattr(bot, "get_guild_prefix"):
    return bot.get_guild_prefix(bot, message)
  return functions.config.defaultPrefix


class Friday(commands.AutoShardedBot):
  def __init__(self):
    super().__init__(
        command_prefix=get_prefix or functions.config.defaultPrefix,
        strip_after_prefix=True,
        case_insensitive=True,
        intents=functions.config.intents,
        status=discord.Status.idle,
        owner_id=215227961048170496,
        description=functions.config.description,
        # member_cache_flags=discord.MemberCacheFlags.voice(),
        # fetch_offline_members=False,
        allowed_mentions=functions.config.allowed_mentions,
        # heartbeat_timeout=150.0
    )

    self.restartPending = False
    self.saved_guilds = {}
    self.songqueue = {}
    self.prod = True if len(sys.argv) > 1 and (sys.argv[1] == "--prod" or sys.argv[1] == "--production") else False
    self.canary = True if len(sys.argv) > 1 and (sys.argv[1] == "--canary") else False

    self.load_cogs()

  async def get_context(self, message, *, cls=None):
    return await super().get_context(message, cls=functions.MyContext)

  def load_cogs(self):
    for cog in cogs.default:
      try:
        self.load_extension(f"cogs.{cog}")
      except Exception as e:
        print(f"Failed to load extenstion {cog} with \n {e}", file=sys.stderr)
        logging.error(f"Failed to load extenstion {cog} with \n {e}")

  async def reload_cogs(self):
    reload(cogs)
    reload(functions)

    for i in functions.modules:
      if not i.startswith("_"):
        reload(getattr(functions, i))

    for i in cogs.default:
      self.reload_extension(f"cogs.{i}")

  async def on_message(self, ctx):
    if ctx.author.bot:
      return

    await self.process_commands(ctx)

  async def on_error(self, event_method, *args, **kwargs):
    return await self.get_cog(functions.config.reloadable_bot).on_error(event_method, *args, **kwargs)

  async def close(self):
    await super().close()


if __name__ == "__main__":
  print(f"Python version: {sys.version}")
  bot = Friday()
  if len(sys.argv) > 1:
    if sys.argv[1] == "--prod" or sys.argv[1] == "--production":
      TOKEN = os.environ.get("TOKEN")
  loop = asyncio.get_event_loop()
  try:
    loop.run_until_complete(bot.start(TOKEN, reconnect=True))
  except KeyboardInterrupt:
    # mydb.close()
    logging.info("STOPED")
    loop.run_until_complete(bot.close())
  finally:
    loop.close()
