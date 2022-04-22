from discord.ext import commands

from functions import embed

from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class Ping(commands.Cog):
  """Ping? Pong!"""

  def __init__(self, bot: "Bot"):
    self.bot = bot

  def __repr__(self) -> str:
    return "<cogs.Ping content=\"Pong\">"

  @commands.hybrid_command(name="ping")
  async def ping(self, ctx):
    """Pong!"""
    latency = f"{self.bot.get_shard(ctx.guild.shard_id).latency*1000:,.0f}" if ctx.guild is not None else f"{self.bot.latency*1000:,.0f}"
    return await ctx.send(embed=embed(title="Pong!", description=f"⏳ API is {latency}ms"))


async def setup(bot):
  await bot.add_cog(Ping(bot))
