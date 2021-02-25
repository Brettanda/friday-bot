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
      await ctx.send(embed=embed(title="Pong!"))
    except discord.HTTPException:
      await ctx.send("Pong!")

def setup(bot):
  bot.add_cog(Ping(bot))