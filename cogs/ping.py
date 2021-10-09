from discord.ext import commands
from discord_slash import cog_ext

from functions import embed

from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class Ping(commands.Cog):
  """Ping? Pong!"""

  def __init__(self, bot: "Bot"):
    self.bot = bot

  @commands.command(name="ping", help="Pong!")
  async def norm_ping(self, ctx):
    await self.ping(ctx)

  @cog_ext.cog_slash(name="ping", description="Ping!")
  async def slash_ping(self, ctx):
    await self.ping(ctx, True)

  async def ping(self, ctx, slash: bool = False):
    latency = f"{self.bot.get_shard(ctx.guild.shard_id).latency*1000:,.0f}" if ctx.guild is not None else f"{self.bot.latency*1000:,.0f}"
    return await ctx.send(embed=embed(title="Pong!", description=f"⏳ API is {latency}ms"))


def setup(bot):
  bot.add_cog(Ping(bot))
