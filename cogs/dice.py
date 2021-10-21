import d20

from nextcord.ext import commands
# from discord_slash import cog_ext

from functions import embed, MessageColors  # , checks

from functions import MyContext


class Dice(commands.Cog):
  """Roll some dice with advantage or just do some basic math."""

  def __repr__(self):
    return "<cogs.Dice>"

  @commands.command(name="dice", extras={"slash": True, "examples": ["1d20", "5d10k3", "d6"]}, aliases=["d", "r", "roll"], help="D&D dice rolling")
  async def norm_dice(self, ctx: "MyContext", *, roll: str):
    if "bump" in roll:
      return

    return await self.dice(ctx, roll)

  # @cog_ext.cog_slash(name="dice", description="D&D dice rolling")
  # @checks.slash(user=False, private=True)
  # async def slash_dice(self, ctx: "MyContext", *, roll: str):
  #   return await self.dice(ctx, roll)

  async def dice(self, ctx: "MyContext", roll):
    roll = roll.lower()

    result = None
    try:
      result = d20.roll(roll)
    except Exception as e:
      return await ctx.send(embed=embed(title=f"{e}", color=MessageColors.ERROR))
    else:
      return await ctx.send(embed=embed(title=f"Your total: {str(result.total)}", description=f"Query: {str(result.ast)}\nResult: {str(result)}"))


def setup(bot):
  bot.add_cog(Dice(bot))
