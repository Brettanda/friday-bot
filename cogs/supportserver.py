from discord.ext import commands
from discord_slash import cog_ext

from functions import config  # ,embed
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot

# import discord

class SupportServer(commands.Cog, name="Support Server"):
  """Every thing related to the [Friday development server](https://discord.gg/XP4avQ449V)"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.server_id = config.support_server_id

  @commands.command(name="support", description="Get an invite link to my support server")
  async def norm_support(self, ctx):
    await ctx.reply("https://discord.gg/NTRuFjU")

  @cog_ext.cog_slash(name="support", description="Support server link")
  async def slash_support(self, ctx):
    await ctx.send("https://discord.gg/NTRuFjU", hidden=True)

  @commands.command(name="donate", description="Get the Patreon link for Friday")
  async def norm_donate(self, ctx):
    await ctx.reply("https://www.patreon.com/fridaybot")

  @cog_ext.cog_slash(name="donate", description="Get the Patreon link for Friday")
  async def slash_donate(self, ctx):
    await ctx.send("https://www.patreon.com/fridaybot", hidden=True)

  @commands.Cog.listener()
  async def on_raw_reaction_add(self, payload):
    member = payload.member

    if not self.bot.prod or not payload.guild_id:
      return

    if member is None:
      member = await self.bot.get_guild(payload.guild_id).fetch_member(payload.user_id)

    if member.bot:
      return

    if payload.guild_id != 707441352367013899 or payload.channel_id != 707458929696702525 or payload.message_id != 707520808448294983:
      return

    if str(payload.emoji) != "📌":
      return

    role = member.guild.get_role(848626624365592636)
    if role is None:
      return

    await member.add_roles(role, reason="Updates!")

  @commands.Cog.listener()
  async def on_raw_reaction_remove(self, payload):
    member = payload.member

    if not self.bot.prod or not payload.guild_id:
      return

    if member is None:
      member = await self.bot.get_guild(payload.guild_id).fetch_member(payload.user_id)

    if member.bot:
      return

    if payload.guild_id != 707441352367013899 or payload.channel_id != 707458929696702525 or payload.message_id != 707520808448294983:
      return

    if str(payload.emoji) != "📌":
      return

    role = member.guild.get_role(848626624365592636)
    if role is None:
      return

    await member.remove_roles(role, reason="No more updates :(")

  @commands.Cog.listener()
  async def on_message(self, ctx):
    # Reacts to any message in the updates channel in the development server
    if ctx.channel.id == 744652167142441020:
      await ctx.add_reaction("♥")

  @commands.Cog.listener()
  async def on_member_join(self, member):
    if member.guild.id != 707441352367013899:
      return

    if 215346091321720832 not in [guild.id for guild in member.mutual_guilds]:
      return

    role = member.guild.get_role(763916955388084246)

    await member.add_roles(role, reason="Friend from NaCl")


def setup(bot):
  bot.add_cog(SupportServer(bot))
