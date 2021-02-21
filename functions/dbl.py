import dbl

from discord.ext import commands

import os#,sys
# sys.path.insert(1, os.path.join(sys.path[0], '..'))
# from functions import *

class TopGG(commands.Cog):
  """Handles interactions with the top.gg API"""

  def __init__(self,bot):
    self.bot = bot
    self.token = os.getenv("TOKENDBL")
    self.dblpy = dbl.DBLClient(self.bot,self.token,autopost=True)

  async def on_guild_post():
    print("Server count posted successfully")
  
def setup(bot):
  bot.add_cog(TopGG(bot))