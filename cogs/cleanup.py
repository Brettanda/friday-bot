import asyncio

# import discord
from discord.ext import commands

from functions import embed, mydb_connect, query

async def get_delete_time(ctx:commands.Context=None,guild_id:int=None):
  if isinstance(ctx,commands.Context) and guild_id is None:
    guild_id = ctx.guild.id
  if ctx is None and guild_id is None:
    return None
  try:
    mydb = mydb_connect()
    result = query(mydb,"SELECT autoDeleteMSGs FROM servers WHERE id=%s",guild_id)
    if result is None or result == 0:
      return None
    return result
  except:
    return

class CleanUp(commands.Cog):
  def __init__(self,bot):
    self.bot = bot
    # self.exlusions = ["meme","issue","reactionrole"]


  # @commands.Cog.listener()
  # async def on_command(self,ctx):
  #   if ctx.command.name in self.exlusions:
  #     return
  #   delete = 10 #seconds
  #   if delete > 0:
  #     await ctx.message.delete(delay=delete)


  # @commands.Cog.listener()
  # async def on_command_error(self,ctx,error):
  #   msg = None
  #   async for message in ctx.channel.history(limit=10):
  #     if message.author == self.bot.user and hasattr(message.reference, "resolved") and message.reference.resolved == ctx.message:
  #       msg = message

  #   if msg is not None:
  #     delete = await get_delete_time(ctx)
  #     if delete is not None and delete > 0:
  #       try:
  #         await asyncio.gather(
  #           ctx.message.delete(delay=delete),
  #           msg.delete(delay=delete)
  #         )
  #       except:
  #         pass

  # @commands.Cog.listener()
  # async def on_command_completion(self,ctx):
  #   if ctx.command.name in self.exlusions:
  #     return
  #   msg = None
  #   async for message in ctx.channel.history(limit=10):
  #     if message.author == self.bot.user and hasattr(message.reference, "resolved") and message.reference.resolved == ctx.message:
  #       msg = message
  #   if msg is not None:
  #     delete = await get_delete_time(ctx)
  #     if delete is not None and delete > 0:
  #       try:
  #         await asyncio.gather(
  #           ctx.message.delete(delay=delete),
  #           msg.delete(delay=delete)
  #         )
  #       except:
  #         pass

def setup(bot):
  bot.add_cog(CleanUp(bot))
