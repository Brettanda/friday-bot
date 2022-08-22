from __future__ import annotations

import asyncio
import datetime
import gc
import io
import json
import logging
import os
import re
import sys
import textwrap
import traceback
from collections import Counter
from typing import TYPE_CHECKING, Optional, Any, TypedDict
from typing_extensions import Annotated

import asyncpg
import discord
import psutil
import wavelink
from discord.ext import commands, tasks

from functions import embed, time

if TYPE_CHECKING:

  from functions import MyContext
  from index import Friday

  from .chat import Chat

  class DataCommandsBatchEntry(TypedDict):
    guild: Optional[str]
    channel: str
    author: str
    used: str
    prefix: str
    command: str
    failed: bool

  class DataJoinsBatchEntry(TypedDict):
    guild: str
    time: str
    joined: Optional[bool]
    current_count: int

  class DataChatsBatchEntry(TypedDict):
    guild: Optional[str]
    channel: str
    author: str
    used: str
    user_msg: str
    bot_msg: Optional[str]
    failed: bool
    filtered: Optional[int]
    persona: str
    prompt: Optional[str]

log = logging.getLogger(__name__)


class GatewayHandler(logging.Handler):
  def __init__(self, cog: Stats):
    self.cog: Stats = cog
    super().__init__(logging.INFO)

  def filter(self, record: logging.LogRecord) -> bool:
    try:
      return record.name == "discord.gateway" or "Shard ID" in record.msg or "Websocket closed" in record.msg
    except TypeError:
      return False

  def emit(self, record: logging.LogRecord) -> None:
    self.cog.add_record(record)


class TabularData:
  def __init__(self):
    self._widths = []
    self._columns = []
    self._rows = []

  def set_columns(self, columns):
    self._columns = columns
    self._widths = [len(c) + 2 for c in columns]

  def add_row(self, row):
    rows = [str(r) for r in row]
    self._rows.append(rows)
    for index, element in enumerate(rows):
      width = len(element) + 2
      if width > self._widths[index]:
        self._widths[index] = width

  def add_rows(self, rows):
    for row in rows:
      self.add_row(row)

  def render(self):
    """Renders a table in rST format.
    Example:
    +-------+-----+
    | Name  | Age |
    +-------+-----+
    | Alice | 24  |
    |  Bob  | 19  |
    +-------+-----+
    """

    sep = '+'.join('-' * w for w in self._widths)
    sep = f'+{sep}+'

    to_draw = [sep]

    def get_entry(d):
      elem = '|'.join(f'{e:^{self._widths[i]}}' for i, e in enumerate(d))
      elem = "\\n".join(elem.splitlines())
      return f'|{elem}|'

    to_draw.append(get_entry(self._columns))
    to_draw.append(sep)

    for row in self._rows:
      to_draw.append(get_entry(row))

    to_draw.append(sep)
    return '\n'.join(to_draw)


_INVITE_REGEX = re.compile(r'(?:https?:\/\/)?discord(?:\.gg|\.com|app\.com\/invite)?\/[A-Za-z0-9]+')


def censor_invite(obj, *, _regex=_INVITE_REGEX) -> str:
  return _regex.sub('[censored-invite]', str(obj))


def hex_value(arg) -> int:
  return int(arg, base=16)


def object_at(addr) -> Optional[Any]:
  for o in gc.get_objects():
    if id(o) == addr:
      return o
  return None


class Stats(commands.Cog, command_attrs=dict(hidden=True)):
  def __init__(self, bot: Friday):
    self.bot: Friday = bot
    self.process = psutil.Process()
    self._batch_commands_lock, self._batch_chats_lock, self._batch_joins_lock = asyncio.Lock(), asyncio.Lock(), asyncio.Lock()
    self._data_commands_batch: list[DataCommandsBatchEntry] = []
    self._data_chats_batch: list[DataChatsBatchEntry] = []
    self._data_joins_batch: list[DataJoinsBatchEntry] = []
    self.bulk_insert_commands_loop.add_exception_type(asyncpg.PostgresConnectionError)

    self.bulk_insert_chats_loop.add_exception_type(asyncpg.PostgresConnectionError)

    self.bulk_insert_joins_loop.add_exception_type(asyncpg.PostgresConnectionError)

    self._gateway_queue = asyncio.Queue()

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def cog_check(self, ctx: MyContext) -> bool:
    is_owner = await self.bot.is_owner(ctx.author)
    if ctx.author.id != 892865928520413245 and not is_owner:
      raise commands.NotOwner()
    if ctx.guild and not ctx.bot_permissions.attach_files:
      raise commands.BotMissingPermissions(["attach_files"])
    return True

  async def bulk_insert_commands(self):
    query = """INSERT INTO commands (guild_id, channel_id, author_id, used, prefix, command, failed)
               SELECT x.guild, x.channel, x.author, x.used, x.prefix, x.command, x.failed
               FROM jsonb_to_recordset($1::jsonb) AS
               x(guild TEXT, channel TEXT, author TEXT, used TIMESTAMP, prefix TEXT, command TEXT, failed BOOLEAN)"""

    if self._data_commands_batch:
      await self.bot.pool.execute(query, json.dumps(self._data_commands_batch))
      total = len(self._data_commands_batch)
      if total > 1:
        log.info(f"Inserted {total} commands into the database")
      self._data_commands_batch.clear()

  async def bulk_insert_joins(self):
    query = """INSERT INTO joined (guild_id, joined, current_count, time)
               SELECT x.guild, x.joined, x.current_count, x.time
               FROM jsonb_to_recordset($1::jsonb) AS
               x(guild TEXT, joined BOOLEAN, current_count BIGINT, time TIMESTAMP)"""

    if self._data_joins_batch:
      await self.bot.pool.execute(query, json.dumps(self._data_joins_batch))
      total = len(self._data_joins_batch)
      if total > 1:
        log.info(f"Inserted {total} guild counts into the database")
      self._data_joins_batch.clear()

  async def bulk_insert_chats(self):
    query = """INSERT INTO chats (guild_id, channel_id, author_id, used, user_msg, bot_msg, failed, filtered, prompt)
               SELECT x.guild, x.channel, x.author, x.used, x.user_msg, x.bot_msg, x.failed, x.filtered, x.prompt
               FROM jsonb_to_recordset($1::jsonb) AS
               x(guild TEXT, channel TEXT, author TEXT, used TIMESTAMP, user_msg TEXT, bot_msg TEXT, failed BOOLEAN, filtered INT, prompt TEXT)"""

    if self._data_chats_batch:
      await self.bot.pool.execute(query, json.dumps(self._data_chats_batch))
      total = len(self._data_chats_batch)
      if total > 1:
        log.info(f"Inserted {total} chats into the database")
      self._data_chats_batch.clear()

  async def cog_load(self):
    self.bulk_insert_commands_loop.start()
    self.bulk_insert_chats_loop.start()
    self.bulk_insert_joins_loop.start()
    self.gateway_worker.start()

  async def cog_unload(self):
    self.bulk_insert_commands_loop.stop()
    self.bulk_insert_chats_loop.stop()
    self.bulk_insert_joins_loop.stop()
    self.gateway_worker.cancel()

  @tasks.loop(seconds=10.0)
  async def bulk_insert_commands_loop(self):
    async with self._batch_commands_lock:
      await self.bulk_insert_commands()

  @tasks.loop(seconds=10.0)
  async def bulk_insert_joins_loop(self):
    async with self._batch_joins_lock:
      await self.bulk_insert_joins()

  @tasks.loop(seconds=10.0)
  async def bulk_insert_chats_loop(self):
    async with self._batch_chats_lock:
      await self.bulk_insert_chats()

  @tasks.loop(seconds=0.0)
  async def gateway_worker(self):
    record = await self._gateway_queue.get()
    await self.notify_gateway_status(record)

  @discord.utils.cached_property
  def webhook(self):
    wh_id, wh_token = os.environ["WEBHOOKINFOID"], os.environ["WEBHOOKINFOTOKEN"]
    return discord.Webhook.partial(id=wh_id, token=wh_token, session=self.bot.session)  # type: ignore

  async def register_command(self, ctx: MyContext):
    if ctx.command is None:
      return

    command = ctx.command.qualified_name
    self.bot.command_stats[command] += 1
    message = ctx.message
    destination = None
    if ctx.guild is None:
      destination = "Private Message"
      guild_id = None
    else:
      destination = f"#{message.channel} ({message.guild})"
      guild_id = ctx.guild.id

    command_with_args = message.content or f"{ctx.clean_prefix}{command} {' '.join([a for a in ctx.args[2:] if a])}{' ' and ' '.join([str(k) for k in ctx.kwargs.values()])}"
    log.info(f'{message.author} [{ctx.lang_code}] in {destination}: {command_with_args}')
    async with self._batch_commands_lock:
      self._data_commands_batch.append({
          'guild': str(guild_id),
          'channel': str(ctx.channel.id),
          'author': str(ctx.author.id),
          'used': message.created_at.isoformat(),
          'prefix': ctx.prefix,
          'command': command,
          'failed': ctx.command_failed,
      })

  async def register_joins(self, guild: discord.Guild, joined: Optional[bool] = None):
    async with self._batch_joins_lock:
      self._data_joins_batch.append({
          'guild': str(guild.id),
          'time': discord.utils.utcnow().isoformat(),
          'joined': joined,
          'current_count': len(self.bot.guilds),
      })

  async def register_chat(self, user_msg: discord.Message, bot_msg: Optional[discord.Message], failed: bool, *, prompt: str = None, filtered: Optional[int] = None, persona: Annotated[str, Optional[str]] = "friday"):
    user_message = user_msg.clean_content
    bot_message = bot_msg and bot_msg.clean_content

    self.bot.chat_stats[user_msg.author.id] += 1
    if user_msg.guild is None:
      guild_id = None
    else:
      guild_id = user_msg.guild.id

    async with self._batch_chats_lock:
      self._data_chats_batch.append({
          'guild': str(guild_id),
          'channel': str(user_msg.channel.id),
          'author': str(user_msg.author.id),
          'used': user_msg.created_at.isoformat(),
          'user_msg': user_message,
          'bot_msg': bot_message,
          'failed': failed,
          'filtered': filtered,
          'persona': persona,
          'prompt': prompt,
      })

  @commands.Cog.listener()
  async def on_command_completion(self, ctx):
    await self.register_command(ctx)

  @commands.Cog.listener()
  async def on_guild_join(self, guild: discord.Guild):
    await self.register_joins(guild, True)

  @commands.Cog.listener()
  async def on_guild_remove(self, guild: discord.Guild):
    await self.register_joins(guild, False)

  @commands.Cog.listener()
  async def on_chat_completion(self, user_msg: discord.Message, bot_msg: discord.Message, failed: bool, *, prompt: str = None, filtered: Optional[int] = None, persona: Annotated[str, Optional[str]] = "friday"):
    await self.register_chat(user_msg, bot_msg, failed, filtered=filtered, persona=persona, prompt=prompt)

  @commands.Cog.listener()
  async def on_socket_event_type(self, event_type):
    self.bot.socket_stats[event_type] += 1

  @commands.group("commandstats", invoke_without_command=True)
  async def commandstats(self, ctx, limit=20):
    counter = self.bot.command_stats
    width = len(max(counter, key=len))

    if limit > 0:
      common = counter.most_common(limit)
    else:
      common = counter.most_common()[limit:]

    output = '\n'.join(f"{k:<{width}}: {c}" for k, c in common)

    await ctx.send(f"```\n{output}\n```")

  @commands.group("chatstats", invoke_without_command=True)
  async def chatstats(self, ctx: MyContext):
    delta = discord.utils.utcnow() - self.bot.uptime
    minutes = delta.total_seconds() / 60
    total = sum(self.bot.chat_stats.values())
    cpm = total / minutes

    counter_message = textwrap.shorten(f"{self.bot.chat_stats}", width=1910)

    chat_cog: Optional[Chat] = self.bot.get_cog("Chat")  # type: ignore
    if chat_cog is None:
      return await ctx.send(embed=embed(title="Chat functionality is not currently available. Please try again later."))

    rate_control = chat_cog._spam_check
    free_rate = [str(key) for key, value in rate_control.free._cache.items() if value._tokens == 0]
    voted_rate = [str(key) for key, value in rate_control.voted._cache.items() if value._tokens == 0]
    patron_rate = [str(key) for key, value in rate_control.patron._cache.items() if value._tokens == 0]
    await ctx.send(f"{total:,} messages ({cpm:.2f}/min)\n**Rate-limits**\nFree: {len(free_rate)} users\nVoted: {len(voted_rate)} users\nPatron: {len(patron_rate)} users\n{counter_message}")

  @commands.command("socketstats")
  async def socketstats(self, ctx: MyContext):
    delta = discord.utils.utcnow() - self.bot.uptime
    minutes = delta.total_seconds() / 60
    total = sum(self.bot.socket_stats.values())
    cpm = total / minutes
    await ctx.send(f"{total:,} socket events observed ({cpm:.2f}/min):\n{self.bot.socket_stats}")

  def censor_object(self, obj):
    if not isinstance(obj, str) and obj.id in self.bot.blacklist:
      return "[censored]"
    return censor_invite(obj)

  medal_lookup = (
        "\N{FIRST PLACE MEDAL}",
        "\N{SECOND PLACE MEDAL}",
        "\N{THIRD PLACE MEDAL}",
        "\N{SPORTS MEDAL}",
        "\N{SPORTS MEDAL}"
  )

  @chatstats.command("global")
  async def chatstats_global(self, ctx: MyContext):
    query = """SELECT COUNT(*) FROM chats;"""
    total = await ctx.db.fetchrow(query)

    e = discord.Embed(title="Chat Stats", colour=discord.Colour.blurple())
    e.description = f"{total[0]:,} chats used."

    # query = """SELECT command, COUNT(*) AS "uses"
    #            FROM chats
    #            GROUP BY command
    #            ORDER BY uses DESC
    #            LIMIT 5;"""

    # records = await ctx.db.fetch(query)
    # value = "\n".join(f"{self.medal_lookup[i]}: {command} ({uses} uses)" for (i, (command, uses)) in enumerate(records))
    # e.add_field(name="Top Commands", value=value, inline=False)

    query = """SELECT guild_id, COUNT(*) AS "uses"
               FROM chats
               GROUP BY guild_id
               ORDER BY uses DESC
               LIMIT 5;"""

    records = await ctx.db.fetch(query)
    value = []
    for (i, (guild_id, uses)) in enumerate(records):
      if guild_id is None:
        guild = "Private Message"
      else:
        guild = self.censor_object(self.bot.get_guild(guild_id.isdigit() and int(guild_id, base=10)) or f"<Unknown {guild_id}>")

      emoji = self.medal_lookup[i]
      value.append(f"{emoji}: {guild} ({uses} uses)")

    e.add_field(name="Top Guilds", value="\n".join(value), inline=False)

    query = """SELECT author_id, COUNT(*) AS "uses"
               FROM chats
               GROUP BY author_id
               ORDER BY "uses" DESC
               LIMIT 5;"""

    records = await ctx.db.fetch(query)
    value = []
    for (i, (author_id, uses)) in enumerate(records):
      user = self.censor_object(self.bot.get_user(author_id.isdigit() and int(author_id, base=10)) or f"<Unknown {author_id}>")
      emoji = self.medal_lookup[i]
      value.append(f"{emoji}: {user} ({uses} uses)")

    e.add_field(name="Top Users", value="\n".join(value), inline=False)
    await ctx.send(embed=e)

  @chatstats.command("today")
  async def chatstats_today(self, ctx: MyContext):
    query = """SELECT COUNT(*) FROM chats WHERE used > (CURRENT_TIMESTAMP - INTERVAL '1 day');"""
    total = await ctx.db.fetchval(query)

    e = discord.Embed(title="Last 24 Hour Chat Stats", colour=discord.Colour.blurple())
    e.description = f"{total:,} chats used today."

    query = """SELECT guild_id, COUNT(*) AS "uses"
                   FROM chats
                   WHERE used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                   GROUP BY guild_id
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

    records = await ctx.db.fetch(query)
    value = []
    for (index, (guild_id, uses)) in enumerate(records):
      if guild_id is None:
        guild = 'Private Message'
      else:
        guild = self.censor_object(self.bot.get_guild(guild_id.isdigit() and int(guild_id, base=10)) or f'<Unknown {guild_id}>')
      emoji = self.medal_lookup[index]
      value.append(f'{emoji}: {guild} ({uses} uses)')

    e.add_field(name='Top Guilds', value='\n'.join(value), inline=False)

    query = """SELECT author_id, COUNT(*) AS "uses"
                  FROM chats
                  WHERE used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                  GROUP BY author_id
                  ORDER BY "uses" DESC
                  LIMIT 5;
              """

    records = await ctx.db.fetch(query)
    value = []
    for (index, (author_id, uses)) in enumerate(records):
      user = self.censor_object(self.bot.get_user(author_id.isdigit() and int(author_id, base=10)) or f'<Unknown {author_id}>')
      emoji = self.medal_lookup[index]
      value.append(f'{emoji}: {user} ({uses} uses)')

    e.add_field(name='Top Users', value='\n'.join(value), inline=False)
    await ctx.send(embed=e)

  @commandstats.command("global")
  async def commandstats_global(self, ctx: MyContext):
    query = """SELECT COUNT(*) FROM commands;"""
    total = await ctx.db.fetchrow(query)

    e = discord.Embed(title="Command Stats", colour=discord.Colour.blurple())
    e.description = f"{total[0]:,} commands used."

    query = """SELECT command, COUNT(*) AS "uses"
               FROM commands
               GROUP BY command
               ORDER BY uses DESC
               LIMIT 5;"""

    records = await ctx.db.fetch(query)
    value = "\n".join(f"{self.medal_lookup[i]}: {command} ({uses} uses)" for (i, (command, uses)) in enumerate(records))
    e.add_field(name="Top Commands", value=value, inline=False)

    query = """SELECT guild_id, COUNT(*) AS "uses"
               FROM commands
               GROUP BY guild_id
               ORDER BY uses DESC
               LIMIT 5;"""

    records = await ctx.db.fetch(query)
    value = []
    for (i, (guild_id, uses)) in enumerate(records):
      if guild_id is None:
        guild = "Private Message"
      else:
        guild = self.censor_object(self.bot.get_guild(guild_id.isdigit() and int(guild_id, base=10)) or f"<Unknown {guild_id}>")

      emoji = self.medal_lookup[i]
      value.append(f"{emoji}: {guild} ({uses} uses)")

    e.add_field(name="Top Guilds", value="\n".join(value), inline=False)

    query = """SELECT author_id, COUNT(*) AS "uses"
               FROM commands
               GROUP BY author_id
               ORDER BY "uses" DESC
               LIMIT 5;"""

    records = await ctx.db.fetch(query)
    value = []
    for (i, (author_id, uses)) in enumerate(records):
      user = self.censor_object(self.bot.get_user(author_id.isdigit() and int(author_id, base=10)) or f"<Unknown {author_id}>")
      emoji = self.medal_lookup[i]
      value.append(f"{emoji}: {user} ({uses} uses)")

    e.add_field(name="Top Users", value="\n".join(value), inline=False)
    await ctx.send(embed=e)

  @commandstats.command("today")
  async def commandstats_today(self, ctx: MyContext):
    query = """SELECT failed, COUNT(*) FROM commands WHERE used > (CURRENT_TIMESTAMP - INTERVAL '1 day') GROUP BY failed;"""
    total = await ctx.db.fetch(query)
    failed, success, question = 0, 0, 0
    for state, count in total:
      if state is False:
        success += count
      elif state is True:
        failed += count
      else:
        question += count

    e = discord.Embed(title="Last 24 Hour Command Stats", colour=discord.Colour.blurple())
    e.description = f"{failed + success + question:,} commands used today." \
                    f"({success} succeeded, {failed} failed, {question} unknown)"

    query = """SELECT command, COUNT(*) AS "uses"
                   FROM commands
                   WHERE used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                   GROUP BY command
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

    records = await ctx.db.fetch(query)
    value = '\n'.join(f'{self.medal_lookup[index]}: {command} ({uses} uses)' for (index, (command, uses)) in enumerate(records))
    e.add_field(name='Top Commands', value=value, inline=False)

    query = """SELECT guild_id, COUNT(*) AS "uses"
                   FROM commands
                   WHERE used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                   GROUP BY guild_id
                   ORDER BY "uses" DESC
                   LIMIT 5;
                """

    records = await ctx.db.fetch(query)
    value = []
    for (index, (guild_id, uses)) in enumerate(records):
      if guild_id is None:
        guild = 'Private Message'
      else:
        guild = self.censor_object(self.bot.get_guild(guild_id.isdigit() and int(guild_id, base=10)) or f'<Unknown {guild_id}>')
      emoji = self.medal_lookup[index]
      value.append(f'{emoji}: {guild} ({uses} uses)')

    e.add_field(name='Top Guilds', value='\n'.join(value), inline=False)

    query = """SELECT author_id, COUNT(*) AS "uses"
                  FROM commands
                  WHERE used > (CURRENT_TIMESTAMP - INTERVAL '1 day')
                  GROUP BY author_id
                  ORDER BY "uses" DESC
                  LIMIT 5;
              """

    records = await ctx.db.fetch(query)
    value = []
    for (index, (author_id, uses)) in enumerate(records):
      user = self.censor_object(self.bot.get_user(author_id.isdigit() and int(author_id, base=10)) or f'<Unknown {author_id}>')
      emoji = self.medal_lookup[index]
      value.append(f'{emoji}: {user} ({uses} uses)')

    e.add_field(name='Top Users', value='\n'.join(value), inline=False)
    await ctx.send(embed=e)

  @commandstats_today.before_invoke
  @chatstats_today.before_invoke
  @commandstats_global.before_invoke
  @chatstats_global.before_invoke
  async def before_stats_invoke(self, ctx):
    await ctx.trigger_typing()

  @commands.Cog.listener()
  async def on_command_error(self, ctx, error):
    await self.register_command(ctx)

  def add_record(self, record):
    if self.bot.prod:
      self._gateway_queue.put_nowait(record)

  async def notify_gateway_status(self, record):
    attributes = {
        'INFO': '\N{INFORMATION SOURCE}',
        'WARNING': '\N{WARNING SIGN}'
    }

    emoji = attributes.get(record.levelname, '\N{CROSS MARK}')
    dt = datetime.datetime.utcfromtimestamp(record.created)
    msg = textwrap.shorten(f'{emoji} [{time.format_dt(dt)}] `{record.msg % record.args}`', width=1990)
    await self.webhook.send(msg, username='Gateway', avatar_url='https://i.imgur.com/4PnCKB3.png')

  @commands.command("bothealth")
  async def bothealth(self, ctx: MyContext):
    """Various bot health monitoring tools."""

    # This uses a lot of private methods because there is no
    # clean way of doing this otherwise.

    HEALTHY = discord.Colour(value=0x43B581)
    UNHEALTHY = discord.Colour(value=0xF04947)
    WARNING = discord.Colour(value=0xF09E47)
    total_warnings = 0

    embed_ = discord.Embed(title='Bot Health Report', colour=HEALTHY)

    # Check the connection pool health.
    pool = self.bot.pool
    total_waiting = len(pool._queue._getters)
    current_generation = pool._generation

    description = [
        f'Total `Pool.acquire` Waiters: {total_waiting}',
        f'Current Pool Generation: {current_generation}',
        f'Connections In Use: {len(pool._holders) - pool._queue.qsize()}'
    ]

    questionable_connections = 0
    connection_value = []
    for index, holder in enumerate(pool._holders, start=1):
      generation = holder._generation
      in_use = holder._in_use is not None
      is_closed = holder._con is None or holder._con.is_closed()
      display = f'gen={holder._generation} in_use={in_use} closed={is_closed}'
      questionable_connections += any((in_use, generation != current_generation))
      connection_value.append(f'<Holder i={index} {display}>')

    joined_value = '\n'.join(connection_value)
    embed_.add_field(name='Connections', value=f'```py\n{joined_value}\n```', inline=False)

    node = wavelink.NodePool.get_node()
    embed_.add_field(name="Wavelink", value=f"```py\n<Node i=\"{node.identifier}\" reg=\"{node.region}\" players={len(node.players):,} pen={node.penalty:.3f} con={node.is_connected()}>\n```", inline=False)

    spam_control = self.bot.log.spam_control
    being_spammed = [
        str(key) for key, value in spam_control._cache.items()
        if value._tokens == 0
    ]

    description.append(f'Current Spammers: {", ".join(being_spammed) if being_spammed else "None"}')
    description.append(f'Questionable Connections: {questionable_connections}')

    total_warnings += questionable_connections
    if being_spammed:
      embed_.colour = WARNING
      total_warnings += 1

    try:
      task_retriever = asyncio.Task.all_tasks
    except AttributeError:
      # future proofing for 3.9 I guess
      task_retriever = asyncio.all_tasks

    all_tasks = task_retriever(loop=self.bot.loop)

    event_tasks = [
        t for t in all_tasks
        if 'Client._run_event' in repr(t) and not t.done()
    ]

    cogs_directory = os.path.dirname(__file__)
    tasks_directory = os.path.join('discord', 'ext', 'tasks', '__init__.py')
    inner_tasks = [
        t for t in all_tasks
        if cogs_directory in repr(t) or tasks_directory in repr(t)
    ]

    bad_inner_tasks = ", ".join(hex(id(t)) for t in inner_tasks if t.done() and t._exception is not None)
    total_warnings += bool(bad_inner_tasks)
    embed_.add_field(name='Inner Tasks', value=f'Total: {len(inner_tasks)}\nFailed: {bad_inner_tasks or "None"}')
    embed_.add_field(name='Events Waiting', value=f'Total: {len(event_tasks)}', inline=False)

    command_waiters = len(self._data_commands_batch)
    is_locked = self._batch_commands_lock.locked()
    description.append(f'Commands Waiting: {command_waiters}, Batch Locked: {is_locked}')

    chat_waiters = len(self._data_chats_batch)
    is_locked = self._batch_chats_lock.locked()
    description.append(f'Chats Waiting: {chat_waiters}, Batch Locked: {is_locked}')

    memory_usage = self.process.memory_full_info().uss / 1024**2
    total_memory = psutil.virtual_memory().total / 1024**2
    memory_percent = self.process.memory_percent()
    cpu_usage = self.process.cpu_percent() / psutil.cpu_count()
    embed_.add_field(name='Process', value=f'{memory_usage:,.2f} MiB/{total_memory/1024:,.2f} GB ({memory_percent:.3f}%)\n{cpu_usage:.3f}% CPU', inline=False)

    global_rate_limit = not self.bot.http._global_over.is_set()
    description.append(f'Global Rate Limit: {global_rate_limit}')

    if command_waiters >= 8:
      total_warnings += 1
      embed_.colour = WARNING

    if chat_waiters >= 8:
      total_warnings += 1
      embed_.colour = WARNING

    if global_rate_limit or total_warnings >= 9:
      embed_.colour = UNHEALTHY

    if not node.is_connected():
      embed_.colour = WARNING

    embed_.set_footer(text=f'{total_warnings} warning(s)')
    embed_.description = '\n'.join(description)
    await ctx.send(embed=embed_)

  @commands.command("gateway")
  async def gateway(self, ctx: MyContext):
    yesterday = discord.utils.utcnow() - datetime.timedelta(days=1)
    identifies = {
        shard_id: sum(1 for dt in dates if dt > yesterday)
        for shard_id, dates in self.bot.identifies.items()
    }

    resumes = {
        shard_id: sum(1 for dt in dates if dt > yesterday)
        for shard_id, dates in self.bot.resumes.items()
    }

    total_identifies = sum(identifies.values())
    builder = [
        f"Total RESUMEs: {sum(resumes.values())}",
        f"Total IDENTIFYs: {total_identifies}",
    ]

    shard_count = len(self.bot.shards)
    if total_identifies > (shard_count * 10):
      issues = 2 + (total_identifies // 10) - shard_count
    else:
      issues = 0

    for shard_id, shard in self.bot.shards.items():
      badge = None
      # Shard WS closed
      # Shard Task failure
      # Shard Task complete (no failure)
      if shard.is_closed():
        badge = ":spider_web:"
        issues += 1
      elif shard._parent._task and shard._parent._task.done():
        exc = shard._parent._task.exception()
        if exc is not None:
          badge = "\N{FIRE}"
          issues += 1
        else:
          badge = "\U0001f504"

      if badge is None:
        badge = "\N{OK HAND SIGN}"

      stats = []
      identify = identifies.get(shard_id, 0)
      resume = resumes.get(shard_id, 0)
      if resume != 0:
        stats.append(f"R: {resume}")
      if identify != 0:
        stats.append(f"ID: {identify}")

      if stats:
        builder.append(f"Shard ID {shard_id}: {badge} ({', '.join(stats)})")
      else:
        builder.append(f"Shard ID {shard_id}: {badge}")
    if issues == 0:
      colour = 0x43B581
    elif issues < len(self.bot.shards) // 4:
      colour = 0xF09E47
    else:
      colour = 0xF04947

    e = discord.Embed(colour=colour, title="Gateway (last 24 hours)")
    e.description = "\n".join(builder)
    e.set_footer(text=f"{issues} warning(s)")
    await ctx.send(embed=e)

  @commands.command(hidden=True, aliases=['cancel_task'])
  @commands.is_owner()
  async def debug_task(self, ctx: MyContext, memory_id: Annotated[int, hex_value]):
    """Debug a task by a memory location."""
    task = object_at(memory_id)
    if task is None or not isinstance(task, asyncio.Task):
      return await ctx.send(f'Could not find Task object at {hex(memory_id)}.')

    if ctx.invoked_with == 'cancel_task':
      task.cancel()
      return await ctx.send(f'Cancelled task object {task!r}.')

    paginator = commands.Paginator(prefix='```py')
    fp = io.StringIO()
    frames = len(task.get_stack())
    paginator.add_line(f'# Total Frames: {frames}')
    task.print_stack(file=fp)

    for line in fp.getvalue().splitlines():
      paginator.add_line(line)

    for page in paginator.pages:
      await ctx.send(page)

  @commands.command("wavelink")
  async def wavelink(self, ctx: MyContext):
    node = wavelink.NodePool.get_node()
    e = discord.Embed(title="Wavelink stats", colour=discord.Colour.blurple())
    e.add_field(name=f"Node: {node.identifier}", value=f"```\nRegion: {node.region}\nPlayers: {len(node.players)}\nPenalty: {node.penalty}\nConnected: {node.is_connected()}\n```")

    await ctx.send(embed=e)

  async def tabulate_query(self, ctx: MyContext, query: str, *args: Any):
    records = await ctx.db.fetch(query, *args)

    if len(records) == 0:
      return await ctx.send('No results found.')

    headers = list(records[0].keys())
    table = TabularData()
    table.set_columns(headers)
    table.add_rows(list(r.values()) for r in records)
    render = table.render()

    fmt = f'```\n{render}\n```'
    if len(fmt) > 2000:
      fp = io.BytesIO(fmt.encode("utf-8"))
      await ctx.send("Too many results to display.", file=discord.File(fp, filename="query.txt"))
    else:
      await ctx.send(fmt)

  @commands.group("commandhistory", invoke_without_command=True)
  async def command_history(self, ctx: MyContext):
    query = """SELECT
                 CASE failed
                   WHEN TRUE THEN command || ' [!]'
                   ELSE command
                 END AS "command",
                 to_char(used, 'Mon DD HH12:MI:SS AM') AS "invoked",
                 author_id,
                 guild_id
               FROM commands
               ORDER BY used DESC
               LIMIT 15;"""

    await self.tabulate_query(ctx, query)

  @command_history.command("for")
  async def command_history_for(self, ctx: MyContext, days: Annotated[int, Optional[int]] = 7, *, command: str):
    query = """SELECT *, t.success + t.failed AS "total"
                FROM (
                  SELECT guild_id,
                         SUM(CASE WHEN failed THEN 0 ELSE 1 END) AS "success",
                         SUM(CASE WHEN failed THEN 1 ELSE 0 END) AS "failed"
                  FROM commands
                  WHERE command=$1
                  AND used > (CURRENT_TIMESTAMP - $2::interval)
                  GROUP BY guild_id
                ) AS t
                ORDER BY "total" DESC
                LIMIT 30;"""

    await self.tabulate_query(ctx, query, command, datetime.timedelta(days=days))

  @command_history.command("guild", aliases=["server"])
  async def command_history_guild(self, ctx: MyContext, guild_id: int):
    query = """SELECT
                 CASE failed
                   WHEN TRUE THEN command || ' [!]'
                   ELSE command
                 END AS "command",
                 channel_id,
                 author_id,
                 used
               FROM commands
               WHERE guild_id=$1
               ORDER BY used DESC
               LIMIT 15;"""
    await self.tabulate_query(ctx, query, str(guild_id))

  @command_history.command(name='user', aliases=['member'])
  async def command_history_user(self, ctx, user_id: int):
    """Command history for a user."""

    query = """SELECT
                      CASE failed
                          WHEN TRUE THEN command || ' [!]'
                          ELSE command
                      END AS "command",
                      guild_id,
                      used
                  FROM commands
                  WHERE author_id=$1
                  ORDER BY used DESC
                  LIMIT 20;
              """
    await self.tabulate_query(ctx, query, str(user_id))

  @commands.group("chathistory", invoke_without_command=True)
  async def chat_histroy(self, ctx: MyContext):
    query = """SELECT
                 guild_id,
                 author_id,
                 to_char(used, 'Mon DD HH12:MI:SS AM') AS "invoked",
                 prompt
               FROM chats
               ORDER BY used DESC
               LIMIT 15;"""

    await self.tabulate_query(ctx, query)

  @commands.group("commandactivity", invoke_without_command=True)
  async def command_activity(self, ctx: MyContext):
      # WHERE used > (CURRENT_TIMESTAMP - '1 day'::interval)
    query = """SELECT
                  extract(hour from used) AS "hour",
                  SUM(CASE WHEN failed THEN 0 ELSE 1 END) AS "success"
              FROM commands
              GROUP BY extract(hour from used)
              ORDER BY extract(hour from used);"""
    record = await ctx.db.fetch(query)
    hours = [0] * 24
    for r in record:
      hours[int(r["hour"])] = r["success"]

    graph = ""
    space = 30
    for i, v in enumerate(hours):
      scaled = int(v / max(hours) * space)
      spacer = " " * (space - scaled)
      graph += f"{i+1:02d} | {'#' * min(space,scaled)}{spacer} | {v or ''}\n"
    mid = int(max(hours) / 2)
    graph += f"   0 {'-':->{space/2-len(str(mid))}} {mid} {'-':->{space/2-len(str(mid))}} {max(hours):,}\n"
    graph = graph.strip()

    await ctx.send(f"```\n{graph}\n```")

  @commands.group("chatactivity", invoke_without_command=True)
  async def chat_activity(self, ctx: MyContext):
      # WHERE used > (CURRENT_TIMESTAMP - '1 day'::interval)
    query = """SELECT
                  extract(hour from used) AS "hour",
                  SUM(CASE WHEN failed THEN 0 ELSE 1 END) AS "success"
              FROM chats
              GROUP BY extract(hour from used)
              ORDER BY extract(hour from used);"""
    record = await ctx.db.fetch(query)
    hours = [0] * 24
    for r in record:
      hours[int(r["hour"])] = r["success"]

    graph = ""
    space = 30
    for i, v in enumerate(hours):
      scaled = int(v / max(hours) * space)
      spacer = " " * (space - scaled)
      graph += f"{i+1:02d} | {'#' * min(space,scaled)}{spacer} | {v or ''}\n"
    mid = int(max(hours) / 2)
    graph += f"   0 {'-':->{space/2-len(str(mid))}} {mid} {'-':->{space/2-len(str(mid))}} {max(hours):,}\n"
    graph = graph.strip()

    await ctx.send(f"```\n{graph}\n```")

  # @commands.command("beforeleave")
  # async def beforeleave(self, ctx: MyContext):
  #   # from the database get the servers that friday joined then left
  #   # get the commands that executed in those servers before friday left
  #   # return the common commands that executed before friday left

  #   query = """SELECT DISTINCT guild_id
  #             FROM joined
  #             WHERE joined IS false;"""
  #   guilds = await ctx.db.fetch(query)
  #   guild_ids = [g["guild_id"] for g in guilds]


old_on_error = commands.AutoShardedBot.on_error


async def on_error(self, event: str, *args: Any, **kwargs: Any) -> None:
  (exc_type, exc, tb) = sys.exc_info()
  # Silence command errors that somehow get bubbled up far enough here
  if isinstance(exc, commands.CommandInvokeError):
    return

  e = discord.Embed(title="Event Error", colour=0xa32952)
  e.add_field(name="Event", value=event)
  trace = "".join(traceback.format_exception(exc_type, exc, tb))
  e.description = f"```py\n{trace}\n```"
  e.timestamp = discord.utils.utcnow()

  args_str = ['```py']
  for index, arg in enumerate(args):
    args_str.append(f"[{index}]: {arg!r}")
  args_str.append('```')
  e.add_field(name="Args", value='\n'.join(args_str), inline=False)
  hook = self.get_cog("Stats").webhook
  try:
    await hook.send(embed=e)
  except BaseException:
    pass


async def setup(bot: Friday):
  if not hasattr(bot, 'command_stats'):
    bot.command_stats = Counter()

  if not hasattr(bot, "chat_stats"):
    bot.chat_stats = Counter()

  if not hasattr(bot, "socket_stats"):
    bot.socket_stats = Counter()

  cog = Stats(bot)
  await bot.add_cog(cog)
  bot.gateway_handler = handler = GatewayHandler(cog)
  logging.getLogger().addHandler(handler)
  commands.AutoShardedBot.on_error = on_error


def teardown(bot: Friday):
  commands.AutoShardedBot.on_error = old_on_error
  logging.getLogger().removeHandler(bot.gateway_handler)
  del bot.gateway_handler
