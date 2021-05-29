from discord.ext import commands
from discord_slash import cog_ext

from functions import config  # ,embed

# import discord


class SupportServer(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.server_id = config.support_server_id

  @commands.command(name="support", description="Get an invite link to my support server")
  async def norm_support(self, ctx):
    await ctx.reply("https://discord.gg/NTRuFjU")

  @cog_ext.cog_slash(name="support", description="Support server link")
  async def slash_support(self, ctx):
    await ctx.send("https://discord.gg/NTRuFjU", hidden=True)

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
