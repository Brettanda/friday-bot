import d20

from discord.ext import commands
from discord_slash import cog_ext

from functions import embed

class Dice(commands.Cog):
  def __init__(self,bot):
    self.bot = bot

  @commands.command(name="dice",aliases=["d","r","roll"])
  async def norm_dice(self,ctx,*,roll:str):
    async with ctx.typing():
      post = await self.dice(roll)
    await ctx.reply(**post)

  @cog_ext.cog_slash(name="dice",description="D&D dice rolling")
  async def slash_dice(self,ctx,*,roll:str):
    await ctx.defer()
    post = await self.dice(roll)
    await ctx.send(**post)

  async def dice(self,roll):
    roll = roll.lower()

    if "bump" in roll:
      return

    result = d20.roll(roll)
    return dict(embed=embed(title=f"Your total: {str(result.total)}",description=f"Query: {str(result.ast)}\nResult: {str(result)}"))

def setup(bot):
  bot.add_cog(Dice(bot))
