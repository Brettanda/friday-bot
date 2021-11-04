import asyncio
from typing import Optional, Union

import nextcord as discord
# import validators
import pycountry
# from interactions import Context as SlashContext, cog_ext, ComponentContext
# from discord_slash.model import SlashCommandOptionType
# from discord_slash.utils.manage_commands import create_option, create_choice
# from discord_slash.utils.manage_components import create_select, create_select_option, create_button, create_actionrow
from nextcord.ext import commands
from typing_extensions import TYPE_CHECKING
from collections import defaultdict

from functions import (MessageColors, MyContext, cache, checks, config, embed,
                       relay_info)

if TYPE_CHECKING:
  from index import Friday as Bot

# def persona_options() -> list:
#   options = []
#   for i in config.personas:
#     options.append(create_choice(i[0], i[1]))
#   return options


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
    ret = f"{ctx.author} (ID: {ctx.author.id}): {argument}"

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


class Config:
  @classmethod
  async def from_record(cls, record, bot):
    self = cls()

    self.bot = bot
    self.id: int = int(record["id"], base=10)
    self.muted_members = set(record["muted_members"] or [])
    self.mute_role_id = int(record["mute_role"], base=10) if record["mute_role"] else None
    return self

  @property
  def mute_role(self):
    guild = self.bot.get_guild(self.id)
    return guild and self.mute_role_id and guild.get_role(self.mute_role_id)

  async def mute(self, member: discord.Member, reason: str) -> None:
    if self.mute_role_id:
      await member.add_roles(discord.Object(id=self.mute_role_id), reason=reason)


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

  @cache()
  async def get_guild_config(self, guild_id: int) -> Optional[Config]:
    query = "SELECT * FROM servers WHERE id=$1 LIMIT 1;"
    async with self.bot.db.pool.acquire(timeout=300.0) as conn:
      record = await conn.fetchrow(query, str(guild_id))
      self.bot.logger.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
      if record is not None:
        return await Config.from_record(record, self.bot)
      return None

  @commands.Cog.listener()
  async def on_guild_role_delete(self, role: discord.Role):
    guild_id = role.guild.id
    config = await self.get_guild_config(guild_id)
    if config is None or config.mute_role_id != role.id:
      return

    await self.bot.db.query("UPDATE servers SET (mute_role, muted_members) = (NULL, '{}'::bigint[]) WHERE id=$1", str(guild_id))
    self.get_guild_config.invalidate(self, guild_id)
    automod = self.bot.get_cog("cogs.automod")
    if automod:
      automod.get_guild_config.invalidate(automod, guild_id)

  @commands.Cog.listener()
  async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if after.channel or before.channel is None:
      return
    time = discord.utils.utcnow()
    self.last_to_leave_vc[before.channel.id] = {"member": member, "time": time.timestamp()}

  # @commands.command(name="mute")
  # @commands.is_owner()
  # @commands.has_guild_permissions(manage_roles=True)
  # async def mute(self,ctx,members:commands.Greedy[discord.Member]=None):
  #   if self.bot.user in members:
  #     muted = await query(self.bot.log.mydb,"SELECT muted FROM servers WHERE id=?",ctx.guild.id)
  #     if muted == 0:
  #       await query(self.bot.log.mydb,"UPDATE servers SET muted=? WHERE id=?",1,ctx.guild.id)
  #       await ctx.reply(embed=embed(title="I will now only respond to commands"))
  #     else:
  #       await query(self.bot.log.mydb,"UPDATE servers SET muted=? WHERE id=?",0,ctx.guild.id)
  #       await ctx.reply(embed=embed(title="I will now respond to chat message as well as commands"))

  @commands.command(name="prefix", extras={"examples": ["?", "f!"]}, help="Sets the prefix for Fridays commands")
  @commands.guild_only()
  @checks.is_admin()
  async def _prefix(self, ctx: "MyContext", new_prefix: Optional[str] = config.defaultPrefix):
    new_prefix = new_prefix.lower()
    if len(new_prefix) > 5:
      return await ctx.reply(embed=embed(title="Can't set a prefix with more than 5 characters", color=MessageColors.ERROR))
    await self.bot.db.query("UPDATE servers SET prefix=$1 WHERE id=$2", str(new_prefix), str(ctx.guild.id))
    self.bot.prefixes[ctx.guild.id] = new_prefix
    await ctx.reply(embed=embed(title=f"My new prefix is `{new_prefix}`"))

  # @commands.group(name="set", invoke_without_command=True, case_insensitive=True)
  # @commands.guild_only()
  # @commands.has_guild_permissions(manage_channels=True)
  # async def settings_bot(self, ctx):
  #   await ctx.send_help(ctx.command)

  # @cog_ext.cog_slash(name="bot", description="Bot settings")
  # @commands.has_guild_permissions(manage_channels=True)
  # @checks.slash(user=True, private=False)
  # async def slash_settings_bot(self, ctx):
  #   print("askjdhla")

  @commands.command(name="chatchannel", help="Set the current channel so that I will always try to respond with something")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def norm_chatchannel(self, ctx):
    post = await self.settings_bot_chat_channel(ctx)
    await ctx.reply(**post)

  # @cog_ext.cog_slash(name="chatchannel", description="Set the current text channel so that I will always try to respond")
  # @commands.has_guild_permissions(manage_channels=True)
  # @checks.slash(user=True, private=False)
  # async def slash_chatchannel(self, ctx):
  #   await ctx.defer()
  #   post = await self.settings_bot_chat_channel(ctx)
  #   await ctx.send(**post)

  async def settings_bot_chat_channel(self, ctx):
    chat_channel = await self.bot.db.query("SELECT chatchannel FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if chat_channel is None:
      await self.bot.db.query("UPDATE servers SET chatchannel=$1 WHERE id=$2", str(ctx.channel.id), str(ctx.guild.id))
      return dict(embed=embed(title="I will now respond to every message in this channel"))
    else:
      await self.bot.db.query("UPDATE servers SET chatchannel=$1 WHERE id=$2", None, str(ctx.guild.id))
      return dict(embed=embed(title="I will no longer respond to all messages from this channel"))

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

  @commands.command(name="deletecommandsafter", extras={"examples": ["0", "180"]}, aliases=["deleteafter", "delcoms"], help="Set the time in seconds for how long to wait before deleting command messages")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def delete_commands_after(self, ctx: "MyContext", time: Optional[int] = 0):
    if time < 0:
      await ctx.reply(embed=embed(title="time has to be above 0"))
      return
    async with ctx.typing():
      await self.bot.db.query("UPDATE servers SET autoDeleteMSGs=$1 WHERE id=$2", time, str(ctx.guild.id))
      self.bot.log.change_guild_delete(str(ctx.guild.id), time)
    if time == 0:
      await ctx.reply(embed=embed(title="I will no longer delete command messages"))
    else:
      await ctx.reply(embed=embed(title=f"I will now delete commands after `{time}` seconds"))

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
      return await ctx.reply(embed=embed(title=f"The last member to leave `{voice_channel}` was not saved.", description="I'll catch the next one :)", color=MessageColors.ERROR))
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
      reason = f"Kicked by {ctx.author} (ID: {ctx.author.id})"
    if len(members) == 0:
      return await ctx.send(embed=embed(title="Missing members to kick.", color=MessageColors.ERROR))

    failed = 0
    for member in members:
      try:
        await ctx.guild.kick(member, reason=reason)
      except discord.HTTPException:
        failed += 1

    await ctx.send(embed=embed(title=f"Kicked {len(members) - failed}/{len(members)} members"))

  @commands.command("ban", extras={"examples": ["@username @someone @someoneelse Spam", "@thisguy The most spam i have ever seen", "12345678910 10987654321 @someone", "@someone They were annoying me", "123456789 2 Sus"]})
  @commands.guild_only()
  @commands.bot_has_guild_permissions(ban_members=True)
  @commands.has_guild_permissions(ban_members=True)
  async def norm_ban(self, ctx, members: commands.Greedy[MemberOrID], *, reason: Optional[ActionReason] = None):
    if not isinstance(members, list):
      members = [members]
    if reason is None:
      reason = f"Banned by {ctx.author} (ID: {ctx.author.id})"

    if len(members) == 0:
      return await ctx.send(embed=embed(title="Missing members to ban.", color=MessageColors.ERROR))

    failed = 0
    for member in members:
      try:
        await ctx.guild.ban(member, reason=reason)
      except discord.HTTPException:
        failed += 1
    await ctx.send(embed=embed(title=f"Banned {len(members) - failed}/{len(members)} members."))

  @commands.command("unban")
  @commands.guild_only()
  @commands.bot_has_guild_permissions(ban_members=True)
  @commands.has_guild_permissions(ban_members=True)
  async def unban(self, ctx, member: BannedMember, *, reason: ActionReason = None):
    if reason is None:
      reason = f"Unbanned by {ctx.author} (ID: {ctx.author.id})"

    await ctx.guild.unban(member.user, reason=reason)
    if member.reason:
      return await ctx.send(embed=embed(title=f"Unbanned {member.user} (ID: {member.user.id})", description=f"Previously banned for `{member.reason}`."))
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
        ctx.reply(embed=embed(title="Message has been removed"), delete_after=20),
        ctx.message.delete(delay=10)
    )

  # TODO: Add a timeout

  @commands.group(name="mute", extras={"examples": ["@Motostar @steve they were annoying me", "@steve 9876543210", "@Motostar spamming general", "0123456789"]}, help="Mute a member from text channels", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @can_mute()
  @commands.has_guild_permissions(manage_roles=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def norm_mute(self, ctx: "MyContext", members: commands.Greedy[discord.Member], *, reason: ActionReason = None):
    if not isinstance(members, list):
      members = [members]

    if reason is None:
      reason = f"Mute done by {ctx.author} (ID: {ctx.author.id})"

    role = discord.Object(id=ctx.guild_config.mute_role_id)
    if len(members) == 0:
      return await ctx.send(embed=embed(title="Missing members to mute.", color=MessageColors.ERROR))

    failed = 0
    async with ctx.typing():
      for member in members:
        try:
          await member.add_roles(role, reason=reason)
        except discord.HTTPException:
          failed += 1
    await ctx.send(embed=embed(title=f"Muted {len(members) - failed}/{len(members)} members."))

  @norm_mute.group("role", help="Set the role to be applied to members that get muted", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @commands.has_guild_permissions(manage_roles=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def mute_role(self, ctx: "MyContext", *, role: Optional[discord.Role] = None):
    await self.bot.db.query("UPDATE servers SET mute_role=$1 WHERE id=$2", str(role.id) if role is not None else None, str(ctx.guild.id))
    if role is not None:
      return await ctx.send(embed=embed(title=f"Friday will now use `{role}` as the new mute role"))
    await ctx.send(embed=embed(title="The saved mute role has been removed"))

  @mute_role.command("create", help="Don't have a muted role? Let Friday create a basic one for you.")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_roles=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  @commands.cooldown(1, 60.0, commands.BucketType.guild)
  async def mute_role_create(self, ctx: "MyContext", *, name: Optional[str] = "Muted"):
    current_role = await self.bot.db.query("SELECT mute_role FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
    if current_role is not None:
      return await ctx.send(embed=embed(title="There is already a saved role.", color=MessageColors.ERROR))

    if current_role is not None and ctx.guild.get_role(int(current_role, base=10)) is not None:
      return await ctx.send(embed=embed(title="This server already has a mute role.", color=MessageColors.ERROR))

    try:
      role = await ctx.guild.create_role(name=name, reason=f"Mute Role created by {ctx.author} (ID: {ctx.author.id})")
    except discord.HTTPException as e:
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
      reason = f"Unmute done by {ctx.author} (ID: {ctx.author.id})"

    role = discord.Object(id=ctx.guild_config.mute_role_id)
    if len(members) == 0:
      return await ctx.send(embed=embed(title="Missing members to unmute.", color=MessageColors.ERROR))

    failed = 0
    async with ctx.typing():
      for member in members:
        try:
          await member.remove_roles(role, reason=reason)
        except discord.HTTPException:
          failed += 1
    await ctx.send(embed=embed(title=f"Unmuted {len(members) - failed}/{len(members)} members"))

  #
  # TODO: Add the cooldown back to the below command but check if the command fails then reset the cooldown
  #

  @commands.command(name="language", extras={"examples": ["en", "es", "english", "spanish"]}, aliases=["lang"], help="Change the language that I will speak")
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
    self.bot.log.change_guild_lang(ctx.guild, final_lang)
    return await ctx.reply(embed=embed(title=f"New language set to: `{final_lang_name}`"))

  @norm_chatchannel.after_invoke
  @music_channel.after_invoke
  @delete_commands_after.after_invoke
  @mute_role.after_invoke
  @mute_role_create.after_invoke
  async def settings_after_invoke(self, ctx: "MyContext"):
    if not ctx.guild:
      return

    self.get_guild_config.invalidate(self, ctx.guild.id)
    automod = self.bot.get_cog("cogs.automod")
    if automod:
      automod.get_guild_config.invalidate(automod, ctx.guild.id)


def setup(bot):
  bot.add_cog(Moderation(bot))
