import discord
from discord.ext import commands

import os,sys
from functions import embed,MessageColors,mydb_connect,query

class CustomMusic(commands.Cog):
  """description goes here"""

  def __init__(self,bot):
    self.bot = bot

  async def connect(self,ctx):
    mydb = mydb_connect()
    mycursor = mydb.cursor()
    mycursor.execute(f"SELECT prefix FROM servers WHERE id='{ctx.guild.id}'")

    result = mycursor.fetchall()

  async def get_command(self,ctx):
    return "ree","https://www.youtube.com/watch?v=e3L6IUm6bQs"

  # commandss = ["this","ree"]
  # for com in commandss:
  #   @commands.command(name=f"{com}")
  #   async def f"_{com}"(self,ctx):
  #     print("this actually worked?")


  # @commands.Cog.listener()
  # # @commands.before_invoke(get_command)
  # async def on_message(self,ctx):
  #   if ctx.author.bot:
  #     return
  #   if str(ctx.channel.type) == "private":
  #     return
  #   command,link = await self.get_command(ctx)
  #   if ctx.content.startswith("!") and command in ctx.content:
  #     await ctx.reply(f"command: {command}")

def setup(bot):
  bot.add_cog(CustomMusic(bot))