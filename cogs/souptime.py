import discord
from discord import Embed
from discord.ext import commands

from functions import embed,MessageColors
import json,random

with open('./config.json') as f:
  config = json.load(f)

class Souptime(commands.Cog):
  """description goes here"""

  def __init__(self,bot):
    self.bot = bot

  @commands.command(name='souptime',help='Soup Time')
  @commands.cooldown(1,7, commands.BucketType.user)
  @commands.bot_has_permissions(send_messages = True, read_messages = True, embed_links = True)
  async def souptime(self,ctx):
    image = random.choice(config['soups'])

    r = embed(
      title="Here is sum soup, just for you",
      color=MessageColors.SOUPTIME,
      description="I hope you enjoy!",
      image=image
    )

    await ctx.reply(embed=r)

def setup(bot):
  bot.add_cog(Souptime(bot))