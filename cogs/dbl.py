import asyncio
import datetime
import os

import discord
import topgg
from discord.ext import commands, tasks
from typing_extensions import TYPE_CHECKING

from functions import MyContext, config, embed

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

  @discord.ui.button(label="Remind me", style=discord.ButtonStyle.primary, custom_id="voting_remind_me")
  async def voting_remind_me(self, button: discord.ui.Button, interaction: discord.Interaction):
    current_reminder = bool(await self.bot.db.query("SELECT to_remind FROM votes WHERE id=$1 LIMIT 1", interaction.user.id))
    await self.bot.db.query("INSERT INTO votes (id,to_remind) VALUES ($1,$2) ON CONFLICT(id) DO UPDATE SET to_remind=$3", str(interaction.user.id), not current_reminder, not current_reminder)
    if current_reminder is not True:
      await interaction.response.send_message(ephemeral=True, embed=embed(title="I will now DM you every 12 hours after you vote for when you can vote again"))
    elif current_reminder is True:
      await interaction.response.send_message(ephemeral=True, embed=embed(title="I will stop DMing you for voting reminders 😢"))


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
      self.update_votes.start()

  def __repr__(self):
    return "<cogs.TopGG>"

  @discord.utils.cached_property
  def log_bumps(self) -> CustomWebhook:
    return CustomWebhook.partial(os.environ.get("WEBHOOKBUMPSID"), os.environ.get("WEBHOOKBUMPSTOKEN"), session=self.bot.session)

  def cog_unload(self):
    self.update_votes.cancel()

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
    prev_time = await self.bot.db.query("SELECT voted_time FROM votes WHERE id=$1 LIMIT 1", str(ctx.author.id))
    if isinstance(prev_time, str):
      next_time = datetime.datetime.strptime(prev_time, "%Y-%m-%d %H:%M:%S.%f") if prev_time is not None else None
    else:
      next_time = prev_time
    time = next_time.timestamp() + datetime.timedelta(hours=12).seconds if next_time is not None else None
    vote_message = f"Your next vote time is: <t:{round(time)}:R>" if prev_time is not None else "You can vote now"
    await ctx.reply(embed=embed(title="Voting", description=f"{vote_message}\n\nWhen you vote you get:", fieldstitle=["Better rate limiting"], fieldsval=["200 messages/12 hours instead of 80 messages/12 hours."], footer="To get voting reminders use the command `!vote remind`"), view=VoteView(self))

  @vote.command(name="remind", help="Whether or not to remind you of the next time that you can vote")
  async def vote_remind(self, ctx: "MyContext"):
    current_reminder = bool(await self.bot.db.query("SELECT to_remind FROM votes WHERE id=$1 LIMIT 1", str(ctx.author.id)))
    await self.bot.db.query("INSERT INTO votes (id,to_remind) VALUES ($1,$2) ON CONFLICT(id) DO UPDATE SET to_remind=$3", str(ctx.author.id), not current_reminder, not current_reminder)
    if current_reminder is not True:
      await ctx.send(embed=embed(title="I will now DM you every 12 hours after you vote for when you can vote again"))
    elif current_reminder is True:
      await ctx.send(embed=embed(title="I will stop DMing you for voting reminders 😢"))

  async def update_stats(self):
    await self.bot.wait_until_ready()
    self.bot.logger.info("Updating DBL stats")
    try:
      await self.topgg.post_guild_count(guild_count=len(self.bot.guilds), shard_count=self.bot.shard_count)
      self.bot.logger.info("Server count posted successfully")
    except Exception as e:
      self.bot.logger.exception('Failed to post server count\n?: ?', type(e).__name__, e)

  @tasks.loop(minutes=5.0)
  async def update_votes(self):
    await self.bot.wait_until_ready()
    reset_time, notify_time = discord.utils.utcnow() - datetime.timedelta(hours=24), discord.utils.utcnow() - datetime.timedelta(hours=12)
    reset_time_formated, notify_time_formated = f"{reset_time.year}-{'0' if reset_time.month < 10 else ''}{reset_time.month}-{'0' if reset_time.day < 10 else ''}{reset_time.day} {'0' if reset_time.hour < 10 else ''}{reset_time.hour}:{'0' if reset_time.minute < 10 else ''}{reset_time.minute}:{'0' if reset_time.second < 10 else ''}{reset_time.second}", f"{notify_time.year}-{'0' if notify_time.month < 10 else ''}{notify_time.month}-{'0' if notify_time.day < 10 else ''}{notify_time.day} {'0' if notify_time.hour < 10 else ''}{notify_time.hour}:{'0' if notify_time.minute < 10 else ''}{notify_time.minute}:{'0' if notify_time.second < 10 else ''}{notify_time.second}"
    votes = await self.bot.db.query(f"SELECT id FROM votes WHERE voted_time < to_timestamp('{reset_time_formated}','YYYY-MM-DD HH24:MI:SS')")
    reminds = await self.bot.db.query(f"SELECT id FROM votes WHERE has_reminded=false AND to_remind=true AND voted_time < to_timestamp('{notify_time_formated}','YYYY-MM-DD HH24:MI:SS')")
    vote_user_ids, remind_user_ids = [str(vote[0]) for vote in votes], [str(vote[0]) for vote in reminds]
    success = 0
    for user_id in remind_user_ids:
      try:
        private = await self.bot.fetch_user(int(user_id, base=10))
        await private.send(embed=embed(title="Your vote time has refreshed.", description="You can now vote again!"), view=Refresh())
      except discord.HTTPException:
        pass
      else:
        success += 1
    await self.bot.db.query(f"UPDATE votes SET has_reminded=true WHERE has_reminded=false AND voted_time < to_timestamp('{notify_time_formated}','YYYY-MM-DD HH24:MI:SS')")
    await self.bot.db.query(f"DELETE FROM votes WHERE to_remind=false AND (voted_time IS NULL OR voted_time < to_timestamp('{notify_time_formated}','YYYY-MM-DD HH24:MI:SS'))")
    if len(remind_user_ids) > 0:
      self.bot.logger.info(f"Reminded {success}/{len(remind_user_ids)} users")
    if len(vote_user_ids) > 0:
      batch, to_purge = [], []
      await self.bot.db.query("""UPDATE votes SET has_reminded=false,voted_time=NULL WHERE id IN $1""", [str(i) for i in vote_user_ids])
      for user_id in vote_user_ids:
        member = await self.bot.get_or_fetch_member(self.bot.get_guild(config.support_server_id), user_id)
        if member is not None:
          self.bot.logger.info(f"Vote expired for {user_id}")
          try:
            await member.remove_roles(member.guild.get_role(VOTE_ROLE), reason="Vote expired")
          except discord.HTTPException:
            pass
          else:
            to_purge.append(user_id)
      if len(to_purge) > 0:
        await self.bot.db.query(f"""DELETE FROM votes WHERE to_remind=false AND id IN ('{"','".join(to_purge)}')""")
      if len(batch) > 0:
        await asyncio.gather(*batch)

  # @commands.Cog.listener()
  # async def on_dbl_test(self, data):
  #   self.bot.logger.info(f"Testing received, {data}")
  #   time = datetime.datetime.now() - datetime.timedelta(hours=11, minutes=59)
  #   await self.on_dbl_vote(data, time)

  @commands.Cog.listener()
  async def on_dbl_vote(self, data, time=datetime.datetime.now()):
    self.bot.logger.info(f'Received an upvote, {data}')
    if data.get("type", None) == "test":
      time = datetime.datetime.now() - datetime.timedelta(hours=11, minutes=59)
    if data.get("user", None) is not None:
      await self.bot.db.query("INSERT INTO votes (id,voted_time) VALUES ($1,$2) ON CONFLICT(id) DO UPDATE SET has_reminded=false,voted_time=$2", str(data["user"]), time)
    if data.get("type", None) == "test" or int(data.get("user", None), base=10) not in (215227961048170496, 813618591878086707):
      if data.get("user", None) is not None:
        support_server = self.bot.get_guild(config.support_server_id)
        member = await self.bot.get_or_fetch_member(support_server, data["user"])
        if member is not None:
          try:
            await member.add_roles(discord.Object(id=VOTE_ROLE), reason="Voted on Top.gg")
          except discord.HTTPException:
            pass
          else:
            self.bot.logger.info(f"Added vote role to {member.id}")
      await self.log_bumps.send(
          username=self.bot.user.name,
          avatar_url=self.bot.user.display_avatar.url,
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
