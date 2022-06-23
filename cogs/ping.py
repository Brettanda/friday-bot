from __future__ import annotations

from discord.ext import commands
from typing import TYPE_CHECKING

from functions import embed

if TYPE_CHECKING:
  from functions import MyContext
  from index import Friday


class Ping(commands.Cog):
  """Ping? Pong!"""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__} content=\"Pong\">"

  @commands.hybrid_command(name="ping")
  async def ping(self, ctx: MyContext):
    """Pong!"""
    shard = ctx.guild and self.bot.get_shard(ctx.guild.shard_id)
    latency = f"{shard.latency*1000:,.0f}" if shard is not None else f"{self.bot.latency*1000:,.0f}"
    await ctx.send(embed=embed(title="Pong!", description=f"⏳ API is {latency}ms"))


async def setup(bot):
  await bot.add_cog(Ping(bot))
