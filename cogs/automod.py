import nextcord as discord
from nextcord.ext import commands

import re

from functions import embed, MyContext

import typing

if typing.TYPE_CHECKING:
  from index import Friday as Bot

INVITE_REG = r"(http(s|)?:\/\/)?(www\.)?(discord(app|)\.(gg|com|net)(\/invite|))\/[a-zA-Z0-9\-]+"


class AutoMod(commands.Cog):
  """There are somethings in this world that bots are better at then humans. Let Friday help out with the moderation of your Discord server."""

  def __init__(self, bot: "Bot"):
    self.bot = bot

  def __repr__(self):
    return "<cogs.AutoMod>"

  @commands.Cog.listener()
  async def on_message_edit(self, before, after):
    # if not self.bot.ready:
    #   return
    if before.guild is None:
      return

    if not isinstance(before.author, discord.Member):
      return

    if before.author.bot and not before.author.id == 892865928520413245:
      return

    bypass = before.author.guild_permissions.manage_guild
    if bypass:
      return
    await self.msg_remove_invites(after)

  @commands.Cog.listener()
  async def on_message(self, msg: discord.Message):
    # if not self.bot.ready:
    #   return
    if not msg.guild or (msg.author.bot and not msg.author.id == 892865928520413245):
      return

    if not isinstance(msg.author, discord.Member):
      return

    bypass = msg.author.guild_permissions.manage_guild if isinstance(msg.author, discord.Member) else False
    if bypass and not msg.author.id == 892865928520413245:
      return
    await self.msg_remove_invites(msg)

  async def msg_remove_invites(self, msg: discord.Message):
    if not msg.guild or (msg.author.bot and not msg.author.id == 892865928520413245):
      return

    to_remove_invites = await self.bot.db.query(f"SELECT remove_invites FROM servers WHERE id={str(msg.guild.id)}::text LIMIT 1")
    try:
      if bool(to_remove_invites) is True:
        reg = re.match(INVITE_REG, msg.clean_content, re.RegexFlag.MULTILINE + re.RegexFlag.IGNORECASE)
        check = bool(reg)
        if check:
          try:
            if discord.utils.resolve_invite(reg.string) in [inv.code for inv in await msg.guild.invites()]:
              return
          except discord.Forbidden or discord.HTTPException:
            pass
          try:
            await msg.delete()
          except discord.Forbidden:
            pass
    except KeyError:
      pass

  @commands.command(name="removeinvites", help="Automaticaly remove Discord invites from text channels")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def norm_remove_discord_invites(self, ctx: "MyContext", *, enable: typing.Union[bool, None] = None):
    if enable is None:
      check = await self.bot.db.query("SELECT remove_invites FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
      check = not bool(check)
    else:
      check = bool(enable)
    await self.bot.db.query("UPDATE servers SET remove_invites=$1 WHERE id=$2", check, str(ctx.guild.id))
    if bool(check) is False:
      await ctx.reply(embed=embed(title="I will no longer remove invites"))
    else:
      await ctx.reply(embed=embed(title="I will begin to remove invites"))


def setup(bot):
  bot.add_cog(AutoMod(bot))
