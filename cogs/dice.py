from __future__ import annotations

from typing import TYPE_CHECKING

import d20
from discord import app_commands
from discord.ext import commands

from functions import MessageColors, embed

if TYPE_CHECKING:
  from functions import MyContext
  from index import Friday


class Dice(commands.Cog):
  """Roll some dice with advantage or just do some basic math."""

  def __init__(self, bot: Friday) -> None:
    self.bot: Friday = bot

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  @commands.hybrid_command(extras={"examples": ["1d20", "5d10k3", "d6"]}, aliases=["d", "r", "roll"])
  @app_commands.describe(roll="The roll to be made. How to: https://d20.readthedocs.io/en/latest/start.html")
  async def dice(self, ctx: MyContext, *, roll: str):
    """Dungeons and Dragons dice rolling"""
    if "bump" in roll.lower():
      raise commands.NotOwner()

    roll = roll.lower()

    result = None
    try:
      result = d20.roll(roll)
    except Exception as e:
      return await ctx.send(embed=embed(title=f"{e}", color=MessageColors.error()))
    else:
      return await ctx.send(embed=embed(
          title=ctx.lang.dice.dice.response_title.format(total=str(result.total)),
          description=ctx.lang.dice.dice.response_description.format(query=str(result.ast), result=str(result))))


async def setup(bot):
  await bot.add_cog(Dice(bot))
