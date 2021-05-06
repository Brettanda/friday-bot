import logging
import os

import dbl
from discord.ext import commands, tasks
from functions import GlobalCog

logger = logging.getLogger('dbl')


class TopGG(GlobalCog):
  """Handles interactions with the top.gg API"""

  def __init__(self, bot):
    super().__init__(bot)
    self.token = os.getenv("TOKENDBL")
    self.dblpy = dbl.DBLClient(self.bot, self.token, autopost=False)
    if self.bot.prod:
      self.update_stats.start()

  def cog_unload(self):
    self.update_stats.cancel()

  @tasks.loop(minutes=30.0)
  async def update_stats(self):
    await self.bot.wait_until_ready()
    logger.info("Updating DBL stats")
    try:
      await self.dblpy.post_guild_count(guild_count=len(self.bot.guilds), shard_count=self.bot.shard_count, shard_id=self.bot.shard_id)
      logger.info("Server count posted successfully")
    except Exception as e:
      logger.exception('Failed to post server count\n%s: %s', type(e).__name__, e)

  @commands.Cog.listener()
  async def on_dbl_vote(self, data):
    logger.info('Received an upvote')
    logger.info(data)


def setup(bot):
  bot.add_cog(TopGG(bot))
