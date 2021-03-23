import discord,logging,asyncio,sys
from discord.ext import tasks,commands
from datetime import date

from functions import embed

original_image = "assets\\friday-logo.png"

class DatedEvents(commands.Cog):
  def __init__(self,bot):
    self.bot = bot
    self.loop = bot.loop
    if len(sys.argv) > 1:
      if sys.argv[1] == "--prod" or sys.argv[1] == "--production":
        self.dated_events.start()
    # self.events = bot.loop.create_task(self.dated_events(),name="Dated events")

  @tasks.loop(seconds=3600.0)
  async def dated_events(self):
    today = date.today()
    month = today.strftime("%m")
    day = today.strftime("%d")
    guild = self.bot.get_guild(707441352367013899)
    user = self.bot.user
    if int(month) == 4 and int(day) == 1:
      print("april fools")
      logger.info("april fools")
      with open("assets\\friday_april_fools.png","rb") as image:
        f = image.read()
        await asyncio.gather(
          guild.edit(icon=f),
          user.edit(avatar=f)
        ) 
      await asyncio.sleep(43200.0)
    elif int(month) == 4 and int(day) == 2:
      print("post-april fools")
      logger.info("post-april fools")
      with open(original_image,"rb") as image:
        f = image.read()
        await asyncio.gather(
          guild.edit(icon=f),
          user.edit(avatar=f)
        ) 
      await asyncio.sleep(43200.0)


  @dated_events.before_loop
  async def before_dated_events(self):
    await self.bot.wait_until_ready()

  def cog_unload(self):
    self.dated_events.cancel()

def setup(bot):
  global logger
  logger = logging.getLogger(__name__)
  bot.add_cog(DatedEvents(bot))