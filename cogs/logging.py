from __future__ import annotations

import datetime
import enum
import re
from typing import (TYPE_CHECKING, AsyncIterator, Callable, Literal, Optional,
                    Union)

import asyncpg
import discord
from discord.ext import commands  # , tasks

from functions import MessageColors, MyContext, cache, embed, formats

if TYPE_CHECKING:
  from typing_extensions import Self

  from functions.custom_contexts import GuildContext
  from index import Friday

  class BannedMember(discord.Member):
    reason: Optional[str]

  class BannedUser(discord.User):
    reason: Optional[str]

EVENT_TYPES = ["bans", "mutes", "unbans", "unmutes", "kicks"]
REASON_REG = re.compile(r"\[[\w\s]+.+#\d{4}\s\(ID:\s(\d{18})\)\](?:\:\s(.+))?")
REASON_ID_REG = re.compile(r"[0-9]{18}")


def create_command_reason(moderator: Union[discord.Member, discord.User], reason: Optional[str] = None) -> str:
  to_return = f"[{moderator} (ID: {moderator.id})]"
  if reason:
    to_return += f": {reason}"
  return to_return


class ModConfig:
  __slots__ = ("bot", "id", "mod_log_channel_id", "mod_log_events", "mute_role_id", )

  bot: Friday
  id: int
  mute_role_id: Optional[int]
  mod_log_channel_id: Optional[int]
  mod_log_events: list[str]

  @classmethod
  def from_record(cls, record: asyncpg.Record, bot: Friday) -> Self:
    self = cls()

    self.bot = bot
    self.id = int(record["id"], base=10)
    self.mute_role_id = int(record["mute_role"], base=10) if record["mute_role"] else None
    self.mod_log_events = list(record["mod_log_events"] or [])
    self.mod_log_channel_id = int(record["mod_log_channel"], base=10) if record["mod_log_channel"] else None
    return self

  @property
  def mod_log_channel(self) -> Optional[discord.TextChannel]:
    guild = self.bot.get_guild(self.id)
    return guild and guild.get_channel(self.mod_log_channel_id)  # type: ignore

  @property
  def mute_role(self) -> Optional[discord.Role]:
    if self.mute_role_id:
      guild = self.bot.get_guild(self.id)
      return guild and guild.get_role(self.mute_role_id)


class ModLogging(commands.Cog):
  """Different from the log cog b/c this one deals with discord logging not bot logging"""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  @cache.cache()
  async def get_guild_config(self, guild_id: int, *, connection: Optional[asyncpg.Connection] = None) -> ModConfig:
    conn = connection or self.bot.pool
    query = "SELECT * FROM servers WHERE id=$1 LIMIT 1"
    record = await conn.fetchrow(query, str(guild_id))
    if not record:
      raise ValueError("Server not found.")
    return ModConfig.from_record(record, self.bot)

  @commands.Cog.listener()
  async def on_invalidate_mod(self, guild_id: int):
    self.get_guild_config.invalidate(self, guild_id)

  @commands.Cog.listener()
  async def on_log_event(self, guild_id: int, event: Literal["ban", "mute", "unban", "unmute", "kick", "timeout", "untimeout"], *, offender: Union[discord.User, discord.Member], moderator: Union[discord.User, discord.Member], reason: str = "No reason given"):
    config = await self.get_guild_config(guild_id)
    if not config:
      return

    if config.mod_log_channel is None:
      return

    await config.mod_log_channel.send(embed=embed(
        title=event.capitalize(),
        description=f"**Offender:** {offender.mention} (ID: {offender.id})\n**Reason:** {reason}\n**Moderator responsible:** {moderator.mention} (ID: {moderator.id})",
        color=MessageColors.logging(),
        timestamp=discord.utils.utcnow()))

  @commands.Cog.listener()
  async def on_member_update(self, before: discord.Member, after: discord.Member):
    if before.roles == after.roles and before.timed_out_until == after.timed_out_until:
      return

    guild_id = after.guild.id
    config = await self.get_guild_config(guild_id)
    if config is None:
      return

    if config.mute_role_id is None:
      return

    if "mutes" not in config.mod_log_events and "unmutes" not in config.mod_log_events:
      return

    before_has = before._roles.has(config.mute_role_id)
    after_has = after._roles.has(config.mute_role_id)

    if before_has == after_has:
      return

    audit = [a async for a in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update, user=before.guild.me, oldest_first=False)]
    if len(audit) == 0 or len([i for i in audit if i.target and i.target.id == before.id]) == 0:
      return

    action: discord.AuditLogEntry = audit[0]
    reg = REASON_REG.match(action.reason)  # type: ignore
    reason = action.reason if reg is None and action.reason is not None else reg[2] if reg is not None and reg[2] is not None else "No reason given"

    if after_has and "mutes" in config.mod_log_events:
      self.bot.dispatch("log_event", before.guild.id, "mute", offender=before, moderator=action.user, reason=reason)
    elif "unmutes" in config.mod_log_events:
      self.bot.dispatch("log_event", before.guild.id, "unmute", offender=before, moderator=action.user, reason=reason)

  @commands.Cog.listener()
  async def on_member_ban(self, guild: discord.Guild, member: Union[discord.User, discord.Member], *, audit_logs: Optional[Callable[..., AsyncIterator[discord.AuditLogEntry]]] = None):
    config = await self.get_guild_config(guild.id)
    if not config:
      return

    if config.mod_log_channel is None:
      return

    if "bans" not in config.mod_log_events:
      return

    # This is only added for pytest-ing
    audit_logs = audit_logs or guild.audit_logs
    audit = [a async for a in audit_logs(limit=5, action=discord.AuditLogAction.ban, user=guild.me, oldest_first=False)]
    if len(audit) == 0 or len([i for i in audit if i.target and i.target.id == member.id]) == 0:
      return

    action: discord.AuditLogEntry = sorted(audit, key=lambda x: x.created_at)[0]
    reg = REASON_REG.match(action.reason)  # type: ignore
    # reason = member.reason if hasattr(member, "reason") and reg is None and member.reason is not None else reg[2] if reg is not None and reg[2] is not None else member.reason if member.reason is not None else "No reason given"
    reason = reg[2] if reg and reg[2] else action.reason or "No reason given"

    # moderator = action.user if action.user and action.user.id != self.bot.user.id and reg is not None else reg and await self.bot.fetch_user(REASON_ID_REG.findall(reg.string)[0])
    # moderator = action.user if action.user and action.user.id != self.bot.user.id and reg is not None else await self.bot.fetch_user(REASON_ID_REG.findall(reg.string)[0])
    if reg is not None:
      if action.user and action.user.id != self.bot.user.id:
        moderator = action.user
      else:
        moderator = await self.bot.get_or_fetch_member(guild, REASON_ID_REG.findall(reg.string)[0])
    else:
      # this should never happen
      moderator = action.user or self.bot.user

    self.bot.dispatch("log_event", guild.id, "ban", offender=member, moderator=moderator, reason=reason)

  @commands.Cog.listener()
  async def on_member_unban(self, guild: discord.Guild, member: Union[discord.User, discord.Member], *, audit_logs: Optional[Callable[..., AsyncIterator[discord.AuditLogEntry]]] = None):
    config = await self.get_guild_config(guild.id)
    if not config:
      return

    if config.mod_log_channel is None:
      return

    if "unbans" not in config.mod_log_events:
      return

    audit_logs = audit_logs or guild.audit_logs
    audit = [a async for a in audit_logs(limit=5, action=discord.AuditLogAction.unban, user=guild.me, oldest_first=False)]
    if len(audit) == 0 or len([i for i in audit if i.target and i.target.id == member.id]) == 0:
      return

    action: discord.AuditLogEntry = audit[0]
    reg = REASON_REG.match(action.reason)  # type: ignore
    # reason = action.reason if reg is None and action.reason is not None else reg[2] if reg is not None and reg[2] is not None else action.reason if action.reason is not None else "No reason given"
    reason = reg[2] if reg and reg[2] else action.reason or "No reason given"

    # moderator = action.user if action.user and action.user.id != self.bot.user.id and reg is not None else await self.bot.fetch_user(REASON_ID_REG.findall(reg.string)[0])
    if reg is not None:
      if action.user and action.user.id != self.bot.user.id:
        moderator = action.user
      else:
        moderator = await self.bot.get_or_fetch_member(guild, REASON_ID_REG.findall(reg.string)[0])
    else:
      # this should never happen
      moderator = action.user or self.bot.user

    self.bot.dispatch("log_event", guild.id, "unban", offender=member, moderator=moderator, reason=reason)

  @commands.Cog.listener()
  async def on_member_remove(self, member: discord.Member, *, audit_logs: Optional[Callable[..., AsyncIterator[discord.AuditLogEntry]]] = None):
    config = await self.get_guild_config(member.guild.id)
    if not config:
      return

    if config.mod_log_channel is None:
      return

    if "kicks" not in config.mod_log_events:
      return

    after = discord.utils.utcnow() - datetime.timedelta(seconds=5)

    audit_logs = audit_logs or member.guild.audit_logs
    audit = [a async for a in audit_logs(limit=5, action=discord.AuditLogAction.kick, oldest_first=False)]
    if len(audit) == 0 or len([i for i in audit if i.target and i.target.id == member.id and i.created_at > after]) == 0:
      return

    action: discord.AuditLogEntry = audit[0]
    reg = action.reason and REASON_REG.match(action.reason)
    reason = reg[2] if reg and reg[2] else action.reason or "No reason given"

    self.bot.dispatch("log_event", member.guild.id, "kick", offender=action.target, moderator=action.user, reason=reason)

  @commands.group(name="modlog", aliases=["modlogs"], help="Set the channel where I can log moderation actions. This will log moderation action done by Friday, Fridays commands, and other moderation action logged by Discord.", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @commands.has_guild_permissions(administrator=True)
  @commands.bot_has_guild_permissions(view_audit_log=True)
  async def mod_log(self, ctx: GuildContext, *, channel: Optional[discord.TextChannel] = None):
    if channel is not None:
      perms = channel.permissions_for(ctx.guild.me)
      if not perms.send_messages or not perms.embed_links:
        return await ctx.send(embed=embed(title=f"I need the `Send Messages` and `Embed Links` permissions in `{channel}` to send logs in that channel.", color=MessageColors.error()))
    channel_id = str(channel.id) if channel else None
    await ctx.db.execute("UPDATE servers SET mod_log_channel=$1 WHERE id=$2", channel_id, str(ctx.guild.id))
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.send(embed=embed(title=f"Mod log channel has been set to `{channel}`"))

  @mod_log.command(name="events", extras={"examples": [*EVENT_TYPES, "bans mutes kicks unbans unmutes", "bans unbans"], "params": EVENT_TYPES}, help="The events that will be logged in the mod log channel")
  @commands.guild_only()
  @commands.has_guild_permissions(administrator=True)
  @commands.bot_has_guild_permissions(view_audit_log=True)
  async def mod_log_events(self, ctx: GuildContext, events: commands.Greedy[Literal["bans", "mutes", "unbans", "unmutes", "kicks"]]):
    config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
    current = config.mod_log_events
    new = await ctx.multi_select(
        options=[
            {
                "label": f"{i}",
                "value": i,
                "default": i in current,
            } for i in EVENT_TYPES
        ], max_values=len(EVENT_TYPES), min_values=0
    )
    if not new:
      return await ctx.send(embed=embed(title="No events selected.", color=MessageColors.error()))

    await ctx.db.execute("UPDATE servers SET mod_log_events=$1 WHERE id=$2", new, str(ctx.guild.id))
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.send(embed=embed(title=f"Mod log events have been set to `{formats.human_join(new, final='and')}`"))

  @mod_log_events.error
  async def mod_log_events_error(self, ctx: MyContext, error: commands.CommandError):
    if isinstance(error, commands.BadLiteralArgument):
      return await ctx.send(embed=embed(title="Invalid event(s)", description=f"You must specify one of the following events: {', '.join(EVENT_TYPES)}.", color=MessageColors.error()))


class LogEvents(enum.Enum):
  # nothing = 0
  delete = 1
  edit = 2
  purge = 4
  role = 8
  join = 256
  leave = 512
  voice_join = 8192
  voice_move = 16384
  voice_leave = 32768

  def __str__(self):
    return self.name


class Logging(commands.Cog):

  def __init__(self, bot: Friday):
    self.bot: Friday = bot

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"
async def setup(bot):
  await bot.add_cog(ModLogging(bot))
  await bot.add_cog(Logging(bot))
