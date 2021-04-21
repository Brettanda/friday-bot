import d20

from discord.ext import commands
from discord_slash import cog_ext

from functions import embed, MessageColors, checks


class Dice(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.command(name="dice", aliases=["d", "r", "roll"])
  async def norm_dice(self, ctx, *, roll: str):
    async with ctx.typing():
      post = await self.dice(roll)
    await ctx.reply(**post)

  @cog_ext.cog_slash(name="dice", description="D&D dice rolling")
  @checks.slash(user=False, private=True)
  async def slash_dice(self, ctx, *, roll: str):
    post = await self.dice(roll)
    await ctx.send(**post)

  async def dice(self, roll):
    roll = roll.lower()

    if "bump" in roll:
      return

    result = None
    try:
      result = d20.roll(roll)
    except Exception as e:
      return dict(embed=embed(title=f"{e}", color=MessageColors.ERROR))
    else:
      return dict(embed=embed(title=f"Your total: {str(result.total)}", description=f"Query: {str(result.ast)}\nResult: {str(result)}"))


def setup(bot):
  bot.add_cog(Dice(bot))
