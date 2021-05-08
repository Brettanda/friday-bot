# from functions.mysql_connection import mydb_connect, query
# from functions import MessageColors, embed, exceptions, relay_info
import functions
import cogs
from importlib import reload
import asyncio
import datetime
import logging
import os
import sys

import discord
from discord.ext import commands
# from discord_slash import SlashCommand
from dotenv import load_dotenv

load_dotenv()


# from chatml import queryGen
# from chatml import queryIntents
# from cogs.cleanup import get_delete_time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(name)s:%(levelname)-8s%(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
    filemode="w",
    filename="logging.log"
)

TOKEN = os.environ.get('TOKENTEST')

songqueue = {}
dead_nodes_sent = False


async def get_prefix(bot, message):
  return bot.get_guild_prefix(message.guild.id)


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
        fetch_offline_members=False,
        allowed_mentions=functions.config.allowed_mentions,
        heartbeat_timeout=150.0
    )

    self.restartPending = False
    self.prod = True if len(sys.argv) > 1 and (sys.argv[1] == "--prod" or sys.argv[1] == "--production") else False

    self.ready = False

    for cog in cogs.default:
      self.load_extension(f"cogs.{cog}")

    self.add_check(
        commands.bot_has_permissions(
            send_messages=True,
            read_messages=True,
            embed_links=True,
            read_message_history=True,
            add_reactions=True,
            manage_messages=True
        ).predicate
    )

  async def get_context(self, message, *, cls=functions.MyContext):
    return await super().get_context(message, cls=cls)

  async def reload_cogs(self):
    self.ready = False

    reload(cogs)
    reload(functions)

    for i in functions.modules:
      if not i.startswith("_"):
        reload(getattr(functions, i))

    for i in cogs.default:
      self.reload_extension(f"cogs.{i}")

  async def on_ready(self):
    self.ready = True

  # @property
  # def enabled(self):
  #   for cog in self.cogs.values():
  #     try:
  #       if not cog.ready:
  #         return False
  #     except AttributeError:
  #       pass
  #   return self.ready

  async def on_message(self, ctx):
    if ctx.author.bot:
      return

    await self.process_commands(ctx)

  async def process_commands(self, message):
    ctx = await self.get_context(message)

    if ctx.command is None:
      return

    bucket = self.spam_control.get_bucket(message)
    current = message.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()
    retry_after = bucket.update_rate_limit(current)
    author_id = message.author.id
    if retry_after and author_id != self.owner_id:
      return await self.log_spammer(ctx, message, retry_after)

    await self.invoke(ctx)

  async def close(self):
    await super().close()
    await self.session.close()


if __name__ == "__main__":
  print(f"Python version: {sys.version}")
  bot = Friday()
  if len(sys.argv) > 1:
    if sys.argv[1] == "--prod" or sys.argv[1] == "--production":
      TOKEN = os.environ.get("TOKEN")
  loop = asyncio.get_event_loop()
  try:
    loop.run_until_complete(bot.start(TOKEN, bot=True, reconnect=True))
  except KeyboardInterrupt:
    # mydb.close()
    logging.info("STOPED")
    loop.run_until_complete(bot.close())
  finally:
    loop.close()
