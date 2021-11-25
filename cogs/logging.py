import re
import datetime
import discord
from discord.ext import commands

from functions import embed, cache, MessageColors, MyContext

from typing import Optional, Literal, Union
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot

EVENT_TYPES = ["bans", "mutes", "unbans", "unmutes", "kicks"]
REASON_REG = re.compile(r"\[[\w\s]+.+#\d{4}\s\(ID:\s(\d{18})\)\](?:\:\s(.+))?")


class Config:
  __slots__ = ("bot", "id", "mod_log_channel_id", "mod_log_events", "mute_role_id", )

  @classmethod
  def from_record(cls, record, bot):
    self = cls()

    self.bot: "Bot" = bot
    self.id: int = record["id"]
    self.mute_role_id = int(record["mute_role"], base=10) if record["mute_role"] else None
    self.mod_log_events = set(record["mod_log_events"] or [])
    self.mod_log_channel_id: int = int(record["mod_log_channel"], base=10) if record["mod_log_channel"] else None
    return self

  @property
  def mod_log_channel(self) -> Optional[discord.TextChannel]:
    return self.bot.get_channel(self.mod_log_channel_id)

  @property
  def mute_role(self):
    guild = self.bot.get_guild(self.id)
    return guild and self.mute_role_id and guild.get_role(self.mute_role_id)


class Logging(commands.Cog):
  """Different from the log cog b/c this one deals with discord logging not bot logging"""

  def __init__(self, bot: "Bot"):
    self.bot = bot

  def __repr__(self) -> str:
    return "<cogs.Logging>"

  @cache.cache()
  async def get_guild_config(self, guild_id: int) -> Optional[Config]:
    query = "SELECT * FROM servers WHERE id=$1 LIMIT 1"
    async with self.bot.db.pool.acquire(timeout=300.0) as conn:
      record = await conn.fetchrow(query, str(guild_id))
      if not record:
        return None
      return Config.from_record(record, self.bot)

  @commands.Cog.listener()
  async def on_invalidate_mod(self, guild_id: int):
    self.get_guild_config.invalidate(self, guild_id)

  @commands.Cog.listener()
  async def on_log_event(self, guild_id: int, event: Literal["ban", "mute", "unban", "unmute", "kick"], *, offender: Union[discord.User, discord.Member], moderator: Union[discord.User, discord.Member], reason: str = "No reason given"):
    config = await self.get_guild_config(guild_id)
    if not config:
      return

    if config.mod_log_channel is None:
      return

    await config.mod_log_channel.send(embed=embed(
        title=event.capitalize(),
        description=f"**Offender:** {offender.mention} (ID: {offender.id})\n**Reason:** {reason}\n**Moderator responsible:** {moderator.mention} (ID: {moderator.id})",
        color=MessageColors.LOGGING,
        timestamp=discord.utils.utcnow()))

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

    if "mutes" not in config.mod_log_events and "unmutes" not in config.mod_log_events:
      return

    before_has = before._roles.has(config.mute_role_id)
    after_has = after._roles.has(config.mute_role_id)

    if before_has == after_has:
      return

    audit = await after.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update, user=before.guild.me, oldest_first=False).flatten()
    if len(audit) == 0 or len([i for i in audit if i.target.id == before.id]) == 0:
      return

    action: discord.AuditLogEntry = audit[0]
    reg = REASON_REG.match(action.reason)
    reason = action.reason if reg is None and action.reason is not None else reg[2] if reg is not None and reg[2] is not None else "No reason given"

    if after_has and "mutes" in config.mod_log_events:
      self.bot.dispatch("log_event", before.guild.id, "mute", offender=before, moderator=action.user, reason=reason)
    elif "unmutes" in config.mod_log_events:
      self.bot.dispatch("log_event", before.guild.id, "unmute", offender=before, moderator=action.user, reason=reason)

  @commands.Cog.listener()
  async def on_member_ban(self, guild: discord.Guild, member: Union[discord.User, discord.Member]):
    config = await self.get_guild_config(guild.id)
    if not config:
      return

    if config.mod_log_channel is None:
      return

    if "bans" not in config.mod_log_events:
      return

    audit = await guild.audit_logs(limit=5, action=discord.AuditLogAction.ban, user=guild.me, oldest_first=False).flatten()
    if len(audit) == 0 or len([i for i in audit if i.target.id == member.id]) == 0:
      return

    action: discord.AuditLogEntry = audit[0]
    reg = REASON_REG.match(member.reason)
    reason = member.reason if reg is None and member.reason is not None else reg[2] if reg is not None and reg[2] is not None else "No reason given"

    self.bot.dispatch("log_event", guild.id, "ban", offender=member, moderator=action.user, reason=reason)

  @commands.Cog.listener()
  async def on_member_unban(self, guild: discord.Guild, member: Union[discord.User, discord.Member]):
    config = await self.get_guild_config(guild.id)
    if not config:
      return

    if config.mod_log_channel is None:
      return

    if "unbans" not in config.mod_log_events:
      return

    audit = await guild.audit_logs(limit=5, action=discord.AuditLogAction.unban, user=guild.me, oldest_first=False).flatten()
    if len(audit) == 0 or len([i for i in audit if i.target.id == member.id]) == 0:
      return

    action: discord.AuditLogEntry = audit[0]
    reg = REASON_REG.match(member.reason)
    reason = member.reason if reg is None and member.reason is not None else reg[2] if reg is not None and reg[2] is not None else "No reason given"

    self.bot.dispatch("log_event", guild.id, "unban", offender=member, moderator=action.user, reason=reason)

  @commands.Cog.listener()
  async def on_member_remove(self, member: discord.Member):
    config = await self.get_guild_config(member.guild.id)
    if not config:
      return

    if config.mod_log_channel is None:
      return

    if "kicks" not in config.mod_log_events:
      return

    after = discord.utils.utcnow() - datetime.timedelta(seconds=5)

    audit = await member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick, after=after).flatten()
    if len(audit) == 0 or len([i for i in audit if i.target.id == member.id and i.created_at > after]) == 0:
      return

    action: discord.AuditLogEntry = audit[0]
    reason = "No reason given"
    if hasattr(member, "reason") and member.reason is not None:
      reg = REASON_REG.match(member.reason)
      reason = member.reason if reg is None and member.reason is not None else reg[2] if reg is not None and reg[2] is not None else "No reason given"

    self.bot.dispatch("log_event", member.guild.id, "kick", offender=action.target, moderator=action.user, reason=reason)

  @commands.group(name="modlog", aliases=["modlogs"], help="Set the channel where I can log moderation actions. This will log moderation action done by Friday, Fridays commands, and other moderation action logged by Discord.", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @commands.has_guild_permissions(administrator=True)
  @commands.bot_has_guild_permissions(view_audit_log=True)
  async def mod_log(self, ctx: "MyContext", *, channel: Optional[discord.TextChannel] = None):
    if channel is not None:
      perms = channel.permissions_for(ctx.guild.me)
      if not perms.send_messages or not perms.embed_links:
        return await ctx.send(embed=embed(title=f"I need the `Send Messages` and `Embed Links` permissions in `{channel}` to send logs in that channel.", color=MessageColors.ERROR))
    channel_id = str(channel.id) if channel else None
    await self.bot.db.query("UPDATE servers SET mod_log_channel=$1 WHERE id=$2", channel_id, str(ctx.guild.id))
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.send(embed=embed(title=f"Mod log channel has been set to `{channel}`"))

  @mod_log.command(name="events", extras={"examples": [*EVENT_TYPES, "bans mutes kicks unbans unmutes", "bans unbans"], "params": EVENT_TYPES}, help="The events that will be logged in the mod log channel")
  @commands.guild_only()
  @commands.has_guild_permissions(administrator=True)
  @commands.bot_has_guild_permissions(view_audit_log=True)
  async def mod_log_events(self, ctx: "MyContext", events: commands.Greedy[Literal["bans", "mutes", "unbans", "unmutes", "kicks"]]):
    if not events:
      return await ctx.send(embed=embed(title="No events specified", description="You must specify at least one event to log.", color=MessageColors.ERROR))

    await self.bot.db.query("UPDATE servers SET mod_log_events=$1 WHERE id=$2", events, str(ctx.guild.id))
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.send(embed=embed(title=f"Mod log events have been set to `{', '.join(events)}`"))

  @mod_log_events.error
  async def mod_log_events_error(self, ctx: "MyContext", error: Exception):
    if isinstance(error, commands.BadLiteralArgument):
      return await ctx.send(embed=embed(title="Invalid event(s)", description=f"You must specify one of the following events: {', '.join(EVENT_TYPES)}.", color=MessageColors.ERROR))


def setup(bot):
  bot.add_cog(Logging(bot))
