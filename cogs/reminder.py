from __future__ import annotations

import asyncio
import datetime
import textwrap
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence

import asyncpg
import discord
from discord.ext import commands
from typing_extensions import Annotated

from functions import MessageColors, db, embed, time

if TYPE_CHECKING:
  from typing_extensions import Self

  from functions.custom_contexts import MyContext
  from index import Friday

log = logging.getLogger(__name__)


class Timer:
  __slots__ = ("args", "kwargs", "event", "id", "created_at", "expires",)

  def __init__(self, *, record: asyncpg.Record):
    self.id: int = record["id"]

    extra = record["extra"]
    self.args: Sequence[Any] = extra.get("args", [])
    self.kwargs: dict[str, Any] = extra.get("kwargs", {})
    self.event: str = record["event"]
    self.created_at: datetime.datetime = record["created"]
    self.expires: datetime.datetime = record["expires"]

  @classmethod
  def temporary(
          cls,
          *,
          expires: datetime.datetime,
          created: datetime.datetime,
          event: str,
          args: Sequence[Any],
          kwargs: Dict[str, Any]
  ) -> Self:
    pseudo = {
        "id": None,
        "extra": {"args": args, "kwargs": kwargs},
        "event": event,
        "created": created,
        "expires": expires,
    }
    return cls(record=pseudo)

  def __eq__(self, other: object) -> bool:
    try:
      return self.id == other.id  # type: ignore
    except AttributeError:
      return False

  def __hash__(self) -> int:
    return hash(self.id)

  @property
  def human_delta(self) -> str:
    return time.format_dt(self.created_at, style="R")

  @property
  def author_id(self) -> Optional[int]:
    if self.args:
      return int(self.args[0])
    return None

  def __repr__(self) -> str:
    return f"<Timer created={self.created_at} expires={self.expires} event={self.event}>"


class Reminder(commands.Cog):
  def __init__(self, bot: Friday):
    self.bot: Friday = bot
    self._have_data = asyncio.Event()
    self._current_timer: Optional[Timer] = None

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def cog_load(self) -> None:
    self._task = self.bot.loop.create_task(self.dispatch_timers())

  async def cog_unload(self) -> None:
    self._task.cancel()

  async def cog_command_error(self, ctx: MyContext, error: commands.CommandError):
    if isinstance(error, commands.TooManyArguments):
      await ctx.send(embed=embed(title=f'You called the {ctx.command.name} command with too many arguments.', color=MessageColors.error()))

  async def get_active_timer(self, *, connection: Optional[asyncpg.Connection] = None, days: int = 7) -> Optional[Timer]:
    query = "SELECT * FROM reminders WHERE expires < (CURRENT_DATE + $1::interval) ORDER BY expires LIMIT 1;"
    con = connection or self.bot.pool

    record = await con.fetchrow(query, datetime.timedelta(days=days))
    log.debug(f"PostgreSQL Query: \"{query}\" + {datetime.timedelta(days=days)}")
    return Timer(record=record) if record else None

  async def wait_for_active_timer(self, *, connection: Optional[asyncpg.Connection] = None, days: int = 7) -> Timer:
    async with db.MaybeAcquire(connection=connection, pool=self.bot.pool) as con:
      timer = await self.get_active_timer(connection=con, days=days)
      if timer is not None:
        self._have_data.set()
        return timer

      self._have_data.clear()
      self._current_timer = None
      await self._have_data.wait()
      return await self.get_active_timer(connection=con, days=days)  # type: ignore

  async def call_timer(self, timer: Timer) -> None:
    await self.bot.pool.execute("DELETE FROM reminders WHERE id=$1;", timer.id)

    self.bot.dispatch(f"{timer.event}_timer_complete", timer)

  async def dispatch_timers(self) -> None:
    try:
      while not self.bot.is_closed():
        timer = self._current_timer = await self.wait_for_active_timer(days=40)
        now = datetime.datetime.utcnow()

        if timer.expires >= now:
          to_sleep = (timer.expires - now).total_seconds()
          await asyncio.sleep(to_sleep)
        await self.call_timer(timer)
    except asyncio.CancelledError as e:
      raise e
    except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
      self._task.cancel()
      self._task = self.bot.loop.create_task(self.dispatch_timers())

  async def short_timer_optimisation(self, seconds: float, timer: Timer) -> None:
    await asyncio.sleep(seconds)
    event_name = f'{timer.event}_timer_complete'
    self.bot.dispatch(event_name, timer)

  async def create_timer(self, when: datetime.datetime, event: str, *args: Any, **kwargs: Any) -> Timer:
    try:
      connection = kwargs.pop('connection')
    except KeyError:
      connection = self.bot.pool

    try:
      now = kwargs.pop('created')
    except KeyError:
      now = discord.utils.utcnow()

    when = when.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    now = now.astimezone(datetime.timezone.utc).replace(tzinfo=None)

    timer = Timer.temporary(event=event, args=args, kwargs=kwargs, expires=when, created=now)
    delta = (when - now).total_seconds()
    if delta <= 60:
      # a shortcut for small timers
      self.bot.loop.create_task(self.short_timer_optimisation(delta, timer))
      return timer

    query = """INSERT INTO reminders (event, extra, expires, created)
                  VALUES ($1, $2::jsonb, $3, $4)
                  RETURNING id;
              """

    row = await connection.fetchrow(query, event, {"args": args, "kwargs": kwargs}, when, now)
    log.debug(f"PostgreSQL Query: \"{query}\" + {event, {'args': args, 'kwargs': kwargs}, when, now}")
    timer.id = row[0]

    if delta <= (86400 * 40):  # 40 days
      self._have_data.set()

    if self._current_timer and when < self._current_timer.expires:
      self._task.cancel()
      self._task = self.bot.loop.create_task(self.dispatch_timers())

    return timer

  @commands.group("reminder", fallback="set", aliases=["timer", "remind"], extras={"examples": ["20m go buy food", "do something in 20m", "jan 1st happy new years"]}, usage="<when> <message>", invoke_without_command=True)
  async def reminder(self, ctx: MyContext, *, when: Annotated[time.FriendlyTimeResult, time.UserFriendlyTime(commands.clean_content, default="...")]):
    """ Create a reminder for a certain time in the future. """
    await self.create_timer(
        when.dt,
        "reminder",
        ctx.author.id,
        ctx.channel.id,
        when.arg,
        connection=ctx.pool,
        created=ctx.message.created_at,
        message_id=ctx.message.id
    )
    await ctx.send(embed=embed(title=f"Reminder set {time.format_dt(when.dt, style='R')}", description=f"{when.arg}"))

  @reminder.command("list", ignore_extra=False)
  async def reminder_list(self, ctx: MyContext):
    """ List all reminders. """
    query = """SELECT id,expires, extra #>> '{args,2}'
              FROM reminders
              WHERE event = 'reminder'
              AND extra #>> '{args,0}' = $1
              ORDER BY expires
              LIMIT 10;"""
    records = await ctx.db.fetch(query, str(ctx.author.id))

    if len(records) == 0:
      return await ctx.send(embed=embed(title="You have no reminders.", color=MessageColors.error()))

    if len(records) == 10:
      footer = "Only 10 reminders are shown."
    else:
      footer = f"{len(records)} reminder{'s' if len(records) > 1 else ''}."

    titles, fields = [], []
    for _id, expires, message in records:
      shorten = textwrap.shorten(message, width=512)
      titles.append(f"{_id}: {time.format_dt(expires, style='R')}")
      fields.append(f"{shorten}")

    await ctx.send(embed=embed(title="Reminders", fieldstitle=titles, fieldsval=fields, fieldsin=[False for _ in range(len(records))], footer=footer))

  @reminder.command("delete", aliases=["remove", "cancel"], extras={"examples": ["1", "200"]}, ignore_extra=False)
  async def reminder_delete(self, ctx: MyContext, *, id: int):
    """ Delete a reminder. """
    query = """DELETE FROM reminders
              WHERE id=$1
              AND event='reminder'
              AND extra #>> '{args,0}' = $2;"""

    status = await ctx.db.execute(query, id, str(ctx.author.id))
    if status == "DELETE 0":
      return await ctx.send(embed=embed(title="You have no reminder with that ID.", color=MessageColors.error()))

    if self._current_timer and self._current_timer.id == id:
      self._task.cancel()
      self._task = self.bot.loop.create_task(self.dispatch_timers())

    await ctx.send(embed=embed(title="Reminder deleted."))

  @reminder.command("clear", ignore_extra=False)
  async def reminder_clear(self, ctx: MyContext):
    """ Delete all your reminders. """
    query = """SELECT COUNT(*)
              FROM reminders
              WHERE event='reminder'
              AND extra #>> '{args,0}' = $1;"""

    author_id = str(ctx.author.id)
    total = await ctx.db.fetchrow(query, author_id)
    total = total[0]
    if total == 0:
      return await ctx.send(embed=embed(title="You have no reminders.", color=MessageColors.error()))

    confirm = await ctx.prompt(f"Are you sure you want to delete {time.plural(total):reminder}?")
    if not confirm:
      return await ctx.send(embed=embed(title="Cancelled."))

    query = """DELETE FROM reminders WHERE event = 'reminder' AND extra #>> '{args,0}' = $1;"""
    await ctx.db.execute(query, author_id)

    if self._current_timer and self._current_timer.author_id == ctx.author.id:
      self._task.cancel()
      self._task = self.bot.loop.create_task(self.dispatch_timers())

    await ctx.send(embed=embed(title=f"Successfully deleted {time.plural(total):reminder}."))

  @commands.Cog.listener()
  async def on_reminder_timer_complete(self, timer: Timer):
    author_id, channel_id, message = timer.args

    try:
      channel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
    except discord.HTTPException:
      return

    guild_id = channel.guild.id if isinstance(channel, (discord.TextChannel, discord.Thread)) else "@me"
    message_id = timer.kwargs.get('message_id')
    view = discord.utils.MISSING

    if message_id:
      url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
      view = discord.ui.View()
      view.add_item(discord.ui.Button(label="Go to original message", url=url))

    try:
      await channel.send(f"<@{author_id}>", embed=embed(title=f"Reminder {timer.human_delta}", description=f"{message}"), view=view)  # type: ignore
    except discord.HTTPException:
      return


async def setup(bot: Friday):
  await bot.add_cog(Reminder(bot))
