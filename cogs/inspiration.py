from discord.ext import commands

# from PIL import Image, ImageDraw
# https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html

# import os,sys
# sys.path.insert(1, os.path.join(sys.path[0], '..'))
from functions import embed


class Inspiration(commands.Cog):
  """description goes here"""

  @commands.command(name="inspiration", hidden=True)
  @commands.is_owner()
  async def inspiration(self, ctx):
    print("pong")
    await ctx.reply(embed=embed(title="Pong!"))


def setup(bot):
  bot.add_cog(Inspiration(bot))
