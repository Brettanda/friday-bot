from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

# from functions import embed

if TYPE_CHECKING:
  from functions.custom_contexts import MyContext
  from index import Friday

log = logging.getLogger(__name__)

SUPPORT_SERVER_ID = 707441352367013899
SUPPORT_SERVER_INVITE = "https://discord.gg/NTRuFjU"
PATREON_LINK = "https://www.patreon.com/bePatron?u=42649008"


class SupportIntroRoles(discord.ui.View):
  """This should only be used in the support guild"""

  def __init__(self):
    super().__init__(timeout=None)

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if interaction.guild_id != 707441352367013899 or interaction.channel_id != 707458929696702525 or interaction.message and interaction.message.id != 707520808448294983:
      return False
    if isinstance(interaction.user, discord.User):
      return False
    if interaction.user.pending:
      await interaction.followup.send(ephemeral=True, content="You must complete the membership screening before you can receive this role")
      return False
    return True

  @discord.ui.button(emoji="📌", label="Get Updates", style=discord.ButtonStyle.blurple, custom_id="support_updates")
  async def support_updates(self, interaction: discord.Interaction, button: discord.ui.Button):
    await interaction.response.defer(ephemeral=True)

    assert interaction.guild is not None
    role = interaction.guild.get_role(848626624365592636)
    if role is None:
      return

    if not isinstance(interaction.user, discord.Member):
      return

    if role in interaction.user.roles:
      await interaction.user.remove_roles(role, reason="No more updates :(")
      await interaction.followup.send(ephemeral=True, content="You will no longer receive pings for updates")
    else:
      await interaction.user.add_roles(role, reason="Updates!")
      await interaction.followup.send(ephemeral=True, content="You will now be pinged when a new update comes out")


class Support(commands.Cog):
  """Every thing related to the Friday development server"""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot

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

    if not self.bot.views_loaded:
      self.bot.add_view(SupportIntroRoles())

  @commands.Cog.listener()
  async def on_member_join(self, member: discord.Member):
    # await self.bot.request_offline_members()
    if self.bot.cluster_idx != 0:
      return

    if member.guild.id != SUPPORT_SERVER_ID or member.bot:
      return

    if self.bot.get_guild(SUPPORT_SERVER_ID) is None:
      return


async def setup(bot):
  await bot.add_cog(Support(bot))
