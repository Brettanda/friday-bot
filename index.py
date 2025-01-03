from __future__ import annotations

import asyncio
import datetime
import logging
import multiprocessing
import os
import sys
import traceback
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Any, AsyncIterator, Iterable, Optional

import aiohttp
import asyncpg
import click
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from topgg.webhook import WebhookManager

import cogs
import functions
from cogs.support import Support
# from cogs.sharding import Sharding
from functions.config import Config
from functions.db import Migrations
from functions.languages import load_languages

if TYPE_CHECKING:
  from concurrent.futures import ThreadPoolExecutor

  from i18n import I18n
  from launcher import Cluster

  from .cogs.database import Database
  from .cogs.dbl import TopGG
  from .cogs.log import Log
  from .cogs.patreons import Patreons
  from .cogs.reminder import Reminder
  from .cogs.sharding import Event
  from .cogs.chat import Chat


load_dotenv()

log = logging.getLogger(__name__)


class Translator(app_commands.Translator):
  async def translate(self, string: app_commands.locale_str, locale: discord.Locale, ctx: app_commands.TranslationContext) -> Optional[str]:
    lang: str = locale.value.split("-")[0]
    data = ctx.data
    cog = getattr(data, "binding", None) or (getattr(data, "commands", None) and data.commands[0].binding) or (getattr(data, "command", None) and data.command.binding)
    cog_name = cog.__class__.__name__.lower()
    if cog is None:
      return None
    lang_file: dict[str, I18n] = cog.bot.language_files
    try:
      c = lang_file[lang][cog_name]
      trans = None
      if ctx.location.name in ("command_name", "command_description"):
        command_name = data.name.lower()
        parent_name = data.parent and data.parent.name
        if parent_name is not None:
          c = c[parent_name]["commands"][command_name]
        else:
          c = c[command_name]
        if ctx.location.name == "command_name":
          trans = c["command_name"].translate(str.maketrans("", "", r"""!"#$%&'()*+,./:;<=>?@[\]^`{|}~""")).lower().replace(" ", "_")
        elif ctx.location.name == "command_description":
          trans = c["help"]
      elif ctx.location.name in ("group_name", "group_description"):
        command_name = data.name.lower()
        c = c[command_name]
        if ctx.location.name == "group_name":
          trans = c["command_name"].translate(str.maketrans("", "", r"""!"#$%&'()*+,./:;<=>?@[\]^`{|}~""")).lower().replace(" ", "_")
        elif ctx.location.name == "group_description":
          # trans = c[command_name]["help"]
          trans = c.help
      elif ctx.location.name in ("parameter_name", "parameter_description"):
        group_name = data.command.parent and data.command.parent.name
        command_name = data.command.name.lower()
        param_name = data.name.lower()
        try:
          if group_name is not None:
            c = c[group_name]["commands"][command_name]["parameters"][param_name]
          else:
            c = c[command_name]["parameters"][param_name]
        except KeyError as e:
          if lang == "en":
            log.error(str(e))
          raise e
        if ctx.location.name == "parameter_name":
          trans = c["name"].lower().replace(" ", "_")
        elif ctx.location.name == "parameter_description":
          trans = c["description"]
      return trans if trans and trans != string.message else None
    except KeyError:
      return None


async def get_prefix(bot: Friday, message: discord.Message):
  if message.guild is not None:
    return bot.prefixes[message.guild.id]
  return functions.config.defaultPrefix


class Friday(commands.AutoShardedBot):
  """Friday is a discord bot that is designed to be a flexible and easy to use bot."""

  user: discord.ClientUser
  pool: asyncpg.Pool
  topgg_webhook: WebhookManager
  command_stats: Counter[str]
  socket_stats: Counter[str]
  chat_stats: Counter[int]
  logging_handler: Any
  bot_app_info: discord.AppInfo
  uptime: datetime.datetime
  chat_repeat_counter: Counter[int]
  old_help_command: commands.HelpCommand | None
  language_files: dict[str, I18n]

  def __init__(self, **kwargs):
    self.cluster: Cluster | None = kwargs.pop("cluster", None)
    self.cluster_name: str | None = kwargs.pop("cluster_name", None)
    self.cluster_idx: int = kwargs.pop("cluster_idx", 0)
    self.openai_api_lock: asyncio.Semaphore = kwargs.pop("openai_api_lock", asyncio.Semaphore(2))
    self.tasks: multiprocessing.Queue[Event] | None = kwargs.pop("tasks", None)
    self.tasks_to_complete: multiprocessing.Queue[Event] | None = kwargs.pop("tasks_to_complete", None)
    self.task_executer: ThreadPoolExecutor | None = kwargs.pop("task_executer", None)

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
        ),
        status=discord.Status.idle,
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
    self.ready = False
    self.testing = False

    # shard_id: List[datetime.datetime]
    # shows the last attempted IDENTIFYs and RESUMEs
    self.resumes: defaultdict[int, list[datetime.datetime]] = defaultdict(list)
    self.identifies: defaultdict[int, list[datetime.datetime]] = defaultdict(list)

  def __repr__(self) -> str:
    return f"<Friday username=\"{self.user.display_name if self.user else None}\" id={self.user.id if self.user else None}>"

  @property
  def prod(self) -> bool:
    return self.user.id == 476303446547365891  # Prod bot

  @property
  def canary(self) -> bool:
    return self.user.id == 760615464300445726  # Canary bot id

  @classmethod
  def from_launcher(
      cls,
      *,
      cluster: Cluster | None = None,
      cluster_name: str = None,
      cluster_idx: int = 0,
      tasks: multiprocessing.Queue[Event] = None,
      tasks_to_complete: multiprocessing.Queue[Event] = None,
      task_executer: ThreadPoolExecutor = None,
      openai_api_lock: asyncio.Semaphore = asyncio.Semaphore(2),
      **kwargs
  ) -> None:
    self = cls(
        cluster=cluster,
        cluster_name=cluster_name,
        cluster_idx=cluster_idx,
        tasks=tasks,
        tasks_to_complete=tasks_to_complete,
        task_executer=task_executer,
        openai_api_lock=openai_api_lock
    )
    log.info(f"Cluster Starting {kwargs.get('shard_ids', None)}, {kwargs.get('shard_count', 1)}")
    self.run(kwargs["token"])

  async def get_context(self, origin: discord.Message | discord.Interaction, /, *, cls=None) -> functions.MyContext:
    return await super().get_context(origin, cls=cls or functions.MyContext)

  async def setup_hook(self) -> None:
    self.session = aiohttp.ClientSession()

    self.blacklist: Config[bool] = Config("blacklist.json")

    await load_languages(self)

    self.languages = Config("languages.json")

    await self.tree.set_translator(Translator())

    # await self.load_extension("cogs.database")
    await self.load_extension("cogs.log")

    self.bot_app_info = await self.application_info()
    self.owner_id = self.bot_app_info.team and self.bot_app_info.team.owner_id or self.bot_app_info.owner.id
    self.owner = self.get_user(self.owner_id) or await self.fetch_user(self.owner_id)

    # Should replace with a json file at some point
    for guild_id, prefix in await self.pool.fetch("SELECT id,prefix FROM servers WHERE prefix!=$1::text", "!"):
      self.prefixes[int(guild_id, base=10)] = prefix

    for cog in [*cogs.default, *cogs.spice]:
      path = "spice.cogs." if cog.lower() in cogs.spice else "cogs."
      await self.load_extension(f"{path}{cog}")

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
    if hasattr(self, "session"):
      await self.session.close()

  async def start(self) -> None:
    await super().start(os.environ['TOKEN'], reconnect=True)

  @property
  def log(self) -> Log:
    return self.get_cog("Log")  # type: ignore

  @property
  def db(self) -> Optional[Database]:
    return self.get_cog("Database")  # type: ignore

  @property
  def reminder(self) -> Optional[Reminder]:
    return self.get_cog("Reminder")  # type: ignore

  @property
  def dbl(self) -> Optional[TopGG]:
    return self.get_cog("TopGG")  # type: ignore

  @property
  def patreon(self) -> Optional[Patreons]:
    return self.get_cog("Patreons")  # type: ignore

  @property
  def support(self) -> Optional[Support]:
    return self.get_cog("Support")  # type: ignore

  @property
  def chat(self) -> Optional[Chat]:
    return self.get_cog("Chat")  # type: ignore

  # @property
  # def sharding(self) -> Optional[Sharding]:
  #   return self.get_cog("Sharding")  # type: ignore


async def run_bot():
  log = logging.getLogger()
  try:
    pool = await functions.db.create_pool()
  except Exception:
    click.echo('Could not set up PostgreSQL. Exiting.', file=sys.stderr)
    log.exception('Could not set up PostgreSQL. Exiting.')
    return

  async with Friday() as bot:
    bot.pool = pool
    await bot.start()


@click.group(invoke_without_command=True, options_metavar='[options]')
@click.pass_context
@click.option('--prod', help='Run in production mode.', is_flag=True)
@click.option('--canary', help='Run in production mode.', is_flag=True)
def main(ctx, prod, canary):
  """Launches the bot."""
  if ctx.invoked_subcommand is None:
    print(f"Python version: {sys.version}")
    from launcher import setup_logging

    with setup_logging():
      asyncio.run(run_bot(), debug=True)


@main.group(short_help='database stuff', options_metavar='[options]')
def db():
  pass


async def ensure_uri_can_run() -> bool:
  connection: asyncpg.Connection = await asyncpg.connect(os.environ["DBURL"])
  await connection.close()
  return True


# @db.command()
# @click.option('--reason', '-r', help='The reason for this revision.', default='Initial migration')
# def init(reason):
#   """Initializes the database and creates the initial revision."""

#   asyncio.run(ensure_uri_can_run())

#   migrations = Migrations()
#   migrations.database_uri = os.environ["DBURL"]
#   revision = migrations.create_revision(reason)
#   click.echo(f'created revision V{revision.version!r}')
#   click.secho('hint: use the `upgrade` command to apply', fg='yellow')


@db.command()
@click.option('--reason', '-r', help='The reason for this revision.', required=True)
def migrate(reason):
  """Creates a new revision for you to edit."""
  asyncio.run(ensure_uri_can_run())

  migrations = Migrations()
  if migrations.is_next_revision_taken():
    click.echo('an unapplied migration already exists for the next version, exiting')
    click.secho('hint: apply pending migrations with the `upgrade` command', bold=True)
    return

  revision = migrations.create_revision(reason)
  click.echo(f'Created revision V{revision.version!r}')


async def run_upgrade(migrations: Migrations) -> int:
  connection: asyncpg.Connection = await asyncpg.connect(migrations.database_uri)
  return await migrations.upgrade(connection)


@db.command()
@click.option('--sql', help='Print the SQL instead of executing it', is_flag=True)
def upgrade(sql):
  """Upgrades the database at the given revision (if any)."""
  asyncio.run(ensure_uri_can_run())

  migrations = Migrations()

  if sql:
    migrations.display()
    return

  try:
    applied = asyncio.run(run_upgrade(migrations))
  except Exception:
    traceback.print_exc()
    click.secho('failed to apply migrations due to error', fg='red')
  else:
    click.secho(f'Applied {applied} revisions(s)', fg='green')


@db.command()
def current():
  """Shows the current active revision version"""
  migrations = Migrations()
  click.echo(f'Version {migrations.version}')


@db.command()
@click.option('--reverse', help='Print in reverse order (oldest first).', is_flag=True)
def logs(reverse):
  """Displays the revision history"""
  migrations = Migrations()
  # Revisions is oldest first already
  revs = reversed(migrations.ordered_revisions) if not reverse else migrations.ordered_revisions
  for rev in revs:
    as_yellow = click.style(f'V{rev.version:>03}', fg='yellow')
    click.echo(f'{as_yellow} {rev.description.replace("_", " ")}')


if __name__ == '__main__':
  main()
