from __future__ import annotations

import datetime
import json
import re
from typing import (TYPE_CHECKING, List, Optional, Sequence, Set,
                    TypedDict, Union)

import logging
import asyncpg
import discord
from discord.ext import commands
from slugify import slugify
from typing_extensions import Annotated

from functions import (MessageColors, cache, checks, embed, exceptions,
                       relay_info, time)
from functions.formats import plural

# from .moderation import can_execute_action

if TYPE_CHECKING:
  from typing_extensions import Self

  from functions.custom_contexts import GuildContext, MyContext
  from index import Friday

  class SpamType(TypedDict):
    rate: float
    seconds: float
    punishments: List[str]

log = logging.getLogger(__name__)

INVITE_REG = re.compile(r"<?(https?:\/\/)?(www\.)?((discord\.(gg|io|me))|(discord(app|)\.(gg|com)\/invite))\/[a-zA-Z0-9\-]+>?", re.RegexFlag.MULTILINE + re.RegexFlag.IGNORECASE)

PUNISHMENT_TYPES = ["delete", "kick", "ban", "mute", "timeout"]


class InvalidPunishments(exceptions.Base):
  def __init__(self, punishments: list = []):
    super().__init__(message=f"The following punishments are invalid: {', '.join(punishments)}" if len(punishments) > 0 else "One or more of the punishments you provided is invalid.")


class RoleOrChannel(commands.Converter):
  async def convert(self, ctx: GuildContext, argument: str):
    try:
      item = await commands.TextChannelConverter().convert(ctx, argument)
    except commands.BadArgument:
      try:
        item = await commands.RoleConverter().convert(ctx, argument)
      except commands.BadArgument:
        raise commands.BadArgument("Role or channel not found.")

    # if isinstance(item, discord.Role) and not can_execute_action(ctx, ctx.author, item):
    #   raise commands.BadArgument("Your role hierarchy is too low for this action.")
    return item


class Config:
  __slots__ = ("bot", "id", "max_mentions", "max_messages", "max_content", "remove_invites", "automod_whitelist", "blacklisted_words", "blacklist_punishments", "muted_members", "mute_role_id",
               )

  bot: Friday
  id: int
  max_mentions: Optional[SpamType]
  max_messages: Optional[SpamType]
  max_content: Optional[SpamType]
  remove_invites: bool
  automod_whitelist: Set[str]
  blacklisted_words: List[str]
  blacklist_punishments: List[str]
  muted_members: Set[str]
  mute_role_id: Optional[int]

  @classmethod
  async def from_record(cls, record: asyncpg.Record, blacklist: asyncpg.Record, bot: Friday) -> Self:
    self = cls()

    self.bot = bot
    self.id = int(record["id"], base=10)
    self.max_mentions = record["max_mentions"] if record["max_mentions"] else None
    self.max_messages = record["max_messages"] if record["max_messages"] else None
    self.max_content = record["max_content"] if record["max_content"] else None
    self.remove_invites = record["remove_invites"]
    self.automod_whitelist = set(record["automod_whitelist"] or [])
    self.blacklisted_words = blacklist["words"] if blacklist else []
    self.blacklist_punishments = blacklist["punishments"] if blacklist else []
    self.muted_members = set(record["muted_members"] or [])
    self.mute_role_id = int(record["mute_role"], base=10) if record["mute_role"] else None
    return self

  @property
  def mute_role(self) -> Optional[discord.Role]:
    if self.mute_role_id:
      guild = self.bot.get_guild(self.id)
      return guild and guild.get_role(self.mute_role_id)

  def is_muted(self, member: discord.abc.Snowflake) -> bool:
    return member.id in [int(i, base=10) for i in self.muted_members]

  def is_timedout(self, member: discord.Member) -> bool:
    return member.timed_out_until is not None

  def is_whitelisted(self, msg: discord.Message, *, channel: discord.TextChannel = None, member: discord.Member = None) -> bool:
    textchannel = channel or msg.channel
    if isinstance(msg.author, discord.Member):
      roles = (member.roles if member is not None else None) or msg.author.roles

      if msg.author.guild_permissions and (msg.author.guild_permissions.administrator or msg.author.guild_permissions.manage_guild):
        return True

      if textchannel and str(textchannel.id) in self.automod_whitelist:
        return True

      if roles and any(str(role.id) in self.automod_whitelist for role in roles):
        return True

    return False

  async def mute(self, member: discord.Member, *, duration: datetime.timedelta = None, reason: Optional[str] = "Auto-mute for spamming.") -> None:
    if self.mute_role_id:
      now = discord.utils.utcnow()
      await member.add_roles(discord.Object(id=self.mute_role_id), reason=reason or "Auto-mute for spamming.")
      if duration:
        dur = now + duration
        reminder = self.bot.reminder
        if reminder is None:
          return log.error("Reminder cog is not loaded.")
        await reminder.create_timer(dur, "tempmute", member.guild.id, self.bot.user.id, member.id, self.mute_role_id, created=now)

  async def timeout(self, member: discord.Member, *, duration: time.TimeoutTime = None, reason: Optional[str] = "Auto-timeout for spamming.") -> None:
    if not duration:
      duration = time.TimeoutTime("20m")
    try:
      await member.edit(timed_out_until=duration.dt, reason=reason or "Auto-timeout for spamming.")
    except (discord.Forbidden, discord.HTTPException):
      pass

  async def delete(self, msg: discord.Message) -> None:
    try:
      await msg.delete()
    except discord.NotFound:
      pass

  async def kick(self, member: discord.Member, reason: Optional[str] = "Auto-kick for spamming.") -> None:
    await member.kick(reason=reason or "Auto-kick for spamming.")

  async def ban(self, member: discord.Member, duration: Optional[datetime.timedelta] = None, reason: Optional[str] = "Auto-ban for spamming.") -> None:
    await member.ban(reason=reason or "Auto-ban for spamming.")
    if duration:
      now = discord.utils.utcnow()
      dur = now + duration
      reminder = self.bot.reminder
      if reminder is None:
        return log.error("Reminder cog is not loaded.")
      await reminder.create_timer(dur, "tempban", member.guild.id, self.bot.user.id, member.id, created=now)

  async def apply_punishment(self, guild: discord.Guild, msg: discord.Message, punishments: Sequence[str], *, member: Optional[discord.Member] = None, reason: Optional[str] = None) -> None:
    new_member = member or msg.author
    assert isinstance(new_member, discord.Member)
    if "delete" in punishments:
      await self.delete(msg)
    if "ban" in punishments:
      await self.ban(new_member, reason=reason)
    elif "kick" in punishments:
      await self.kick(new_member, reason=reason)
    elif "timeout" in punishments:
      await self.timeout(new_member, reason=reason)
    elif "mute" in punishments:
      await self.mute(new_member, reason=reason)


class CooldownByContent(commands.CooldownMapping):
  def _bucket_key(self, msg):
    return (msg.channel.id, msg.content)


class SpamChecker:
  __slots__ = ("bot", "_message_spam", "_mention_spam", "_content_spam",)

  bot: Friday
  _message_spam: Optional[commands.CooldownMapping]
  _mention_spam: Optional[commands.CooldownMapping]
  _content_spam: Optional[commands.CooldownMapping]

  @classmethod
  def from_cooldowns(cls, *, bot: Friday, config: Config) -> Self:  # message_spam: Optional[commands.CooldownMapping], mention_spam: Optional[commands.CooldownMapping], content_spam: Optional[CooldownByContent]):
    self = cls()

    self.bot = bot
    self._message_spam = config.max_messages is not None and commands.CooldownMapping.from_cooldown(config.max_messages["rate"], config.max_messages["seconds"], commands.BucketType.user) or None
    self._mention_spam = config.max_mentions is not None and commands.CooldownMapping.from_cooldown(config.max_mentions["rate"], config.max_mentions["seconds"], commands.BucketType.user) or None
    self._content_spam = config.max_content is not None and CooldownByContent.from_cooldown(config.max_content["rate"], config.max_content["seconds"], commands.BucketType.member) or None

    return self

  @property
  def is_disabled(self) -> bool:
    return not self._message_spam and not self._mention_spam and not self._content_spam

  def is_spamming(self, message: discord.Message) -> bool:
    if message.guild is None:
      return False

    current = message.created_at.timestamp()

    bucket = self._message_spam and self._message_spam.get_bucket(message)
    if bucket and bucket.update_rate_limit(current):
      return True

    return False

  def is_content_spamming(self, message: discord.Message) -> bool:
    if message.guild is None:
      return False

    current = message.created_at.timestamp()

    bucket = self._content_spam and self._content_spam.get_bucket(message)
    if bucket and bucket.update_rate_limit(current):
      return True

    return False

  def is_mention_spamming(self, message: discord.Message) -> bool:
    if message.guild is None:
      return False

    current = message.created_at.timestamp()

    bucket = self._mention_spam and self._mention_spam.get_bucket(message)
    if bucket and bucket.update_rate_limit(current):
      return True

    return False


class AutoMod(commands.Cog):
  """There are somethings in this world that bots are better at then humans. Let Friday help out with the moderation of your Discord server."""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot

    self._spam_check: dict[int, SpamChecker] = dict()

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def cog_command_error(self, ctx: MyContext, error: commands.CommandError):
    error = getattr(error, "original", error)
    if isinstance(error, (commands.MissingRequiredArgument)):
      return
    if isinstance(error, (commands.BadArgument, InvalidPunishments)):
      return await ctx.send(embed=embed(title=str(error), color=MessageColors.error()))
    log.error(f"Error in {ctx.command.qualified_name}: {type(error).__name__}: {error}")

  async def cog_after_invoke(self, ctx: MyContext):
    if not ctx.guild:
      return

    self._spam_check.pop(ctx.guild.id, None)
    self.bot.dispatch("invalidate_mod", ctx.guild.id)

  @commands.Cog.listener()
  async def on_invalidate_mod(self, guild_id: int):
    self.get_guild_config.invalidate(self, guild_id)

  @cache.cache()
  async def get_guild_config(self, guild_id: int, *, connection: Optional[Union[asyncpg.Pool, asyncpg.Connection]] = None) -> Optional[Config]:
    query = "SELECT * FROM servers WHERE id=$1 LIMIT 1;"
    blquery = "SELECT * FROM blacklist WHERE guild_id=$1 LIMIT 1;"
    conn = connection or self.bot.pool
    record = await conn.fetchrow(query, str(guild_id))
    # REMOVE THIS AT SOME POINT
    if record and record["max_mentions"] is not None:
      try:
        mm = record["max_mentions"]
        mm["rate"]
      except KeyError:
        new: SpamType = {"rate": record["max_mentions"]["mentions"], "seconds": record["max_mentions"]["seconds"], "punishments": record["max_mentions"]["punishments"]}
        record = await conn.fetchrow("UPDATE servers SET max_mentions=$1 WHERE id=$2 RETURNING *", new, str(guild_id))
    # _________________________
    log.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
    blrecord = await conn.fetchrow(blquery, str(guild_id))
    log.debug(f"PostgreSQL Query: \"{blquery}\" + {str(guild_id)}")
    if record is not None:
      return await Config.from_record(record, blrecord, self.bot)
    return None

  @commands.Cog.listener()
  async def on_message_edit(self, before: discord.Message, after: discord.Message):
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

    if config.max_messages is not None and config.max_messages != {}:
      if spam.is_spamming(msg):
        return await config.apply_punishment(msg.guild, msg, config.max_messages["punishments"], reason="Spamming messages.")

  @commands.Cog.listener()
  async def on_member_join(self, member: discord.Member):
    guild_id = member.guild.id
    config = await self.get_guild_config(guild_id)
    if config is None:
      return

    if config.is_muted(member):
      await config.mute(member, reason="Member was previously muted.")

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
      await self.bot.pool.execute("UPDATE servers SET muted_members=array_append(muted_members, $1) WHERE id=$2 AND NOT ($1=any(muted_members))", str(after.id), str(guild_id))
    else:
      await self.bot.pool.execute("UPDATE servers SET muted_members=array_remove(muted_members, $1) WHERE id=$2", str(after.id), str(guild_id))
    self.bot.dispatch("invalidate_mod", before.guild.id)

  @commands.Cog.listener()
  async def on_guild_role_delete(self, role: discord.Role):
    guild_id = role.guild.id
    config = await self.get_guild_config(guild_id)
    if config is None or config.mute_role_id != role.id:
      return

    await self.bot.pool.execute("UPDATE servers SET (mute_role, muted_members) = (NULL, '{}'::text[]) WHERE id=$1", str(guild_id))
    self.bot.dispatch("invalidate_mod", role.guild.id)

  def do_slugify(self, string):
    string = slugify(string).replace("-", "")
    for old, new in (("4", "a"), ("@", "a"), ("3", "e"), ("1", "i"), ("0", "o"), ("7", "t"), ("5", "s")):
      string = string.replace(old, new)

    return string.lower()

  async def check_blacklist(self, msg: discord.Message):
    if not isinstance(msg.author, discord.Member) or not msg.guild:
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
          await relay_info(f"Error when trying to apply punishment {type(e).__name__}: {e}", self.bot, webhook=self.bot.log.log_errors)
    except Exception as e:
      await relay_info(f"Error when trying to apply punishment (big) {type(e).__name__}: {e}", self.bot, webhook=self.bot.log.log_errors)

  @commands.command(name="whitelist", aliases=["wl"], extras={"examples": ["#memes", "#admin @admin 707457407512739951"]}, invoke_without_command=True, case_insensitive=True, help="Whitelist channels and/or roles from being automoded.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def whitelist(self, ctx: GuildContext, channel_or_roles: Annotated[Sequence[Union[discord.Role, discord.abc.GuildChannel]], commands.Greedy[RoleOrChannel]]):
    if not channel_or_roles:
      raise commands.MissingRequiredArgument(ctx.command.params["channel_or_roles"])
    ids = [str(i.id) for i in channel_or_roles]
    await ctx.db.execute(
        """UPDATE servers SET automod_whitelist=
            ARRAY(SELECT DISTINCT UNNEST(automod_whitelist || $1) FROM servers WHERE id=$2)::text[]
        WHERE id=$2""", ids, str(ctx.guild.id))
    await ctx.send(embed=embed(title=f"Whitelisted `{', '.join([i.name for i in channel_or_roles])}`"))

  @commands.command(name="unwhitelist", aliases=["unwl"], extras={"examples": ["#memes", "@admin #admin 707457407512739951"]}, invoke_without_command=True, case_insensitive=True, help="Unwhitelist channels and/or roles from being automoded.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def unwhitelist(self, ctx: GuildContext, channel_or_roles: Annotated[Sequence[Union[discord.Role, discord.abc.GuildChannel]], commands.Greedy[RoleOrChannel]]):
    if not channel_or_roles:
      raise commands.MissingRequiredArgument(ctx.command.params["channel_or_roles"])
    ids = [str(i.id) for i in channel_or_roles]
    await ctx.db.execute(
        """with cte(array1, array2) as (values ((SELECT automod_whitelist FROM servers WHERE id=$2), $1::text[]))
        UPDATE servers SET automod_whitelist=
          (SELECT array_agg(elem) from cte, UNNEST(array1) elem WHERE elem <> all(array2::text[]))
        WHERE id=$2""", ids, str(ctx.guild.id))
    await ctx.send(embed=embed(title=f"Unwhitelisted `{', '.join([i.name for i in channel_or_roles])}`"))

  @commands.group(name="blacklist", aliases=["bl"], invoke_without_command=True, case_insensitive=True, help="Blacklist words from being sent in text channels")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def _blacklist(self, ctx: GuildContext):
    return await self._blacklist_display_words(ctx)

  @_blacklist.command(name="add", aliases=["+"], extras={"examples": ["penis", "shit", "cum"]}, help="Add a word to the current servers blacklist settings.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def _blacklist_add_word(self, ctx: GuildContext, *, phrase: str):
    if len(phrase) < 3:
      raise commands.BadArgument("Word must be at least 3 characters long.")
    config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
    if config and phrase in config.blacklisted_words:
      return await ctx.reply(embed=embed(title="Can't add duplicate word", color=MessageColors.error()))
    await ctx.db.execute("INSERT INTO blacklist (guild_id,words) VALUES ($1::text,array[$2]::text[]) ON CONFLICT(guild_id) DO UPDATE SET words = array_append(blacklist.words, $2)", str(ctx.guild.id), phrase)
    await ctx.reply(embed=embed(title=f"Added `{phrase}` to the blacklist"))

  @_blacklist.command(name="remove", aliases=["-"], extras={"examples": ["penis", "shit"]}, help="Remove a word from the current servers blacklist settings.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def _blacklist_remove_word(self, ctx: GuildContext, *, word: str):
    cleansed_word = word
    config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
    if config and cleansed_word not in config.blacklisted_words:
      return await ctx.reply(embed=embed(title="You don't seem to be blacklisting that word"))
    await ctx.db.execute("UPDATE blacklist SET words = array_remove(words,$2::text) WHERE guild_id=$1", str(ctx.guild.id), cleansed_word)
    await ctx.reply(embed=embed(title=f"Removed `{word}` from the blacklist"))

  @_blacklist.command(name="display", aliases=["list", "show"], help="Display the current servers blacklist settings.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def _blacklist_display_words(self, ctx: GuildContext):
    config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
    if config and config.blacklisted_words:
      return await ctx.reply(embed=embed(title="Blocked words", description='\n'.join(config.blacklisted_words)))
    await ctx.reply(embed=embed(title=f"No blacklisted words yet, use `{ctx.prefix}blacklist add <word>` to get started"))

  @_blacklist.command(name="punishment", aliases=["punishments"], extras={"examples": PUNISHMENT_TYPES, "params": PUNISHMENT_TYPES}, help="Set the punishment for blacklisted words. Combining kick,ban and/or mute will only apply one of them.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def _blacklist_punishment(self, ctx: GuildContext, *, punishments: str = None):
    if punishments is None:
      old_punishments = await ctx.db.fetchval(f"SELECT punishments FROM blacklist WHERE guild_id='{ctx.guild.id}'")
      return await ctx.send(embed=embed(title="Blacklist punishments", description=f"The blacklist punishments for `{ctx.guild}` are `{', '.join(old_punishments)}`."))

    new_punishments = [i for i in punishments.split(" ") if i.lower() in PUNISHMENT_TYPES]
    if not all(new_punishments) in PUNISHMENT_TYPES:
      raise InvalidPunishments([p for p in new_punishments if p not in PUNISHMENT_TYPES])

    await ctx.db.execute("UPDATE blacklist SET punishments=$1 WHERE guild_id=$2", new_punishments, str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"Set punishment to `{', '.join(new_punishments)}`"))

  @_blacklist.command(name="clear", help="Remove all words from the current servers blacklist settings.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def _blacklist_clear(self, ctx: GuildContext):
    await ctx.db.execute("DELETE FROM blacklist WHERE guild_id=$1", str(ctx.guild.id))
    await ctx.reply(embed=embed(title="Removed all blacklisted words"))

  async def msg_remove_invites(self, msg: discord.Message):
    if not msg.guild:
      return

    if msg.author.bot and msg.author.id != 892865928520413245 and msg.author.id != 968261189828231308:
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

  @commands.command(name="invitespam", aliases=["removeinvites"], extras={"examples": ["on", "off", "true", "false"]}, help="Automaticaly remove Discord invites (originating from external servers) from text channels. Not giving an argument will display the current setting.")
  @commands.guild_only()
  @checks.is_mod_or_guild_permissions(manage_messages=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def norm_remove_discord_invites(self, ctx: GuildContext, *, enable: Union[bool, None] = None):
    if enable is None:
      current = await ctx.db.fetchval("SELECT remove_invites FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
      return await ctx.send(embed=embed(title="Current remove invites", description="I **will** remove invites from external servers" if current is True else "I **will not** remove invites from external servers" if current is False else f"{current}"))

    await ctx.db.execute("UPDATE servers SET remove_invites=$1 WHERE id=$2", enable, str(ctx.guild.id))
    if bool(enable) is False:
      await ctx.reply(embed=embed(title="I will no longer remove invites"))
    else:
      await ctx.reply(embed=embed(title="I will begin to remove invites"))

  @commands.group(name="mentionspam", extras={"examples": ["3", "5", "10"]}, aliases=["maxmentions", "maxpings"], help="Set the max amount of mentions one user can send per message before muting the author", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_mentions(self, ctx: GuildContext, mention_count: int, seconds: int):
    if mention_count < 3 and seconds < 5:
      return await ctx.send(embed=embed(title="Count must be greater than 3", color=MessageColors.error()))
    current = await ctx.db.fetchval("SELECT max_mentions FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {"punishments": ["mute"]}
    punishments = current["punishments"]
    data: SpamType = {"rate": mention_count, "seconds": seconds, "punishments": punishments}
    await ctx.db.execute("UPDATE servers SET max_mentions=$1 WHERE id=$2", data, str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"I will now apply the punishments `{', '.join(punishments)}` to members that mention `>={mention_count}` within `{plural(seconds):second}`."))

  @max_mentions.error
  async def max_mentions_error(self, ctx: GuildContext, error: commands.CommandError):
    if isinstance(error, commands.MissingRequiredArgument):
      config = await self.get_guild_config(ctx.guild.id)
      if config is None or config.max_mentions is None:
        return await ctx.send(embed=embed(title="No settings found", color=MessageColors.error()))
      return await ctx.send(embed=embed(title="Current mention spam settings", description=f"Mention count: `{config.max_mentions['rate']}`\nSeconds: `{config.max_mentions['seconds']}`"))

  @max_mentions.command(name="punishment", aliases=["punishments"], extras={"examples": PUNISHMENT_TYPES, "params": PUNISHMENT_TYPES}, help="Set the punishment for the max amount of mentions one user can send per message. Combining kick,ban and/or mute will only apply one of them.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_mentions_punishment(self, ctx: GuildContext, *, punishments: str = None):
    if punishments is None:
      old_punishments = await ctx.db.fetchval(f"SELECT warn_punishments FROM servers WHERE id='{ctx.guild.id}'")
      return await ctx.send(embed=embed(title="Warning punishments", description=f"The warning punishments for `{ctx.guild}` are `{', '.join(old_punishments)}`."))

    new_punishments = [i for i in punishments.split(" ") if i.lower() in PUNISHMENT_TYPES]
    if not all(new_punishments) in PUNISHMENT_TYPES:
      raise InvalidPunishments([p for p in new_punishments if p not in PUNISHMENT_TYPES])
    current = await ctx.db.fetchval("SELECT max_mentions FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {}
    current.update({"punishments": new_punishments})
    await ctx.db.execute("UPDATE servers SET max_mentions=$1 WHERE id=$2", current, str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"New punishment for max amount of mentions in a single message is `{', '.join(new_punishments)}`"))

  @max_mentions.command(name="disable", help="Disable the max amount of mentions per message for this server.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_mentions_disable(self, ctx: GuildContext):
    await ctx.db.execute("UPDATE servers SET max_mentions=$1 WHERE id=$2", None, str(ctx.guild.id))
    await ctx.reply(embed=embed(title="Disabled max mentions"))

  @commands.group(name="messagespam", extras={"examples": ["3 5", "10 12"]}, aliases=["maxmessages", "ratelimit"], help="Sets a max message count for users per x seconds", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_spam(self, ctx: GuildContext, message_rate: int, seconds: int):
    if message_rate < 3 or seconds < 5:
      return await ctx.send(embed=embed(title="Some arguments are too small", description="`message_rate` must be greater than 3\n`seconds` must be greater than 5", color=MessageColors.error()))
    current = await ctx.db.fetchval("SELECT max_messages FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {"punishments": ["mute"]}
    punishments = current.get("punishments", ["mute"])
    value: SpamType = {"rate": message_rate, "seconds": seconds, "punishments": punishments}
    await ctx.db.execute("UPDATE servers SET max_messages=$1 WHERE id=$2", value, str(ctx.guild.id))
    if value is None:
      return await ctx.reply(embed=embed(title="I will no longer delete messages"))
    await ctx.reply(embed=embed(title=f"I will now apply `{', '.join(punishments)}` to messages matching the same author that are sent more than the rate of `{plural(message_rate):message}`, for every `{plural(seconds):second}`."))

  @max_spam.error
  async def max_spam_error(self, ctx: GuildContext, error: commands.CommandError):
    if isinstance(error, commands.MissingRequiredArgument):
      config = await self.get_guild_config(ctx.guild.id)
      if config is None or config.max_messages is None:
        return await ctx.send(embed=embed(title="No settings found", color=MessageColors.error()))
      return await ctx.send(embed=embed(title="Current message spam settings", description=f"Message count: `{config.max_messages['rate']}`\nSeconds: `{config.max_messages['seconds']}`\nPunishments: `{', '.join(config.max_messages['punishments'])}`"))

  @max_spam.command(name="punishment", aliases=["punishments"], extras={"examples": PUNISHMENT_TYPES, "params": PUNISHMENT_TYPES}, help="Set the punishment for the max amount of message every x seconds. Combining kick,ban and/or mute will only apply one of them.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_spam_punishment(self, ctx: GuildContext, *, punishments: str = None):
    if punishments is None:
      old_punishments = await ctx.db.fetchval(f"SELECT warn_punishments FROM servers WHERE id='{ctx.guild.id}'")
      return await ctx.send(embed=embed(title="Warning punishments", description=f"The warning punishments for `{ctx.guild}` are `{', '.join(old_punishments)}`."))

    old_punishments = [i for i in punishments.split(" ") if i.lower() in PUNISHMENT_TYPES]
    if not all(old_punishments) in PUNISHMENT_TYPES:
      raise InvalidPunishments([p for p in old_punishments if p not in PUNISHMENT_TYPES])
    current = await ctx.db.fetchval("SELECT max_messages FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {}
    current.update({"punishments": old_punishments})
    await ctx.db.execute("UPDATE servers SET max_messages=$1 WHERE id=$2", current, str(ctx.guild.id))
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.reply(embed=embed(title=f"New punishment(s) for spam is `{', '.join(old_punishments)}`"))

  @max_spam.command(name="disable", aliases=["clear"], help="Disable the max amount of messages per x seconds by the same member for this server.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_spam_disable(self, ctx: GuildContext):
    await ctx.db.execute("UPDATE servers SET max_messages=$1 WHERE id=$2", None, str(ctx.guild.id))
    await ctx.reply(embed=embed(title="Disabled max messages"))

  @commands.group(name="contentspam", extras={"examples": ["3 5", "15 17"]}, help="Sets the max number of message that can have the same content (ignoring who sent the message) until passing the given threshold and muting anyone spamming the same content further.", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_content_spam(self, ctx: GuildContext, message_rate: int, seconds: int):
    if message_rate < 3 or seconds < 5:
      return await ctx.send(embed=embed(title="Some arguments are too small", description="`message_rate` must be greater than 3\n`seconds` must be greater than 5", color=MessageColors.error()))
    current = await ctx.db.fetchval("SELECT max_content FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {"punishments": ["mute"]}
    punishments = current["punishments"] if "punishments" in current else ["mute"]
    value: SpamType = {"rate": message_rate, "seconds": seconds, "punishments": punishments}
    await ctx.db.execute("UPDATE servers SET max_content=$1 WHERE id=$2", value, str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"I will now apply `{', '.join(punishments)}` to messages matching the same content that are sent more than the rate of `{plural(message_rate):message}`, for every `{plural(seconds):second}`."))

  @max_content_spam.error
  async def max_content_spam_error(self, ctx: GuildContext, error: commands.CommandError):
    if isinstance(error, commands.MissingRequiredArgument):
      config = await self.get_guild_config(ctx.guild.id)
      if config is None or config.max_content is None:
        return await ctx.send(embed=embed(title="No settings found", color=MessageColors.error()))
      return await ctx.send(embed=embed(title="Current message content spam settings", description=f"Message count: `{config.max_content['rate']}`\nSeconds: `{config.max_content['seconds']}`\nPunishments: `{', '.join(config.max_content['punishments'])}`"))

  @max_content_spam.command(name="punishment", aliases=["punishments"], extras={"examples": PUNISHMENT_TYPES, "params": PUNISHMENT_TYPES}, help="Set the punishment for the max amount of message every x seconds. Combining kick,ban and/or mute will only apply one of them.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_content_spam_punishment(self, ctx: GuildContext, *, punishments: str = None):
    if punishments is None:
      old_punishments = await ctx.db.fetchval(f"SELECT warn_punishments FROM servers WHERE id='{ctx.guild.id}'")
      return await ctx.send(embed=embed(title="Warning punishments", description=f"The warning punishments for `{ctx.guild}` are `{', '.join(old_punishments)}`."))

    new_punishments = [i for i in punishments.split(" ") if i.lower() in PUNISHMENT_TYPES]
    if not all(new_punishments) in PUNISHMENT_TYPES:
      raise InvalidPunishments([p for p in new_punishments if p not in PUNISHMENT_TYPES])
    current = await ctx.db.fetchval("SELECT max_content FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current is None or current == "null":
      current = {}
    current.update({"punishments": new_punishments})
    await ctx.db.execute("UPDATE servers SET max_content=$1 WHERE id=$2", current, str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"New punishment(s) for content spam is `{', '.join(new_punishments)}`"))

  @max_content_spam.command(name="disable", help="Disable the max amount of messages per x seconds with the same content for this server.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_messages=True, manage_roles=True)
  async def max_content_spam_disable(self, ctx: GuildContext):
    await ctx.db.execute("UPDATE servers SET max_content=$1 WHERE id=$2", None, str(ctx.guild.id))
    await ctx.reply(embed=embed(title="Disabled max content messages"))


async def setup(bot):
  await bot.add_cog(AutoMod(bot))
