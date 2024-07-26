from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional, Sequence

import discord
from discord.ext import commands

from functions import cache

# from functions import embed

if TYPE_CHECKING:
  from functions.custom_contexts import MyContext, GuildContext
  from index import Friday

log = logging.getLogger(__name__)

SUPPORT_SERVER_ID = 707441352367013899
SUPPORT_SERVER_INVITE = "https://discord.gg/NTRuFjU"
SUPPORT_HELP_FORUM = 1019654818962358272
SUPPORT_HELP_FORUM_SOLVED_TAG = 1019679906357055558
PATREON_LINK = "https://www.patreon.com/bePatron?u=42649008"


def is_help_thread():
  def predicate(ctx: GuildContext) -> bool:
    return isinstance(ctx.channel, discord.Thread) and ctx.channel.parent_id == SUPPORT_HELP_FORUM

  return commands.check(predicate)


def can_close_threads(ctx: GuildContext) -> bool:
  if not isinstance(ctx.channel, discord.Thread):
    return False

  permissions = ctx.channel.permissions_for(ctx.author)
  return ctx.channel.parent_id == SUPPORT_HELP_FORUM and (
      permissions.manage_threads or ctx.channel.owner_id == ctx.author.id
  )


class Support(commands.Cog):
  """Every thing related to the Friday development server"""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot

  @cache.cache()
  async def is_server_boosted(self, user_id: int) -> bool:
    guild = self.bot.get_guild(SUPPORT_SERVER_ID)
    if guild is None:
      return False

    member = await self.bot.get_or_fetch_member(guild, user_id)
    if member is None:
      return False

    return member.premium_since is not None

  async def clear_is_server_boosted(self, before: discord.Member, after: discord.Member):
    if after.guild.id != SUPPORT_SERVER_ID:
      return

    if before.premium_since == after.premium_since:
      return

    self.is_server_boosted.invalidate(self, after.id)

  @commands.hybrid_command(name="support")
  async def _support(self, ctx: MyContext):
    """Get an invite link to my support server"""
    await ctx.reply(SUPPORT_SERVER_INVITE)

  @commands.hybrid_command(name="donate")
  async def _donate(self, ctx: MyContext):
    """Get the Patreon link for Friday"""
    await ctx.reply(PATREON_LINK)

  @commands.Cog.listener()
  async def on_member_update(self, before: discord.Member, after: discord.Member):
    if after.guild.id != SUPPORT_SERVER_ID:
      return

    await self.clear_is_server_boosted(before, after)

    if before.roles == after.roles:
      return

    before_has = before._roles.has(843941723041300480)  # Supporting role
    after_has = after._roles.has(843941723041300480)  # Supporting role

    if before_has == after_has:
      return

    if not after_has and self.bot.patreon:
      self.bot.patreon.get_patrons.invalidate(self.bot.patreon)
      log.info(f"Lost patreonage for guild {after.guild.id} with user {after.id} :(")
    # else:
    #   welcome new patron

  @commands.Cog.listener()
  async def on_ready(self):
    guild: Optional[discord.Guild] = self.bot.get_guild(SUPPORT_SERVER_ID)
    if self.bot.intents.members and guild and not guild.chunked:
      await guild.chunk(cache=True)

  @commands.Cog.listener()
  async def on_member_join(self, member: discord.Member):
    # await self.bot.request_offline_members()
    if self.bot.cluster_idx != 0:
      return

    if member.guild.id != SUPPORT_SERVER_ID or member.bot:
      return

    if self.bot.get_guild(SUPPORT_SERVER_ID) is None:
      return

  async def mark_as_solved(self, thread: discord.Thread, user: discord.abc.User) -> None:
    tags: Sequence[discord.abc.Snowflake] = thread.applied_tags

    if not any(tag.id == SUPPORT_HELP_FORUM_SOLVED_TAG for tag in tags):
      tags.append(discord.Object(id=SUPPORT_HELP_FORUM_SOLVED_TAG))  # type: ignore

    await thread.edit(
        locked=True,
        archived=True,
        applied_tags=tags[:5],
        reason=f'Marked as solved by {user} (ID: {user.id})',
    )

  @commands.hybrid_command(name='solved', aliases=['is_solved'])
  @commands.cooldown(1, 20, commands.BucketType.channel)
  @commands.guild_only()
  @discord.app_commands.guilds(707441352367013899)
  @is_help_thread()
  async def solved(self, ctx: GuildContext):
    """Marks a thread as solved."""

    assert isinstance(ctx.channel, discord.Thread)

    if can_close_threads(ctx) and ctx.invoked_with == 'solved':
      await ctx.message.add_reaction('\u2705')
      await self.mark_as_solved(ctx.channel, ctx.author)
    else:
      msg = f"<@!{ctx.channel.owner_id}>, would you like to mark this thread as solved? This has been requested by {ctx.author.mention}."
      confirm = await ctx.prompt(msg, author_id=ctx.channel.owner_id, timeout=300.0)

      if ctx.channel.locked:
        return

      if confirm:
        await ctx.send(
            'Marking as solved. Note that next time, you can mark the thread as solved yourself with `!solved`.'
        )
        await self.mark_as_solved(ctx.channel, ctx.channel.owner or ctx.author)
      elif confirm is None:
        await ctx.send('Timed out waiting for a response. Not marking as solved.')
      else:
        await ctx.send('Not marking as solved.')

  @solved.error
  async def on_solved_error(self, ctx: GuildContext, error: Exception):
    if isinstance(error, commands.CommandOnCooldown):
      await ctx.send(f'This command is on cooldown. Try again in {error.retry_after:.2f}s')


async def setup(bot):
  await bot.add_cog(Support(bot))
