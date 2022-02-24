import asyncio
import datetime
import logging
import os
import sys
from collections import defaultdict
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional

import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv
from typing_extensions import TYPE_CHECKING

import cogs
import functions
from functions.config import Config, ReadOnly

if TYPE_CHECKING:
  from .cogs.database import Database
  from .cogs.log import Log

load_dotenv()

TOKEN = os.environ.get('TOKENTEST')


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
        intents=discord.Intents(
            guilds=True,
            voice_states=True,
            messages=True,
            reactions=True,
            members=True,
            bans=True,
            # TODO: message_content=True,
            # invites=True,
        ),
        status=discord.Status.idle,
        owner_id=215227961048170496,
        debug_guilds=[243159711237537802],
        description=functions.config.description,
        member_cache_flags=discord.MemberCacheFlags.all(),
        chunk_guilds_at_startup=False,
        allowed_mentions=discord.AllowedMentions(roles=False, everyone=False, users=True),
        enable_debug_events=True,
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

    # shard_id: List[datetime.datetime]
    # shows the last attempted IDENTIFYs and RESUMEs
    self.resumes = defaultdict(list)
    self.identifies = defaultdict(list)

    self.blacklist = Config("blacklist.json")

    self.load_extension("cogs.database")
    self.load_extension("cogs.log")
    self.loop.run_until_complete(self.setup(True))
    self.logger.info(f"Cluster Starting {kwargs.get('shard_ids', None)}, {kwargs.get('shard_count', 1)}")
    if self.should_start:
      self.run(kwargs["token"])

  def __repr__(self) -> str:
    return f"<Friday username=\"{self.user.display_name if self.user else None}\" id={self.user.id if self.user else None}>"

  @property
  def log(self) -> "Log":
    return self.get_cog("Log")

  @property
  def logger(self) -> logging.Logger:
    return self._logger

  @property
  def db(self) -> Optional["Database"]:
    return self.get_cog("Database")

  @property
  def langs(self) -> Dict[str, ReadOnly]:
    return {
        "en": ReadOnly("i18n/source/commands.json"),
        **{name: ReadOnly(f"i18n/translations/{name}/commands.json") for name in os.listdir("./i18n/translations")}
    }

  async def get_lang(self, msg: discord.Message) -> ReadOnly:
    if msg.guild is None:
      return self.langs["en"]
    if not self.log:
      return self.langs.get(msg.guild.preferred_locale[:2], "en")
    return self.langs.get((await self.log.get_guild_config(msg.guild.id)).lang)

  async def get_context(self, message, *, cls=None) -> functions.MyContext:
    return await super().get_context(message, cls=functions.MyContext)

  async def setup(self, load_extentions: bool = False):
    self.session: aiohttp.ClientSession() = aiohttp.ClientSession(loop=self.loop)

    # Should replace with a json file at some point
    for guild_id, prefix in await self.db.query("SELECT id,prefix FROM servers WHERE prefix!=$1::text", "!"):
      self.prefixes[int(guild_id, base=10)] = prefix

    if load_extentions:
      for cog in [*cogs.default, *cogs.spice]:
        path = "spice.cogs." if cog.lower() in cogs.spice else "cogs."
        try:
          self.load_extension(f"{path}{cog}")
        except Exception as e:
          self.logger.error(f"Failed to load extenstion {cog} with \n {e}")

  def _clear_gateway_data(self):
    one_week_ago = discord.utils.utcnow() - datetime.timedelta(days=7)
    for shard_id, dates in self.identifies.items():
      to_remove = [index for index, dt in enumerate(dates) if dt < one_week_ago]
      for index in reversed(to_remove):
        del dates[index]

    for shard_id, dates in self.resumes.items():
      to_remove = [index for index, dt in enumerate(dates) if dt < one_week_ago]
      for index in reversed(to_remove):
        del dates[index]

  async def before_identify_hook(self, shard_id, *, initial):
    self._clear_gateway_data()
    self.identifies[shard_id].append(discord.utils.utcnow())
    await super().before_identify_hook(shard_id, initial=initial)

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
  max_bytes = 8 * 1024 * 1024  # 8 MiB
  logging.getLogger("discord").setLevel(logging.INFO)
  logging.getLogger("discord.http").setLevel(logging.WARNING)

  log = logging.getLogger("Friday")
  log.setLevel(logging.INFO)
  filehandler = RotatingFileHandler(filename="logging.log", encoding="utf-8", mode="w", maxBytes=max_bytes, backupCount=5)
  formatter = logging.Formatter("%(levelname)s:%(name)s: %(message)s")
  filehandler.setFormatter(logging.Formatter("%(asctime)s:%(name)s:%(levelname)-8s%(message)s"))
  handler = logging.StreamHandler(sys.stdout)
  handler.setFormatter(formatter)
  log.addHandler(handler)
  log.addHandler(filehandler)
  handler.setFormatter(formatter)

  bot = Friday(logger=log)
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
