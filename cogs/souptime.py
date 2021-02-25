import discord
from discord import Embed
from discord.ext.commands import Cog
from discord.ext import commands

import os,sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from functions import *
import json

with open('./config.json') as f:
  config = json.load(f)

class Souptime(Cog):
  """description goes here"""

  def __init__(self,bot):
    self.bot = bot

  @commands.command(name='souptime',help='Soup Time')
  @commands.cooldown(1,7, commands.BucketType.user)
  async def souptime(self,ctx):
    num = random.randint(0,len(config['soups']))
    image = config['soups'][num]

    r = embed(
      title="Here is sum soup, just for you",
      color=MessageColors.SOUPTIME,
      description="I hope you enjoy!",
      image=image
    )

    await ctx.reply(embed=r)

def setup(bot):
  bot.add_cog(Souptime(bot))