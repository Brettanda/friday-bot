import asyncio
import datetime
import io
import json
import os
from collections import Counter
from typing import Optional

import asyncpg
import discord
import psutil
from discord.ext import commands, tasks
from typing_extensions import TYPE_CHECKING

from functions import MyContext

if TYPE_CHECKING:
  from index import Friday as Bot


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
      return f'|{elem}|'

    to_draw.append(get_entry(self._columns))
    to_draw.append(sep)

    for row in self._rows:
      to_draw.append(get_entry(row))

    to_draw.append(sep)
    return '\n'.join(to_draw)


class Stats(commands.Cog, command_attrs=dict(hidden=True)):
  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.process = psutil.Process()
    self._batch_lock = asyncio.Lock()
    self._data_batch = []
    self.bulk_insert_loop.add_exception_type(asyncpg.PostgresConnectionError)
    self.bulk_insert_loop.start()

  def __repr__(self) -> str:
    return "<cogs.Stats>"

  async def cog_check(self, ctx: "MyContext") -> bool:
    if ctx.author.id == 892865928520413245:
      return True
    if not await self.bot.is_owner(ctx.author):
      raise commands.NotOwner()
    return True

  async def bulk_insert(self):
    query = """INSERT INTO commands (guild_id, channel_id, author_id, used, prefix, command, failed)
               SELECT x.guild, x.channel, x.author, x.used, x.prefix, x.command, x.failed
               FROM jsonb_to_recordset($1::jsonb) AS
               x(guild TEXT, channel TEXT, author TEXT, used TIMESTAMP, prefix TEXT, command TEXT, failed BOOLEAN)"""

    if self._data_batch:
      await self.bot.pool.execute(query, json.dumps(self._data_batch))
      total = len(self._data_batch)
      if total > 1:
        self.bot.logger.info(f"Inserted {total} commands into the database")
      self._data_batch.clear()

  def cog_unload(self):
    self.bulk_insert_loop.cancel()

  @tasks.loop(seconds=10.0)
  async def bulk_insert_loop(self):
    async with self._batch_lock:
      await self.bulk_insert()

  async def register_command(self, ctx: "MyContext"):
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

    self.bot.logger.info(f'{message.created_at}: {message.author} in {destination}: {message.content}')
    async with self._batch_lock:
      self._data_batch.append({
          'guild': str(guild_id),
          'channel': str(ctx.channel.id),
          'author': str(ctx.author.id),
          'used': message.created_at.isoformat(),
          'prefix': ctx.prefix,
          'command': command,
          'failed': ctx.command_failed,
      })

  @commands.Cog.listener()
  async def on_command_completion(self, ctx):
    await self.register_command(ctx)

  @commands.command("commandstats")
  async def commandstats(self, ctx, limit=20):
    counter = self.bot.command_stats
    width = len(max(counter, key=len))

    if limit > 0:
      common = counter.most_common(limit)
    else:
      common = counter.most_common()[limit:]

    output = '\n'.join(f"{k:<{width}}: {c}" for k, c in common)

    await ctx.send(f"```\n{output}\n```")

  @commands.command("bothealth")
  async def bothealth(self, ctx: "MyContext"):
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

    # spam_control = self.bot.spam_control
    # being_spammed = [
    #     str(key) for key, value in spam_control._cache.items()
    #     if value._tokens == 0
    # ]

    # description.append(f'Current Spammers: {", ".join(being_spammed) if being_spammed else "None"}')
    description.append(f'Questionable Connections: {questionable_connections}')

    total_warnings += questionable_connections
    # if being_spammed:
    #   embed_.colour = WARNING
    #   total_warnings += 1

    try:
      task_retriever = asyncio.Task.all_tasks
    except AttributeError:
      # future proofing for 3.9 I guess
      task_retriever = asyncio.all_tasks
    else:
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

    command_waiters = len(self._data_batch)
    is_locked = self._batch_lock.locked()
    description.append(f'Commands Waiting: {command_waiters}, Batch Locked: {is_locked}')

    memory_usage = self.process.memory_full_info().uss / 1024**2
    cpu_usage = self.process.cpu_percent() / psutil.cpu_count()
    embed_.add_field(name='Process', value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU', inline=False)

    global_rate_limit = not self.bot.http._global_over.is_set()
    description.append(f'Global Rate Limit: {global_rate_limit}')

    if command_waiters >= 8:
      total_warnings += 1
      embed_.colour = WARNING

    if global_rate_limit or total_warnings >= 9:
      embed_.colour = UNHEALTHY

    embed_.set_footer(text=f'{total_warnings} warning(s)')
    embed_.description = '\n'.join(description)
    await ctx.send(embed=embed_)

  async def tabulate_query(self, ctx: "MyContext", query: str, *args):
    records = await ctx.pool.fetch(query, *args)

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
  async def command_history(self, ctx: "MyContext"):
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
  async def command_history_for(self, ctx: "MyContext", days: Optional[int] = 7, *, command: str):
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


def setup(bot):
  if not hasattr(bot, 'command_stats'):
    bot.command_stats = Counter()
  bot.add_cog(Stats(bot))
