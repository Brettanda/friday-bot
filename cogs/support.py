from discord.ext import commands
# from discord_slash import cog_ext

from functions import config  # ,embed
from typing import Optional
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot

import discord

SUPPORT_SERVER_ID = 707441352367013899
SUPPORT_SERVER_INVITE = "https://discord.gg/NTRuFjU"
PATREON_LINK = "https://www.patreon.com/bePatron?u=42649008"


class SupportIntroRoles(discord.ui.View):
  """This should only be used in the support guild"""

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(emoji="📌", label="Get Updates", style=discord.ButtonStyle.blurple, custom_id="support_updates")
  async def support_updates(self, interaction: discord.Interaction, button: discord.ui.Button):
    if interaction.guild_id != 707441352367013899 or interaction.channel_id != 707458929696702525 or interaction.message.id != 707520808448294983:
      return

    await interaction.response.defer(ephemeral=True)

    if interaction.user.pending:
      return await interaction.followup.send(ephemeral=True, content="You must complete the membership screening before you can receive this role")

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


class Support(commands.Cog, name="Support"):
  """Every thing related to the Friday development server"""

  def __init__(self, bot: "Bot"):
    self.bot = bot

    if not hasattr(self.bot, "invite_tracking"):
      self.bot.invite_tracking = {}

  @commands.command(name="support", help="Get an invite link to my support server")
  async def norm_support(self, ctx):
    await ctx.reply(SUPPORT_SERVER_INVITE)

  @commands.command(name="donate", help="Get the Patreon link for Friday")
  async def norm_donate(self, ctx):
    await ctx.reply(PATREON_LINK)

  @commands.Cog.listener()
  async def on_message(self, msg):
    if not msg.guild or msg.author.bot or msg.guild.id != 707441352367013899:
      return
    # print(discord.utils.resolve_invite(msg.clean_content))

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

    if not after_has:
      await self.bot.db.query("UPDATE servers SET patreon_user=NULL,tier=NULL WHERE patreon_user=$1", str(after.id))
      self.bot.logger.info(f"Lost patreonage for guild {after.guild.id} with user {after.id} :(")
    # else:
    #   welcome new patron

  @commands.Cog.listener()
  async def on_ready(self):
    guild: Optional[discord.Guild] = self.bot.get_guild(SUPPORT_SERVER_ID)
    if self.bot.intents.members and guild and not guild.chunked:
      await guild.chunk(cache=True)

    if not self.bot.views_loaded:
      self.bot.add_view(SupportIntroRoles())

  @commands.Cog.listener("on_ready")
  @commands.Cog.listener("on_invite_create")
  @commands.Cog.listener("on_invite_delete")
  async def set_invite_tracking(self, invite: discord.Invite = None):
    if self.bot.cluster_idx != 0:
      return

    try:
      if invite is not None:
        if hasattr(invite, "guild") and hasattr(invite.guild, "id") and invite.guild.id != SUPPORT_SERVER_ID:
          return

      if self.bot.get_guild(SUPPORT_SERVER_ID) is not None:
        for invite in await self.bot.get_guild(SUPPORT_SERVER_ID).invites():
          if invite.max_age == 0 and invite.max_uses == 0 and invite.inviter.id == self.bot.owner_id:
            self.bot.invite_tracking.update({invite.code: invite.uses})
    except discord.Forbidden:
      pass

  @commands.Cog.listener()
  async def on_member_join(self, member: discord.Member):
    # await self.bot.request_offline_members()
    if self.bot.cluster_idx != 0:
      return

    if member.guild.id != SUPPORT_SERVER_ID or member.bot:
      return

    if self.bot.get_guild(SUPPORT_SERVER_ID) is None:
      return

    invite_used, x, invites = None, 0, await self.bot.get_guild(SUPPORT_SERVER_ID).invites()
    for invite in invites:
      if invite.max_age == 0 and invite.max_uses == 0 and invite.inviter.id == self.bot.owner_id:
        if int(invite.uses) > int(self.bot.invite_tracking[invite.code]):
          invite_used = invite
          self.bot.invite_tracking[invite.code] = invite.uses
        x += 1

    if invite_used is not None:
      if config.support_server_invites.get(invite_used.code, None) is not None:
        with open("invite_tracking.csv", "w") as f:
          f.write("reference,key,count\n")
          x = 0
          for reference in config.support_server_invites:
            inv = [invite for invite in invites if invite.code == reference][0]
            count, inv = inv.uses, inv.code
            f.write(f"{config.support_server_invites.get(reference, None)},{inv},{count}\n")
            x += 1
          f.close()
        print(config.support_server_invites[invite_used.code])
      else:
        print(invite_used.code)

    if 215346091321720832 not in [guild.id for guild in member.mutual_guilds]:
      return

    role = member.guild.get_role(763916955388084246)

    await member.add_roles(role, reason="Friend from NaCl")


async def setup(bot):
  await bot.add_cog(Support(bot))
