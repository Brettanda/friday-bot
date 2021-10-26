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
    await self.check_blacklist(after)

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
    await self.check_blacklist(msg)

  def do_slugify(self, string):
    string = slugify(string).replace("-", "")
    for old, new in (("4", "a"), ("@", "a"), ("3", "e"), ("1", "i"), ("0", "o"), ("7", "t"), ("5", "s")):
      string = string.replace(old, new)

    return string.lower()

  async def check_blacklist(self, msg: discord.Message):
    bypass = msg.author.guild_permissions.manage_guild
    if bypass:
      return
    cleansed_msg = self.do_slugify(msg.clean_content)
    words = await self.bot.db.query("SELECT words FROM blacklist WHERE guild_id=$1::text LIMIT 1", str(msg.guild.id))
    if words is None or len(words) == 0:
      return
    try:
      for blacklisted_word in words:
        if blacklisted_word in cleansed_msg:
          try:
            await msg.delete()
            return await msg.author.send(f"""Your message `{msg.content}` was removed for containing the blacklisted word `{blacklisted_word}`""")
          except Exception as e:
            await relay_info(f"Error when trying to remove message {type(e).__name__}: {e}", self.bot, logger=self.bot.log.log_errors)
    except Exception as e:
      await relay_info(f"Error when trying to remove message (big) {type(e).__name__}: {e}", self.bot, logger=self.bot.log.log_errors)

  @commands.group(name="blacklist", aliases=["bl"], invoke_without_command=True, case_insensitive=True, help="Blacklist words from being sent in text channels")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def _blacklist(self, ctx: "MyContext"):
    return await self._blacklist_display_words(ctx)

  @_blacklist.command(name="add", aliases=["+"], extras={"examples": ["penis", "shit"]}, help="Add a word to the current servers blacklist settings.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def _blacklist_add_word(self, ctx, *, word: str):
    cleansed_word = self.do_slugify(word)
    if len(await self.bot.db.query("SELECT words FROM blacklist WHERE guild_id=$1::text AND $2::text = ANY(words)", str(ctx.guild.id), cleansed_word)) > 0:
      return await ctx.reply(embed=embed(title="Can't add duplicate word", color=MessageColors.ERROR))
    await self.bot.db.query("INSERT INTO blacklist (guild_id,words) VALUES ($1::text,array[$2]::text[]) ON CONFLICT(guild_id) DO UPDATE SET words = array_append(blacklist.words, $2)", str(ctx.guild.id), cleansed_word)
    word = word
    await ctx.reply(embed=embed(title=f"Added `{word}` to the blacklist"))

  @_blacklist.command(name="remove", aliases=["-"], extras={"examples": ["penis", "shit"]}, help="Remove a word from the current servers blacklist settings.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def _blacklist_remove_word(self, ctx, *, word: str):
    cleansed_word = word
    current_words = await self.bot.db.query("SELECT words FROM blacklist WHERE guild_id=$1 AND $2::text = ANY(words) LIMIT 1", str(ctx.guild.id), cleansed_word)
    if current_words is None or len(current_words) == 0:
      return await ctx.reply(embed=embed(title="You don't seem to be blacklisting that word"))
    await self.bot.db.query("UPDATE blacklist SET words = array_remove(words,$2::text) WHERE guild_id=$1", str(ctx.guild.id), cleansed_word)
    word = word
    await ctx.reply(embed=embed(title=f"Removed `{word}` from the blacklist"))

  @_blacklist.command(name="display", aliases=["list", "show"], help="Display the current servers blacklist settings.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def _blacklist_display_words(self, ctx):
    words = await self.bot.db.query("SELECT words FROM blacklist WHERE guild_id=$1 LIMIT 1", str(ctx.guild.id))
    if words == [] or words is None:
      return await ctx.reply(embed=embed(title=f"No blacklisted words yet, use `{ctx.prefix}blacklist add <word>` to get started"))
    await ctx.reply(embed=embed(title="Blocked words", description='\n'.join(x for x in words)))

  # @_blacklist.command(name="ignoreadmins", aliases=["exemptadmins"])
  # @commands.guild_only()
  # @commands.has_guild_permissions(administrator=True)
  # @commands.bot_has_guild_permissions(manage_messages=True)
  # async def _blacklist_ignoreadmins(self, ctx):
  #   await self.bot.db.query("INSERT INTO blacklist (guild_id,ignoreadmins) VALUES ($1,true) ON CONFLICT(guild_id) DO UPDATE SET ignoreadmins=NOT ignoreadmins", str(ctx.guild.id))
  #   await ctx.reply(embed=embed(title="Removed all blacklisted words"))

  @_blacklist.command(name="clear", help="Remove all words from the current servers blacklist settings.")
  @commands.guild_only()
  @commands.has_guild_permissions(administrator=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def _blacklist_clear(self, ctx):
    await self.bot.db.query("DELETE FROM blacklist WHERE guild_id=$1", str(ctx.guild.id))
    await ctx.reply(embed=embed(title="Removed all blacklisted words"))

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
