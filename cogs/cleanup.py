from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Optional

from discord.ext import commands

if TYPE_CHECKING:
  from functions.custom_contexts import GuildContext, MyContext
  from index import Friday


async def get_delete_time(ctx: MyContext, guild_id: int = None) -> Optional[int]:
  if guild_id is None:
    guild_id = ctx.guild.id if ctx.guild is not None else None
  if ctx is None and guild_id is None:
    return None
  try:
    result = await ctx.db.fetchval("SELECT autoDeleteMSGs FROM servers WHERE id=%s", guild_id)
    if result is None or result == 0:
      return None
    return result
  except BaseException:
    return


class CleanUp(commands.Cog):
  def __init__(self, bot: Friday):
    self.bot: Friday = bot
  #   # self.exlusions = ["meme","issue","reactionrole"]

  async def _basic_cleanup_strategy(self, ctx: GuildContext, search):
    count = 0
    async for msg in ctx.history(limit=search, before=ctx.message):
      if msg.author == ctx.me and not (msg.mentions or msg.role_mentions):
        await msg.delete()
        count += 1
    return {'Bot': count}

  async def _complex_cleanup_strategy(self, ctx: GuildContext, search):
    prefixes = tuple(self.bot.prefixes[ctx.guild.id])  # thanks startswith

    def check(m):
      return m.author == ctx.me or m.content.startswith(prefixes)

    deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
    return Counter(m.author.display_name for m in deleted)

  async def _regular_user_cleanup_strategy(self, ctx: GuildContext, search):
    prefixes = tuple(self.bot.prefixes[ctx.guild.id])

    def check(m):
      return (m.author == ctx.me or m.content.startswith(prefixes)) and not (m.mentions or m.role_mentions)

    deleted = await ctx.channel.purge(limit=search, check=check, before=ctx.message)
    return Counter(m.author.display_name for m in deleted)

  @commands.command("cleanup", help="Deletes the bots commands ignoring anything that is not a command", hidden=True)
  @commands.guild_only()
  @commands.has_permissions(manage_messages=True)
  @commands.bot_has_permissions(manage_messages=True)
  @commands.is_owner()
  async def cleanup(self, ctx: GuildContext, search: int = 100):
    """Cleans up the bot's messages from the channel.
      If a search number is specified, it searches that many messages to delete.
      If the bot has Manage Messages permissions then it will try to delete
      messages that look like they invoked the bot as well.
      After the cleanup is completed, the bot will send you a message with
      which people got their messages deleted and their count. This is useful
      to see which users are spammers.
      Members with Manage Messages can search up to 1000 messages.
      Members without can search up to 25 messages.
    """

    strategy = self._basic_cleanup_strategy
    is_mod = ctx.channel.permissions_for(ctx.author).manage_messages
    if ctx.channel.permissions_for(ctx.me).manage_messages:
      if is_mod:
        strategy = self._complex_cleanup_strategy
      else:
        strategy = self._regular_user_cleanup_strategy

    if is_mod:
      search = min(max(2, search), 1000)
    else:
      search = min(max(2, search), 25)

    async with ctx.typing():
      spammers = await strategy(ctx, search)
    deleted = sum(spammers.values())
    messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
    if deleted:
      messages.append('')
      spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
      messages.extend(f'- **{author}**: {count}' for author, count in spammers)

    await ctx.send('\n'.join(messages), delete_after=10)
    # user_messages_confirm = await ctx.prompt("Would you like messages that looks like they invoked my commands to be deleted?")
    # chat_messages_confirm = await ctx.prompt("Would you like messages from my chatbot system to be deleted?")

    # user_messages_to_remove = []

    # def bot_predicate(m: discord.Message):
    #   norm = (m.author == m.guild.me and (not chat_messages_confirm and len(m.embeds) > 0))
    #   chat = (chat_messages_confirm and m.reference and hasattr(m.reference.resolved, "author") and m.reference.resolved.author)
    #   return norm or chat

    # def user_predicate(m: discord.Message):
    #   if m.author == m.guild.me and m.reference and m.reference.resolved:
    #     user_messages_to_remove.append(m.id)
    #   user = (user_messages_confirm and m.content.startswith(ctx.prefix))
    #   user_chat = (chat_messages_confirm and m.guild.me in m.mentions and len(m.content) < 200)
    #   return m.id in user_messages_to_remove or user or user_chat

    # async with ctx.typing():
    #   await ctx.channel.purge(limit=search, check=bot_predicate, oldest_first=False, bulk=False)
    #   await ctx.channel.purge(limit=search, check=user_predicate, oldest_first=False, bulk=True)
    # await ctx.send("Done", delete_after=5)
    # @commands.command(name="clear", help="Deletes the bots commands ignoring anything that is not a command", hidden=True)
    # @commands.is_owner()
    # @commands.has_permissions(manage_channels=True)
    # @commands.bot_has_permissions(manage_channels=True)
    # async def clear(self, ctx):
    #   def _check(m):
    #     try:
    #       coms = []
    #       if m.author == self.bot.user and m.reference.resolved is not None and m.reference.resolved.content.startswith(ctx.prefix):
    #         coms.append(m.reference.resolved.id)
    #         return m.author == self.bot.user or m.id in coms
    #       return False
    #     except AttributeError:
    #       return False

    #   # def _command_check(m):
    #   #   return m.id in commands
    #     # return (
    #     #   r.emoji in SEARCHOPTIONS.keys()
    #     #   and u == ctx.author
    #     #   and r.message.id == msg.id
    #     # )

    #   deleted = await ctx.channel.purge(check=_check)
    #   # deleted = deleted + await ctx.channel.purge(check=_command_check)
    #   await asyncio.gather(
    #       ctx.message.delete(),
    #       ctx.reply(embed=embed(title=f"Deleted `{len(deleted)}` message(s)"), delete_after=10.0)
    #   )

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


async def setup(bot):
  ...
  # await bot.add_cog(CleanUp(bot))
