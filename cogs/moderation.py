import datetime
import asyncio
import re
from collections import defaultdict
from typing import Optional, Union

import discord
# import validators
import pycountry
from discord.ext import commands
from typing_extensions import TYPE_CHECKING

from functions import (MessageColors, MyContext, embed,
                       relay_info, time)

if TYPE_CHECKING:
  from index import Friday as Bot


REASON_REG = re.compile(r"\[[\w\s]+.+#\d{4}\s\(ID:\s(\d{18})\)\](?:\:\s(.+))?")


def can_execute_action(ctx: "MyContext", user: Union[discord.User, discord.Member], target: Union[discord.User, discord.Member]) -> bool:
  return user.id == ctx.bot.owner_id or user == ctx.guild.owner or user.id == ctx.guild.owner_id or user.top_role > target.top_role


class MemberOrID(commands.Converter):
  async def convert(self, ctx: "MyContext", argument):
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
          return type("_HackBan", (), {"id": member_id, "__str__": lambda c: f"Member ID {c.id}"})()
    if not can_execute_action(ctx, ctx.author, member):
      raise commands.BadArgument("Your role hierarchy is too low for this action.")
    return member


class BannedMember(commands.Converter):
  async def convert(self, ctx, argument):
    if argument.isdigit():
      member_id = int(argument, base=10)
      try:
        return await ctx.guild.fetch_ban(discord.Object(id=member_id))
      except discord.NotFound:
        raise commands.BadArgument("This member has not been banned.") from None

    ban_list = await ctx.guild.bans()
    entity = discord.utils.find(lambda u: str(u.user) == argument, ban_list)

    if entity is None:
      raise commands.BadArgument("This member has not been banned.")
    return entity


class ActionReason(commands.Converter):
  async def convert(self, ctx, argument):
    ret = f"[{ctx.author} (ID: {ctx.author.id})]: {argument}"

    if len(ret) > 512:
      reason_max = 512 - len(ret) + len(argument)
      raise commands.BadArgument(f"Reason is too long ({len(argument)}/{reason_max})")
    return ret


class MissingMuteRole(commands.CommandError):
  def __init__(self, message="This server does not currently have a mute role set up.", *args, **kwargs):
    self.log = False
    super().__init__(message=message, *args, **kwargs)

  def __str__(self):
    return super().__str__()


def can_mute():
  async def predicate(ctx: "MyContext") -> bool:
    if ctx.guild is None:
      return False

    is_owner = await ctx.bot.is_owner(ctx.author)
    if not ctx.author.guild_permissions.manage_roles and not is_owner:
      return False

    ctx.guild_config = config = await ctx.cog.get_guild_config(ctx.guild.id)
    role = config and config.mute_role
    if role is None:
      raise MissingMuteRole()

    return ctx.author.top_role > role or ctx.author.guild_permissions.manage_roles or is_owner
  return commands.check(predicate)


def can_timeout():
  async def predicate(ctx: "MyContext") -> bool:
    if ctx.guild is None:
      return False

    is_owner = await ctx.bot.is_owner(ctx.author)

    return ctx.author.guild_permissions.moderate_members or is_owner
  return commands.check(predicate)


class Moderation(commands.Cog):
  """Manage your server with these commands"""

  def __init__(self, bot: "Bot"):
    self.bot = bot

    # voice channel id: {member, time}
    self.last_to_leave_vc = defaultdict(lambda: None)

  def __repr__(self):
    return "<cogs.Moderation>"

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
      self.bot.logger.error(error)

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

  @commands.command(name="chatchannel", help="Set the current channel so that I will always try to respond with something")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def norm_chatchannel(self, ctx):
    chat_channel = await self.bot.db.query("SELECT chatchannel FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    chat = self.bot.get_cog("Chat")
    if chat is not None:
      chat.get_guild_config.invalidate(chat, ctx.guild.id)
    if chat_channel is None:
      await self.bot.db.query("UPDATE servers SET chatchannel=$1 WHERE id=$2", str(ctx.channel.id), str(ctx.guild.id))
      return await ctx.send(embed=embed(title="I will now respond to every message in this channel"))
    else:
      await self.bot.db.query("UPDATE servers SET chatchannel=$1 WHERE id=$2", None, str(ctx.guild.id))
      return await ctx.send(embed=embed(title="I will no longer respond to all messages from this channel"))

  @commands.command(name="musicchannel", help="Set the channel where I can join and play music. If none then I will join any VC", hidden=True)
  @commands.is_owner()
  @commands.has_guild_permissions(manage_channels=True)
  async def music_channel(self, ctx, voicechannel: Optional[discord.VoiceChannel] = None):
    async with ctx.typing():
      await self.bot.db.query("UPDATE servers SET musicChannel=$1 WHERE id=$2", voicechannel.id if voicechannel is not None else None, str(ctx.guild.id))
    if voicechannel is None:
      await ctx.reply(embed=embed(title="All the voice channels are my music channels 😈 (jk)"))
    else:
      await ctx.reply(embed=embed(title=f"`{voicechannel}` is now my music channel"))

  @commands.command(name="last", help="Gets the last member to leave a voice channel.")
  @commands.guild_only()
  async def last_member(self, ctx: "MyContext", *, voice_channel: Optional[discord.VoiceChannel] = None):
    if voice_channel is None and ctx.author.voice is None:
      return await ctx.reply(embed=embed(title="You must either select a voice channel or be in one.", color=MessageColors.ERROR))
    if voice_channel is None:
      voice_channel = ctx.author.voice.channel
    if not isinstance(voice_channel, discord.VoiceChannel):
      return await ctx.reply(embed=embed(title="That is not a voice channel.", color=MessageColors.ERROR))
    member = self.last_to_leave_vc[voice_channel.id]
    if member is None:
      return await ctx.reply(embed=embed(title=f"No currently saved departing member of `{voice_channel}` saved.", description="I'll catch the next one :)", color=MessageColors.ERROR))
    await ctx.reply(embed=embed(title=f"`{member['member']}` left `{voice_channel}` <t:{int(member['time'])}:R>."))

  # @commands.command(name="clear",description="Deletes my messages and commands (not including the meme command)")
  # @commands.has_permissions(manage_messages = True)
  # @commands.bot_has_permissions(manage_messages = True)
  # async def clear(self,ctx,count:int):
  #   # await ctx.channel.purge(limit=count)
  #   async for message in ctx.channel.history():
  #     if message.author == self.bot.user:
  #       print("")

  @commands.command(name="kick", extras={"examples": ["@username @someone @someoneelse", "@thisguy", "12345678910 10987654321 @someone", "@someone I just really didn't like them", "@thisguy 12345678910 They were spamming general"]})
  @commands.guild_only()
  @commands.bot_has_guild_permissions(kick_members=True)
  @commands.has_guild_permissions(kick_members=True)
  async def norm_kick(self, ctx, members: commands.Greedy[discord.Member], *, reason: Optional[ActionReason] = None):
    if not isinstance(members, list):
      members = [members]
    if reason is None:
      reason = f"[Kicked by {ctx.author} (ID: {ctx.author.id})]"
    if len(members) == 0:
      return await ctx.send(embed=embed(title="Missing members to kick.", color=MessageColors.ERROR))

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
  @commands.has_guild_permissions(ban_members=True)
  async def norm_ban(self, ctx, duration: Optional[time.FutureTime] = None, members: commands.Greedy[MemberOrID] = [], *, reason: Optional[ActionReason] = None):
    if not isinstance(members, list):
      members = [members]
    if reason is None:
      reason = f"[Banned by {ctx.author} (ID: {ctx.author.id})]"

    if len(members) == 0:
      return await ctx.send(embed=embed(title="Missing members to ban.", color=MessageColors.ERROR))

    reminder = self.bot.get_cog("Reminder")
    if reminder is None:
      confirm = await ctx.prompt("", embed=embed(title="Tempban functionality is not currently available.", description="Do you still want to continue with the ban?"))
      if not confirm:
        return await ctx.send(embed=embed(title="Ban cancelled.", color=MessageColors.ERROR))

    failed = 0
    for member in members:
      try:
        await self.bot.get_or_fetch_member(ctx.guild, member.id)
        await ctx.guild.ban(member, reason=reason)
        if duration is not None:
          await reminder.create_timer(duration.dt, "tempban", ctx.guild.id, ctx.author.id, member.id, connection=ctx.pool, created=ctx.message.created_at)
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
  @commands.has_guild_permissions(ban_members=True)
  async def unban(self, ctx, member: BannedMember, *, reason: ActionReason = None):
    if reason is None:
      reason = f"[Unbanned by {ctx.author} (ID: {ctx.author.id})]"

    await ctx.guild.unban(member.user, reason=reason)
    if member.reason:
      reg = REASON_REG.match(member.reason)
      old_reason = member.reason if reg is None and member.reason is not None else reg[2] if reg is not None and reg[2] is not None else "No reason given"
      return await ctx.send(embed=embed(title=f"Unbanned {member.user} (ID: {member.user.id})", description=f"Previously banned for `{old_reason}`."))
    await ctx.send(embed=embed(title=f"Unbanned {member.user} (ID: {member.user.id})."))

  @commands.command(name="rolecall", aliases=["rc"], extras={"examples": ["@mods vc-1", "123456798910 vc-2 vc-1 10987654321", "@admins general @username @username"]}, help="Moves everyone with a specific role to a voicechannel. Objects that can be exluded are voicechannels,roles,and members")
  @commands.guild_only()
  @commands.has_guild_permissions(move_members=True)
  @commands.bot_has_guild_permissions(move_members=True)
  async def norm_rolecall(self, ctx, role: discord.Role, voicechannel: Optional[Union[discord.VoiceChannel, discord.StageChannel]], exclusions: commands.Greedy[Union[discord.Role, discord.VoiceChannel]] = None):
    if voicechannel.permissions_for(ctx.author).view_channel is not True:
      return await ctx.send(embed=embed(title="Trying to connect to a channel you can't view 🤔", description="Im going to have to stop you right there", color=MessageColors.ERROR))
    if voicechannel.permissions_for(ctx.author).connect is not True:
      return await ctx.send(embed=embed(title=f"You don't have permission to connect to `{voicechannel}` so I can't complete this command", color=MessageColors.ERROR))

    moved = 0
    for member in role.members:
      if (exclusions is None or (isinstance(exclusions, list) and exclusions is not None and member not in exclusions)) and member not in voicechannel.members:
        try:
          await member.move_to(voicechannel, reason=f"Role call command by {ctx.author}")
          moved += 1
        except BaseException:
          pass

    return await ctx.send(embed=embed(title=f"Moved {moved} members with the role `{role}` to `{voicechannel}`"))

  @commands.command(name="massmove", aliases=["move"], extras={"examples": ["general", "vc-2 general", "'long voice channel' general"]}, help="Move everyone from one voice channel to another")
  @commands.guild_only()
  @commands.has_guild_permissions(move_members=True)
  @commands.bot_has_guild_permissions(move_members=True)
  async def norm_massmove(self, ctx, to_channel: Union[discord.VoiceChannel, discord.StageChannel] = None, from_channel: Optional[Union[discord.VoiceChannel, discord.StageChannel]] = None):
    if (from_channel is not None and not isinstance(from_channel, (discord.VoiceChannel, discord.StageChannel))) or (to_channel is not None and not isinstance(to_channel, (discord.VoiceChannel, discord.StageChannel))):
      return await ctx.send(embed=embed(title="Please only select voice channels for moving", color=MessageColors.ERROR))

    if from_channel is None and ctx.author.voice is not None and ctx.author.voice.channel is not None and ctx.author.voice.channel == to_channel:
      return await ctx.send(embed=embed(title="Please select a voice channel different from the one you are already in to move to", color=MessageColors.ERROR))

    if to_channel.permissions_for(ctx.author).view_channel is not True:
      return await ctx.send(embed=embed(title="Trying to connect to a channel you can't view 🤔", description="Im going to have to stop you right there", color=MessageColors.ERROR))

    if to_channel.permissions_for(ctx.author).connect is not True:
      return await ctx.send(embed=embed(title=f"You don't have permission to connect to `{to_channel}` so I can't complete this command", color=MessageColors.ERROR))

    try:
      if from_channel is None:
        from_channel = ctx.author.voice.channel
    except BaseException:
      return await ctx.send(embed=embed(title="To move users from one channel to another, you need to be connected to one or specify the channel to send from.", color=MessageColors.ERROR))

    memberCount = len(from_channel.members)

    failed = 0

    for member in from_channel.members:
      try:
        await member.move_to(to_channel, reason=f"Mass move called by {ctx.author} (ID: {ctx.author.id})")
      except discord.HTTPException:
        failed += 1

    if ctx.guild.me and ctx.guild.me in to_channel.members:
      if to_channel.type == discord.ChannelType.stage_voice:
        await ctx.guild.me.edit(suppress=False)

    return await ctx.send(embed=embed(title=f"Successfully moved {memberCount - failed}/{memberCount} member(s)"))

  @commands.command(name="lock", help="Sets your voice channels user limit to the current number of occupants", hidden=True)
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  @commands.bot_has_guild_permissions(manage_channels=True)
  async def norm_lock(self, ctx, *, voicechannel: Optional[discord.VoiceChannel] = None):
    if voicechannel is None:
      if ctx.author.voice is None:
        return await ctx.send(embed=embed(title="You either need to specify a voicechannel or be connected to one", color=MessageColors.ERROR))
      voicechannel = ctx.author.voice.channel
    if voicechannel.user_limit > 0:
      await voicechannel.edit(user_limit=0)
      return await ctx.send(embed=embed(title=f"Unlocked `{voicechannel}`"))
    else:
      await voicechannel.edit(user_limit=len(voicechannel.members))
      return await ctx.send(embed=embed(title=f"Locked `{voicechannel}`"))

  @commands.command(name="begone", extras={"examples": ["https://discord.com/channels/707441352367013899/707458929696702525/707520808448294983", "707520808448294983"]}, help="Delete unwanted message that I send")
  @commands.bot_has_permissions(manage_messages=True)
  async def begone(self, ctx, message: Optional[discord.Message] = None):
    if message is not None and ctx.message.reference is not None:
      raise commands.TooManyArguments("Please only either reply to the problemed message or add it to the end of this message not both")

    message = message if message is not None else ctx.message.reference.resolved if ctx.message.reference is not None else None
    if message is None:
      raise commands.MessageNotFound("Please either reply to the message with this command or add the message to the end of this command")

    if message.author != ctx.guild.me:
      raise commands.CommandError("I will not delete messages that I didn't author with this command")
    reference = await ctx.channel.fetch_message(message.reference.message_id)
    if reference.author != ctx.author:
      raise commands.CommandError("You are not the author of that message, I will only 'begone' messages that referenced a message authored by you")

    await asyncio.gather(
        relay_info(
            f"**Begone**\nUSER: {reference.clean_content}\nME: {message.clean_content}```{message}```",
            self.bot,
            webhook=self.bot.log.log_chat
        ),
        message.delete(),
        ctx.reply(embed=embed(title="Message has been removed"), delete_after=10),
        ctx.message.delete(delay=10)
    )

  @commands.command(name="timeout", extras={"examples": ["20m @Motostar @steve they were annoying me", "1week @steve 9876543210", "5d @Motostar spamming general", "0123456789"]}, help="Timeout a member from chating, replying, reacting, and joining voice channels.")
  @commands.guild_only()
  @can_timeout()
  @commands.has_guild_permissions(moderate_members=True)
  @commands.bot_has_guild_permissions(moderate_members=True)
  async def timeout(self, ctx: "MyContext", duration: time.TimeoutTime, members: commands.Greedy[discord.Member], *, reason: Optional[ActionReason] = None):
    if not isinstance(members, list):
      members = [members]

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
  @commands.has_guild_permissions(moderate_members=True)
  @commands.bot_has_guild_permissions(moderate_members=True)
  async def norm_untimeout(self, ctx: "MyContext", members: commands.Greedy[discord.Member], *, reason: ActionReason = None):
    if not isinstance(members, list):
      members = [members]

    if reason is None:
      reason = f"[Timeout removed by {ctx.author} (ID: {ctx.author.id})]"

    failed = 0
    async with ctx.typing():
      for member in members:
        try:
          await member.remove_timeout(reason=reason)
        except discord.HTTPException:
          failed += 1
    if len(members) == 1:
      await ctx.send(embed=embed(title=f"Removed timeout for {members[0]}"))
    else:
      await ctx.send(embed=embed(title=f"Removed timeout for {len(members) - failed}/{len(members)} members."))

  @commands.command(extras={"examples": ["20m", "1h20m", "5h"]}, help="Temporarily timeout yourself for the specified duration, min 5 minutes, max 24 hours")
  @commands.guild_only()
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def selftimeout(self, ctx: "MyContext", *, duration: time.ShortTime):
    created_at = ctx.message.created_at
    if duration.dt > (created_at + datetime.timedelta(days=1)):
      return await ctx.send(embed=embed(title="Duration is too long. Must be at most 24 hours.", color=MessageColors.ERROR))

    if duration.dt < (created_at + datetime.timedelta(minutes=5)):
      return await ctx.send(embed=embed(title="Duration is too short. Must be at least 5 minutes.", color=MessageColors.ERROR))

    confirm = await ctx.prompt("", embed=embed(title=f"Are you sure you want to self-timeout, and retracted {time.format_dt(duration.dt, style='R')}?", description="Do not ask the moderators to undo this!"))
    if not confirm:
      return await ctx.send(embed=embed(title="Cancelled.", color=MessageColors.ERROR))

    await ctx.author.edit(communication_disabled_until=duration.dt, reason=f"Self-timeout for {ctx.author} (ID: {ctx.author.id}) for {time.human_timedelta(duration.dt, source=created_at)}")
    await ctx.send(embed=embed(title=f"Timed out, and retracted {time.format_dt(duration.dt, style='R')}. Be sure not to bother anyone about it."))

  @selftimeout.error
  async def on_selftimeout_error(self, ctx: "MyContext", error: Exception):
    if isinstance(error, commands.MissingRequiredArgument):
      await ctx.send(embed=embed(title="Missing duration.", color=MessageColors.ERROR))

  @commands.group(name="mute", extras={"examples": ["20m @Motostar @steve they were annoying me", "@steve 9876543210", "30d @Motostar spamming general", "0123456789"]}, help="Mute a member from text channels", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @can_mute()
  @commands.has_guild_permissions(manage_roles=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def norm_mute(self, ctx: "MyContext", duration: Optional[time.FutureTime], members: commands.Greedy[discord.Member], *, reason: Optional[ActionReason] = None):
    if not isinstance(members, list):
      members = [members]

    if reason is None:
      reason = f"[Muted by {ctx.author} (ID: {ctx.author.id})]"

    reminder = self.bot.get_cog("Reminder")
    if reminder is None:
      confirm = await ctx.prompt("", embed=embed(title="Tempmute functionality is not currently available.", description="Do you still want to continue with the mute?"))
      if not confirm:
        return await ctx.send(embed=embed(title="Mute cancelled.", color=MessageColors.ERROR))

    role = discord.Object(id=ctx.guild_config.mute_role_id)
    if len(members) == 0:
      return await ctx.send(embed=embed(title="Missing members to mute.", color=MessageColors.ERROR))

    failed = 0
    async with ctx.typing():
      for member in members:
        try:
          await member.add_roles(role, reason=reason)
          if duration is not None and reminder:
            await reminder.create_timer(duration.dt, "tempmute", ctx.guild.id, ctx.author.id, member.id, role.id, created=ctx.message.created_at)
        except discord.HTTPException:
          failed += 1

    if len(members) == 1:
      await ctx.send(embed=embed(title=f"Muted {members[0]}{' and retracted '+time.format_dt(duration.dt,style='R') if duration else ''}"))
    else:
      await ctx.send(embed=embed(title=f"Muted {len(members) - failed}/{len(members)} members{' and retracted '+time.format_dt(duration.dt,style='R') if duration else ''}."))

  @commands.Cog.listener()
  async def on_tempmute_timer_complete(self, timer):
    guild_id, mod_id, member_id, role_id = timer.args
    await self.bot.wait_until_ready()

    guild = self.bot.get_guild(guild_id)
    if guild is None:
      return

    member = await self.bot.get_or_fetch_member(guild, member_id)
    if member is None or not member._roles.has(role_id):
      async with self.bot.db.pool.acquire() as conn:
        await conn.query("UPDATE servers SET muted_members=array_remove(muted_members, $1) WHERE id=$2", str(member_id), str(guild_id))
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
      async with self.bot.db.pool.acquire() as conn:
        await conn.query("UPDATE servers SET muted_members=array_remove(muted_members, $1) WHERE id=$2", str(member_id), str(guild_id))

  @norm_mute.group("role", help="Set the role to be applied to members that get muted", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @commands.has_guild_permissions(manage_roles=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def mute_role(self, ctx: "MyContext", *, role: Optional[discord.Role] = None):
    await self.bot.db.query("UPDATE servers SET mute_role=$1 WHERE id=$2", str(role.id) if role is not None else None, str(ctx.guild.id))
    if role is not None:
      return await ctx.send(embed=embed(title=f"Friday will now use `{role}` as the new mute role"))
    await ctx.send(embed=embed(title="The saved mute role has been removed"))

  @mute_role.command(name="update", help="Updates every channel with the mute role overwrites")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_roles=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  @commands.cooldown(1, 60.0, commands.BucketType.guild)
  async def mute_role_update(self, ctx: "MyContext"):
    con = await self.get_guild_config(ctx.guild.id)
    if con.mute_role_id is None:
      ctx.command.reset_cooldown(ctx)
      return await ctx.send(embed=embed(title=f"The mute role is not set, please set it with `{ctx.prefix}mute role`", color=MessageColors.ERROR))

    role = config.mute_role
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

  @mute_role.command("create", help="Don't have a muted role? Let Friday create a basic one for you.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_roles=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  @commands.cooldown(1, 60.0, commands.BucketType.guild)
  async def mute_role_create(self, ctx: "MyContext", *, name: Optional[str] = "Muted"):
    con = await self.get_guild_config(ctx.guild.id)
    if con.mute_role is not None:
      ctx.command.reset_cooldown(ctx)
      return await ctx.send(embed=embed(title="This server already has a mute role.", color=MessageColors.ERROR))

    try:
      role = await ctx.guild.create_role(name=name, reason=f"Mute Role created by {ctx.author} (ID: {ctx.author.id})")
    except discord.HTTPException as e:
      ctx.command.reset_cooldown(ctx)
      return await ctx.send(embed=embed(title="An error occurred", description=str(e), color=MessageColors.ERROR))

    await self.bot.db.query("UPDATE servers SET mute_role=$1 WHERE id=$2", str(role.id), str(ctx.guild.id))

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
  @commands.has_guild_permissions(manage_roles=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def norm_unmute(self, ctx: "MyContext", members: commands.Greedy[discord.Member], *, reason: ActionReason = None):
    if not isinstance(members, list):
      members = [members]

    if reason is None:
      reason = f"[Unmuted by {ctx.author} (ID: {ctx.author.id})]"

    failed = 0
    async with ctx.typing():
      for member in members:
        try:
          await member.remove_timeout(reason=reason)
          # await member.remove_roles(role, reason=reason)
        except discord.HTTPException:
          failed += 1
    if len(members) == 1:
      await ctx.send(embed=embed(title=f"Unmuted {members[0]}"))
    else:
      await ctx.send(embed=embed(title=f"Unmuted {len(members) - failed}/{len(members)} members."))

  @commands.command(extras={"examples": ["20m", "1h20m", "5h"]}, help="Temporarily mutes yourself for the specified duration, min 5 minutes, max 24 hours")
  @commands.guild_only()
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def selfmute(self, ctx: "MyContext", *, duration: time.ShortTime):
    reminder = self.bot.get_cog("Reminder")
    if reminder is None:
      return await ctx.send(embed=embed(title="Sorry, this funcitonality is not available.", color=MessageColors.ERROR))

    con = await self.get_guild_config(ctx.guild.id)
    role_id = con and con.mute_role_id
    if role_id is None:
      raise MissingMuteRole()

    if ctx.author._roles.has(role_id):
      return await ctx.send(embed=embed(title="You are already muted. 🤔🤔", color=MessageColors.ERROR))

    created_at = ctx.message.created_at
    if duration.dt > (created_at + datetime.timedelta(days=1)):
      return await ctx.send(embed=embed(title="Duration is too long. Must be at most 24 hours.", color=MessageColors.ERROR))

    if duration.dt < (created_at + datetime.timedelta(minutes=5)):
      return await ctx.send(embed=embed(title="Duration is too short. Must be at least 5 minutes.", color=MessageColors.ERROR))
    confirm = await ctx.prompt("", embed=embed(title=f"Are you sure you want to self-mute, and retracted {time.format_dt(duration.dt, style='R')}?", description="Do not ask the moderators to undo this!"))
    if not confirm:
      return await ctx.send(embed=embed(title="Cancelled.", color=MessageColors.ERROR))

    await ctx.author.add_roles(discord.Object(id=role_id), reason=f"Self-mute for {ctx.author} (ID: {ctx.author.id}) for {time.human_timedelta(duration.dt, source=created_at)}")
    await reminder.create_timer(duration.dt, "tempmute", ctx.guild.id, ctx.author.id, ctx.author.id, role_id, created=created_at)
    await ctx.author.edit(communication_disabled_until=duration.dt, reason=f"Self-mute for {ctx.author} (ID: {ctx.author.id}) for {time.human_timedelta(duration.dt, source=created_at)}")
    await ctx.send(embed=embed(title=f"Muted, and retracted {time.format_dt(duration.dt, style='R')}. Be sure not to bother anyone about it."))

  @selfmute.error
  async def on_selfmute_error(self, ctx: "MyContext", error: Exception):
    if isinstance(error, commands.MissingRequiredArgument):
      await ctx.send(embed=embed(title="Missing duration.", color=MessageColors.ERROR))

  #
  # TODO: Add the cooldown back to the below command but check if the command fails then reset the cooldown
  #

  @commands.command(name="language", extras={"examples": ["en", "es", "english", "spanish"]}, aliases=["lang"], help="Change the language that I will speak. This currently only applies to the chatbot messages not the commands.")
  # @commands.cooldown(1, 3600, commands.BucketType.guild)
  @commands.has_guild_permissions(administrator=True)
  async def language(self, ctx, language: Optional[str] = None):
    lang = ctx.guild.preferred_locale.split("-")[0]
    if language is None and ctx.guild is not None:
      language = lang

    new_lang = pycountry.languages.get(alpha_2=language) if len(language) <= 2 else pycountry.languages.get(name=language)
    if new_lang is None:
      return await ctx.reply(embed=embed(title=f"Failed to find language: `{language}`", color=MessageColors.ERROR))

    final_lang = new_lang.alpha_2 if new_lang is not None else lang
    final_lang_name = new_lang.name if new_lang is not None else lang
    await self.bot.db.query("UPDATE servers SET lang=$1 WHERE id=$2", final_lang, str(ctx.guild.id))
    chat = self.bot.get_cog("Chat")
    if chat is not None:
      chat.get_guild_config.invalidate(chat, ctx.guild.id)
    return await ctx.reply(embed=embed(title=f"New language set to: `{final_lang_name}`"))

  @norm_chatchannel.after_invoke
  @music_channel.after_invoke
  @mute_role.after_invoke
  @mute_role_create.after_invoke
  async def settings_after_invoke(self, ctx: "MyContext"):
    if not ctx.guild:
      return

    self.bot.dispatch("invalidate_mod", ctx.guild.id)


def setup(bot):
  bot.add_cog(Moderation(bot))
