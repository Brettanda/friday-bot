from discord.ext import commands
from discord_slash import cog_ext

from functions import embed


class Ping(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.command(name="ping", description="Pong!")
  async def norm_ping(self, ctx):
    await ctx.reply(**await self.ping(ctx))

  @cog_ext.cog_slash(name="ping", description="Ping!")
  async def slash_ping(self, ctx):
    await ctx.send(**await self.ping(ctx))

  async def ping(self, ctx):
    return dict(embed=embed(title="Pong!"))


def setup(bot):
  bot.add_cog(Ping(bot))
