import logging

from discord.ext import commands
# from importlib import reload

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

  async def reload_imports(self, **imports):
    # https://stackoverflow.com/questions/437589/how-do-i-unload-reload-a-python-module
    print(imports)
