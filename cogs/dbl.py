import os
# import discord
import topgg
import asyncio
import datetime
from discord.ext import commands, tasks
from typing_extensions import TYPE_CHECKING
from functions import embed, config, query, non_coro_query

if TYPE_CHECKING:
  from index import Friday as Bot


class TopGG(commands.Cog):
  """Handles interactions with the top.gg API"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.token = os.getenv("TOKENDBL")
    self.topgg = topgg.DBLClient(self.bot, self.token, autopost=False)
    if self.bot.cluster_idx == 0:  # and self.bot.prod:
      non_coro_query(self.bot.log.mydb, """CREATE TABLE IF NOT EXISTS votes
                                        (id bigint UNIQUE NOT NULL,
                                        to_remind tinyint(1) NOT NULL DEFAULT 0,
                                        has_reminded tinyint(1) NOT NULL DEFAULT 0,
                                        voted_time timestamp NULL DEFAULT NULL)""")
      if not hasattr(self.bot, "topgg_webhook"):
        self.bot.topgg_webhook = topgg.WebhookManager(self.bot).dbl_webhook("/dblwebhook", os.environ["DBLWEBHOOKPASS"])
        self.bot.topgg_webhook.run(5000)
      self.update_votes.start()

    self.vote_role = 834347369998843904
    self.vote_url = "https://top.gg/bot/476303446547365891/vote"

    if self.bot.prod:
      self.update_stats.start()

  def cog_unload(self):
    self.update_votes.cancel()
    self.update_stats.cancel()

  @commands.group(name="vote", help="Get the link to vote for me on Top.gg", invoke_without_command=True)
  async def vote(self, ctx: commands.Context):
    await ctx.reply(embed=embed(title="Vote link!", description=self.vote_url))

  @vote.command(name="remind", help="Whether or not to remind you of the next time that you can vote")
  async def vote_remind(self, ctx: commands.Context):
    current_reminder = bool(await query(self.bot.log.mydb, "SELECT to_remind FROM votes WHERE id=%s", ctx.author.id))
    await query(self.bot.log.mydb, "INSERT INTO votes (id,to_remind) VALUES (%s,%s) ON DUPLICATE KEY UPDATE to_remind=%s", ctx.author.id, not current_reminder, not current_reminder)
    if current_reminder is not True:
      await ctx.reply(embed=embed(title="I will now DM you every 12 hours after you vote for when you can vote again"))
    elif current_reminder is True:
      await ctx.reply(embed=embed(title="I will stop DMing you for voting reminders 😢"))

  @tasks.loop(minutes=30.0)
  async def update_stats(self):
    if not self.bot.ready:
      return
    self.bot.logger.info("Updating DBL stats")
    try:
      await self.topgg.post_guild_count(guild_count=len(self.bot.guilds), shard_count=self.bot.shard_count)
      self.bot.logger.info("Server count posted successfully")
    except Exception as e:
      self.bot.logger.exception('Failed to post server count\n%s: %s', type(e).__name__, e)

  @tasks.loop(minutes=1.0)
  async def update_votes(self):
    while not self.bot.ready:
      await asyncio.sleep(0.2)
    reset_time, notify_time = datetime.datetime.utcnow() - datetime.timedelta(hours=24), datetime.datetime.utcnow() - datetime.timedelta(hours=12)
    reset_time_formated, notify_time_formated = f"{reset_time.year}-{'0' if reset_time.month < 10 else ''}{reset_time.month}-{'0' if reset_time.day < 10 else ''}{reset_time.day} {'0' if reset_time.hour < 10 else ''}{reset_time.hour}:{'0' if reset_time.minute < 10 else ''}{reset_time.minute}:{'0' if reset_time.second < 10 else ''}{reset_time.second}", f"{notify_time.year}-{'0' if notify_time.month < 10 else ''}{notify_time.month}-{'0' if notify_time.day < 10 else ''}{notify_time.day} {'0' if notify_time.hour < 10 else ''}{notify_time.hour}:{'0' if notify_time.minute < 10 else ''}{notify_time.minute}:{'0' if notify_time.second < 10 else ''}{notify_time.second}"
    votes = await query(self.bot.log.mydb, f"SELECT id FROM votes WHERE voted_time < timestamp('{reset_time_formated}')")
    reminds = await query(self.bot.log.mydb, f"SELECT id FROM votes WHERE has_reminded=0 AND to_remind=1 AND voted_time < timestamp('{notify_time_formated}')")
    vote_user_ids, remind_user_ids = [str(vote[0]) for vote in votes], [str(vote[0]) for vote in reminds]
    for user_id in remind_user_ids:
      try:
        private = await self.bot.http.start_private_message(user_id)
        await self.bot.http.send_message(private["id"], f"Your vote time has refreshed. You can now vote again! {self.vote_url}")
      except Exception:
        pass
    await query(self.bot.log.mydb, f"UPDATE votes SET has_reminded=1 WHERE has_reminded=0 AND voted_time < timestamp('{notify_time_formated}')")
    await query(self.bot.log.mydb, f"DELETE FROM votes WHERE to_remind=0 AND (voted_time IS NULL OR voted_time < timestamp('{notify_time_formated}'))")
    if len(remind_user_ids) > 0:
      self.bot.logger.info(f"Reminded {len(remind_user_ids)} users")
    if len(vote_user_ids) > 0:
      await query(self.bot.log.mydb, f"DELETE FROM votes WHERE to_remind=0 AND id IN ({','.join(vote_user_ids)})")
      await query(self.bot.log.mydb, f"UPDATE votes SET has_reminded=0,voted_time=NULL WHERE id IN ({','.join(vote_user_ids)})")
      batch = []
      for user_id in vote_user_ids:
        member = await self.bot.get_guild(config.support_server_id).fetch_member(user_id)
        if member is not None:
          self.bot.logger.info(f"Vote expired for {user_id}")
          batch.append(member.remove_roles(member.guild.get_role(self.vote_role), reason="Vote expired"))
      if len(batch) > 0:
        await asyncio.gather(*batch)

  @commands.Cog.listener()
  async def on_dbl_test(self, data):
    self.bot.logger.info(f"Testing received, {data}")
    await self.on_dbl_vote(data)

  @commands.Cog.listener()
  async def on_dbl_vote(self, data):
    self.bot.logger.info(f'Received an upvote, {data}')
    if data.get("user", None) is not None:
      await query(self.bot.log.mydb, "INSERT INTO votes (id,voted_time) VALUES (%s,%s) ON DUPLICATE KEY UPDATE has_reminded=0,voted_time=%s", int(data["user"]), datetime.datetime.now(), datetime.datetime.now())
    if data.get("type", None) == "test" or int(data.get("user", None)) not in (215227961048170496, 813618591878086707):
      if data.get("user", None) is not None:
        support_server = self.bot.get_guild(config.support_server_id)
        member = await support_server.fetch_member(data["user"]) if support_server is not None else None
        if member is not None:
          role = member.guild.get_role(self.vote_role)
          await member.add_roles(role, reason="Voted on Top.gg")
      await self.bot.log.log_bumps.send(
          username=self.bot.user.name,
          avatar_url=self.bot.user.avatar.url if hasattr(self.bot.user, "avatar") and not isinstance(self.bot.user.avatar, str) else self.bot.user.avatar_url if hasattr(self.bot.user, "avatar_url") else None,
          embed=embed(
              title=f"Somebody Voted - {data.get('type',None)}",
              fieldstitle=["Member", "Is week end"],
              fieldsval=[
                  f'{self.bot.get_user(data.get("user",None))} (ID: {data.get("user",None)})',
                  f'{data.get("isWeekend",None)}'],
              fieldsin=[False, False]
          )
      )


def setup(bot):
  bot.add_cog(TopGG(bot))
