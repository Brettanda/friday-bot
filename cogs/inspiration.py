from discord.ext.commands import Cog,command,bot_has_permissions

from PIL import Image, ImageDraw
# https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html

# import os,sys
# sys.path.insert(1, os.path.join(sys.path[0], '..'))
from functions import embed

class Inspiration(Cog):
  """description goes here"""

  def __init__(self,bot):
    self.bot = bot

  @command(name="inspiration",enabled=False)
  @bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def inspiration(self,ctx):
    print("pong")
    await ctx.reply(embed=embed(title="Pong!"))

def setup(bot):
  bot.add_cog(Inspiration(bot))