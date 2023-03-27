from __future__ import annotations

import asyncio
import datetime
import logging
import textwrap
from typing import TYPE_CHECKING, Any, Dict, NamedTuple, Optional, Sequence

import asyncpg
import dateutil.zoneinfo
import discord
from dateutil.zoneinfo import get_zonefile_instance
from discord import app_commands
from discord.ext import commands, menus
from discord.utils import format_dt
from lxml import etree
from typing_extensions import Annotated

from functions import cache, fuzzy, time
from functions.custom_contexts import MyContext
from functions.myembed import embed

if TYPE_CHECKING:
  from typing_extensions import Self

  from index import Friday

log = logging.getLogger(__name__)


class MaybeAcquire:
  def __init__(self, connection: Optional[asyncpg.Connection], *, pool: asyncpg.Pool) -> None:
    self.connection: Optional[asyncpg.Connection] = connection
    self.pool: asyncpg.Pool = pool
    self._cleanup: bool = False

  async def __aenter__(self) -> asyncpg.Connection:
    if self.connection is None:
      self._cleanup = True
      self._connection = c = await self.pool.acquire()
      return c
    return self.connection

  async def __aexit__(self, *args) -> None:
    if self._cleanup:
      await self.pool.release(self._connection)


class SnoozeModal(discord.ui.Modal, title='Snooze'):
  duration = discord.ui.TextInput(label='Duration', placeholder='10 minutes', default='10 minutes', min_length=2)

  def __init__(self, parent: ReminderView, cog: Reminder, timer: Timer) -> None:
    super().__init__()
    self.parent: ReminderView = parent
    self.timer: Timer = timer
    self.cog: Reminder = cog

  async def on_submit(self, interaction: discord.Interaction) -> None:
    try:
      when = time.FutureTime(str(self.duration)).dt
    except Exception:
      await interaction.response.send_message(
          embed=embed(title='Duration could not be parsed, sorry. Try something like "5 minutes" or "1 hour"'), ephemeral=True
      )
      return

    self.parent.snooze.disabled = True
    await interaction.response.edit_message(view=self.parent)

    refreshed = await self.cog.create_timer(
        when, self.timer.event, *self.timer.args, **self.timer.kwargs, created=interaction.created_at
    )
    _, _, message = self.timer.args
    delta = time.human_timedelta(when, source=refreshed.created_at)
    await interaction.followup.send(embed=embed(
        title=f"I've snoozed your reminder for {delta}: {message}"
    ), ephemeral=True)


class SnoozeButton(discord.ui.Button['ReminderView']):
  def __init__(self, cog: Reminder, timer: Timer) -> None:
    super().__init__(label='Snooze', style=discord.ButtonStyle.blurple)
    self.timer: Timer = timer
    self.cog: Reminder = cog

  async def callback(self, interaction: discord.Interaction) -> Any:
    assert self.view is not None
    await interaction.response.send_modal(SnoozeModal(self.view, self.cog, self.timer))


class ReminderView(discord.ui.View):
  message: discord.Message

  def __init__(self, *, url: str, timer: Timer, cog: Reminder, author_id: int) -> None:
    super().__init__(timeout=300)
    self.author_id: int = author_id
    self.snooze = SnoozeButton(cog, timer)
    self.add_item(discord.ui.Button(url=url, label='Go to original message'))
    self.add_item(self.snooze)

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if interaction.user.id != self.author_id:
      await interaction.response.send_message(embed=embed(title='This snooze button is not for you, sorry!'), ephemeral=True)
      return False
    return True

  async def on_timeout(self) -> None:
    self.snooze.disabled = True
    await self.message.edit(view=self)


class PaginatorSource(menus.ListPageSource):
  def __init__(self, entries: list[asyncpg.Record], *, per_page: int = 10, title: str = "Reminders"):
    self.title = title
    super().__init__(entries, per_page=per_page)

  async def format_page(self, menu: menus.MenuPages, page: list[asyncpg.Record]) -> discord.Embed:
    titles, values = [], []

    for _id, expires, _, _, extra in page:
      message = extra["args"][2]
      shorten = textwrap.shorten(message, width=512)
      titles.append(f"{_id}: {time.format_dt(expires, style='R')}")
      values.append(f"{shorten}")
    return embed(
        title=self.title,
        fieldstitle=titles,
        fieldsval=values,
        fieldsin=[False] * len(titles),
        footer=f"{menu.current_page}/{self.get_max_pages()} pages"
    )

  def is_paginating(self) -> bool:
    return True


class TimeZone(NamedTuple):
  label: str
  key: str

  @classmethod
  async def convert(cls, ctx: MyContext, argument: str) -> Self:
    assert isinstance(ctx.cog, Reminder)

    # Prioritise aliases because they handle short codes slightly better
    if argument in ctx.cog._timezone_aliases:
      return cls(key=argument, label=ctx.cog._timezone_aliases[argument])

    if argument in ctx.cog.valid_timezones:
      return cls(key=argument, label=argument)

    timezones = ctx.cog.find_timezones(argument)

    try:
      return await ctx.disambiguate(timezones, lambda t: t[0], ephemeral=True)
    except ValueError:
      raise commands.BadArgument(ctx.lang.reminder.errors.no_find_timezone.format(argument=f"{argument!r}"))

  def to_choice(self) -> app_commands.Choice[str]:
    return app_commands.Choice(name=self.label, value=self.key)


class Timer:
  __slots__ = ("args", "kwargs", "event", "id", "created_at", "expires", "timezone",)

  def __init__(self, *, record: asyncpg.Record):
    self.id: int = record["id"]

    extra = record["extra"]
    self.args: Sequence[Any] = extra.get("args", [])
    self.kwargs: dict[str, Any] = extra.get("kwargs", {})
    self.event: str = record["event"]
    self.created_at: datetime.datetime = record["created"]
    self.expires: datetime.datetime = record["expires"]
    self.timezone: str = record['timezone']

  @classmethod
  def temporary(
          cls,
          *,
          expires: datetime.datetime,
          created: datetime.datetime,
          event: str,
          args: Sequence[Any],
          kwargs: Dict[str, Any],
          timezone: str,
  ) -> Self:
    pseudo = {
        "id": None,
        "extra": {"args": args, "kwargs": kwargs},
        "event": event,
        "created": created,
        "expires": expires,
        "timezone": timezone,
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


class CLDRDataEntry(NamedTuple):
  description: str
  aliases: list[str]
  deprecated: bool
  preferred: Optional[str]


class Reminder(commands.Cog):
  """Set reminders for yourself"""

  # CLDR identifiers for most common timezones for the default autocomplete drop down
  # n.b. limited to 25 choices
  DEFAULT_POPULAR_TIMEZONE_IDS = (
      # America
      'usnyc',  # America/New_York
      'uslax',  # America/Los_Angeles
      'uschi',  # America/Chicago
      'usden',  # America/Denver
      # India
      'inccu',  # Asia/Kolkata
      # Europe
      'trist',  # Europe/Istanbul
      'rumow',  # Europe/Moscow
      'gblon',  # Europe/London
      'frpar',  # Europe/Paris
      'esmad',  # Europe/Madrid
      'deber',  # Europe/Berlin
      'grath',  # Europe/Athens
      'uaiev',  # Europe/Kyev
      'itrom',  # Europe/Rome
      'nlams',  # Europe/Amsterdam
      'plwaw',  # Europe/Warsaw
      # Canada
      'cator',  # America/Toronto
      # Australia
      'aubne',  # Australia/Brisbane
      'ausyd',  # Australia/Sydney
      # Brazil
      'brsao',  # America/Sao_Paulo
      # Japan
      'jptyo',  # Asia/Tokyo
      # China
      'cnsha',  # Asia/Shanghai
  )

  def __init__(self, bot: Friday):
    self.bot: Friday = bot
    self._have_data = asyncio.Event()
    self._current_timer: Optional[Timer] = None
    self._task = bot.loop.create_task(self.dispatch_timers())
    self.valid_timezones: set[str] = set(get_zonefile_instance().zones)
    # User-friendly timezone names, some manual and most from the CLDR database.
    self._timezone_aliases: dict[str, str] = {
          'Eastern Time': 'America/New_York',
          'Central Time': 'America/Chicago',
          'Mountain Time': 'America/Denver',
          'Pacific Time': 'America/Los_Angeles',
          # (Unfortunately) special case American timezone abbreviations
          'EST': 'America/New_York',
          'CST': 'America/Chicago',
          'MST': 'America/Denver',
          'PST': 'America/Los_Angeles',
          'EDT': 'America/New_York',
          'CDT': 'America/Chicago',
          'MDT': 'America/Denver',
          'PDT': 'America/Los_Angeles',
         }
    self._default_timezones: list[app_commands.Choice[str]] = []

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def cog_load(self) -> None:
    await self.parse_bcp47_timezones()
    self._task = self.bot.loop.create_task(self.dispatch_timers())

  async def cog_unload(self) -> None:
    self._task.cancel()

  async def cog_command_error(self, ctx: MyContext, error: commands.CommandError):
    if isinstance(error, commands.TooManyArguments):
      await ctx.send(f'You called the {ctx.command.name} command with too many arguments.', ephemeral=True)

  async def parse_bcp47_timezones(self) -> None:
    async with self.bot.session.get(
        'https://raw.githubusercontent.com/unicode-org/cldr/main/common/bcp47/timezone.xml'
    ) as resp:
      if resp.status != 200:
        return

      parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
      tree = etree.fromstring(await resp.read(), parser=parser)

      # Build a temporary dictionary to resolve "preferred" mappings
      entries: dict[str, CLDRDataEntry] = {
          node.attrib['name']: CLDRDataEntry(
              description=node.attrib['description'],
              aliases=node.get('alias', 'Etc/Unknown').split(' '),
              deprecated=node.get('deprecated', 'false') == 'true',
              preferred=node.get('preferred'),
          )
          for node in tree.iter('type')
          # Filter the Etc/ entries (except UTC)
          if not node.attrib['name'].startswith(('utcw', 'utce', 'unk')) \
          and not node.attrib['description'].startswith('POSIX')
      }

      for entry in entries.values():
        # These use the first entry in the alias list as the "canonical" name to use when mapping the
        # timezone to the IANA database.
        # The CLDR database is not particularly correct when it comes to these, but neither is the IANA database.
        # It turns out the notion of a "canonical" name is a bit of a mess. This works fine for users where
        # this is only used for display purposes, but it's not ideal.
        if entry.preferred is not None:
          preferred = entries.get(entry.preferred)
          if preferred is not None:
            self._timezone_aliases[entry.description] = preferred.aliases[0]
        else:
          self._timezone_aliases[entry.description] = entry.aliases[0]

      for key in self.DEFAULT_POPULAR_TIMEZONE_IDS:
        entry = entries.get(key)
        if entry is not None:
          self._default_timezones.append(app_commands.Choice(name=entry.description, value=entry.aliases[0]))

  @cache.cache()
  async def get_timezone(self, user_id: int, /) -> Optional[str]:
    query = "SELECT timezone from user_settings WHERE id = $1;"
    record = await self.bot.pool.fetchrow(query, user_id)
    return record['timezone'] if record else None

  async def get_tzinfo(self, user_id: int, /) -> datetime.tzinfo:
    tz = await self.get_timezone(user_id)
    if tz is None:
      return datetime.timezone.utc
    return dateutil.zoneinfo.gettz(tz) or datetime.timezone.utc

  def find_timezones(self, query: str) -> list[TimeZone]:
    # A bit hacky, but if '/' is in the query then it's looking for a raw identifier
    # otherwise it's looking for a CLDR alias
    if '/' in query:
      return [TimeZone(key=a, label=a) for a in fuzzy.finder(query, self.valid_timezones)]

    keys = fuzzy.finder(query, self._timezone_aliases.keys())
    return [TimeZone(label=k, key=self._timezone_aliases[k]) for k in keys]

  async def get_active_timer(self, *, connection: Optional[asyncpg.Connection] = None, days: int = 7) -> Optional[Timer]:
    query = """
        SELECT * FROM reminders
        WHERE (expires AT TIME ZONE 'UTC' AT TIME ZONE timezone) < (CURRENT_TIMESTAMP + $1::interval)
        ORDER BY expires
        LIMIT 1;
    """
    con = connection or self.bot.pool

    record = await con.fetchrow(query, datetime.timedelta(days=days))
    log.debug(f"PostgreSQL Query: \"{query}\" + {datetime.timedelta(days=days)}")
    return Timer(record=record) if record else None

  async def wait_for_active_timer(self, *, connection: Optional[asyncpg.Connection] = None, days: int = 7) -> Timer:
    async with MaybeAcquire(connection=connection, pool=self.bot.pool) as con:
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

  async def create_timer(self, when: datetime.datetime, event: str, /, *args: Any, **kwargs: Any) -> Timer:
    pool = self.bot.pool

    try:
      now = kwargs.pop('created')
    except KeyError:
      now = discord.utils.utcnow()

    timezone_name = kwargs.pop('timezone', 'UTC')
    when = when.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    now = now.astimezone(datetime.timezone.utc).replace(tzinfo=None)

    timer = Timer.temporary(event=event, args=args, kwargs=kwargs, expires=when, created=now, timezone=timezone_name)
    delta = (when - now).total_seconds()
    if delta <= 60:
      # a shortcut for small timers
      self.bot.loop.create_task(self.short_timer_optimisation(delta, timer))
      return timer

    query = """INSERT INTO reminders (event, extra, expires, created, timezone)
                  VALUES ($1, $2::jsonb, $3, $4, $5)
                  RETURNING id;
              """

    row = await pool.fetchrow(query, event, {"args": args, "kwargs": kwargs}, when, now, timezone_name)
    log.debug(f"PostgreSQL Query: \"{query}\" + {event, {'args': args, 'kwargs': kwargs}, when, now}")
    timer.id = row[0]

    if delta <= (86400 * 40):  # 40 days
      self._have_data.set()

    if self._current_timer and when < self._current_timer.expires:
      self._task.cancel()
      self._task = self.bot.loop.create_task(self.dispatch_timers())

    return timer

  @commands.hybrid_group("reminder", aliases=["timer", "remind"], extras={"examples": ["20m go buy food", "do something in 20m", "jan 1st happy new years"]}, usage="<when> <message>")
  async def reminder(self, ctx: MyContext, *, when: Annotated[time.FriendlyTimeResult, time.UserFriendlyTime(commands.clean_content, default="...")]):
    """Create a reminder for a certain time in the future."""
    zone = await self.get_timezone(ctx.author.id)
    await self.create_timer(
        when.dt,
        "reminder",
        ctx.author.id,
        ctx.channel.id,
        when.arg,
        created=ctx.message.created_at,
        message_id=ctx.interaction is None and ctx.message.id,
        timezone=zone or "UTC",
    )
    # self.get_records.invalidate(self, ctx.author.id)
    await ctx.send(embed=embed(title=ctx.lang.reminder.reminder.commands.set.response.format(time.format_dt(when.dt, style='R')), description=when.arg))

  @reminder.app_command.command(name="set")
  @app_commands.describe(when="The time to be reminded. In UTC", text="Your reminder message")
  async def reminder_set(self, interaction: discord.Interaction, when: app_commands.Transform[datetime.datetime, time.TimeTransformer], text: str = "..."):
    """Create a reminder for a certain time in the future."""
    zone = await self.get_timezone(interaction.user.id)
    await self.create_timer(
        when,
        'reminder',
        interaction.user.id,
        interaction.channel_id,
        text,
        created=interaction.created_at,
        message_id=None,
        timezone=zone or 'UTC',
    )
    # self.get_records.invalidate(self, interaction.user.id)
    ctx = await MyContext.from_interaction(interaction)
    await interaction.response.send_message(embed=embed(title=ctx.lang.reminder.reminder.commands.set.response.format(time.format_dt(when, style='R')), description=text))

  @reminder.command("list", ignore_extra=False)
  async def reminder_list(self, ctx: MyContext):
    """List all reminders."""
    query = """SELECT id, expires, extra #>> '{args,2}'
            FROM reminders
            WHERE event = 'reminder'
            AND extra #>> '{args,0}' = $1
            ORDER BY expires
            LIMIT 10;
        """

    records = await ctx.db.fetch(query, str(ctx.author.id))

    if len(records) == 0:
      return await ctx.send(ctx.lang.reminder.errors.not_found)

    e = discord.Embed(colour=discord.Colour.blurple(), title=ctx.lang.reminder.reminder.commands.list.list_title)

    if len(records) == 10:
      e.set_footer(text=ctx.lang.reminder.reminder.commands.list.ten_limit)
    else:
      e.set_footer(text=f'{len(records)} reminder{"s" if len(records) > 1 else ""}')

    for _id, expires, message in records:
      shorten = textwrap.shorten(message, width=512)
      e.add_field(name=f'{_id}: {format_dt(expires,style="R")}', value=shorten, inline=False)

    await ctx.send(embed=e)

  @reminder.command("delete", aliases=["remove", "cancel"], extras={"examples": ["1", "200"]}, ignore_extra=False)
  async def reminder_delete(self, ctx: MyContext, *, id: int):
    """Delete a reminder."""
    query = """DELETE FROM reminders
              WHERE id=$1
              AND event='reminder'
              AND extra #>> '{args,0}' = $2;"""

    status = await ctx.db.execute(query, id, str(ctx.author.id))
    if status == "DELETE 0":
      return await ctx.send(ctx.lang.reminder.errors.not_found, ephemeral=True)

    if self._current_timer and self._current_timer.id == id:
      self._task.cancel()
      self._task = self.bot.loop.create_task(self.dispatch_timers())
    # self.get_records.invalidate(self, ctx.author.id)

    await ctx.send(ctx.lang.reminder.reminder.commands.delete.response)

  @reminder.command("clear", ignore_extra=False)
  async def reminder_clear(self, ctx: MyContext):
    """Delete all your reminders."""
    query = """SELECT COUNT(*)
              FROM reminders
              WHERE event='reminder'
              AND extra #>> '{args,0}' = $1;"""

    author_id = str(ctx.author.id)
    total: asyncpg.Record = await ctx.db.fetchrow(query, author_id)
    total = total[0]
    if total == 0:
      return await ctx.send(ctx.lang.reminder.errors.empty, ephemeral=True)

    confirm = await ctx.prompt(ctx.lang.reminder.reminder.commands.clear.prompt.format(f"{time.plural(total):reminder}"))
    if not confirm:
      return await ctx.send(ctx.lang.errors.canceled, ephemeral=True)

    query = """DELETE FROM reminders WHERE event = 'reminder' AND extra #>> '{args,0}' = $1;"""
    await ctx.db.execute(query, author_id)

    if self._current_timer and self._current_timer.author_id == ctx.author.id:
      self._task.cancel()
      self._task = self.bot.loop.create_task(self.dispatch_timers())
    # self.get_records.invalidate(self, ctx.author.id)

    await ctx.send(ctx.lang.reminder.reminder.commands.clear.response.format(f"{time.plural(total):reminder}"))

  @commands.hybrid_group()
  async def timezone(self, ctx: MyContext):
    """Commands related to managing timezone info."""
    # await ctx.send_help(ctx.command)
    tz = await self.get_timezone(ctx.author.id)
    if tz is None:
      return await ctx.send(embed=embed(title='You have not set your timezone.'), ephemeral=True)

    time = discord.utils.utcnow().astimezone(dateutil.zoneinfo.gettz(tz)).strftime('%Y-%m-%d %I:%M %p')
    await ctx.send(embed=embed(title=f'Your timezone is {tz!r}. The current time is {time}.'), ephemeral=True)

  @timezone.command(name='set')
  @app_commands.describe(timezone='The timezone to change to.')
  async def timezone_set(self, ctx: MyContext, *, timezone: TimeZone):
    """Sets your timezone for all related commands."""

    await ctx.db.execute(
        """INSERT INTO user_settings (id, timezone)
              VALUES ($1, $2)
              ON CONFLICT (id) DO UPDATE SET timezone = $2;
          """,
        ctx.author.id,
        timezone.key,
    )

    self.get_timezone.invalidate(self, ctx.author.id)
    await ctx.send(embed=embed(title=ctx.lang.reminder.timezone.commands.set.response.format(tz=timezone.label)), ephemeral=True, delete_after=10)

  @timezone_set.autocomplete('timezone')
  async def timezone_set_autocomplete(
      self, interaction: discord.Interaction, argument: str
  ) -> list[app_commands.Choice[str]]:
    if not argument:
      return self._default_timezones
    matches = self.find_timezones(argument)
    return [tz.to_choice() for tz in matches[:25]]

  @timezone.command(name='clear')
  async def timezone_clear(self, ctx: MyContext):
    """Clears your timezone."""
    await ctx.db.execute("UPDATE user_settings SET timezone = NULL WHERE id=$1", ctx.author.id)
    self.get_timezone.invalidate(self, ctx.author.id)
    await ctx.send(embed=embed(title=ctx.lang.reminder.timezone.commands.clear.response), ephemeral=True)

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
      view = ReminderView(url=url, timer=timer, cog=self, author_id=author_id)

    try:
      msg = await channel.send(f"<@{author_id}>", embed=embed(title=f"Reminder {timer.human_delta}", description=f"{message}"), view=view)  # type: ignore
    except discord.HTTPException:
      return
    else:
      if view is not discord.utils.MISSING:
        view.message = msg
      log.info(f"reminder sent to {timer.author_id}, with timer id {timer.id}")


async def setup(bot: Friday):
  await bot.add_cog(Reminder(bot))
