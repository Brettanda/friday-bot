import asyncio
import typing
# import datetime
# import validators
from slugify import slugify
import pycountry

import discord
import datetime

# from PIL import Image, ImageDraw
# https://code-maven.com/create-images-with-python-pil-pillow
from discord.ext import commands
from discord_slash import SlashContext, cog_ext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option
from typing_extensions import TYPE_CHECKING

from cogs.help import cmd_help
from functions import MessageColors, embed, query, checks, relay_info, config

if TYPE_CHECKING:
  from index import Friday as Bot


class Moderation(commands.Cog):
  """Manage your server with these commands"""

  def __init__(self, bot: "Bot"):
    self.bot = bot

    if not hasattr(self, "message_spam_control"):
      self.message_spam_control = {}

    if not hasattr(self, "message_spam_control_counter"):
      self.message_spam_control_counter = {}

    if not hasattr(self, "blacklist"):
      self.blacklist = {}

  def cog_check(self, ctx):
    if ctx.guild is None:
      raise commands.NoPrivateMessage("This command can only be used within a guild")
    return True

  @commands.Cog.listener()
  async def on_ready(self):
    blacklists = await query(self.bot.mydb, "SELECT * FROM blacklist")
    for server, word in blacklists:
      if server not in self.blacklist:
        self.blacklist[int(server)] = [word]
      else:
        self.blacklist[int(server)].append(word)

  @commands.command(name="defaultrole", hidden=True, help="Set the role that is given to new members when they join the server")
  @commands.is_owner()
  @commands.has_guild_permissions(manage_roles=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def _defaultrole(self, ctx, role: typing.Optional[discord.Role] = None):
    # TODO: Need the members intent so assign the role
    role_id = role.id if role is not None else None
    await query(self.bot.mydb, "UPDATE servers SET defaultRole=%s WHERE id=%s", role_id, ctx.guild.id)
    await ctx.reply(embed=embed(title=f"The new default role for new members is `{role}`"))

  @commands.Cog.listener()
  async def on_member_join(self, member: discord.Member):
    if member.pending:
      return
    await self.add_defaultrole(member)

  @commands.Cog.listener()
  async def on_member_update(self, before: discord.Member, after: discord.Member):
    if before.pending is not True or after.pending is not False:
      return
    await self.add_defaultrole(after)

  async def add_defaultrole(self, member: discord.Member):
    role_id = await query(self.bot.mydb, "SELECT defaultRole FROM servers WHERE id=%s", member.guild.id)
    if role_id == 0 or role_id is None or str(role_id).lower() == "null":
      return
    else:
      role = member.guild.get_role(role_id)
      if role is None:
        # await member.guild.owner.send(f"The default role that was chosen for me to add to members when they join yours server \"{member.guild.name}\" could not be found, please update the default role at https://friday-self.bot.com")
        await query(self.bot.mydb, "UPDATE servers SET defaultRole=NULL WHERE id=%s", member.guild.id)
      else:
        await member.add_roles(role, reason="Default Role")

  # @commands.command(name="mute")
  # @commands.is_owner()
  # @commands.has_guild_permissions(manage_roles=True)
  # async def mute(self,ctx,members:commands.Greedy[discord.Member]=None):
  #   if self.bot.user in members:
  #     muted = await query(self.bot.mydb,"SELECT muted FROM servers WHERE id=%s",ctx.guild.id)
  #     if muted == 0:
  #       await query(self.bot.mydb,"UPDATE servers SET muted=%s WHERE id=%s",1,ctx.guild.id)
  #       await ctx.reply(embed=embed(title="I will now only respond to commands"))
  #     else:
  #       await query(self.bot.mydb,"UPDATE servers SET muted=%s WHERE id=%s",0,ctx.guild.id)
  #       await ctx.reply(embed=embed(title="I will now respond to chat message as well as commands"))

  @commands.command(name="prefix", help="Sets the prefix for Fridays commands")
  @commands.has_guild_permissions(administrator=True)
  async def _prefix(self, ctx, new_prefix: typing.Optional[str] = config.defaultPrefix):
    new_prefix = new_prefix.lower()
    if len(new_prefix) > 5:
      await ctx.reply(embed=embed(title="Can't set a prefix with more than 5 characters", color=MessageColors.ERROR))
      return
    await query(self.bot.mydb, "UPDATE servers SET prefix=%s WHERE id=%s", new_prefix, ctx.guild.id)
    self.bot.log.change_guild_prefix(ctx.guild.id, new_prefix)
    try:
      await ctx.reply(embed=embed(title=f"My new prefix is `{new_prefix}`"))
    except discord.Forbidden:
      await ctx.reply(f"My new prefix is `{new_prefix}`")

  @commands.group(name="set", aliases=["bot"], invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def settings_bot(self, ctx):
    await cmd_help(ctx, ctx.command)

  # @cog_ext.cog_slash(name="bot", description="Bot settings")
  # @commands.has_guild_permissions(manage_channels=True)
  # @checks.slash(user=True, private=False)
  # async def slash_settings_bot(self, ctx):
  #   print("askjdhla")

  @settings_bot.command(name="mute")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def norm_settings_bot_mute(self, ctx):
    post = await self.settings_bot_mute(ctx)
    await ctx.reply(**post)

  @cog_ext.cog_subcommand(base="set", base_description="Bot settings", name="mute", description="Stop me from responding to non-command messages or not")
  @commands.has_guild_permissions(manage_channels=True)
  @checks.slash(user=True, private=False)
  async def slash_settings_bot_mute(self, ctx):
    post = await self.settings_bot_mute(ctx)
    await ctx.send(**post)

  async def settings_bot_mute(self, ctx):
    muted = await query(self.bot.mydb, "SELECT muted FROM servers WHERE id=%s", ctx.guild.id)
    if int(muted) == 0:
      await query(self.bot.mydb, "UPDATE servers SET muted=%s WHERE id=%s", 1, ctx.guild.id)
      self.bot.log.change_guild_muted(ctx.guild.id, True)
      return dict(embed=embed(title="I will now only respond to commands"))
    else:
      await query(self.bot.mydb, "UPDATE servers SET muted=%s WHERE id=%s", 0, ctx.guild.id)
      self.bot.log.change_guild_muted(ctx.guild.id, False)
      return dict(embed=embed(title="I will now respond to chat message as well as commands"))

  @settings_bot.command(name="chatchannel", alias="chat", help="Set the current channel so that I will always try to respond with something")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def norm_settings_bot_chat_channel(self, ctx):
    post = await self.settings_bot_chat_channel(ctx)
    await ctx.reply(**post)

  @cog_ext.cog_subcommand(base="set", base_description="Bot settings", name="chatchannel", description="Set the current text channel so that I will always try to respond")
  @commands.has_guild_permissions(manage_channels=True)
  @checks.slash(user=True, private=False)
  async def slash_settings_bot_chat_channel(self, ctx):
    await ctx.defer()
    post = await self.settings_bot_chat_channel(ctx)
    await ctx.send(**post)

  async def settings_bot_chat_channel(self, ctx):
    chat_channel = await query(self.bot.mydb, "SELECT chatChannel FROM servers WHERE id=%s", ctx.guild.id)
    if chat_channel is None:
      await query(self.bot.mydb, "UPDATE servers SET chatChannel=%s WHERE id=%s", ctx.channel.id, ctx.guild.id)
      self.bot.log.change_guild_chat_channel(ctx.guild.id, ctx.channel.id)
      return dict(embed=embed(title="I will now (try to) respond to every message in this channel"))
    else:
      await query(self.bot.mydb, "UPDATE servers SET chatChannel=%s WHERE id=%s", None, ctx.guild.id)
      self.bot.log.change_guild_chat_channel(ctx.guild.id, None)
      return dict(embed=embed(title="I will no longer (try to) respond to all messages from this channel"))

  @settings_bot.command(name="musicchannel", help="Set the channel where I can join and play music. If none then I will join any VC", hidden=True)
  @commands.is_owner()
  @commands.has_guild_permissions(manage_channels=True)
  async def music_channel(self, ctx, voicechannel: typing.Optional[discord.VoiceChannel] = None):
    async with ctx.typing():
      await query(self.bot.mydb, "UPDATE servers SET musicChannel=%s WHERE id=%s", voicechannel.id if voicechannel is not None else None, ctx.guild.id)
    if voicechannel is None:
      await ctx.reply(embed=embed(title="All the voice channels are my music channels 😈 (jk)"))
    else:
      await ctx.reply(embed=embed(title=f"`{voicechannel}` is now my music channel"))

  @settings_bot.command(name="deletecommandsafter", aliases=["deleteafter", "delcoms"], help="Set the time in seconds for how long to wait before deleting command messages")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def delete_commands_after(self, ctx, time: typing.Optional[int] = 0):
    if time < 0:
      await ctx.reply(embed=embed(title="time has to be above 0"))
      return
    async with ctx.typing():
      await query(self.bot.mydb, "UPDATE servers SET autoDeleteMSGs=%s WHERE id=%s", time, ctx.guild.id)
      self.bot.log.change_guild_delete(ctx.guild.id, time)
    if time == 0:
      await ctx.reply(embed=embed(title="I will no longer delete command messages"))
    else:
      await ctx.reply(embed=embed(title=f"I will now delete commands after `{time}` seconds"))

  # @commands.command(name="clear",description="Deletes my messages and commands (not including the meme command)")
  # @commands.has_permissions(manage_messages = True)
  # @commands.bot_has_permissions(manage_messages = True)
  # async def clear(self,ctx,count:int):
  #   # await ctx.channel.purge(limit=count)
  #   async for message in ctx.channel.history():
  #     if message.author == self.bot.user:
  #       print("")

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
    try:
      if msg.guild.id in self.blacklist:
        for blacklisted_word in self.blacklist[msg.guild.id]:
          if blacklisted_word in cleansed_msg:
            try:
              await msg.delete()
              return await msg.author.send(f"""Your message `{msg.content}` was removed for containing the blacklisted word `{blacklisted_word}`""")
            except Exception as e:
              await relay_info(f"Error when trying to remove message {type(e).__name__}: {e}")
    except Exception as e:
      await relay_info(f"Error when trying to remove message (big) {type(e).__name__}: {e}")

  @commands.group(name="blacklist", aliases=["bl"], invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @commands.has_guild_permissions(manage_guild=True)
  async def _blacklist(self, ctx: commands.Context):
    await ctx.send_help(ctx.command)
    # await cmd_help(ctx, ctx.command)

  @_blacklist.command(name="add", aliases=["+"])
  @commands.guild_only()
  @commands.has_guild_permissions(manage_guild=True)
  async def _blacklist_add_word(self, ctx, *, word: str):
    cleansed_word = self.do_slugify(word)
    await query(self.bot.mydb, "INSERT IGNORE INTO blacklist VALUES (%s,%s)", ctx.guild.id, cleansed_word)
    try:
      self.blacklist[ctx.guild.id].append(cleansed_word)
    except KeyError:
      self.blacklist[ctx.guild.id] = [cleansed_word]
    word = word
    await ctx.reply(embed=embed(title=f"Added `{word}` to the blacklist"))

  @_blacklist.command(name="remove", aliases=["-"])
  @commands.guild_only()
  @commands.has_guild_permissions(manage_guild=True)
  async def _blacklist_remove_word(self, ctx, *, word: str):
    cleansed_word = word
    if cleansed_word not in self.blacklist[ctx.guild.id]:
      return await ctx.reply(embed=embed(title="You don't seem to blacklisting that word"))
    await query(self.bot.mydb, "DELETE FROM blacklist WHERE (id=%s AND word=%s)", ctx.guild.id, cleansed_word)
    self.blacklist[ctx.guild.id].remove(cleansed_word)
    word = word
    await ctx.reply(embed=embed(title=f"Removed `{word}` from the blacklist"))

  @_blacklist.command(name="display", aliases=["list", "show"])
  @commands.guild_only()
  @commands.has_guild_permissions(manage_guild=True)
  async def _blacklist_display_words(self, ctx):
    words = await query(self.bot.mydb, "SELECT word FROM blacklist WHERE id=%s", ctx.guild.id, rlist=True)
    if words == [] or words is None:
      return await ctx.reply(embed=embed(title=f"No blacklisted words yet, use `{ctx.prefix}blacklist add <word>` to get started"))
    await ctx.reply(embed=embed(title="Blocked words", description='\n'.join(x[0] for x in words)))

  @_blacklist.command(name="clear")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_guild=True)
  async def _blacklist_clear(self, ctx):
    await query(self.bot.mydb, "DELETE FROM blacklist WHERE id=%s", ctx.guild.id)
    self.blacklist[ctx.guild.id] = []
    await ctx.reply(embed=embed(title="Removed all blacklisted words"))

  @commands.command(name="kick")
  @commands.bot_has_guild_permissions(kick_members=True)
  @commands.has_guild_permissions(kick_members=True)
  async def norm_kick(self, ctx, members: commands.Greedy[discord.Member], *, reason: typing.Optional[str] = None):
    post = await self.kick(ctx, members, reason)
    await ctx.reply(post)

  @cog_ext.cog_slash(
      name="kick",
      description="Kick a member from the server",
      options=[
          create_option(
              "member",
              "The member to kick",
              SlashCommandOptionType.USER,
              True
          ),
          create_option(
              "reason",
              "The reason for kicking these member(s)",
              SlashCommandOptionType.STRING,
              False
          )
      ]
  )
  @checks.bot_has_guild_permissions(kick_members=True)
  @commands.has_guild_permissions(kick_members=True)
  @checks.slash(user=True, private=False)
  async def slash_kick(self, ctx, members: commands.Greedy[discord.Member], reason=None):
    post = await self.kick(ctx, [members], reason, True)
    await ctx.send(**post)

  async def kick(self, ctx, members, reason=None, slash=False):
    if isinstance(members, list) and len(members) == 0 and not slash:
      await cmd_help(ctx, ctx.command)

    tokick = []

    if not isinstance(members, list):
      members = list(members)

    if self.bot.user in members:
      if slash:
        return dict(hidden=True, content="But I don't want to kick myself 😭")
      return dict(embed=embed(title="But I don't want to kick myself 😭", color=MessageColors.ERROR))

    if ctx.author in members:
      if slash:
        return dict(hidden=True, content="Failed to kick yourself")
      return dict(embed=embed(title="Failed to kick yourself", color=MessageColors.ERROR))

    for member in members:
      pos = ctx.guild.me.top_role.position
      uspos = member.top_role.position

      if pos == uspos:
        if slash:
          return dict(hidden=True, content="I am not able to kick a member in the same highest role as me.")
        return dict(embed=embed(title="I am not able to kick a member in the same highest role as me.", color=MessageColors.ERROR))

      if pos < uspos:
        if slash:
          return dict(hidden=True, content="I am not able to kick a member with a role higher than my own permissions role(s)")
        return dict(embed=embed(title="I am not able to kick a member with a role higher than my own permissions role(s)", color=MessageColors.ERROR))

    if self.bot.user in members and not slash:
      try:
        await ctx.add_reaction("😢")
      except BaseException:
        pass
      return

    for member in members:
      tokick.append(member.name)
      await member.kick(reason=f"{ctx.author}: {reason}")

    return dict(embed=embed(title=f"Kicked `{', '.join(tokick)}`{(' for reason `' + reason+'`') if reason is not None else ''}"))

  @commands.command(name="ban")
  @commands.bot_has_guild_permissions(ban_members=True)
  @commands.has_guild_permissions(ban_members=True)
  async def norm_ban(self, ctx, members: commands.Greedy[discord.Member], delete_message_days: typing.Optional[int] = 0, *, reason: str = None):
    post = await self.ban(ctx, members, reason, delete_message_days)
    await ctx.reply(**post)

  @cog_ext.cog_slash(
      name="ban",
      description="Ban a member from the server",
      options=[
          create_option(
              "member",
              "The member to ban",
              SlashCommandOptionType.USER,
              True
          ),
          create_option(
              "reason",
              "The reason for banning",
              SlashCommandOptionType.STRING,
              False
          ),
          create_option(
              "delete_message_days",
              "The number of days of messages to remove from this user",
              SlashCommandOptionType.INTEGER,
              False
          )
      ]
  )
  @checks.bot_has_guild_permissions(ban_members=True)
  @commands.has_guild_permissions(ban_members=True)
  @checks.slash(user=True, private=False)
  async def slash_ban(self, ctx, member, reason=None, delete_message_days=0):
    post = await self.ban(ctx, member, reason, delete_message_days, True)
    await ctx.send(**post)

  async def ban(self, ctx, members, reason=None, delete_message_days=0, slash=False):
    if isinstance(members, list) and len(members) == 0 and not slash:
      await cmd_help(ctx, ctx.command)

    toban = []

    if not isinstance(members, list):
      members = [members]

    if self.bot.user in members and slash:
      if slash:
        return dict(hidden=True, content="But I don't want to ban myself 😭")
      return dict(embed=embed(title="But I don't want to ban myself 😭"))

    if ctx.author in members:
      if slash:
        return dict(hidden=True, content="Failed to ban yourself")
      return dict(embed=embed(title="Failed to ban yourself", color=MessageColors.ERROR))

    for member in members:
      pos = ctx.guild.me.top_role.position
      uspos = member.top_role.position

      if pos == uspos:
        if slash:
          return dict(hidden=True, content="I am not able to ban a member in the same highest role as me.")
        return dict(embed=embed(title="I am not able to ban a member in the same highest role as me.", color=MessageColors.ERROR))

      if pos < uspos:
        if slash:
          return dict(hidden=True, content="I am not able to ban a member with a role higher than my own permissions role(s)")
        return dict(embed=embed(title="I am not able to ban a member with a role higher than my own permissions role(s)", color=MessageColors.ERROR))

    if self.bot.user in members and not slash:
      try:
        await ctx.add_reaction("😢")
      except BaseException:
        pass
      return

    for member in members:
      if member == ctx.author:
        if slash:
          return dict(hidden=True, content="Failed to ban yourself")
        return dict(embed=embed(title="Failed to ban yourself", color=MessageColors.ERROR))
      toban.append(member.name)
      await member.ban(delete_message_days=delete_message_days, reason=f"{ctx.author}: {reason}")
    return dict(embed=embed(title=f"Banned `{', '.join(toban)}`{(' with `'+str(delete_message_days)+'` messages deleted') if delete_message_days > 0 else ''}{(' for reason `'+reason+'`') if reason is not None else ''}"))

  @commands.command(name="rolecall", aliases=["rc"], help="Moves everyone with a specific role to a voicechannel. Objects that can be exluded are voicechannels,roles,and members")
  @commands.guild_only()
  @commands.has_guild_permissions(move_members=True)
  @commands.bot_has_guild_permissions(move_members=True)
  async def norm_rolecall(self, ctx, role: discord.Role, voicechannel: typing.Optional[typing.Union[discord.VoiceChannel, discord.StageChannel]], exclusions: commands.Greedy[typing.Union[discord.Role, discord.VoiceChannel]] = None):
    post = await self.rolecall(ctx, role, voicechannel, exclusions)
    await ctx.reply(**post)

  @cog_ext.cog_slash(
      name="rolecall",
      description="Moves everyone with a specific role to a voicechannel.",
      options=[
          create_option("role", "The role to rolecall", SlashCommandOptionType.ROLE, True),
          create_option("voicechannel", "The voice channel to move members to", SlashCommandOptionType.CHANNEL, True),
          create_option("exclusion1", "A member that you don't want moved", SlashCommandOptionType.USER, False),
          create_option("exclusion2", "A member that you don't want moved", SlashCommandOptionType.USER, False),
          create_option("exclusion3", "A member that you don't want moved", SlashCommandOptionType.USER, False),
          create_option("exclusion4", "A member that you don't want moved", SlashCommandOptionType.USER, False),
          create_option("exclusion5", "A member that you don't want moved", SlashCommandOptionType.USER, False)
      ]
  )
  @checks.bot_has_guild_permissions(move_members=True)
  @commands.has_guild_permissions(move_members=True)
  @checks.slash(user=False, private=False)
  async def slash_rolecall(self, ctx, role, voicechannel, exclusion1=None, exclusion2=None, exclusion3=None, exclusion4=None, exclusion5=None):
    exclusions = []
    for item in [exclusion1, exclusion2, exclusion3, exclusion4, exclusion5]:
      if item is not None:
        exclusions.append(item)
    post = await self.rolecall(ctx, role, voicechannel, exclusions)
    await ctx.send(**post)

  async def rolecall(self, ctx, role, voicechannel, exclusions=None):
    if ctx.author.permissions_in(voicechannel).view_channel is not True:
      return dict(embed=embed(title="Trying to connect to a channel you can't view 🤔", description="Im going to have to stop you right there", color=MessageColors.ERROR))
    if ctx.author.permissions_in(voicechannel).connect is not True:
      return dict(embed=embed(title=f"You don't have permission to connect to `{voicechannel}` so I can't complete this command", color=MessageColors.ERROR))

    moved = 0
    for member in role.members:
      if (exclusions is None or (isinstance(exclusions, list) and exclusions is not None and member not in exclusions)) and member not in voicechannel.members:
        try:
          await member.move_to(voicechannel, reason=f"Role call command by {ctx.author}")
          moved += 1
        except BaseException:
          pass

    return dict(embed=embed(title=f"Moved {moved} members with the role `{role}` to `{voicechannel}`"))

  @commands.command(name="massmove", aliases=["move"], help="Move everyone from one voice channel to another")
  @commands.guild_only()
  @commands.has_guild_permissions(move_members=True)
  @commands.bot_has_guild_permissions(move_members=True)
  async def norm_mass_move(self, ctx, toChannel: typing.Union[discord.VoiceChannel, discord.StageChannel] = None, fromChannel: typing.Optional[typing.Union[discord.VoiceChannel, discord.StageChannel]] = None):
    post = await self.mass_move(ctx, toChannel, fromChannel)
    await ctx.reply(**post)

  @cog_ext.cog_slash(
      name="move",
      description="Move users from one voice channel to another",
      options=[
          create_option(
              "tochannel",
              "The voice channel to move to",
              SlashCommandOptionType.CHANNEL,
              True
          ),
          create_option(
              "fromchannel",
              "The voice channel to move from",
              SlashCommandOptionType.CHANNEL,
              False
          )
      ],
  )
  @checks.bot_has_guild_permissions(move_members=True)
  @commands.has_guild_permissions(move_members=True)
  @checks.slash(user=True, private=False)
  async def slash_mass_move(self, ctx, toChannel, fromChannel=None):
    post = await self.mass_move(ctx, toChannel, fromChannel)
    await ctx.send(**post)

  async def mass_move(self, ctx, toChannel, fromChannel=None):
    if (fromChannel is not None and not isinstance(fromChannel, (discord.VoiceChannel, discord.StageChannel))) or (toChannel is not None and not isinstance(toChannel, (discord.VoiceChannel, discord.StageChannel))):
      if isinstance(ctx, SlashContext):
        return dict(hidden=True, content="Please only select voice channels for moving")
      return dict(embed=embed(title="Please only select voice channels for moving", color=MessageColors.ERROR))

    if fromChannel is None and ctx.author.voice is not None and ctx.author.voice.channel is not None and ctx.author.voice.channel == toChannel:
      if isinstance(ctx, SlashContext):
        return dict(hidden=True, content="Please select a voice channel different from the one you are already in to move to")
      return dict(embed=embed(title="Please select a voice channel different from the one you are already in to move to", color=MessageColors.ERROR))

    if ctx.author.permissions_in(toChannel).view_channel is not True:
      if isinstance(ctx, SlashContext):
        return dict(hidden=True, content="Trying to connect to a channel you can't view 🤔\nIm going to have to stop you right there")
      return dict(embed=embed(title="Trying to connect to a channel you can't view 🤔", description="Im going to have to stop you right there", color=MessageColors.ERROR))

    if ctx.author.permissions_in(toChannel).connect is not True:
      if isinstance(ctx, SlashContext):
        return dict(hidden=True, content=f"You don't have permission to connect to `{toChannel}` so I can't complete this command")
      return dict(embed=embed(title=f"You don't have permission to connect to `{toChannel}` so I can't complete this command", color=MessageColors.ERROR))

    try:
      if fromChannel is None:
        fromChannel = ctx.author.voice.channel
    except BaseException:
      if isinstance(ctx, SlashContext):
        return dict(hidden=True, content="To move users from one channel to another, you need to be connected to one or specify the channel to send from.")
      return dict(embed=embed(title="To move users from one channel to another, you need to be connected to one or specify the channel to send from.", color=MessageColors.ERROR))

    memberCount = len(fromChannel.members)

    tomove = []
    for member in fromChannel.members:
      tomove.append(member.move_to(toChannel, reason=f"{ctx.author} called the move command"))
    await asyncio.gather(*tomove)
    # if isinstance(ctx, SlashContext):
    #   return dict(content=f"Successfully moved {memberCount} member(s)")
    return dict(embed=embed(title=f"Successfully moved {memberCount} member(s)"))

  @commands.command(name="lock", help="Sets your voice channels user limit to the current number of occupants", hidden=True)
  @commands.guild_only()
  # @commands.is_owner()
  @commands.has_guild_permissions(manage_channels=True)
  @commands.bot_has_guild_permissions(manage_channels=True)
  async def norm_lock(self, ctx, *, voicechannel: typing.Optional[discord.VoiceChannel] = None):
    post = await self.lock(ctx, voicechannel)
    await ctx.reply(**post)

  @cog_ext.cog_slash(
      name="lock",
      description="Sets your voice channels user limit to the current number of occupants",
      options=[
          create_option("voicechannel", "The voice channel you wish to lock", SlashCommandOptionType.CHANNEL, required=False)
      ]
  )
  @checks.bot_has_guild_permissions(manage_channels=True)
  @commands.has_guild_permissions(manage_channels=True)
  @checks.slash(user=True, private=False)
  async def slash_lock(self, ctx, *, voicechannel=None):
    post = await self.lock(ctx, voicechannel)
    await ctx.send(hidden=True, **post)

  async def lock(self, ctx, voicechannel: typing.Optional[discord.VoiceChannel] = None):
    # await ctx.guild.chunk(cache=False)
    if voicechannel is None:
      if ctx.author.voice is None:
        if isinstance(ctx, SlashContext):
          return dict(content="You either need to specify a voicechannel or be connected to one")
        return dict(embed=embed(title="You either need to specify a voicechannel or be connected to one", color=MessageColors.ERROR))
      voicechannel = ctx.author.voice.channel
    if voicechannel.user_limit > 0:
      await voicechannel.edit(user_limit=0)
      if isinstance(ctx, SlashContext):
        return dict(content=f"Unlocked `{voicechannel}`")
      return dict(embed=embed(title=f"Unlocked `{voicechannel}`"))
    else:
      await voicechannel.edit(user_limit=len(voicechannel.members))
      if isinstance(ctx, SlashContext):
        return dict(content=f"Locked `{voicechannel}`")
      return dict(embed=embed(title=f"Locked `{voicechannel}`"))

  @commands.command(name="begone", help="Delete unwanted message that I send")
  @commands.bot_has_permissions(manage_messages=True)
  async def begone(self, ctx, message: typing.Optional[discord.Message] = None):
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
        ctx.message.delete(delay=20)
    )

  @commands.Cog.listener()
  async def on_message_edit(self, before, after):
    if before.guild is None:
      return
    if before.author.bot:
      return
    bypass = before.author.guild_permissions.manage_guild
    if bypass:
      return
    await self.check_blacklist(after)

  @commands.Cog.listener()
  async def on_message(self, msg: discord.Message):
    if not msg.guild or msg.author.bot:
      return
    bypass = msg.author.guild_permissions.manage_guild if isinstance(msg.author, discord.Member) else False
    if bypass:
      return
    await self.check_blacklist(msg)

  @commands.command(name="mute", help="Mute a member from text channels")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  @commands.bot_has_guild_permissions(manage_channels=True)
  async def norm_mute(self, ctx, *, member: discord.Member):
    async with ctx.typing():
      await self.mute(ctx, member=member)

  @cog_ext.cog_slash(
      name="mute",
      description="Mute a member from text channels",
      options=[
          create_option(name="member", description="The member to mute", option_type=SlashCommandOptionType.USER, required=True)
      ]
  )
  @commands.has_guild_permissions(manage_channels=True)
  @checks.bot_has_guild_permissions(manage_channels=True)
  @checks.slash(user=True, private=False)
  async def slash_mute(self, ctx, member: discord.Member):
    await ctx.defer()
    await self.mute(ctx, member=member, slash=True)

  async def mute(self, ctx, *, member: discord.Member, slash: False):
    x = 0
    for channel in ctx.guild.text_channels:
      perms = channel.overwrites_for(member)
      if perms.send_messages is False:
        x += 1
      perms.send_messages = False
      try:
        await channel.set_permissions(member, reason="Muted!", overwrite=perms)
      except discord.Forbidden:
        pass
    if x >= len(ctx.guild.text_channels):
      if slash:
        return await ctx.send(embed=embed(title=f"`{member.name}` has already been muted", color=MessageColors.ERROR))
      return await ctx.reply(embed=embed(title=f"`{member.name}` has already been muted", color=MessageColors.ERROR))
    if slash:
      return await ctx.send(embed=embed(title=f"`{member.name}` has been muted."))
    await ctx.reply(embed=embed(title=f"`{member.name}` has been muted."))

  @commands.command(name="unmute", help="Unmute a member from text channels")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  @commands.bot_has_guild_permissions(manage_channels=True)
  async def norm_unmute(self, ctx, *, member: discord.Member):
    async with ctx.typing():
      await self.unmute(ctx, member=member)

  @cog_ext.cog_slash(
      name="unmute",
      description="Unmute a member from text channels",
      options=[
          create_option(name="member", description="The member to unmute", option_type=SlashCommandOptionType.USER, required=True)
      ]
  )
  @checks.slash(user=True, private=False)
  async def slash_unmute(self, ctx, member: discord.Member):
    await ctx.defer()
    await self.unmute(ctx, member=member, slash=True)

  async def unmute(self, ctx, *, member: discord.Member, slash: False):
    for channel in ctx.guild.text_channels:
      perms = channel.overwrites_for(member)
      perms.send_messages = None
      try:
        await channel.set_permissions(member, reason="Unmuted!", overwrite=perms if perms._values != {} else None)
      except discord.Forbidden:
        pass
    if slash:
      return await ctx.send(embed=embed(title=f"`{member.name}` has been unmuted."))
    await ctx.reply(embed=embed(title=f"`{member.name}` has been unmuted."))

  @settings_bot.command(name="language", aliases=["lang"], help="Change the language that I will speak")
  # @commands.cooldown(1, 3600, commands.BucketType.guild)
  @commands.has_guild_permissions(administrator=True)
  async def language(self, ctx, language: typing.Optional[str] = None):
    lang = ctx.guild.preferred_locale.split("-")[0]
    if language is None and ctx.guild is not None:
      language = lang

    new_lang = pycountry.languages.get(alpha_2=language) if len(language) <= 2 else pycountry.languages.get(name=language)
    if new_lang is None:
      return await ctx.reply(embed=embed(title=f"Failed to find language: `{language}`", color=MessageColors.ERROR))

    final_lang = new_lang.alpha_2 if new_lang is not None else lang
    final_lang_name = new_lang.name if new_lang is not None else lang
    await query(self.bot.mydb, "UPDATE servers SET lang=%s WHERE id=%s", final_lang, ctx.guild.id)
    self.bot.log.change_guild_lang(ctx.guild, final_lang)
    return await ctx.reply(embed=embed(title=f"New language set to: `{final_lang_name}`"))

  # @commands.Cog.listener()
  # async def on_message(self, msg):
  #   if msg.author.bot:
  #     return

  #   if not msg.guild:
  #     return

  #   if msg.guild.id != 215346091321720832:
  #     return

  #   if not validators.url(msg.clean_content) and len(msg.attachments) == 0:
  #     return

  #   ctx = await self.bot.get_context(msg)
  #   if ctx.command:
  #     return

  #   async for message in msg.channel.history(limit=None, after=datetime.datetime.today() - datetime.timedelta(days=14), oldest_first=False):
  #     if message.id != msg.id:
  #       if len(msg.attachments) > 0 and len(message.attachments) > 0:
  #         for msg_att in msg.attachments:
  #           for att in message.attachments:
  #             if msg_att.url == att.url:
  #               return await msg.add_reaction("🔁")
  #       if message.content == msg.content and message.content != "" and msg.content != "":
  #         return await msg.add_reaction("🔁")


def setup(bot):
  bot.add_cog(Moderation(bot))
