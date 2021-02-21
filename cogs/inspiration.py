from discord.ext.commands import Cog
from discord.ext.commands import command

from PIL import Image, ImageDraw
# https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html

import os,sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from functions import *

class Inspiration(Cog):
  """description goes here"""

  def __init__(self,bot):
    self.bot = bot

  @command(name="inspiration",enabled=False)
  async def inspiration(self,ctx):
    print("pong")
    await ctx.reply(embed=embed(title="Pong!"),mention_author=False)

def setup(bot):
  bot.add_cog(Inspiration(bot))