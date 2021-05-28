import os

import dbl
from discord.ext import commands, tasks


class TopGG(commands.Cog):
  """Handles interactions with the top.gg API"""

  def __init__(self, bot):
    self.bot = bot
    self.token = os.getenv("TOKENDBL")
    self.dblpy = dbl.DBLClient(self.bot, self.token, autopost=False)
    if self.bot.prod:
      self.update_stats.start()

  def cog_unload(self):
    self.update_stats.cancel()

  @tasks.loop(minutes=30.0)
  async def update_stats(self):
    await self.bot.wait_until_ready()
    self.bot.logger.info("Updating DBL stats")
    try:
      await self.dblpy.post_guild_count(guild_count=len(self.bot.guilds), shard_count=self.bot.shard_count, shard_id=self.bot.shard_id)
      self.bot.logger.info("Server count posted successfully")
    except Exception as e:
      self.bot.logger.exception('Failed to post server count\n%s: %s', type(e).__name__, e)

  @commands.Cog.listener()
  async def on_dbl_vote(self, data):
    self.bot.logger.info('Received an upvote')
    self.bot.logger.info(data)


def setup(bot):
  bot.add_cog(TopGG(bot))
