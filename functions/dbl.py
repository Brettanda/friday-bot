import dbl,logging

from discord.ext.commands import Cog

import os#,sys
# sys.path.insert(1, os.path.join(sys.path[0], '..'))
# from functions import *

class TopGG(Cog):
  """Handles interactions with the top.gg API"""

  def __init__(self,bot):
    self.bot = bot
    self.token = os.getenv("TOKENDBL")
    self.dblpy = dbl.DBLClient(self.bot,self.token,autopost=True)

  @Cog.listener()
  async def on_guild_post(self):
    print("Server count posted successfully")
    logging.info("Server count posted successfully")
  
def setup(bot):
  bot.add_cog(TopGG(bot))