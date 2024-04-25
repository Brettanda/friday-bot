from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING, Optional, Union

import discord
import datetime
import asyncpg
from discord.ext import commands, tasks
from topgg.webhook import WebhookManager

from functions import MyContext, cache, config, embed, time, formats

from .log import CustomWebhook

if TYPE_CHECKING:
  from cogs.reminder import Timer
  from index import Friday

log = logging.getLogger(__name__)

VOTE_ROLE = 834347369998843904
VOTE_URL = "https://top.gg/bot/476303446547365891/vote"


class StreakConfig:
  __slots__ = ("user_id", "created", "last_vote", "days", "expires",)

  def __init__(self, *, record: asyncpg.Record):
    self.user_id: int = record["user_id"]
    self.created: datetime.datetime = record["created"]
    self.last_vote: datetime.datetime = record["last_vote"]
    self.days: int = record["days"]
    self.expires: datetime.datetime = record["expires"]

  @property
  def gets_perks(self) -> bool:
    """Whether or not the user gets perks from their current vote streak."""
    return self.days >= 2

# TODO: Add support for voting on discords.com and discordbotlist.com https://cdn.discordapp.com/attachments/892840236781015120/947203621358010428/unknown.png


class TopGG(commands.Cog):
  """Voting for Friday on Top.gg really helps with getting Friday to more people because the more votes a bot has the higher ranking it gets.

    To get Friday higher in the rankings you can vote here
    [top.gg/bot/476303446547365891/vote](https://top.gg/bot/476303446547365891/vote)

    When voting you will receive some cool perks currently including:

      - Better rate limits when chatting with Friday"""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot

    self._current_len_guilds = len(self.bot.guilds)

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  @discord.utils.cached_property
  def log_bumps(self) -> CustomWebhook:
    id = int(os.environ["WEBHOOKBUMPSID"], base=10)
    token = os.environ["WEBHOOKBUMPSTOKEN"]
    return CustomWebhook.partial(id, token, session=self.bot.session)

  async def start_webhook(self):
    if self.bot.cluster_idx == 0:
      if not hasattr(self.bot, "topgg_webhook"):
        self.bot.topgg_webhook = WebhookManager(self.bot).dbl_webhook("/dblwebhook", os.environ["DBLWEBHOOKPASS"])
        self.bot.topgg_webhook.run(5000)
      self._update_stats_loop.start()

  async def cog_load(self):
    self.bot.loop.create_task(self.start_webhook())

  async def cog_unload(self):
    self._update_stats_loop.cancel()

  @cache.cache()
  async def user_has_voted(self, user_id: int) -> bool:
    query = """SELECT id
              FROM reminders
              WHERE event = 'vote'
              AND extra #>> '{args,0}' = $1
              ORDER BY expires
              LIMIT 1;"""
    conn = self.bot.pool
    record = await conn.fetchrow(query, str(user_id))
    return True if record else False

  @cache.cache()
  async def user_streak(self, user_id: int) -> Optional[StreakConfig]:
    query = """SELECT *
              FROM voting_streaks
              WHERE user_id = $1;"""
    conn = self.bot.pool
    record = await conn.fetchrow(query, user_id)
    return record and StreakConfig(record=record)

  @tasks.loop(minutes=10.0)
  async def _update_stats_loop(self):
    if self.bot.prod and self._current_len_guilds != len(self.bot.guilds):
      await self.update_stats()

  @commands.command(help="Get the link to vote for me on Top.gg", case_insensitive=True)
  async def vote(self, ctx: MyContext):
    self.user_streak.invalidate(self, ctx.author.id)
    async with ctx.db.acquire():
      query = """SELECT id,expires
                FROM reminders
                WHERE event = 'vote'
                AND extra #>> '{args,0}' = $1
                ORDER BY expires
                LIMIT 1;"""
      record = await ctx.db.fetchrow(query, str(ctx.author.id))
      expires = record["expires"] if record else None
      query = """SELECT expires, days
                FROM voting_streaks
                WHERE user_id = $1::bigint;"""
      record_streak = await ctx.db.fetchrow(query, ctx.author.id)
    vote_message = f"Your next vote time is: {time.format_dt(expires, style='R')}" if expires is not None else "You can vote now"
    streak_expiration = time.format_dt(record_streak['expires'], style="R") if record_streak else "some time ago"
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Vote", url=VOTE_URL, style=discord.ButtonStyle.url))
    await ctx.reply(embed=embed(
        author_name=f"Voting streak - {formats.plural(record_streak and record_streak['days'] or 0):day}",
        title="Voting",
        description=f"{vote_message}\n"
        f"Your voting streak is currently `{record_streak and record_streak['days'] or '0'}` and expires {streak_expiration}. "
        f"**To increase your streak, you need to vote at least once per day**. You can vote every 12 hours.\n\nWhen you vote you get:",
        fieldstitle=["Better rate limiting", "Longer chat messages"],
        fieldsval=[f"{config.ChatSpamConfig.voted_rate} messages/12 hours instead of {config.ChatSpamConfig.free_rate} messages/12 hours.", f"{config.PremiumPerks(config.PremiumTiersNew.voted).max_chat_characters} characters instead of {config.PremiumPerks(config.PremiumTiersNew.free).max_chat_characters} characters."]
    ), view=view)

  @commands.command(extras={"examples": ["test", "upvote"]}, hidden=True)
  @commands.is_owner()
  async def vote_fake(self, ctx: MyContext, user: Optional[Union[discord.User, discord.Member]] = None, _type: Optional[str] = "test"):
    user = user or ctx.author
    self.user_streak.invalidate(self, user.id)
    data = {
        "type": _type,
        "user": str(user.id),
        "query": {},
        "bot": self.bot.user.id,
        "is_weekend": False
    }
    self.bot.dispatch("dbl_vote", data)
    await ctx.send("Fake vote sent")

  async def update_stats(self):
    await self.bot.wait_until_ready()
    self._current_len_guilds = len(self.bot.guilds)
    log.info("Updating DBL stats")
    try:
      tasks = [self.bot.session.post(
          f"https://top.gg/api/bots/{self.bot.user.id}/stats",
          headers={"Authorization": os.environ["TOKENTOP"]},
          json={
              "server_count": len(self.bot.guilds),
              "shard_count": self.bot.shard_count,
          }
      ),
          self.bot.session.post(
          f"https://discord.bots.gg/api/v1/bots/{self.bot.user.id}/stats",
          headers={"Authorization": os.environ["TOKENDBOTSGG"]},
          json={
              "guildCount": len(self.bot.guilds),
              "shardCount": self.bot.shard_count,
          }
      ),
          self.bot.session.post(
          f"https://discordbotlist.com/api/v1/bots/{self.bot.user.id}/stats",
          headers={"Authorization": f'Bot {os.environ["TOKENDBL"]}'},
          json={
              "guilds": len(self.bot.guilds),
              "users": len(self.bot.users),
              "voice_connections": len(self.bot.voice_clients),
          }
      ),
          self.bot.session.post(
          f"https://api.discordlist.space/v2/bots/{self.bot.user.id}",
          headers={"Authorization": os.environ["TOKENDLS"], 'Content-Type': 'application/json'},
          json={
              "serverCount": len(self.bot.guilds)
          }
      )]
      await asyncio.gather(*tasks)
    except Exception as e:
      log.exception('Failed to post server count\n?: ?', type(e).__name__, e)
    else:
      log.info("Server count posted successfully")

  @commands.Cog.listener()
  async def on_vote_streak_timer_complete(self, timer: Timer):
    user_id = timer.args[0]
    await self.bot.wait_until_ready()

    query = "DELETE FROM voting_streaks WHERE user_id = $1::bigint RETURNING days;"
    days = await self.bot.pool.fetchval(query, int(user_id, base=10))
    self.user_streak.invalidate(self, int(user_id, base=10))
    log.info(f"User {user_id}'s voting streak expired, days: {days}")

  @commands.Cog.listener()
  async def on_vote_timer_complete(self, timer: Timer):
    user_id = timer.args[0]
    await self.bot.wait_until_ready()

    self.user_has_voted.invalidate(self, user_id)

    support_server = self.bot.get_guild(config.support_server_id)
    query = "SELECT days FROM voting_streaks WHERE user_id = $1"
    days: int | None = await self.bot.pool.fetchval(query, int(user_id, base=10))
    days = days or 1
    role_removed = False
    if support_server:
      member = await self.bot.get_or_fetch_member(support_server, user_id)
      if member is not None:
        try:
          await member.remove_roles(discord.Object(id=VOTE_ROLE), reason="Top.gg vote expired")
        except discord.HTTPException:
          pass
        else:
          role_removed = True
    reminder_sent = False
    try:
      private = self.bot.get_user(user_id) or (await self.bot.fetch_user(user_id))
      view = discord.ui.View()
      view.add_item(discord.ui.Button(label="Vote", style=discord.ButtonStyle.url, url=VOTE_URL))
      await private.send(embed=embed(title="Your vote has expired.", description=f"Vote again to keep your perks and to keep your streak of `{formats.plural(days):day}` going!"), view=view)
    except discord.HTTPException:
      pass
    else:
      reminder_sent = True

    log.info(f"Vote expired for {user_id}. Reminder sent: {reminder_sent}, role removed: {role_removed}")

  @commands.Cog.listener()
  async def on_dbl_vote(self, data: dict):
    now = discord.utils.utcnow()
    fut = now + datetime.timedelta(hours=12)
    expires = fut + datetime.timedelta(days=1)
    _type, user = data.get("type", None), data.get("user", None)
    log.info(f'Received an upvote, {data}')
    if _type == "test":
      fut = now + datetime.timedelta(seconds=10)
      expires = fut + datetime.timedelta(minutes=1)
    if user is None:
      return
    reminder = self.bot.reminder
    if reminder is None:
      return
    async with self.bot.pool.acquire(timeout=300.0) as conn:
      await reminder.create_timer(fut, "vote", user, created=now)
      query = "DELETE FROM reminders WHERE event='vote_streak' AND extra #>> '{args,0}' = $1;"
      status = await conn.execute(query, user)
      if status != "DELETE 0":
        if reminder._current_timer and reminder._current_timer.id == id:
          reminder._task.cancel()
          reminder._task = self.bot.loop.create_task(reminder.dispatch_timers())

      query = "INSERT INTO voting_streaks (user_id, last_vote, expires) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET days = voting_streaks.days + 1, last_vote = $2, expires = $3;"
      await conn.execute(query, int(user, base=10), now.replace(tzinfo=None), expires.replace(tzinfo=None))
      await reminder.create_timer(expires, "vote_streak", user, created=now)
    self.user_streak.invalidate(self, int(user, base=10))
    self.user_has_voted.invalidate(self, int(user, base=10))
    if _type == "test" or int(user, base=10) not in (215227961048170496, 813618591878086707):
      support_server = self.bot.get_guild(config.support_server_id)
      if not support_server:
        return

      member = await self.bot.get_or_fetch_member(support_server, user)
      if member is not None and not member.pending:
        try:
          await member.add_roles(discord.Object(id=VOTE_ROLE), reason="Voted on Top.gg")
        except discord.HTTPException:
          pass
        else:
          log.info(f"Added vote role to {member.id}")
      await self.log_bumps.send(
          username=self.bot.user.display_name,
          avatar_url=self.bot.user.display_avatar.url,
          embed=embed(
              title=f"Somebody Voted - {_type}",
              description=f'{member and member.mention} (ID: {user})',
          )
      )


async def setup(bot: Friday):
  await bot.add_cog(TopGG(bot))
