from discord.ext import commands
from discord_slash import SlashContext, cog_ext

from functions import embed  # ,MySlashContext#,profile


class Ping(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.command(name="ping", description="Pong!")
  async def norm_ping(self, ctx):
    await ctx.reply(**await self.ping(ctx))

  @cog_ext.cog_slash(name="ping", description="Ping!")
  async def slash_ping(self, ctx: SlashContext):
    await ctx.defer(True)
    await ctx.send(hidden=True, **await self.ping(ctx))

  async def ping(self, ctx):
    if isinstance(ctx, SlashContext):
      return dict(content="Pong!")
    return dict(embed=embed(title="Pong!"))


def setup(bot):
  bot.add_cog(Ping(bot))
