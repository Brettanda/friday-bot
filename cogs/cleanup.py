import discord 
from discord.ext import commands

# from functions import 

async def get_delete_time():
  return 30

class CleanUp(commands.Cog):
  def __init__(self,bot):
    self.bot = bot
    self.exlusions = ["meme","issue"]

  # @commands.Cog.listener()
  # async def on_command(self,ctx):
  #   if ctx.command.name in self.exlusions:
  #     return
  #   delete = 10 #seconds
  #   if delete > 0:
  #     await ctx.message.delete(delay=delete)


  @commands.Cog.listener()
  async def on_command_error(self,ctx,error):
    msg = None
    async for message in ctx.channel.history(limit=10):
      if message.author == self.bot.user and hasattr(message.reference, "resolved") and message.reference.resolved == ctx.message:
        msg = message

    if msg is not None:
      delete = await get_delete_time()
      if delete > 0:
        await ctx.message.delete(delay=delete)
        await msg.delete(delay=delete)

  @commands.Cog.listener()
  async def on_command_completion(self,ctx):
    if ctx.command.name in self.exlusions:
      return
    msg = None
    async for message in ctx.channel.history(limit=10):
      if message.author == self.bot.user and hasattr(message.reference, "resolved") and message.reference.resolved == ctx.message:
        msg = message
    if msg is not None:
      delete = await get_delete_time()
      if delete > 0:
        await ctx.message.delete(delay=delete)
        await msg.delete(delay=delete)

def setup(bot):
  bot.add_cog(CleanUp(bot))