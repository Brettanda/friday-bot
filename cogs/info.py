import discord
from discord.ext import commands

from functions import embed


class Info(commands.Cog):
  """description goes here"""

  def __init__(self,bot):
    self.bot = bot

  @commands.command(name="info",description="Displays some information about myself :)")
  async def info(self,ctx):

    await ctx.reply(
      embed=embed(
        title=f"{self.bot.user.name} - Info",
        thumbnail=self.bot.user.avatar_url,
        description="Some information about me, Friday ;)",
        fieldstitle=["Username","Guilds joined","Status","Latency","Loving Life"],
        fieldsval=[self.bot.user.name,len(self.bot.guilds),self.bot.activity,f"{self.bot.latency*1000:,.0f} ms","True"]
      ),mention_author=False
    )

def setup(bot):
  bot.add_cog(Info(bot))