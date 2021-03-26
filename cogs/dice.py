import d20

import discord
from discord.ext import commands
from discord_slash import cog_ext,SlashContext

from functions import embed

class Dice(commands.Cog):
  """description goes here"""

  def __init__(self,bot):
    self.bot = bot

  @commands.command(name="dice",aliases=["d","r","roll"])
  async def norm_dice(self,ctx,*,roll:str):
    async with ctx.typing():
      post = await self.dice(ctx,roll)
    await ctx.reply(**post)

  @cog_ext.cog_slash(name="dice",description="D&D dice rolling",guild_ids=[243159711237537802,805579185879121940])
  async def slash_dice(self,ctx,*,roll:str):
    await ctx.respond()
    post = await self.dice(ctx,roll)
    await ctx.send(**post)
  
  async def dice(self,ctx,roll):
    roll = roll.lower()

    if "bump" in roll:
      return
      
    result = d20.roll(roll)
    return dict(embed=embed(title=f"Your total: {str(result.total)}",description=f"Query: {str(result.ast)}\nResult: {str(result)}"))

def setup(bot):
  bot.add_cog(Dice(bot))