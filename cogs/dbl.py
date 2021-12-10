import datetime
import os

import discord
import topgg
from discord.ext import commands
from typing_extensions import TYPE_CHECKING

from functions import MyContext, config, embed, time

from .log import CustomWebhook

if TYPE_CHECKING:
  from index import Friday as Bot

VOTE_ROLE = 834347369998843904
VOTE_URL = "https://top.gg/bot/476303446547365891/vote"


class VoteView(discord.ui.View):
  """A view that shows the user how to vote for the bot."""

  def __init__(self, parent: "TopGG", *, timeout=None):
    self.parent = parent
    self.bot = self.parent.bot
    super().__init__(timeout=timeout)
    self.add_item(discord.ui.Button(label="Vote link", url=VOTE_URL, style=discord.ButtonStyle.url))


class Refresh(discord.ui.View):
  def __init__(self):
    super().__init__()
    self.add_item(discord.ui.Button(label="Vote", style=discord.ButtonStyle.url, url=VOTE_URL))


class TopGG(commands.Cog):
  """Handles interactions with the top.gg API"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.token = os.getenv("TOKENDBL")
    self.topgg = topgg.DBLClient(self.bot, self.token, autopost=False)
    if self.bot.cluster_idx == 0:
      if not hasattr(self.bot, "topgg_webhook"):
        self.bot.topgg_webhook = topgg.WebhookManager(self.bot).dbl_webhook("/dblwebhook", os.environ["DBLWEBHOOKPASS"])
        self.bot.topgg_webhook.run(5000)

  def __repr__(self):
    return "<cogs.TopGG>"

  @discord.utils.cached_property
  def log_bumps(self) -> CustomWebhook:
    return CustomWebhook.partial(os.environ.get("WEBHOOKBUMPSID"), os.environ.get("WEBHOOKBUMPSTOKEN"), session=self.bot.session)

  @commands.Cog.listener()
  async def on_ready(self):
    if not self.bot.views_loaded:
      self.bot.add_view(VoteView(self))
    if self.bot.prod:
      await self.update_stats()

  @commands.Cog.listener("on_guild_join")
  @commands.Cog.listener("on_guild_remove")
  async def guild_change(self, guild):
    if self.bot.prod:
      await self.update_stats()

  @commands.group(name="vote", help="Get the link to vote for me on Top.gg", invoke_without_command=True, case_insensitive=True)
  async def vote(self, ctx: "MyContext"):
    query = """SELECT id,expires
              FROM reminders
              WHERE event = 'vote'
              AND extra #>> '{args,0}' = $1
              ORDER BY expires
              LIMIT 1;"""
    record = await ctx.pool.fetchrow(query, str(ctx.author.id))
    expires = record["expires"] if record else None
    vote_message = f"Your next vote time is: {time.format_dt(expires, style='R')}" if expires is not None else "You can vote now"
    await ctx.reply(embed=embed(title="Voting", description=f"{vote_message}\n\nWhen you vote you get:", fieldstitle=["Better rate limiting"], fieldsval=["200 messages/12 hours instead of 80 messages/12 hours."]), view=VoteView(self))

  @vote.command(name="fake", extras={"examples": ["test", "upvote"]}, hidden=True)
  @commands.is_owner()
  async def vote_fake(self, ctx: "MyContext", _type: str = "test"):
    data = {
        "type": _type,
        "user": str(ctx.author.id),
        "query": {},
        "bot": self.bot.user.id,
        "is_weekend": False
    }
    self.bot.dispatch("dbl_vote", data)
    await ctx.send("Fake vote sent")

  async def update_stats(self):
    await self.bot.wait_until_ready()
    self.bot.logger.info("Updating DBL stats")
    try:
      await self.topgg.post_guild_count(guild_count=len(self.bot.guilds), shard_count=self.bot.shard_count)
      self.bot.logger.info("Server count posted successfully")
    except Exception as e:
      self.bot.logger.exception('Failed to post server count\n?: ?', type(e).__name__, e)

  @commands.Cog.listener()
  async def on_vote_timer_complete(self, timer):
    user_id = timer.args[0]
    await self.bot.wait_until_ready()

    support_server = self.bot.get_guild(config.support_server_id)
    member = await self.bot.get_or_fetch_member(support_server, user_id)
    role_removed = False
    if member is not None:
      try:
        await member.remove_roles(discord.Object(id=VOTE_ROLE), reason="Top.gg vote expired")
      except discord.HTTPException:
        pass
      else:
        role_removed = True
    reminder_sent = False
    try:
      private = await self.bot.fetch_user(user_id)
      await private.send(embed=embed(title="Your vote time has refreshed.", description="You can now vote again!"), view=Refresh())
    except discord.HTTPException:
      pass
    else:
      reminder_sent = True

    self.bot.logger.info(f"Vote expired for {user_id}. Reminder sent: {reminder_sent}, role removed: {role_removed}")

  # @commands.Cog.listener()
  # async def on_dbl_test(self, data):
  #   self.bot.logger.info(f"Testing received, {data}")
  #   time = datetime.datetime.now() - datetime.timedelta(hours=11, minutes=59)
  #   await self.on_dbl_vote(data, time)

  @commands.Cog.listener()
  async def on_dbl_vote(self, data: dict, fut=time.FutureTime("12h")):
    _type, user, isWeekend = data.get("type", None), data.get("user", None), data.get("isWeekend", False)
    self.bot.logger.info(f'Received an upvote, {data}')
    if _type == "test":
      fut = time.FutureTime("2m")
    if user is None:
      return
    reminder = self.bot.get_cog("Reminder")
    if reminder is None:
      return
    await reminder.create_timer(fut.dt, "vote", user)
    if _type == "test" or int(user, base=10) not in (215227961048170496, 813618591878086707):
      if user is not None:
        support_server = self.bot.get_guild(config.support_server_id)
        member = await self.bot.get_or_fetch_member(support_server, user)
        if member is not None:
          try:
            await member.add_roles(discord.Object(id=VOTE_ROLE), reason="Voted on Top.gg")
          except discord.HTTPException:
            pass
          else:
            self.bot.logger.info(f"Added vote role to {member.id}")
      await self.log_bumps.send(
          username=self.bot.user.display_name,
          avatar_url=self.bot.user.display_avatar.url,
          embed=embed(
              title=f"Somebody Voted - {_type}",
              fieldstitle=["Member", "Is week end"],
              fieldsval=[
                  f'{self.bot.get_user(user)} (ID: {user})',
                  f'{isWeekend}'],
              fieldsin=[False, False]
          )
      )


def setup(bot):
  bot.add_cog(TopGG(bot))
