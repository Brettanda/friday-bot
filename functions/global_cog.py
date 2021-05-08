import logging

from discord.ext import commands

logger = logging.getLogger(__name__)


class GlobalCog(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.loop = bot.loop

  @commands.Cog.listener()
  async def on_shard_ready(self, shard_id):
    logger.info(f"Cog ready: {self.__cog_name__}")

  def cog_unload(self):
    return super().cog_unload()
