import re

from discord.ext import commands

import os,sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from functions import *

class ServerSettings(commands.Cog):
  """description goes here"""

  def __init__(self,bot):
    self.bot = bot

  @commands.command(name="prefix",hidden=True)
  @commands.is_owner()
  async def prefix(self,ctx,new_prefix:str):
    if len(new_prefix) > 3:
      print(f"max string met: {len(new_prefix)}")
    appinfo = await self.bot.application_info()
    if ctx.message.author.id != appinfo.owner.id:
      return
    # if ctx.message.author.guild_permissions.administrator != True:
    #   return
    if await is_pm(ctx) == True:
      return
    await ctx.reply(embed=embed(title=f"My new prefix is `{new_prefix}`"),mention_author=False)

def setup(bot):
  bot.add_cog(ServerSettings(bot))