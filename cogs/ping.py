import discord
from discord.ext import commands

from functions import embed

class Ping(commands.Cog):
  """description goes here"""

  def __init__(self,bot):
    self.bot = bot

  @commands.command(name="ping",hidden=True)
  async def ping(self,ctx):
    print("pong")

    try:
      await ctx.reply(embed=embed(title="Pong!"),mention_author=False)
    except discord.HTTPException:
      await ctx.reply("Pong!",mention_author=False)

def setup(bot):
  bot.add_cog(Ping(bot))