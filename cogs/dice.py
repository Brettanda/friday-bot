import d20

import discord
from discord.ext.commands import Cog,command,bot_has_permissions

from functions import embed

class Dice(Cog):
  """description goes here"""

  def __init__(self,bot):
    self.bot = bot

  @command(name="dice",aliases=["d","r","roll"])
  @bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def dice(self,ctx,*,roll:str):
    roll = roll.lower()
    result = d20.roll(roll)
    try:
      await ctx.reply(embed=embed(title=f"Your total: {str(result.total)}",description=f"Query: {str(result.ast)}\nResult: {str(result)}"))
    except discord.HTTPException:
      await ctx.reply(f"Your total: {str(result.total)}\nQuery: {str(result.ast)}\nResult: {str(result)}")

def setup(bot):
  bot.add_cog(Dice(bot))