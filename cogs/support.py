from discord.ext import commands
from discord_slash import cog_ext

from functions import config  # ,embed
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot

import discord


class Support(commands.Cog, name="Support"):
  """Every thing related to the Friday development server"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.server_id = config.support_server_id

    if not hasattr(self.bot, "invite_tracking"):
      self.bot.invite_tracking = {}

  @commands.command(name="support", help="Get an invite link to my support server")
  async def norm_support(self, ctx):
    await ctx.reply("https://discord.gg/NTRuFjU")

  @cog_ext.cog_slash(name="support", description="Support server link")
  async def slash_support(self, ctx):
    await ctx.send("https://discord.gg/NTRuFjU", hidden=True)

  @commands.command(name="donate", help="Get the Patreon link for Friday")
  async def norm_donate(self, ctx):
    await ctx.reply("https://www.patreon.com/bePatron?u=42649008")

  @cog_ext.cog_slash(name="donate", description="Get the Patreon link for Friday")
  async def slash_donate(self, ctx):
    await ctx.send("https://www.patreon.com/bePatron?u=42649008", hidden=True)

  @commands.Cog.listener()
  async def on_message(self, msg):
    # Reacts to any message in the updates channel in the development server
    if msg.channel.id == 744652167142441020:
      await msg.add_reaction("♥")

    if not msg.guild or msg.author.bot or msg.guild.id != 707441352367013899:
      return
    # print(discord.utils.resolve_invite(msg.clean_content))

  @commands.Cog.listener()
  async def on_ready(self):
    guild: discord.Guild = self.bot.get_guild(config.support_server_id)
    if self.bot.intents.members and not guild.chunked:
      await guild.chunk(cache=True)

  @commands.Cog.listener("on_ready")
  @commands.Cog.listener("on_invite_create")
  @commands.Cog.listener("on_invite_delete")
  async def set_invite_tracking(self, invite: discord.Invite = None):
    if self.bot.cluster_idx != 0:
      return

    try:
      if invite is not None:
        if hasattr(invite, "guild") and hasattr(invite.guild, "id") and invite.guild.id != self.server_id:
          return

      if self.bot.get_guild(self.server_id) is not None:
        for invite in await self.bot.get_guild(self.server_id).invites():
          if invite.max_age == 0 and invite.max_uses == 0 and invite.inviter.id == self.bot.owner_id:
            self.bot.invite_tracking.update({invite.code: invite.uses})
    except discord.Forbidden:
      pass

  @commands.Cog.listener()
  async def on_member_join(self, member: discord.Member):
    # await self.bot.request_offline_members()
    if self.bot.cluster_idx != 0:
      return

    if member.guild.id != self.server_id or member.bot:
      return

    if self.bot.get_guild(self.server_id) is None:
      return

    invite_used, x, invites = None, 0, await self.bot.get_guild(self.server_id).invites()
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


def setup(bot):
  bot.add_cog(Support(bot))
