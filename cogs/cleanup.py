import asyncio

# import discord
from discord.ext import commands

from functions import embed, query


async def get_delete_time(ctx: commands.Context = None, guild_id: int = None):
  if isinstance(ctx, commands.Context) and guild_id is None:
    guild_id = ctx.guild.id if ctx.guild is not None else None
  if ctx is None and guild_id is None:
    return None
  try:
    result = await query(ctx.bot.mydb, "SELECT autoDeleteMSGs FROM servers WHERE id=%s", guild_id)
    if result is None or result == 0:
      return None
    return result
  except BaseException:
    return


class CleanUp(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
  #   # self.exlusions = ["meme","issue","reactionrole"]

  @commands.command(name="clear", description="Deletes the bots commands ignoring anything that is not a command", hidden=True)
  @commands.is_owner()
  @commands.has_permissions(manage_channels=True)
  @commands.bot_has_permissions(manage_channels=True)
  async def clear(self, ctx):
    def _check(m):
      try:
        coms = []
        if m.author == self.bot.user and m.reference.resolved is not None and m.reference.resolved.content.startswith(ctx.prefix):
          coms.append(m.reference.resolved.id)
          return m.author == self.bot.user or m.id in coms
        return False
      except AttributeError:
        return False

    # def _command_check(m):
    #   return m.id in commands
      # return (
      #   r.emoji in SEARCHOPTIONS.keys()
      #   and u == ctx.author
      #   and r.message.id == msg.id
      # )

    deleted = await ctx.channel.purge(check=_check)
    # deleted = deleted + await ctx.channel.purge(check=_command_check)
    await asyncio.gather(
        ctx.message.delete(),
        ctx.reply(embed=embed(title=f"Deleted `{len(deleted)}` message(s)"), delete_after=10.0)
    )

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
