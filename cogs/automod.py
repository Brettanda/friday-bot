import nextcord as discord
from nextcord.ext import commands

import re
import json
from slugify import slugify

from functions import embed, MyContext, MessageColors, relay_info

from typing import Optional, Union, List
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot

INVITE_REG = r"(http(s|)?:\/\/)?(www\.)?(discord(app|)\.(gg|com|net)(\/invite|))\/[a-zA-Z0-9\-]+"


class CooldownByContent(commands.CooldownMapping):
  def _bucket_key(self, msg):
    return (msg.channel.id, msg.content)


class SpamChecker:
  def __init__(self, bot: "Bot", cooldown: commands.CooldownMapping = None):
    self.bot = bot
    self.cooldown = cooldown

  def get_bucket(self, message: discord.Message) -> commands.Cooldown:
    return self.cooldown.get_bucket(message)

  def is_spamming(self, message: discord.Message) -> bool:
    if message.guild is None:
      return False

    current = message.created_at.timestamp()

    bucket = self.get_bucket(message)
    if bucket.update_rate_limit(current):
      return True

    return False

  async def mute(self, guild: discord.Guild, member: discord.Member, reason: str = "Auto-mute for spamming.") -> None:
    role_id = await self.bot.db.query("SELECT mute_role FROM servers WHERE id=$1 LIMIT 1", str(guild.id))
    if role_id is None:
      return
    role = guild.get_role(int(role_id, base=10))
    if role is None:
      return
    await member.add_roles(role, reason=reason)

  async def delete(self, msg: discord.Message) -> None:
    if msg.guild is None:
      return
    await msg.delete()

  async def kick(self, member: discord.Member, reason: str = "Auto-kick for spamming.") -> None:
    if member.guild is None:
      return
    await member.kick(reason=reason)

  async def ban(self, member: discord.Member, reason: str = "Auto-ban for spamming.") -> None:
    if member.guild is None:
      return
    await member.ban(reason=reason)

  async def apply_punishment(self, guild: discord.Guild, msg: discord.Message, punishments: List[str]) -> discord.Message:
    if "delete" in punishments:
      await self.delete(msg)
    if "ban" in punishments:
      await self.ban(msg.author)
    elif "kick" in punishments:
      await self.kick(msg.author)
    elif "mute" in punishments:
      await self.mute(guild, msg.author)
    return await msg.channel.send(embed=embed(title=f"Punishments applied: `{', '.join(punishments)}` to {msg.author}"))


class AutoMod(commands.Cog):
  """There are somethings in this world that bots are better at then humans. Let Friday help out with the moderation of your Discord server."""

  def __init__(self, bot: "Bot"):
    self.bot = bot

    self.message_spam_control = {}
    self.content_spam_control = {}

  def __repr__(self) -> str:
    return "<cogs.AutoMod>"

  async def cog_command_error(self, ctx: "MyContext", error: Exception):
    if isinstance(error, (commands.MissingRequiredArgument)):
      return
    print(f"Error in {ctx.command.qualified_name}: {type(error).__name__}: {error}")

  @commands.Cog.listener()
  async def on_message_edit(self, before, after):
    if not self.bot.ready:
      return
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
    if not self.bot.ready:
      return

    if msg.author.id in (self.bot.user.id, self.bot.owner_id, 892865928520413245):
      return

    if not msg.guild:
      return

    if not isinstance(msg.author, discord.Member):
      return

    max_mentions, max_messages, max_content = await self.bot.db.query("SELECT max_mentions,max_messages,max_content FROM servers WHERE id=$1 LIMIT 1", str(msg.guild.id))
    max_mentions, max_messages, max_content = json.loads(max_mentions) if max_mentions is not None else None, json.loads(max_messages) if max_messages is not None else None, json.loads(max_content) if max_content is not None else None
    mention_count = sum(not m.bot and m.id != msg.author.id for m in msg.mentions)
    if max_mentions is not None and len(max_mentions) == 2 and len(msg.mentions) >= 3:
      count, punishments = max_mentions["count"], max_mentions["punishments"]
      spam = SpamChecker(self.bot)
      if max_mentions is not None and mention_count >= count:
        await spam.apply_punishment(msg.guild, msg, punishments)

    if max_content is not None and max_content != {}:
      rate, delay, punishments = max_content["rate"], max_content["seconds"], max_content["punishments"]
      if self.content_spam_control.get(msg.guild.id, None) is None:
        self.content_spam_control.update({msg.guild.id: CooldownByContent.from_cooldown(rate, delay, commands.BucketType.member)})
      content_cooldown = self.content_spam_control[msg.guild.id]
      spam = SpamChecker(bot=self.bot, cooldown=content_cooldown)
      if spam.is_spamming(msg):
        spam.get_bucket(msg).reset()
        return await spam.apply_punishment(msg.guild, msg, punishments)

    if max_messages is not None and max_content != {}:
      rate, delay, punishments = max_messages["rate"], max_messages["seconds"], max_messages["punishments"]

      if self.message_spam_control.get(msg.guild.id, None) is None:
        self.message_spam_control.update({msg.guild.id: commands.CooldownMapping.from_cooldown(rate, delay, commands.BucketType.user)})

      author_cooldown = self.message_spam_control[msg.guild.id]
      spam = SpamChecker(bot=self.bot, cooldown=author_cooldown)
      if spam.is_spamming(msg):
        spam.get_bucket(msg).reset()
        return await spam.apply_punishment(msg.guild, msg, punishments)

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
        if bool(reg):
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

  @commands.command(name="removeinvites", extras={"examples": ["1", "0", "true", "false"]}, help="Automaticaly remove Discord invites (originating from external servers) from text channels. Not giving an argument will display the current setting.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True, manage_messages=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def norm_remove_discord_invites(self, ctx: "MyContext", *, enable: Union[bool, None] = None):
    if enable is None:
      current = await self.bot.db.query("SELECT remove_invites FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
      return await ctx.send(embed=embed(title="Current remove invites", description="I **will** remove invites from external servers" if current is True else "I **will not** remove invites from external servers" if current is False else f"{current}"))

    await self.bot.db.query("UPDATE servers SET remove_invites=$1 WHERE id=$2", enable, str(ctx.guild.id))
    if bool(enable) is False:
      await ctx.reply(embed=embed(title="I will no longer remove invites"))
    else:
      await ctx.reply(embed=embed(title="I will begin to remove invites"))


  @commands.group(name="mentionspam", extras={"examples": ["3", "5", "10"]}, aliases=["maxmentions", "maxpings"], help="Set the max amount of mentions one user can send per message before muting the author", invoke_without_command=True)
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True, manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_mentions(self, ctx: "MyContext", mentions_per_message: int):
    if mentions_per_message < 3:
      return await ctx.send(embed=embed(title="Count must be greater than 3", color=MessageColors.ERROR))
    current = await self.bot.db.query("SELECT max_mentions FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {"punishments": ["mute"]}
    else:
      current = json.loads(current)
    punishments = current["punishments"]
    await self.bot.db.query("UPDATE servers SET max_mentions=$1 WHERE id=$2", json.dumps({"count": mentions_per_message, "punishments": punishments}), str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"New max amount of mentions per message is `{mentions_per_message}`"))

  @max_mentions.command(name="punishment", aliases=["punishments"], extras={"examples": ["delete", "mute", "kick", "ban", "delete kick", "ban delete"]}, help="Set the punishment for the max amount of mentions one user can send per message. Combining kick,ban and/or mute will only apply one of them.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True, manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_mentions_punishment(self, ctx: "MyContext", *, punishments: Optional[str] = "mute"):
    punishments = [i for i in punishments.split(" ") if i.lower() in ["delete", "mute", "kick", "ban"]]
    if len(punishments) == 0:
      return await ctx.send(embed=embed(title="Punishment must be either delete, mute, kick, ban or some combination of those.", color=MessageColors.ERROR))
    current = await self.bot.db.query("SELECT max_mentions FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {}
    else:
      current = json.loads(current)
    current.update({"punishments": punishments})
    await self.bot.db.query("UPDATE servers SET max_mentions=$1 WHERE id=$2", json.dumps(current), str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"New punishment for max amount of mentions in a single message is `{', '.join(punishments)}`"))

  @max_mentions.command(name="disable", help="Disable the max amount of mentions per message for this server.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True, manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_mentions_disable(self, ctx: "MyContext"):
    await self.bot.db.query("UPDATE servers SET max_mentions=$1 WHERE id=$2", None, str(ctx.guild.id))
    await ctx.reply(embed=embed(title="Disabled max mentions"))

  @commands.group(name="messagespam", extras={"examples": ["3 10", "5 15"]}, aliases=["maxmessages", "ratelimit"], help="Sets a max message count for users per x seconds", invoke_without_command=True)
  @commands.guild_only()
  @commands.bot_has_guild_permissions(manage_channels=True, manage_messages=True)
  @commands.has_guild_permissions(manage_messages=True)
  async def max_spam(self, ctx: "MyContext", message_rate: int, seconds: int):
    if message_rate < 3 or seconds < 5:
      return await ctx.send(embed=embed(title="Some arguments are too small", description="`message_rate` must be greater than 3\n`seconds` must be greater than 5", color=MessageColors.ERROR))
    current = await self.bot.db.query("SELECT max_messages FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {"punishments": ["mute"]}
    else:
      current = json.loads(current)
    punishments = current.get("punishments", ["mute"])
    value = json.dumps({"rate": message_rate, "seconds": seconds, "punishments": punishments})
    await self.bot.db.query("UPDATE servers SET max_messages=$1::json WHERE id=$2", value, str(ctx.guild.id))
    if value is None:
      if self.message_spam_control.get(ctx.guild.id, None) is not None:
        del self.message_spam_control[ctx.guild.id]
      if self.message_spam_control_counter.get(ctx.guild.id, None) is not None:
        del self.message_spam_control_counter[ctx.guild.id]
      return await ctx.reply(embed=embed(title="I will no longer delete messages"))
    await ctx.reply(embed=embed(title=f"I will now delete messages matching the same author that are sent more than the rate of `{message_rate}` message, for every `{seconds}` seconds."))

  @max_spam.command(name="punishment", aliases=["punishments"], extras={"examples": ["delete", "mute", "kick", "ban", "delete kick", "ban delete"]}, help="Set the punishment for the max amount of message every x seconds. Combining kick,ban and/or mute will only apply one of them.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True, manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_spam_punishment(self, ctx: "MyContext", *, punishments: Optional[str] = "mute"):
    punishments = [i for i in punishments.split(" ") if i.lower() in ["delete", "mute", "kick", "ban"]]
    if len(punishments) == 0:
      return await ctx.send(embed=embed(title="Punishment must be either delete, mute, kick, ban or some combination of those.", color=MessageColors.ERROR))
    current = await self.bot.db.query("SELECT max_mentions FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {}
    else:
      current = json.loads(current)
    current.update({"punishments": punishments})
    await self.bot.db.query("UPDATE servers SET max_mentions=$1 WHERE id=$2", json.dumps(current), str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"New punishment(s) for spam is `{', '.join(punishments)}`"))

  @max_spam.command(name="disable", help="Disable the max amount of messages per x seconds by the same member for this server.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True, manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_spam_disable(self, ctx: "MyContext"):
    await self.bot.db.query("UPDATE servers SET max_messages=$1 WHERE id=$2", None, str(ctx.guild.id))
    if self.message_spam_control.get(ctx.guild.id, None) is not None:
      del self.message_spam_control[ctx.guild.id]
    await ctx.reply(embed=embed(title="Disabled max messages"))

  @commands.group(name="contentspam", extras={"examples": ["3 5", "5 15"]}, help="Sets the max number of message that can have the same content (ignoring who sent the message) until passing the given threshold and muting anyone spamming the same content further.", invoke_without_command=True)
  @commands.guild_only()
  @commands.bot_has_guild_permissions(manage_channels=True, manage_messages=True, manage_roles=True)
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_content_spam(self, ctx: "MyContext", message_rate: int, seconds: int):
    if message_rate < 3 or seconds < 5:
      return await ctx.send(embed=embed(title="Some arguments are too small", description="`message_rate` must be greater than 3\n`seconds` must be greater than 5", color=MessageColors.ERROR))
    current = await self.bot.db.query("SELECT max_content FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {"punishments": ["mute"]}
    else:
      current = json.loads(current)
    punishments = current["punishments"] if "punishments" in current else ["mute"]
    value = json.dumps({"rate": message_rate, "seconds": seconds, "punishments": punishments})
    await self.bot.db.query("UPDATE servers SET max_content=$1 WHERE id=$2", value, str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"I will now delete messages matching the same content that are sent more than the rate of `{message_rate}` message, for every `{seconds}` seconds."))

  @max_content_spam.command(name="punishment", aliases=["punishments"], extras={"examples": ["delete", "mute", "kick", "ban", "delete kick", "ban delete"]}, help="Set the punishment for the max amount of message every x seconds. Combining kick,ban and/or mute will only apply one of them.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True, manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_content_spam_punishment(self, ctx: "MyContext", *, punishments: Optional[str] = "mute"):
    punishments = [i for i in punishments.split(" ") if i.lower() in ["delete", "mute", "kick", "ban"]]
    if len(punishments) == 0:
      return await ctx.send(embed=embed(title="Punishment must be either delete, mute, kick, ban or some combination of those.", color=MessageColors.ERROR))
    current = await self.bot.db.query("SELECT max_content FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {}
    else:
      current = json.loads(current)
    current.update({"punishments": punishments})
    await self.bot.db.query("UPDATE servers SET max_content=$1 WHERE id=$2", json.dumps(current), str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"New punishment(s) for content spam is `{', '.join(punishments)}`"))

  @max_content_spam.command(name="disable", help="Disable the max amount of messages per x seconds with the same content for this server.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True, manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_content_spam_disable(self, ctx: "MyContext"):
    await self.bot.db.query("UPDATE servers SET max_content=$1 WHERE id=$2", None, str(ctx.guild.id))
    if self.content_spam_control.get(ctx.guild.id, None) is not None:
      del self.content_spam_control[ctx.guild.id]
    await ctx.reply(embed=embed(title="Disabled max content messages"))


def setup(bot):
  bot.add_cog(AutoMod(bot))
