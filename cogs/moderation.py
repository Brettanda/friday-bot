from __future__ import annotations

import argparse
import datetime
import io
import logging
import re
import shlex
from collections import defaultdict
from typing import TYPE_CHECKING, Any, List, Optional, Set, Union

import asyncpg
import discord
from discord.ext import commands
from typing_extensions import Annotated

from functions import (MessageColors, cache, checks, embed, exceptions,
                       relay_info, time)
from functions.formats import plural

if TYPE_CHECKING:
  from reminder import Timer

  from functions.custom_contexts import GuildContext, MyContext
  from index import Friday

  class ModGuildContext(GuildContext):
    cog: Moderation
    guild_config: Config

log = logging.getLogger(__name__)

VoiceChannel = Union[discord.VoiceChannel, discord.StageChannel]


REASON_REG = re.compile(r"\[[\w\s]+.+#\d{4}\s\(ID:\s(\d{18})\)\](?:\:\s(.+))?")
PUNISHMENT_TYPES = ["delete", "kick", "ban", "mute", "timeout"]


class InvalidPunishments(exceptions.Base):
  def __init__(self, punishments: list = []):
    super().__init__(message=f"The following punishments are invalid: {', '.join(punishments)}" if len(punishments) > 0 else "One or more of the punishments you provided is invalid.")


def can_execute_action(ctx: GuildContext, user: discord.Member, target: discord.Member) -> bool:
  return user.id == ctx.bot.owner_id or user == ctx.guild.owner or user.top_role > target.top_role


class Arguments(argparse.ArgumentParser):
  def error(self, message):
    raise RuntimeError(message)


class MemberOrID(commands.Converter):
  async def convert(self, ctx: GuildContext, argument: str):
    try:
      member = await commands.MemberConverter().convert(ctx, argument)
    except commands.BadArgument:
      try:
        member_id = int(argument, base=10)
      except ValueError:
        raise commands.BadArgument(f"{argument} is not a valid member or member ID.") from None
      else:
        member = await ctx.bot.get_or_fetch_member(ctx.guild, member_id)
        if member is None:
          try:
            await commands.UserConverter().convert(ctx, argument)
          except commands.UserNotFound:
            raise commands.BadArgument(f"Could not find `{member_id}` on Discord at all.")
          return type("_HackBan", (), {"id": member_id, "__str__": lambda c: f"Member ID {c.id}"})()
    if not can_execute_action(ctx, ctx.author, member):
      raise commands.BadArgument("Your role hierarchy is too low for this action.")
    return member


class BannedMember(commands.Converter):
  async def convert(self, ctx: GuildContext, argument: str):
    if argument.isdigit():
      member_id = int(argument, base=10)
      try:
        return await ctx.guild.fetch_ban(discord.Object(id=member_id))
      except discord.NotFound:
        raise commands.BadArgument("This member has not been banned.") from None

    entity = await discord.utils.find(lambda u: u.user.mention == argument, ctx.guild.bans(limit=None))

    if entity is None:
      raise commands.BadArgument("This member has not been banned.")
    return entity


class ActionReason(commands.Converter):
  async def convert(self, ctx: GuildContext, argument: str):
    ret = f"[{ctx.author} (ID: {ctx.author.id})]: {argument}"

    if len(ret) > 512:
      reason_max = 512 - len(ret) + len(argument)
      raise commands.BadArgument(f"Reason is too long ({len(argument)}/{reason_max})")
    return ret


class CommandName(commands.Converter):
  async def convert(self, ctx: MyContext, argument: str):
    lowered = argument.lower()

    valid_commands = {
        c.qualified_name
        for c in ctx.bot.walk_commands()
        if c.cog_name and c.cog_name not in ("Dev")
    }

    if lowered not in valid_commands:
      raise commands.BadArgument(f"Command {lowered!r} does not exist.")

    return lowered


class MissingMuteRole(commands.CommandError):
  def __init__(self, message="This server does not currently have a mute role set up.", *args, **kwargs):
    self.log = False
    super().__init__(message=message, *args, **kwargs)

  def __str__(self):
    return super().__str__()


def can_mute():
  async def predicate(ctx: ModGuildContext) -> bool:
    if ctx.guild is None:
      return False

    is_owner = await ctx.bot.is_owner(ctx.author)
    if not ctx.permissions.manage_roles and not is_owner:
      return False

    # This will only be used within this cog.
    ctx.guild_config = con = await ctx.cog.get_guild_config(ctx.guild.id)
    role = con and con.mute_role
    if role is None:
      raise MissingMuteRole()

    return ctx.author.top_role > role or ctx.permissions.manage_roles or is_owner
  return commands.check(predicate)


def can_timeout():
  async def predicate(ctx: GuildContext) -> bool:
    if ctx.guild is None:
      return False

    is_owner = await ctx.bot.is_owner(ctx.author)

    return ctx.permissions.moderate_members or is_owner
  return commands.check(predicate)


class Config:
  __slots__ = ("bot", "id", "muted_members", "mute_role_id",)

  def __init__(self, *, record: asyncpg.Record, bot: Friday):
    self.bot: Friday = bot
    self.id: int = int(record["id"], base=10)
    self.muted_members: Set[int] = set(record["muted_members"] or [])
    self.mute_role_id: Optional[int] = int(record["mute_role"], base=10) if record["mute_role"] else None

  @property
  def mute_role(self) -> Optional[discord.Role]:
    if self.mute_role_id:
      guild = self.bot.get_guild(self.id)
      return guild and guild.get_role(self.mute_role_id)

  async def mute(self, member: discord.Member, reason: Optional[str]) -> None:
    if self.mute_role_id:
      await member.add_roles(discord.Object(id=self.mute_role_id), reason=reason)


class Moderation(commands.Cog):
  """Manage your server with these commands"""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot

    # voice channel id: {member, time}
    self.last_to_leave_vc: defaultdict[int, dict | Any] = defaultdict(lambda: None)

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  def cog_check(self, ctx):
    if ctx.guild is None:
      raise commands.NoPrivateMessage("This command can only be used within a guild")
    return True

  async def cog_command_error(self, ctx, error):
    if isinstance(error, commands.BadArgument):
      await ctx.send(embed=embed(title=error, color=MessageColors.ERROR))
    elif isinstance(error, commands.CommandInvokeError):
      original = error.original
      if isinstance(original, discord.Forbidden):
        await ctx.send(embed=embed(title="Bot doesn't have permission to execute this action.", color=MessageColors.ERROR))
      elif isinstance(original, discord.NotFound):
        await ctx.send(embed=embed(title=f"This entity does not exist: {original.text}", color=MessageColors.ERROR))
      elif isinstance(original, discord.HTTPException):
        await ctx.send(embed=embed(title="An unexpected error occured. Try again later?", color=MessageColors.ERROR))
    elif isinstance(error, MissingMuteRole):
      await ctx.send(embed=embed(title=error, color=MessageColors.ERROR))
    else:
      log.error(error)

  @cache.cache()
  async def get_guild_config(self, guild_id: int) -> Config:
    query = "SELECT * FROM servers WHERE id=$1 LIMIT 1;"
    async with self.bot.pool.acquire(timeout=300.0) as conn:
      record = await conn.fetchrow(query, str(guild_id))
      log.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
      if record is None:
        raise commands.CommandError("This server does not have a configuration set up. Please contact developer.")
      return Config(record=record, bot=self.bot)

  @commands.Cog.listener()
  async def on_invalidate_mod(self, guild_id: int):
    self.get_guild_config.invalidate(self, guild_id)

  @commands.Cog.listener()
  async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if after.channel or before.channel is None:
      return
    time = discord.utils.utcnow()
    self.last_to_leave_vc[before.channel.id] = {"member": member, "time": time.timestamp()}

  # @cog_ext.cog_slash(name="bot", description="Bot settings")
  # @commands.has_guild_permissions(manage_channels=True)
  # @checks.slash(user=True, private=False)
  # async def slash_settings_bot(self, ctx):
  #   print("askjdhla")

  @commands.command(name="musicchannel", help="Set the channel where I can join and play music. If none then I will join any VC", hidden=True)
  @commands.is_owner()
  @checks.is_mod_or_guild_permissions(manage_channels=True)
  async def music_channel(self, ctx: GuildContext, voicechannel: Optional[VoiceChannel] = None):
    async with ctx.typing():
      await ctx.db.execute("UPDATE servers SET musicChannel=$1 WHERE id=$2", voicechannel.id if voicechannel is not None else None, str(ctx.guild.id))
    if voicechannel is None:
      await ctx.reply(embed=embed(title="All the voice channels are my music channels 😈 (jk)"))
    else:
      await ctx.reply(embed=embed(title=f"`{voicechannel}` is now my music channel"))

  @commands.command(name="last", help="Gets the last member to leave a voice channel.")
  @commands.guild_only()
  async def last_member(self, ctx: GuildContext, *, voice_channel: Optional[VoiceChannel] = None):
    if voice_channel is None and ctx.author.voice is None:
      return await ctx.reply(embed=embed(title="You must either select a voice channel or be in one.", color=MessageColors.error()))
    voice = voice_channel or ctx.author.voice and ctx.author.voice.channel
    # if not isinstance(voice, VoiceChannel):
    #   return await ctx.reply(embed=embed(title="That is not a voice channel.", color=MessageColors.error()))
    member = voice and self.last_to_leave_vc[voice.id]
    if member is None:
      return await ctx.reply(embed=embed(title=f"No currently saved departing member of `{voice}` saved.", description="I'll catch the next one :)", color=MessageColors.error()))
    await ctx.reply(embed=embed(title=f"`{member['member']}` left `{voice}` <t:{int(member['time'])}:R>."))

  # @commands.command(name="clear",description="Deletes my messages and commands (not including the meme command)")
  # @commands.has_permissions(manage_messages = True)
  # @commands.bot_has_permissions(manage_messages = True)
  # async def clear(self,ctx: MyContextcount:int):
  #   # await ctx.channel.purge(limit=count)
  #   async for message in ctx.channel.history():
  #     if message.author == self.bot.user:
  #       print("")

  @commands.command(name="kick", extras={"examples": ["@username @someone @someoneelse", "@thisguy", "12345678910 10987654321 @someone", "@someone I just really didn't like them", "@thisguy 12345678910 They were spamming general"]})
  @commands.guild_only()
  @commands.bot_has_guild_permissions(kick_members=True)
  @checks.is_mod_or_guild_permissions(kick_members=True)
  async def norm_kick(self, ctx: GuildContext, members: commands.Greedy[discord.Member], *, reason: Annotated[Optional[str], ActionReason] = None):
    if not reason:
      reason = f"[Kicked by {ctx.author} (ID: {ctx.author.id})]"
    if len(members) == 0:
      return await ctx.send(embed=embed(title="Missing members to kick.", color=MessageColors.error()))

    failed = 0
    for member in members:
      try:
        await self.bot.get_or_fetch_member(ctx.guild, member.id)
        await ctx.guild.kick(member, reason=reason)
      except discord.HTTPException:
        failed += 1

    await ctx.send(embed=embed(title=f"Kicked {len(members) - failed}/{len(members)} members"))

  @commands.command("ban", extras={"examples": ["20m @username @someone @someoneelse Spam", "@thisguy The most spam i have ever seen", "12345678910 10987654321 @someone", "@someone They were annoying me", "40d 123456789 2 Sus"]})
  @commands.guild_only()
  @commands.bot_has_guild_permissions(ban_members=True)
  @checks.is_mod_or_guild_permissions(ban_members=True)
  async def norm_ban(self, ctx: GuildContext, duration: Optional[time.FutureTime] = None, members: Annotated[List[Union[discord.abc.Snowflake, discord.Member]], commands.Greedy[MemberOrID]] = [], *, reason: Annotated[Optional[str], ActionReason] = None):
    if reason is None:
      reason = f"[Banned by {ctx.author} (ID: {ctx.author.id})]"

    if len(members) == 0:
      return await ctx.send(embed=embed(title="Missing or failed to get members to ban.", color=MessageColors.error()))

    reminder = self.bot.reminder
    if reminder is None:
      confirm = await ctx.prompt("", embed=embed(title="Tempban functionality is not currently available.", description="Do you still want to continue with the ban?"))
      if not confirm:
        return await ctx.send(embed=embed(title="Ban cancelled.", color=MessageColors.error()))

    failed = 0
    for member in members:
      try:
        await self.bot.get_or_fetch_member(ctx.guild, member.id)
        await ctx.guild.ban(member, reason=reason)
        if reminder and duration is not None:
          zone = await reminder.get_timezone(ctx.author.id)
          await reminder.create_timer(
              duration.dt,
              "tempban",
              ctx.guild.id,
              ctx.author.id,
              member.id,
              connection=ctx.pool,
              created=ctx.message.created_at,
              timezone=zone or "UTC"
          )
      except discord.HTTPException:
        failed += 1

    if len(members) == 1:
      await ctx.send(embed=embed(title=f"Banned {members[0]}{' and retracted '+time.format_dt(duration.dt,style='R') if duration else ''}"))
    else:
      await ctx.send(embed=embed(title=f"Banned {len(members) - failed}/{len(members)} members{' and retracted '+time.format_dt(duration.dt,style='R') if duration else ''}."))

  @commands.Cog.listener()
  async def on_tempban_timer_complete(self, timer):
    guild_id, mod_id, member_id = timer.args
    await self.bot.wait_until_ready()

    guild = self.bot.get_guild(guild_id)
    if guild is None:
      return

    moderator = await self.bot.get_or_fetch_member(guild, mod_id)
    if moderator is None:
      try:
        moderator = await self.bot.fetch_user(mod_id)
      except BaseException:
        moderator = f"Mod ID {mod_id}"
      else:
        moderator = f"{moderator} (ID: {mod_id})"
    else:
      moderator = f"{moderator} (ID: {mod_id})"

    reason = f"Automatic unban from timer made on {timer.created_at} by {moderator}"
    await guild.unban(discord.Object(id=member_id), reason=reason)

  @commands.command("unban")
  @commands.guild_only()
  @commands.bot_has_guild_permissions(ban_members=True)
  @checks.is_mod_or_guild_permissions(ban_members=True)
  async def unban(self, ctx: GuildContext, member: Annotated[discord.BanEntry, BannedMember], *, reason: Annotated[Optional[str], ActionReason] = None):
    if reason is None:
      reason = f"[Unbanned by {ctx.author} (ID: {ctx.author.id})]"

    await ctx.guild.unban(member.user, reason=reason)
    if member.reason:
      reg = REASON_REG.match(member.reason)
      old_reason = member.reason if reg is None and member.reason is not None else reg[2] if reg is not None and reg[2] is not None else "No reason given"
      return await ctx.send(embed=embed(title=f"Unbanned {member.user} (ID: {member.user.id})", description=f"Previously banned for `{old_reason}`."))
    await ctx.send(embed=embed(title=f"Unbanned {member.user} (ID: {member.user.id})."))

  @commands.command("massban", extras={"examples": ["--show --no-roles --channel 707458929696702525 --contains \"n-word\"", "--reason \"people can't send embeds\" --channel 707458929696702525 --search 100 --embeds"]}, hidden=True)
  @commands.guild_only()
  @commands.bot_has_guild_permissions(ban_members=True)
  @checks.is_mod_or_guild_permissions(ban_members=True)
  @commands.is_owner()
  async def massban(self, ctx: GuildContext, *, arguments: str):
    """Mass bans multiple members from the server.

      This command has a powerful "command line" syntax. To use this command
      you and the bot must both have Ban Members permission. **Every option is optional.**

      Users are only banned **if and only if** all conditions are met.

      The following options are valid.

      `--channel` or `-c`: Channel to search for message history.
      `--reason` or `-r`: The reason for the ban.
      `--regex`: Regex that usernames must match.
      `--created`: Matches users whose accounts were created less than specified minutes ago.
      `--joined`: Matches users that joined less than specified minutes ago.
      `--joined-before`: Matches users who joined before the member ID given.
      `--joined-after`: Matches users who joined after the member ID given.
      `--no-avatar`: Matches users who have no avatar. (no arguments)
      `--no-roles`: Matches users that have no role. (no arguments)
      `--show`: Show members instead of banning them (no arguments).

      Message history filters (Requires `--channel`):

      `--contains`: A substring to search for in the message.
      `--starts`: A substring to search if the message starts with.
      `--ends`: A substring to search if the message ends with.
      `--match`: A regex to match the message content to.
      `--search`: How many messages to search. Default 100. Max 2000.
      `--after`: Messages must come after this message ID.
      `--before`: Messages must come before this message ID.
      `--files`: Checks if the message has attachments (no arguments).
      `--embeds`: Checks if the message has embeds (no arguments).
    """
    if not isinstance(ctx.author, discord.Member):  # type: ignore
      try:
        author = await ctx.guild.fetch_member(ctx.author.id)
      except discord.HTTPException:
        return await ctx.send(embed=embed(title="Discord does not seem to think you are in this server.", color=MessageColors.error()))
    else:
      author = ctx.author

    parser = Arguments(add_help=False, allow_abbrev=False)
    parser.add_argument("--channel", "-c")
    parser.add_argument("--reason", "-r")
    parser.add_argument('--search', type=int, default=100)
    parser.add_argument('--regex')
    parser.add_argument('--no-avatar', action='store_true')
    parser.add_argument('--no-roles', action='store_true')
    parser.add_argument('--created', type=int)
    parser.add_argument('--joined', type=int)
    parser.add_argument('--joined-before', type=int)
    parser.add_argument('--joined-after', type=int)
    parser.add_argument('--contains')
    parser.add_argument('--starts')
    parser.add_argument('--ends')
    parser.add_argument('--match')
    parser.add_argument('--show', action='store_true')
    parser.add_argument('--embeds', action='store_const', const=lambda m: len(m.embeds))
    parser.add_argument('--files', action='store_const', const=lambda m: len(m.attachments))
    parser.add_argument('--after', type=int)
    parser.add_argument('--before', type=int)

    try:
      args = parser.parse_args(shlex.split(arguments))
    except Exception as e:
      return await ctx.send(embed=embed(title=str(e), color=MessageColors.error()))

    members = []

    if args.channel:
      channel = await commands.TextChannelConverter().convert(ctx, args.channel)
      before = args.before and discord.Object(id=args.before)
      after = args.after and discord.Object(id=args.after)
      predicates = []
      if args.contains:
        predicates.append(lambda m: args.contains in m.content)
      if args.starts:
        predicates.append(lambda m: m.content.startswith(args.starts))
      if args.ends:
        predicates.append(lambda m: m.content.endswith(args.ends))
      if args.match:
        try:
          _match = re.compile(args.match)
        except re.error as e:
          return await ctx.send(embed=embed(title=f"Invalid regex passed to `--match`: {e}", color=MessageColors.error()))
        else:
          predicates.append(lambda m, x=_match: x.match(m.content))
      if args.embeds:
        predicates.append(args.embeds)
      if args.files:
        predicates.append(args.files)

      async for message in channel.history(limit=min(max(1, args.search), 2000), before=before, after=after):
        if all(p(message) for p in predicates):
          members.append(message.author)

    else:
      if ctx.guild.chunked:
        members = ctx.guild.members
      else:
        async with ctx.typing():
          await ctx.guild.chunk(cache=True)
        members = ctx.guild.members

    # member predicates
    predicates = [
        lambda m: isinstance(m, discord.Member) and can_execute_action(ctx, author, m),  # Only if applicable
        lambda m: not m.bot,  # No bots
        lambda m: m.discriminator != "0000",  # No deleted accounts
    ]

    convertor = commands.MemberConverter()

    if args.regex:
      try:
        _regex = re.compile(args.regex)
      except re.error as e:
        return await ctx.send(embed=embed(title=f"Invalid regex passed to `--regex`: {e}", color=MessageColors.error()))
      else:
        predicates.append(lambda m, x=_regex: x.match(m.name))

    if args.no_avatar:
      predicates.append(lambda m: m.avatar is None)
    if args.no_roles:
      predicates.append(lambda m: len(getattr(m, "roles", [])) <= 1)

    now = discord.utils.utcnow()
    if args.created:
      def created(member, *, offset=now - datetime.timedelta(minutes=args.created)):
        return member.created_at > offset
      predicates.append(created)
    if args.joined:
      def joined(member, *, offset=now - datetime.timedelta(minutes=args.joined)):
        if isinstance(member, discord.User):
          # If the member is a user then they left already
          return True
        return member.joined_at and member.joined_at > offset
      predicates.append(joined)
    if args.joined_after:
      _joined_after_member = await convertor.convert(ctx, str(args.joined_after))

      def joined_after(member, *, _other=_joined_after_member):
        return member.joined_at and _other.joined_at and member.joined_at > _other.joined_at
      predicates.append(joined_after)
    if args.joined_before:
      _joined_before_member = await convertor.convert(ctx, str(args.joined_before))

      def joined_before(member, *, _other=_joined_before_member):
        return member.joined_at and _other.joined_at and member.joined_at < _other.joined_at
      predicates.append(joined_before)

    members = {m for m in members if all(p(m) for p in predicates)}
    if len(members) == 0:
      return await ctx.send(embed=embed(title="No members found matching your criteria.", color=MessageColors.error()))

    if args.show:
      members = sorted(members, key=lambda m: m.joined_at or now)
      fmt = "\n".join(f"{m.id}\tJoined: {m.joined_at}\tCreated: {m.created_at}\t{m}" for m in members)
      content = f"Current Time: {discord.utils.utcnow()}\tTotal members: {len(members)}\n{fmt}"
      file = discord.File(io.BytesIO(content.encode("utf-8")), filename="members.txt")
      return await ctx.send(file=file)

    if args.reason is None:
      return await ctx.send(embed=embed(title="--reason flag is required.", color=MessageColors.error()))
    else:
      reason = await ActionReason().convert(ctx, args.reason)

    confirm = await ctx.prompt(f"This will ban **{plural(len(members)):member}**. Are you sure you want to continue?")
    if not confirm:
      return await ctx.send(embed=embed(title="Aborted."))

    count = 0
    for member in members:
      try:
        await ctx.guild.ban(member, reason=reason)
      except discord.HTTPException:
        pass
      else:
        count += 1

    await ctx.send(embed=embed(title=f"Banned {count}/{len(members)}."))

  @commands.command(name="rolecall", aliases=["rc"], extras={"examples": ["@mods vc-1", "123456798910 vc-2 vc-1 10987654321", "@admins general @username @username"]}, help="Moves everyone with a specific role to a voicechannel. Objects that can be exluded are voicechannels,roles,and members")
  @commands.guild_only()
  @checks.is_mod_or_guild_permissions(move_members=True)
  @commands.bot_has_guild_permissions(move_members=True)
  async def norm_rolecall(self, ctx: GuildContext, role: discord.Role, voicechannel: Optional[VoiceChannel], exclusions: commands.Greedy[Union[discord.Role, VoiceChannel]] = None):
    voice = voicechannel or ctx.author.voice and ctx.author.voice.channel
    if not voice:
      return await ctx.send(embed=embed(title="You must provide or be in a voice channel to use this command.", color=MessageColors.error()))
    if voice.permissions_for(ctx.author).view_channel is not True:
      return await ctx.send(embed=embed(title="Trying to connect to a channel you can't view 🤔", description="Im going to have to stop you right there", color=MessageColors.error()))
    if voice.permissions_for(ctx.author).connect is not True:
      return await ctx.send(embed=embed(title=f"You don't have permission to connect to `{voice}` so I can't complete this command", color=MessageColors.error()))

    moved = 0
    for member in role.members:
      if (exclusions is None or (exclusions is not None and member not in exclusions)) and member not in voice.members:
        try:
          await member.move_to(voice, reason=f"Role call command by {ctx.author}")
          moved += 1
        except BaseException:
          pass

    return await ctx.send(embed=embed(title=f"Moved {moved} members with the role `{role}` to `{voice}`"))

  @commands.command(name="massmove", aliases=["move"], extras={"examples": ["general", "vc-2 general", "'long voice channel' general"]}, help="Move everyone from one voice channel to another")
  @commands.guild_only()
  @checks.is_mod_or_guild_permissions(move_members=True)
  @commands.bot_has_guild_permissions(move_members=True)
  async def norm_massmove(self, ctx: GuildContext, to_channel: VoiceChannel = None, from_channel: Optional[VoiceChannel] = None):
    # if (from_channel is not None and not isinstance(from_channel, VoiceChannel)) or (to_channel is not None and not isinstance(to_channel, VoiceChannel)):
    #   return await ctx.send(embed=embed(title="Please only select voice channels for moving", color=MessageColors.error()))

    if from_channel is None and ctx.author.voice is not None and ctx.author.voice.channel is not None and ctx.author.voice.channel == to_channel:
      return await ctx.send(embed=embed(title="Please select a voice channel different from the one you are already in to move to", color=MessageColors.error()))

    if to_channel and to_channel.permissions_for(ctx.author).view_channel is not True:
      return await ctx.send(embed=embed(title="Trying to connect to a channel you can't view 🤔", description="Im going to have to stop you right there", color=MessageColors.error()))

    if to_channel and to_channel.permissions_for(ctx.author).connect is not True:
      return await ctx.send(embed=embed(title=f"You don't have permission to connect to `{to_channel}` so I can't complete this command", color=MessageColors.error()))

    if from_channel is None:
      from_channel = ctx.author.voice and ctx.author.voice.channel
    if from_channel is None:
      return await ctx.send(embed=embed(title="To move users from one channel to another, you need to be connected to one or specify the channel to send from.", color=MessageColors.error()))

    memberCount = len(from_channel.members)

    failed = 0

    for member in from_channel.members:
      try:
        await member.move_to(to_channel, reason=f"Mass move called by {ctx.author} (ID: {ctx.author.id})")
      except discord.HTTPException:
        failed += 1

    if ctx.guild.me and to_channel and ctx.guild.me in to_channel.members:
      if to_channel.type == discord.ChannelType.stage_voice:
        await ctx.guild.me.edit(suppress=False)

    return await ctx.send(embed=embed(title=f"Successfully moved {memberCount - failed}/{plural(memberCount):member}"))

  @commands.command(name="lock", help="Sets your voice channels user limit to the current number of occupants", hidden=True)
  @commands.guild_only()
  @checks.is_mod_or_guild_permissions(manage_channels=True)
  @commands.bot_has_guild_permissions(manage_channels=True)
  async def norm_lock(self, ctx: GuildContext, *, voicechannel: Optional[VoiceChannel] = None):
    voice = voicechannel or ctx.author.voice and ctx.author.voice.channel
    if voice is None:
      return await ctx.send(embed=embed(title="You either need to specify a voicechannel or be connected to one", color=MessageColors.error()))
    if voice.user_limit > 0:
      await voice.edit(user_limit=0)  # type: ignore
      return await ctx.send(embed=embed(title=f"Unlocked `{voice}`"))
    else:
      await voice.edit(user_limit=len(voice.members))  # type: ignore
      return await ctx.send(embed=embed(title=f"Locked `{voice}`"))

  @commands.command(name="begone", extras={"examples": ["https://discord.com/channels/707441352367013899/707458929696702525/707520808448294983", "707520808448294983"]}, help="Delete unwanted message that I send")
  @commands.bot_has_permissions(manage_messages=True)
  async def begone(self, ctx: GuildContext, message: Optional[discord.Message] = None):
    if message is not None and ctx.message.reference is not None:
      raise commands.TooManyArguments("Please only either reply to the problemed message or add it to the end of this message not both")

    msg: Optional[discord.Message] = message if message is not None else ctx.message.reference.resolved if ctx.message.reference is not None else None  # type: ignore
    if msg is None:
      raise commands.CommandError("Please either reply to the message with this command or add the message to the end of this command")

    if msg.author != ctx.guild.me:
      raise commands.CommandError("I will not delete messages that I didn't author with this command")
    reference = await ctx.channel.fetch_message(msg.reference.message_id)  # type: ignore
    if reference.author != ctx.author:
      raise commands.CommandError("You are not the author of that message, I will only 'begone' messages that referenced a message authored by you")

    await relay_info(
            f"**Begone**\nUSER: {reference.clean_content}\nME: {msg.clean_content}```{msg}```",
            self.bot,
    )
    await msg.delete()
    await ctx.reply(embed=embed(title="Message has been removed"), delete_after=10)
    await ctx.message.delete(delay=10)

  @commands.command(name="timeout", extras={"examples": ["20m @Motostar @steve they were annoying me", "1week @steve 9876543210", "5d @Motostar spamming general", "0123456789"]}, help="Timeout a member from chating, replying, reacting, and joining voice channels.")
  @commands.guild_only()
  @can_timeout()
  @checks.is_mod_or_guild_permissions(moderate_members=True)
  @commands.bot_has_guild_permissions(moderate_members=True)
  async def timeout(self, ctx: MyContext, duration: time.TimeoutTime, members: commands.Greedy[discord.Member], *, reason: Annotated[Optional[str], ActionReason] = None):
    if reason is None:
      reason = f"[Timed out by {ctx.author} (ID: {ctx.author.id})]"

    failed = 0
    async with ctx.typing():
      for member in members:
        try:
          await member.timeout(duration.dt, reason=reason)
        except discord.HTTPException:
          failed += 1

    if len(members) == 1:
      await ctx.send(embed=embed(title=f"Timed out {members[0]}{' and retracted '+time.format_dt(duration.dt,style='R') if duration else ''}"))
    else:
      await ctx.send(embed=embed(title=f"Timed out {len(members) - failed}/{len(members)} members{' and retracted '+time.format_dt(duration.dt,style='R') if duration else ''}."))

  @commands.command(name="untimeout", aliases=["removetimeout"], extras={"examples": ["@Motostar @steve they said sorry", "@steve 9876543210", "@Motostar", "0123456789"]}, help="Remove the timeout of a member")
  @commands.guild_only()
  @can_timeout()
  @checks.is_mod_or_guild_permissions(moderate_members=True)
  @commands.bot_has_guild_permissions(moderate_members=True)
  async def norm_untimeout(self, ctx: MyContext, members: commands.Greedy[discord.Member], *, reason: Annotated[Optional[str], ActionReason] = None):
    if reason is None:
      reason = f"[Timeout removed by {ctx.author} (ID: {ctx.author.id})]"

    failed = 0
    async with ctx.typing():
      for member in members:
        try:
          await member.timeout(None, reason=reason)
        except discord.HTTPException:
          failed += 1
    if len(members) == 1:
      await ctx.send(embed=embed(title=f"Removed timeout for {members[0]}"))
    else:
      await ctx.send(embed=embed(title=f"Removed timeout for {len(members) - failed}/{len(members)} members."))

  @commands.command(extras={"examples": ["20m", "1h20m", "5h"]}, help="Temporarily timeout yourself for the specified duration, min 5 minutes, max 24 hours")
  @commands.guild_only()
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def selftimeout(self, ctx: GuildContext, *, duration: time.ShortTime):
    created_at = ctx.message.created_at
    if duration.dt > (created_at + datetime.timedelta(days=1)):
      return await ctx.send(embed=embed(title="Duration is too long. Must be at most 24 hours.", color=MessageColors.error()))

    if duration.dt < (created_at + datetime.timedelta(minutes=5)):
      return await ctx.send(embed=embed(title="Duration is too short. Must be at least 5 minutes.", color=MessageColors.error()))

    confirm = await ctx.prompt("", embed=embed(title=f"Are you sure you want to self-timeout, and retracted {time.format_dt(duration.dt, style='R')}?", description="Do not ask the moderators to undo this!"))
    if not confirm:
      return await ctx.send(embed=embed(title="Cancelled.", color=MessageColors.error()))

    await ctx.author.edit(timed_out_until=duration.dt, reason=f"Self-timeout for {ctx.author} (ID: {ctx.author.id}) for {time.human_timedelta(duration.dt, source=created_at)}")
    await ctx.send(embed=embed(title=f"Timed out, and retracted {time.format_dt(duration.dt, style='R')}. Be sure not to bother anyone about it."))

  @selftimeout.error
  async def on_selftimeout_error(self, ctx: MyContext, error: Exception):
    if isinstance(error, commands.MissingRequiredArgument):
      await ctx.send(embed=embed(title="Missing duration.", color=MessageColors.error()))

  @commands.group(name="mute", extras={"examples": ["20m @Motostar @steve they were annoying me", "@steve 9876543210", "30d @Motostar spamming general", "0123456789"]}, help="Mute a member from text channels", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @can_mute()
  @checks.is_mod_or_guild_permissions(manage_roles=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def norm_mute(self, ctx: ModGuildContext, duration: Optional[time.FutureTime], members: commands.Greedy[discord.Member], *, reason: Annotated[Optional[str], ActionReason] = None):
    if reason is None:
      reason = f"[Muted by {ctx.author} (ID: {ctx.author.id})]"

    reminder = self.bot.reminder
    if reminder is None:
      confirm = await ctx.prompt("", embed=embed(title="Tempmute functionality is not currently available.", description="Do you still want to continue with the mute?"))
      if not confirm:
        return await ctx.send(embed=embed(title="Mute cancelled.", color=MessageColors.error()))

    if len(members) == 0:
      return await ctx.send(embed=embed(title="Missing members to mute.", color=MessageColors.error()))

    role = discord.Object(id=ctx.guild_config.mute_role_id)  # type: ignore
    failed = 0
    async with ctx.typing():
      for member in members:
        try:
          await member.add_roles(role, reason=reason)
          if duration is not None and reminder:
            zone = await reminder.get_timezone(ctx.author.id)
            await reminder.create_timer(
                duration.dt,
                "tempmute",
                ctx.guild.id,
                ctx.author.id,
                member.id,
                role.id,
                created=ctx.message.created_at,
                timezone=zone or "UTC"
            )
        except discord.HTTPException:
          failed += 1

    if len(members) == 1:
      await ctx.send(embed=embed(title=f"Muted {members[0]}{' and retracted '+time.format_dt(duration.dt,style='R') if duration else ''}"))
    else:
      await ctx.send(embed=embed(title=f"Muted {len(members) - failed}/{len(members)} members{' and retracted '+time.format_dt(duration.dt,style='R') if duration else ''}."))

  @commands.Cog.listener()
  async def on_tempmute_timer_complete(self, timer: Timer):
    guild_id, mod_id, member_id, role_id = timer.args
    await self.bot.wait_until_ready()

    guild = self.bot.get_guild(guild_id)
    if guild is None:
      return

    member = await self.bot.get_or_fetch_member(guild, member_id)
    if member is None or not member._roles.has(role_id):
      await self.bot.pool.execute("UPDATE servers SET muted_members=array_remove(muted_members, $1) WHERE id=$2", str(member_id), str(guild_id))
      return

    if mod_id != member_id:
      moderator = await self.bot.get_or_fetch_member(guild, mod_id)
      if moderator is None:
        try:
          moderator = await self.bot.fetch_user(mod_id)
        except BaseException:
          moderator = f"Mod ID {mod_id}"
        else:
          moderator = f"{moderator} (ID: {mod_id})"
      else:
        moderator = f"{moderator} (ID: {mod_id})"

      reason = f"Automatic unmute from timer mode on {timer.created_at} by {moderator}"
    else:
      reason = f"Expiring self-mute made on {timer.created_at} by {member}"

    try:
      await member.remove_roles(discord.Object(id=role_id), reason=reason)
    except discord.HTTPException:
      await self.bot.pool.execute("UPDATE servers SET muted_members=array_remove(muted_members, $1) WHERE id=$2", str(member_id), str(guild_id))

  @norm_mute.group("role", help="Set the role to be applied to members that get muted", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @checks.is_mod_or_guild_permissions(manage_roles=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  @commands.cooldown(1, 60.0, commands.BucketType.guild)
  async def mute_role(self, ctx: GuildContext, *, role: discord.Role):
    if role.is_default():
      return await ctx.send(embed=embed(title="Cannot use the @\u200beveryone role.", color=MessageColors.error()))

    if role > ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
      return await ctx.send(embed=embed(title='This role is higher than your highest role.', color=MessageColors.error()))

    if role > ctx.me.top_role:
      return await ctx.send(embed=embed(title='This role is higher than my highest role.', color=MessageColors.error()))

    await self.bot.pool.execute("UPDATE servers SET mute_role=$1 WHERE id=$2", str(role.id) if role is not None else None, str(ctx.guild.id))
    if role is not None:
      return await ctx.send(embed=embed(title=f"Friday will now use `{role}` as the new mute role"))
    await ctx.send(embed=embed(title="The saved mute role has been removed"))

  @mute_role.command(name="update", help="Updates every channel with the mute role overwrites")
  @commands.guild_only()
  @checks.is_mod_or_guild_permissions(manage_roles=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  @commands.cooldown(1, 60.0, commands.BucketType.guild)
  async def mute_role_update(self, ctx: GuildContext):
    con = await self.get_guild_config(ctx.guild.id)
    if con.mute_role is None:
      ctx.command.reset_cooldown(ctx)
      return await ctx.send(embed=embed(title=f"The mute role is not set, please set it with `{ctx.prefix}mute role`", color=MessageColors.error()))

    role = con.mute_role
    async with ctx.typing():
      success, failed, skipped = 0, 0, 0
      for channel in ctx.guild.channels:
        perms = channel.permissions_for(ctx.guild.me)
        if perms.manage_roles:
          try:
            await channel.set_permissions(role, send_messages=False, send_messages_in_threads=False, create_public_threads=False, create_private_threads=False, speak=False, add_reactions=False, reason=f"Mute role overwrites by {ctx.author} (ID: {ctx.author.id})")
          except discord.HTTPException:
            failed += 1
          else:
            success += 1
        else:
          skipped += 1
      await ctx.send(embed=embed(title="Mute role successfully updated", description=f"Overwrites:\nUpdated: {success}, Failed: {failed}, Skipped: {skipped}"))

  @mute_role.command("create", help="Don't have a muted role? Let Friday create a basic one for you.")
  @commands.guild_only()
  @checks.is_mod_or_guild_permissions(manage_roles=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  @commands.cooldown(1, 60.0, commands.BucketType.guild)
  async def mute_role_create(self, ctx: GuildContext, *, name: str = "Muted"):
    con = await self.get_guild_config(ctx.guild.id)
    if con.mute_role is not None:
      ctx.command.reset_cooldown(ctx)
      return await ctx.send(embed=embed(title="This server already has a mute role.", color=MessageColors.error()))

    try:
      role = await ctx.guild.create_role(name=name, reason=f"Mute Role created by {ctx.author} (ID: {ctx.author.id})")
    except discord.HTTPException as e:
      ctx.command.reset_cooldown(ctx)
      return await ctx.send(embed=embed(title="An error occurred", description=str(e), color=MessageColors.error()))

    await self.bot.pool.execute("UPDATE servers SET mute_role=$1 WHERE id=$2", str(role.id), str(ctx.guild.id))

    confirm = await ctx.prompt("Would you like to update the channel overwrites")
    if not confirm:
      return await ctx.send(embed=embed(title="Mute role successfully created."))

    async with ctx.typing():
      success, failed, skipped = 0, 0, 0
      for channel in ctx.guild.channels:
        perms = channel.permissions_for(ctx.guild.me)
        if perms.manage_roles:
          try:
            await channel.set_permissions(role, send_messages=False, send_messages_in_threads=False, create_public_threads=False, create_private_threads=False, speak=False, add_reactions=False, reason=f"Mute role overwrites by {ctx.author} (ID: {ctx.author.id})")
          except discord.HTTPException:
            failed += 1
          else:
            success += 1
        else:
          skipped += 1
      await ctx.send(embed=embed(title="Mute role successfully created.", description=f"Overwrites:\nUpdated: {success}, Failed: {failed}, Skipped: {skipped}"))

  @commands.command(name="unmute", extras={"examples": ["@Motostar @steve they said sorry", "@steve 9876543210", "@Motostar", "0123456789"]}, help="Unmute a member from text channels")
  @commands.guild_only()
  @can_mute()
  @checks.is_mod_or_guild_permissions(manage_roles=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def norm_unmute(self, ctx: ModGuildContext, members: commands.Greedy[discord.Member], *, reason: Annotated[Optional[str], ActionReason] = None):
    if reason is None:
      reason = f"[Unmuted by {ctx.author} (ID: {ctx.author.id})]"

    assert ctx.guild_config.mute_role_id is not None
    role = discord.Object(id=ctx.guild_config.mute_role_id)
    if len(members) == 0:
      return await ctx.send(embed=embed(title="Missing members to unmute.", color=MessageColors.error()))

    failed = 0
    async with ctx.typing():
      for member in members:
        try:
          await member.remove_roles(role, reason=reason)
        except discord.HTTPException:
          failed += 1
    if len(members) == 1:
      await ctx.send(embed=embed(title=f"Unmuted {members[0]}"))
    else:
      await ctx.send(embed=embed(title=f"Unmuted {len(members) - failed}/{len(members)} members."))

  @commands.command(extras={"examples": ["20m", "1h20m", "5h"]}, help="Temporarily mutes yourself for the specified duration, min 5 minutes, max 24 hours")
  @commands.guild_only()
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def selfmute(self, ctx: GuildContext, *, duration: time.ShortTime):
    reminder = self.bot.reminder
    if reminder is None:
      return await ctx.send(embed=embed(title="Sorry, this funcitonality is not available.", color=MessageColors.error()))

    con = await self.get_guild_config(ctx.guild.id)
    role_id = con and con.mute_role_id
    if role_id is None:
      raise MissingMuteRole()

    if ctx.author._roles.has(role_id):
      return await ctx.send(embed=embed(title="You are already muted. 🤔🤔", color=MessageColors.error()))

    created_at = ctx.message.created_at
    if duration.dt > (created_at + datetime.timedelta(days=1)):
      return await ctx.send(embed=embed(title="Duration is too long. Must be at most 24 hours.", color=MessageColors.error()))

    if duration.dt < (created_at + datetime.timedelta(minutes=5)):
      return await ctx.send(embed=embed(title="Duration is too short. Must be at least 5 minutes.", color=MessageColors.error()))
    confirm = await ctx.prompt("", embed=embed(title=f"Are you sure you want to self-mute, and retracted {time.format_dt(duration.dt, style='R')}?", description="Do not ask the moderators to undo this!"))
    if not confirm:
      return await ctx.send(embed=embed(title="Cancelled.", color=MessageColors.error()))

    await ctx.author.add_roles(discord.Object(id=role_id), reason=f"Self-mute for {ctx.author} (ID: {ctx.author.id}) for {time.human_timedelta(duration.dt, source=created_at)}")
    await reminder.create_timer(duration.dt, "tempmute", ctx.guild.id, ctx.author.id, ctx.author.id, role_id, created=created_at)
    await ctx.author.edit(timed_out_until=duration.dt, reason=f"Self-mute for {ctx.author} (ID: {ctx.author.id}) for {time.human_timedelta(duration.dt, source=created_at)}")
    await ctx.send(embed=embed(title=f"Muted, and retracted {time.format_dt(duration.dt, style='R')}. Be sure not to bother anyone about it."))

  @selfmute.error
  async def on_selfmute_error(self, ctx: MyContext, error: commands.CommandError):
    if isinstance(error, commands.MissingRequiredArgument):
      await ctx.send(embed=embed(title="Missing duration.", color=MessageColors.error()))

  @music_channel.after_invoke
  @mute_role.after_invoke
  @mute_role_create.after_invoke
  async def settings_after_invoke(self, ctx: MyContext):
    if not ctx.guild:
      return

    self.bot.dispatch("invalidate_mod", ctx.guild.id)


async def setup(bot: Friday):
  await bot.add_cog(Moderation(bot))
