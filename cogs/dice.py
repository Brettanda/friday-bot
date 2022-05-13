import d20

from discord.ext import commands
# from discord_slash import cog_ext

from functions import embed, MessageColors  # , checks

from functions import MyContext


class Dice(commands.Cog):
  """Roll some dice with advantage or just do some basic math."""

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  @commands.command(name="dice", extras={"slash": True, "examples": ["1d20", "5d10k3", "d6"]}, aliases=["d", "r", "roll"], help="D&D dice rolling")
  async def norm_dice(self, ctx: "MyContext", *, roll: str):
    if "bump" in roll.lower():
      raise commands.NotOwner()

    roll = roll.lower()

    result = None
    try:
      result = d20.roll(roll)
    except Exception as e:
      return await ctx.send(embed=embed(title=f"{e}", color=MessageColors.ERROR))
    else:
      return await ctx.send(embed=embed(title=f"Your total: {str(result.total)}", description=f"Query: {str(result.ast)}\nResult: {str(result)}"))


async def setup(bot):
  await bot.add_cog(Dice(bot))
