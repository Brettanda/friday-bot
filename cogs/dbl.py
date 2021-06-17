import os
import discord
import topgg
import asyncio
import datetime
from discord.ext import commands, tasks
from typing_extensions import TYPE_CHECKING
from functions import embed, config, query

if TYPE_CHECKING:
  from index import Friday as Bot


class TopGG(commands.Cog):
  """Handles interactions with the top.gg API"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.token = os.getenv("TOKENDBL")
    self.topgg = topgg.DBLClient(self.bot, self.token, autopost=False)
    if self.bot.cluster_idx == 0:  # and self.bot.prod:
      if not hasattr(self.bot, "topgg_webhook"):
        self.bot.topgg_webhook = topgg.WebhookManager(self.bot).dbl_webhook("/dblwebhook", os.environ["DBLWEBHOOKPASS"])
        self.bot.topgg_webhook.run(5000)
      self.update_votes.start()

    self.vote_url = "https://top.gg/bot/476303446547365891/vote"

    if self.bot.prod:
      self.update_stats.start()

  def cog_unload(self):
    self.update_votes.cancel()
    self.update_stats.cancel()

  @commands.command(name="vote", help="Get the link to vote for me on Top.gg")
  async def vote(self, ctx):
    await ctx.reply(embed=embed(title="Vote link!", description=f"[Vote Link!]({self.vote_url})"))

  @tasks.loop(minutes=30.0)
  async def update_stats(self):
    await self.bot.wait_until_ready()
    self.bot.logger.info("Updating DBL stats")
    try:
      await self.topgg.post_guild_count(guild_count=len(self.bot.guilds), shard_count=self.bot.shard_count)
      self.bot.logger.info("Server count posted successfully")
    except Exception as e:
      self.bot.logger.exception('Failed to post server count\n%s: %s', type(e).__name__, e)

  @tasks.loop(minutes=1.0)
  async def update_votes(self):
    await self.bot.wait_until_ready()
    reset_time, notify_time = datetime.datetime.utcnow() - datetime.timedelta(hours=48), datetime.datetime.utcnow() - datetime.timedelta(hours=12)
    reset_time_formated, notify_time_formated = f"{reset_time.year}-{'0' if reset_time.month < 10 else ''}{reset_time.month}-{'0' if reset_time.day < 10 else ''}{reset_time.day} {'0' if reset_time.hour < 10 else ''}{reset_time.hour}:{'0' if reset_time.minute < 10 else ''}{reset_time.minute}:{'0' if reset_time.second < 10 else ''}{reset_time.second}", f"{notify_time.year}-{'0' if notify_time.month < 10 else ''}{notify_time.month}-{'0' if notify_time.day < 10 else ''}{notify_time.day} {'0' if notify_time.hour < 10 else ''}{notify_time.hour}:{'0' if notify_time.minute < 10 else ''}{notify_time.minute}:{'0' if notify_time.second < 10 else ''}{notify_time.second}"
    votes = await query(self.bot.mydb, f"SELECT id FROM votes WHERE voted_time < timestamp('{reset_time_formated}')")
    reminds = await query(self.bot.mydb, f"SELECT id,remind FROM votes WHERE remind=0 AND voted_time < timestamp('{notify_time_formated}')")
    vote_user_ids, remind_user_ids = [str(vote[0]) for vote in votes], [str(vote[0]) for vote in reminds]
    # for user_id in remind_user_ids:
    #   try:
    #     private = await self.bot.http.start_private_message(user_id)
    #     await self.bot.http.send_message(private["id"], f"Your vote time has refreshed. You can now vote again! {self.vote_url}")
    #   except Exception:
    #     pass
    if len(remind_user_ids) > 0:
      await query(self.bot.mydb, f"UPDATE votes SET remind=0 WHERE remind=1 AND voted_time < timestamp('{notify_time_formated}')")
    if len(vote_user_ids) > 0:
      await query(self.bot.mydb, f"DELETE FROM votes WHERE id IN ({','.join(vote_user_ids)})")

  @commands.Cog.listener()
  async def on_dbl_test(self, data):
    self.bot.logger.info(f"Testing received, {data}")
    await self.on_dbl_vote(data)

  @commands.Cog.listener()
  async def on_dbl_vote(self, data):
    self.bot.logger.info(f'Received an upvote, {data}')
    if data.get("user", None) is not None:
      await query(self.bot.mydb, "INSERT INTO votes (id,voted_time) VALUES (%s,%s) ON DUPLICATE KEY UPDATE voted_time=%s", int(data["user"]), datetime.datetime.now(), datetime.datetime.now())
    if int(data.get("user", None)) not in (215227961048170496, 813618591878086707):
      if data.get("user", None) is not None:
        support_server = self.bot.get_guild(config.support_server_id)
        member = await support_server.fetch_member(data["user"]) if support_server is not None else None
        if member is not None:
          role = member.guild.get_role(834347369998843904)
          await member.add_roles(role, reason="Voted on Top.gg")
      await self.bot.log.log_bumps.send(
          username=self.bot.user.name,
          avatar_url=self.bot.user.avatar_url,
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
