import json
import re
from typing import List, Optional, Union

import discord
from discord.ext import commands
from slugify import slugify
from typing_extensions import TYPE_CHECKING

from functions import MessageColors, MyContext, cache, embed, relay_info, time

from .moderation import can_execute_action

if TYPE_CHECKING:
  from index import Friday as Bot

INVITE_REG = re.compile(r"<?(https?:\/\/)?(www\.)?(discord(app|)\.(gg|com|net)(\/invite|))\/[a-zA-Z0-9\-]+>?", re.RegexFlag.MULTILINE + re.RegexFlag.IGNORECASE)

PUNISHMENT_TYPES = ["delete", "kick", "ban", "mute"]


class RoleOrChannel(commands.Converter):
  async def convert(self, ctx, argument):
    try:
      item = await commands.TextChannelConverter().convert(ctx, argument)
    except commands.BadArgument:
      try:
        item = await commands.RoleConverter().convert(ctx, argument)
      except commands.BadArgument:
        raise commands.BadArgument("Role or channel not found.")

    if isinstance(item, discord.Role) and not can_execute_action(ctx, ctx.author, item):
      raise commands.BadArgument("Your role hierarchy is too low for this action.")
    return item


class Config:
  __slots__ = ("bot", "id", "max_mentions", "max_messages", "max_content", "remove_invites", "automod_whitelist", "blacklisted_words", "blacklist_punishments", "mute_role_id", "muted_members")

  @classmethod
  async def from_record(cls, record, blacklist, bot):
    self = cls()

    self.bot: "Bot" = bot
    self.id: int = int(record["id"], base=10)
    self.max_mentions = json.loads(record["max_mentions"]) if record["max_mentions"] else None
    self.max_messages = json.loads(record["max_messages"]) if record["max_messages"] else None
    self.max_content = json.loads(record["max_content"]) if record["max_content"] else None
    self.remove_invites: bool = record["remove_invites"]
    self.automod_whitelist = set(record["automod_whitelist"] or [])
    self.blacklisted_words: List[str] = blacklist["words"] if blacklist else []
    self.blacklist_punishments: List[str] = blacklist["punishments"] if blacklist else []
    self.muted_members = set(record["muted_members"] or [])
    self.mute_role_id = int(record["mute_role"], base=10) if record["mute_role"] else None
    return self

  @property
  def mute_role(self):
    guild = self.bot.get_guild(self.id)
    return guild and self.mute_role_id and guild.get_role(self.mute_role_id)

  def is_muted(self, member: discord.Member) -> bool:
    return member.id in [int(i, base=10) for i in self.muted_members]

  def is_timedout(self, member: discord.Member) -> bool:
    return member.communication_disabled_until is not None

  def is_whitelisted(self, msg: discord.Message, *, channel: discord.TextChannel = None, member: discord.Member = None) -> bool:
    channel = channel or msg.channel
    roles = (member.roles if member is not None else None) or msg.author.roles

    if msg.author.guild_permissions and (msg.author.guild_permissions.administrator or msg.author.guild_permissions.manage_guild):
      return True

    if channel and str(channel.id) in self.automod_whitelist:
      return True

    if roles and any(str(role.id) in self.automod_whitelist for role in roles):
      return True

    return False

  async def mute(self, member: discord.Member, reason: str = "Auto-mute for spamming.") -> None:
    if self.mute_role_id:
      await member.add_roles(discord.Object(id=self.mute_role_id), reason=reason)

  async def timeout(self, member: discord.Member, *, duration: time.TimeoutTime = None, reason: str = "Auto-timeout for spamming.") -> None:
    if not duration:
      duration = time.TimeoutTime("20m")
    try:
      await member.edit(communication_disabled_until=duration.dt, reason=reason)
    except (discord.Forbidden, discord.HTTPException):
      pass

  async def delete(self, msg: discord.Message) -> None:
    try:
      await msg.delete()
    except discord.NotFound:
      pass

  async def kick(self, member: discord.Member, reason: str = "Auto-kick for spamming.") -> None:
    await member.kick(reason=reason)

  async def ban(self, member: discord.Member, reason: str = "Auto-ban for spamming.") -> None:
    await member.ban(reason=reason)

  async def apply_punishment(self, guild: discord.Guild, msg: discord.Message, punishments: List[str], *, reason: str = None) -> Optional[discord.Message]:
    if "delete" in punishments:
      await self.delete(msg)
    if "ban" in punishments:
      await self.ban(msg.author, reason=reason)
    elif "kick" in punishments:
      await self.kick(msg.author, reason=reason)
    elif "timeout" in punishments:
      await self.timeout(msg.author, reason=reason)
    elif "mute" in punishments:
      await self.mute(msg.author, reason=reason)


class CooldownByContent(commands.CooldownMapping):
  def _bucket_key(self, msg):
    return (msg.channel.id, msg.content)


class SpamChecker:
  @classmethod
  def from_cooldowns(cls, *, bot: "Bot", config: Config):  # message_spam: Optional[commands.CooldownMapping], mention_spam: Optional[commands.CooldownMapping], content_spam: Optional[CooldownByContent]):
    self = cls()

    self.bot = bot
    self._message_spam = commands.CooldownMapping.from_cooldown(config.max_messages["rate"], config.max_messages["seconds"], commands.BucketType.user) if config.max_messages else None
    self._mention_spam = commands.CooldownMapping.from_cooldown(config.max_mentions["rate"], config.max_mentions["seconds"], commands.BucketType.user) if config.max_mentions else None
    self._content_spam = CooldownByContent.from_cooldown(config.max_content["rate"], config.max_content["seconds"], commands.BucketType.member) if config.max_content else None

    return self

  @property
  def is_disabled(self) -> bool:
    return not self._message_spam and not self._mention_spam and not self._content_spam

  def is_spamming(self, message: discord.Message) -> bool:
    if message.guild is None:
      return False

    current = message.created_at.timestamp()

    bucket = self._message_spam and self._message_spam.get_bucket(message)
    if bucket.update_rate_limit(current):
      return True

    return False

  def is_content_spamming(self, message: discord.Message) -> bool:
    if message.guild is None:
      return False

    current = message.created_at.timestamp()

    bucket = self._content_spam and self._content_spam.get_bucket(message)
    if bucket.update_rate_limit(current):
      return True

    return False

  def is_mention_spamming(self, message: discord.Message) -> bool:
    if message.guild is None:
      return False

    current = message.created_at.timestamp()

    bucket = self._mention_spam and self._mention_spam.get_bucket(message)
    if bucket.update_rate_limit(current):
      return True

    return False


class AutoMod(commands.Cog):
  """There are somethings in this world that bots are better at then humans. Let Friday help out with the moderation of your Discord server."""

  def __init__(self, bot: "Bot"):
    self.bot = bot

    self._spam_check = dict()

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def cog_command_error(self, ctx: "MyContext", error: Exception):
    error = getattr(error, "original", error)
    if isinstance(error, (commands.MissingRequiredArgument)):
      return
    if isinstance(error, commands.BadArgument):
      return await ctx.send(embed=embed(title=str(error), color=MessageColors.ERROR))
    self.bot.logger.error(f"Error in {ctx.command.qualified_name}: {type(error).__name__}: {error}")

  async def cog_after_invoke(self, ctx: "MyContext"):
    if not ctx.guild:
      return

    self._spam_check.pop(ctx.guild.id, None)
    self.bot.dispatch("invalidate_mod", ctx.guild.id)

  @commands.Cog.listener()
  async def on_invalidate_mod(self, guild_id: int):
    self.get_guild_config.invalidate(self, guild_id)

  @cache.cache()
  async def get_guild_config(self, guild_id: int) -> Optional[Config]:
    query = "SELECT * FROM servers WHERE id=$1 LIMIT 1;"
    blquery = "SELECT * FROM blacklist WHERE guild_id=$1 LIMIT 1;"
    async with self.bot.db.pool.acquire(timeout=300.0) as conn:
      record = await conn.fetchrow(query, str(guild_id))
      self.bot.logger.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
      blrecord = await conn.fetchrow(blquery, str(guild_id))
      self.bot.logger.debug(f"PostgreSQL Query: \"{blquery}\" + {str(guild_id)}")
      if record is not None:
        return await Config.from_record(record, blrecord, self.bot)
      return None

  @commands.Cog.listener()
  async def on_message_edit(self, before, after):
    await self.bot.wait_until_ready()
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
    await self.bot.wait_until_ready()

    if not msg.guild:
      return

    if not isinstance(msg.author, discord.Member):
      return

    await self.msg_remove_invites(msg)

    if msg.author.id in (self.bot.user.id, self.bot.owner_id, 892865928520413245):
      return

    await self.check_blacklist(msg)

    config = await self.get_guild_config(msg.guild.id)
    if config is None:
      return

    if config.is_whitelisted(msg):
      return

    try:
      spam = self._spam_check[msg.guild.id]
    except KeyError:
      self._spam_check.update({msg.guild.id: SpamChecker.from_cooldowns(bot=self.bot, config=config)})
      spam = self._spam_check[msg.guild.id]
    if spam.is_disabled:
      return

    mention_count = sum(not m.bot and m.id != msg.author.id for m in msg.mentions)
    if config.max_mentions is not None and mention_count >= 1:
      if spam.is_mention_spamming(msg):
        return await config.apply_punishment(msg.guild, msg, config.max_mentions["punishments"], reason="Spamming mentions.")

    if config.max_content is not None and config.max_content != {}:
      if spam.is_content_spamming(msg):
        return await config.apply_punishment(msg.guild, msg, config.max_content["punishments"], reason="Spamming with content matching previous messages.")

    if config.max_messages is not None and config.max_content != {}:
      if spam.is_spamming(msg):
        return await config.apply_punishment(msg.guild, msg, config.max_messages["punishments"], reason="Spamming messages.")

  @commands.Cog.listener()
  async def on_member_join(self, member: discord.Member):
    guild_id = member.guild.id
    config = await self.get_guild_config(guild_id)
    if config is None:
      return

    if config.is_muted(member):
      return await config.mute(member, "Member was previously muted.")

  @commands.Cog.listener()
  async def on_member_update(self, before: discord.Member, after: discord.Member):
    if before.roles == after.roles:
      return

    guild_id = after.guild.id
    config = await self.get_guild_config(guild_id)
    if config is None:
      return

    if config.mute_role_id is None:
      return

    before_has = before._roles.has(config.mute_role_id)
    after_has = after._roles.has(config.mute_role_id)

    if before_has == after_has:
      return

    if after_has:
      await self.bot.db.query("UPDATE servers SET muted_members=array_append(muted_members, $1) WHERE id=$2 AND NOT ($1=any(muted_members))", str(after.id), str(guild_id))
    else:
      await self.bot.db.query("UPDATE servers SET muted_members=array_remove(muted_members, $1) WHERE id=$2", str(after.id), str(guild_id))
    self.bot.dispatch("invalidate_mod", before.guild.id)

  @commands.Cog.listener()
  async def on_guild_role_delete(self, role: discord.Role):
    guild_id = role.guild.id
    config = await self.get_guild_config(guild_id)
    if config is None or config.mute_role_id != role.id:
      return

    await self.bot.db.query("UPDATE servers SET (mute_role, muted_members) = (NULL, '{}'::text[]) WHERE id=$1", str(guild_id))
    self.bot.dispatch("invalidate_mod", role.guild.id)

  def do_slugify(self, string):
    string = slugify(string).replace("-", "")
    for old, new in (("4", "a"), ("@", "a"), ("3", "e"), ("1", "i"), ("0", "o"), ("7", "t"), ("5", "s")):
      string = string.replace(old, new)

    return string.lower()

  async def check_blacklist(self, msg: discord.Message):
    if not isinstance(msg.author, discord.Member):
      return
    bypass = msg.author.guild_permissions.manage_guild
    if bypass:
      return
    cleansed_msg = self.do_slugify(msg.clean_content)

    config = await self.get_guild_config(msg.guild.id)
    if config is None:
      return
    words = config.blacklisted_words
    if config.is_whitelisted(msg):
      return
    if words is None or len(words) == 0:
      return
    try:
      if bool([word for word in words if word in cleansed_msg or word in msg.clean_content]):
        try:
          await config.apply_punishment(msg.guild, msg, config.blacklist_punishments, reason="Blacklisted word.")
        except Exception as e:
          await relay_info(f"Error when trying to apply punishment {type(e).__name__}: {e}", self.bot, logger=self.bot.log.log_errors)
    except Exception as e:
      await relay_info(f"Error when trying to apply punishment (big) {type(e).__name__}: {e}", self.bot, logger=self.bot.log.log_errors)

  @commands.command(name="whitelist", aliases=["wl"], extras={"examples": ["#memes", "#admin @admin 707457407512739951"]}, invoke_without_command=True, case_insensitive=True, help="Whitelist channels and/or roles from being automoded.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def whitelist(self, ctx: "MyContext", channel_or_roles: commands.Greedy[RoleOrChannel]):
    if not channel_or_roles:
      raise commands.MissingRequiredArgument(ctx.command.params["channel_or_roles"])
    ids = [str(i.id) for i in channel_or_roles]
    await self.bot.db.query(
        """UPDATE servers SET automod_whitelist=
            ARRAY(SELECT DISTINCT UNNEST(automod_whitelist || $1) FROM servers WHERE id=$2)::text[]
        WHERE id=$2""", ids, str(ctx.guild.id))
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.send(embed=embed(title=f"Whitelisted `{', '.join([i.name for i in channel_or_roles])}`"))

  @commands.command(name="unwhitelist", aliases=["unwl"], extras={"examples": ["#memes", "@admin #admin 707457407512739951"]}, invoke_without_command=True, case_insensitive=True, help="Unwhitelist channels and/or roles from being automoded.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def unwhitelist(self, ctx: "MyContext", channel_or_roles: commands.Greedy[RoleOrChannel]):
    if not channel_or_roles:
      raise commands.MissingRequiredArgument(ctx.command.params["channel_or_roles"])
    ids = [str(i.id) for i in channel_or_roles]
    await self.bot.db.query(
        """with cte(array1, array2) as (values ((SELECT automod_whitelist FROM servers WHERE id=$2), $1::text[]))
        UPDATE servers SET automod_whitelist=
          (SELECT array_agg(elem) from cte, UNNEST(array1) elem WHERE elem <> all(array2::text[]))
        WHERE id=$2""", ids, str(ctx.guild.id))
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.send(embed=embed(title=f"Unwhitelisted `{', '.join([i.name for i in channel_or_roles])}`"))

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
  async def _blacklist_add_word(self, ctx, *, phrase: str):
    if len(phrase) < 3:
      raise commands.BadArgument("Word must be at least 3 characters long.")
    if len(await self.bot.db.query("SELECT words FROM blacklist WHERE guild_id=$1::text AND $2::text = ANY(words)", str(ctx.guild.id), phrase)) > 0:
      return await ctx.reply(embed=embed(title="Can't add duplicate word", color=MessageColors.ERROR))
    await self.bot.db.query("INSERT INTO blacklist (guild_id,words) VALUES ($1::text,array[$2]::text[]) ON CONFLICT(guild_id) DO UPDATE SET words = array_append(blacklist.words, $2)", str(ctx.guild.id), phrase)
    phrase = phrase
    await ctx.reply(embed=embed(title=f"Added `{phrase}` to the blacklist"))

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

  @_blacklist.command(name="punishment", aliases=["punishments"], extras={"examples": PUNISHMENT_TYPES, "params": PUNISHMENT_TYPES}, help="Set the punishment for the max amount of mentions one user can send per message. Combining kick,ban and/or mute will only apply one of them.", hidden=True)
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def _blacklist_punishment(self, ctx, *, action: str):
    action = [i for i in action.split(" ") if i.lower() in PUNISHMENT_TYPES]
    if len(action) == 0:
      return await ctx.send(embed=embed(title=f"The action must be one of the following: {', '.join(PUNISHMENT_TYPES)}", color=MessageColors.ERROR))
    await self.bot.db.query("UPDATE blacklist SET punishments=$1 WHERE guild_id=$2", action, str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"Set punishment to `{', '.join(action)}`"))

  @_blacklist.command(name="clear", help="Remove all words from the current servers blacklist settings.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def _blacklist_clear(self, ctx):
    await self.bot.db.query("DELETE FROM blacklist WHERE guild_id=$1", str(ctx.guild.id))
    await ctx.reply(embed=embed(title="Removed all blacklisted words"))

  async def msg_remove_invites(self, msg: discord.Message):
    if not msg.guild or (msg.author.bot and not msg.author.id == 892865928520413245):
      return

    config = await self.get_guild_config(msg.guild.id)
    if not config:
      return

    to_remove_invites = config.remove_invites
    try:
      if to_remove_invites is True:
        reg = INVITE_REG.match(msg.clean_content.strip(" "))  # re.match(INVITE_REG, msg.clean_content.strip(" "), re.RegexFlag.MULTILINE + re.RegexFlag.IGNORECASE)
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

  @commands.command(name="invitespam", aliases=["removeinvites"], extras={"examples": ["1", "0", "true", "false"]}, help="Automaticaly remove Discord invites (originating from external servers) from text channels. Not giving an argument will display the current setting.")
  @commands.guild_only()
  @commands.bot_has_guild_permissions(manage_messages=True)
  @commands.has_guild_permissions(manage_messages=True)
  async def norm_remove_discord_invites(self, ctx: "MyContext", *, enable: Union[bool, None] = None):
    if enable is None:
      current = await self.bot.db.query("SELECT remove_invites FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
      return await ctx.send(embed=embed(title="Current remove invites", description="I **will** remove invites from external servers" if current is True else "I **will not** remove invites from external servers" if current is False else f"{current}"))

    await self.bot.db.query("UPDATE servers SET remove_invites=$1 WHERE id=$2", enable, str(ctx.guild.id))
    if bool(enable) is False:
      await ctx.reply(embed=embed(title="I will no longer remove invites"))
    else:
      await ctx.reply(embed=embed(title="I will begin to remove invites"))

  @commands.group(name="mentionspam", extras={"examples": ["3", "5", "10"]}, aliases=["maxmentions", "maxpings"], help="Set the max amount of mentions one user can send per message before muting the author", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_mentions(self, ctx: "MyContext", mention_count: int, seconds: int):
    if mention_count < 3 and seconds < 5:
      return await ctx.send(embed=embed(title="Count must be greater than 3", color=MessageColors.ERROR))
    current = await self.bot.db.query("SELECT max_mentions FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {"punishments": ["mute"]}
    else:
      current = json.loads(current)
    punishments = current["punishments"]
    await self.bot.db.query("UPDATE servers SET max_mentions=$1 WHERE id=$2", json.dumps({"mentions": mention_count, "seconds": seconds, "punishments": punishments}), str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"I will now apply the punishments `{', '.join(punishments)}` to members that mention `>={mention_count}` within `{seconds}` seconds."))

  @max_mentions.error
  async def max_mentions_error(self, ctx: "MyContext", error):
    if isinstance(error, commands.MissingRequiredArgument):
      config = await self.get_guild_config(ctx.guild.id)
      if config is None or config.max_mentions is None:
        return await ctx.send(embed=embed(title="No settings found", color=MessageColors.ERROR))
      return await ctx.send(embed=embed(title="Current mention spam settings", description=f"Mention count: `{config.max_mentions['mentions']}`\nSeconds: `{config.max_mentions['seconds']}`"))

  @max_mentions.command(name="punishment", aliases=["punishments"], extras={"examples": PUNISHMENT_TYPES, "params": PUNISHMENT_TYPES}, help="Set the punishment for the max amount of mentions one user can send per message. Combining kick,ban and/or mute will only apply one of them.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_mentions_punishment(self, ctx: "MyContext", *, action: str):
    action = [i for i in action.split(" ") if i.lower() in PUNISHMENT_TYPES]
    if len(action) == 0:
      return await ctx.send(embed=embed(title=f"The action must be one of the following: {', '.join(PUNISHMENT_TYPES)}", color=MessageColors.ERROR))
    current = await self.bot.db.query("SELECT max_mentions FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {}
    else:
      current = json.loads(current)
    current.update({"punishments": action})
    await self.bot.db.query("UPDATE servers SET max_mentions=$1 WHERE id=$2", json.dumps(current), str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"New punishment for max amount of mentions in a single message is `{', '.join(action)}`"))

  @max_mentions.command(name="disable", help="Disable the max amount of mentions per message for this server.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_mentions_disable(self, ctx: "MyContext"):
    await self.bot.db.query("UPDATE servers SET max_mentions=$1 WHERE id=$2", None, str(ctx.guild.id))
    await ctx.reply(embed=embed(title="Disabled max mentions"))

  @commands.group(name="messagespam", extras={"examples": ["3 5", "10 12"]}, aliases=["maxmessages", "ratelimit"], help="Sets a max message count for users per x seconds", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
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
      return await ctx.reply(embed=embed(title="I will no longer delete messages"))
    await ctx.reply(embed=embed(title=f"I will now `{', '.join(punishments)}` messages matching the same author that are sent more than the rate of `{message_rate}` message, for every `{seconds}` seconds."))

  @max_spam.error
  async def max_spam_error(self, ctx: "MyContext", error):
    if isinstance(error, commands.MissingRequiredArgument):
      config = await self.get_guild_config(ctx.guild.id)
      if config is None or config.max_messages is None:
        return await ctx.send(embed=embed(title="No settings found", color=MessageColors.ERROR))
      return await ctx.send(embed=embed(title="Current message spam settings", description=f"Message count: `{config.max_messages['rate']}`\nSeconds: `{config.max_messages['seconds']}`\nPunishments: `{', '.join(config.max_messages['punishments'])}`"))

  @max_spam.command(name="punishment", aliases=["punishments"], extras={"examples": PUNISHMENT_TYPES, "params": PUNISHMENT_TYPES}, help="Set the punishment for the max amount of message every x seconds. Combining kick,ban and/or mute will only apply one of them.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_spam_punishment(self, ctx: "MyContext", *, action: str):
    action = [i for i in action.split(" ") if i.lower() in PUNISHMENT_TYPES]
    if len(action) == 0:
      return await ctx.send(embed=embed(title=f"The action must be one of the following: {', '.join(PUNISHMENT_TYPES)}.", color=MessageColors.ERROR))
    current = await self.bot.db.query("SELECT max_messages FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {}
    else:
      current = json.loads(current)
    current.update({"punishments": action})
    await self.bot.db.query("UPDATE servers SET max_messages=$1 WHERE id=$2", json.dumps(current), str(ctx.guild.id))
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.reply(embed=embed(title=f"New punishment(s) for spam is `{', '.join(action)}`"))

  @max_spam.command(name="disable", help="Disable the max amount of messages per x seconds by the same member for this server.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_spam_disable(self, ctx: "MyContext"):
    await self.bot.db.query("UPDATE servers SET max_messages=$1 WHERE id=$2", None, str(ctx.guild.id))
    await ctx.reply(embed=embed(title="Disabled max messages"))

  @commands.group(name="contentspam", extras={"examples": ["3 5", "15 17"]}, help="Sets the max number of message that can have the same content (ignoring who sent the message) until passing the given threshold and muting anyone spamming the same content further.", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
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

  @max_content_spam.error
  async def max_content_spam_error(self, ctx: "MyContext", error):
    if isinstance(error, commands.MissingRequiredArgument):
      config = await self.get_guild_config(ctx.guild.id)
      if config is None or config.max_content is None:
        return await ctx.send(embed=embed(title="No settings found", color=MessageColors.ERROR))
      return await ctx.send(embed=embed(title="Current message content spam settings", description=f"Message count: `{config.max_content['rate']}`\nSeconds: `{config.max_content['seconds']}`\nPunishments: `{', '.join(config.max_content['punishments'])}`"))

  @max_content_spam.command(name="punishment", aliases=["punishments"], extras={"examples": PUNISHMENT_TYPES, "params": PUNISHMENT_TYPES}, help="Set the punishment for the max amount of message every x seconds. Combining kick,ban and/or mute will only apply one of them.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_content_spam_punishment(self, ctx: "MyContext", *, action: str):
    action = [i for i in action.split(" ") if i.lower() in PUNISHMENT_TYPES]
    if len(action) == 0:
      return await ctx.send(embed=embed(title=f"The action must be one of the following: {', '.join(PUNISHMENT_TYPES)}.", color=MessageColors.ERROR))
    current = await self.bot.db.query("SELECT max_content FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {}
    else:
      current = json.loads(current)
    current.update({"punishments": action})
    await self.bot.db.query("UPDATE servers SET max_content=$1 WHERE id=$2", json.dumps(current), str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"New punishment(s) for content spam is `{', '.join(action)}`"))

  @max_content_spam.command(name="disable", help="Disable the max amount of messages per x seconds with the same content for this server.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_content_spam_disable(self, ctx: "MyContext"):
    await self.bot.db.query("UPDATE servers SET max_content=$1 WHERE id=$2", None, str(ctx.guild.id))
    await ctx.reply(embed=embed(title="Disabled max content messages"))


async def setup(bot):
  await bot.add_cog(AutoMod(bot))
