# import discord
from discord.ext.commands import Cog,command,bot_has_permissions

import random

from functions import embed,MessageColors

class RockPaperScissors(Cog):
  def __init__(self,bot):
    self.bot = bot
    self.options = ["rock","paper","scissors"]

  @command(name="rockpaperscissors",description="Play Rock Paper Scissors with Friday",aliases=["rps"],usage="<rock, paper or scissors>")
  @bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def rock_paper_scissors(self,ctx,args:str):
    # args = args.split(" ")
    # arg = args[0].lower()
    arg = args.lower()
    # if args not in self.options
    #   await ctx.reply(embed=embed(title="Please only choose one of three options, Rock, Paper, or Scissors",color=MessageColors.ERROR))
    #   return

    if arg not in self.options:
      await ctx.reply(embed=embed(title=f"`{arg}` is not Rock, Paper, Scissors. Please choose one of those three.",color=MessageColors.ERROR))
      return

    num = random.randint(0,len(self.options)-1)

    mychoice = self.options[num]

    if mychoice == arg:
      conclusion = "Draw"
    elif mychoice == "rock" and arg == "paper":
      conclusion = self.bot.user
    elif mychoice == "rock" and arg == "scissors":
      conclusion = ctx.author
    elif mychoice == "paper" and arg == "scissors":
      conclusion = self.bot.user
    elif mychoice == "paper" and arg == "rock":
      conclusion = ctx.author
    elif mychoice == "scissors" and arg == "rock":
      conclusion = self.bot.user
    elif mychoice == "scissors" and arg == "paper":
      conclusion = ctx.author

    await ctx.reply(embed=embed(title=f"Your move: {arg} VS My move: {mychoice}",color=MessageColors.RPS,description=f"The winner of this round is: **{conclusion}**"))


def setup(bot):
  bot.add_cog(RockPaperScissors(bot))