import asyncio
import typing
import datetime
import validators

import discord
from discord.ext import commands
from discord_slash import SlashContext, cog_ext, SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option

from cogs.help import cmd_help
from functions import MessageColors, embed, mydb_connect, query, checks, relay_info, config


class ServerManage(commands.Cog):
  """Commands for managing Friday on your server"""

  def __init__(self, bot):
    self.bot = bot

  def cog_check(self, ctx):
    if ctx.guild is None:
      raise commands.NoPrivateMessage("This command can only be used within a guild")
    return True

  @commands.command(name="defaultrole", hidden=True)
  @commands.is_owner()
  @commands.has_guild_permissions(manage_roles=True)
  async def _defaultrole(self, ctx, role: discord.Role):
    # TODO: Need the members intent so assign the role
    mydb = mydb_connect()
    query(mydb, "UPDATE servers SET defaultRole=%s WHERE id=%s", role.id, ctx.guild.id)
    try:
      await ctx.reply(embed=embed(title=f"The new default role for new members is `{role}`"))
    except discord.Forbidden:
      await ctx.reply(f"The new default role for new members is `{role}`")

  # @commands.command(name="mute")
  # @commands.is_owner()
  # @commands.has_guild_permissions(manage_roles=True)
  # async def mute(self,ctx,members:commands.Greedy[discord.Member]=None):
  #   if self.bot.user in members:
  #     mydb = mydb_connect()
  #     muted = query(mydb,"SELECT muted FROM servers WHERE id=%s",ctx.guild.id)
  #     if muted == 0:
  #       query(mydb,"UPDATE servers SET muted=%s WHERE id=%s",1,ctx.guild.id)
  #       await ctx.reply(embed=embed(title="I will now only respond to commands"))
  #     else:
  #       query(mydb,"UPDATE servers SET muted=%s WHERE id=%s",0,ctx.guild.id)
  #       await ctx.reply(embed=embed(title="I will now respond to chat message as well as commands"))

  @commands.command(name="prefix")
  @commands.has_guild_permissions(administrator=True)
  async def _prefix(self, ctx, new_prefix: typing.Optional[str] = config.defaultPrefix):
    new_prefix = new_prefix.lower()
    if len(new_prefix) > 5:
      await ctx.reply(embed=embed(title="Can't set a prefix with more than 5 characters", color=MessageColors.ERROR))
      return
    mydb = mydb_connect()
    query(mydb, "UPDATE servers SET prefix=%s WHERE id=%s", new_prefix, ctx.guild.id)
    self.bot.change_guild_prefix(ctx.guild.id, new_prefix)
    try:
      await ctx.reply(embed=embed(title=f"My new prefix is `{new_prefix}`"))
    except discord.Forbidden:
      await ctx.reply(f"My new prefix is `{new_prefix}`")

  @commands.group(name="bot", invoke_without_command=True)
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

  @cog_ext.cog_subcommand(base="bot", base_description="Bot settings", name="mute", description="Stop me from responding to non-command messages or not")
  @commands.has_guild_permissions(manage_channels=True)
  @checks.slash(user=True, private=False)
  async def slash_settings_bot_mute(self, ctx):
    post = await self.settings_bot_mute(ctx)
    await ctx.send(**post)

  async def settings_bot_mute(self, ctx):
    mydb = mydb_connect()
    muted = query(mydb, "SELECT muted FROM servers WHERE id=%s", ctx.guild.id)
    if muted == 0:
      query(mydb, "UPDATE servers SET muted=%s WHERE id=%s", 1, ctx.guild.id)
      return dict(embed=embed(title="I will now only respond to commands"))
    else:
      query(mydb, "UPDATE servers SET muted=%s WHERE id=%s", 0, ctx.guild.id)
      return dict(embed=embed(title="I will now respond to chat message as well as commands"))

  @settings_bot.command(name="chatchannel", alias="chat", description="Set the current channel so that I will always try to respond with something")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def norm_settings_bot_chat_channel(self, ctx):
    post = await self.settings_bot_chat_channel(ctx)
    await ctx.reply(**post)

  @cog_ext.cog_subcommand(base="bot", base_description="Bot settings", name="chatchannel", description="Set the current text channel so that I will always try to respond")
  @commands.has_guild_permissions(manage_channels=True)
  @checks.slash(user=True, private=False)
  async def slash_settings_bot_chat_channel(self, ctx):
    await ctx.defer()
    post = await self.settings_bot_chat_channel(ctx)
    await ctx.send(**post)

  async def settings_bot_chat_channel(self, ctx):
    mydb = mydb_connect()
    chat_channel = query(mydb, "SELECT chatChannel FROM servers WHERE id=%s", ctx.guild.id)
    if chat_channel is None:
      query(mydb, "UPDATE servers SET chatChannel=%s WHERE id=%s", ctx.channel.id, ctx.guild.id)
      self.bot.change_guild_chat_channel(ctx.guild.id, ctx.channel.id)
      return dict(embed=embed(title="I will now (try to) respond to every message in this channel"))
    else:
      query(mydb, "UPDATE servers SET chatChannel=%s WHERE id=%s", None, ctx.guild.id)
      self.bot.change_guild_chat_channel(ctx.guild.id, None)
      return dict(embed=embed(title="I will no longer (try to) respond to all messages from this channel"))

  @commands.command(name="musicchannel", description="Set the channel where I can join and play music. If none then I will join any VC", hidden=True)
  @commands.is_owner()
  @commands.has_guild_permissions(manage_channels=True)
  async def music_channel(self, ctx, voicechannel: typing.Optional[discord.VoiceChannel] = None):
    async with ctx.typing():
      mydb = mydb_connect()
      query(mydb, "UPDATE servers SET musicChannel=%s WHERE id=%s", voicechannel.id if voicechannel is not None else None, ctx.guild.id)
    if voicechannel is None:
      await ctx.reply(embed=embed(title="All the voice channels are my music channels 😈 (jk)"))
    else:
      await ctx.reply(embed=embed(title=f"`{voicechannel}` is now my music channel"))

  @commands.command(name="deletecommandsafter", aliases=["deleteafter", "delcoms"], description="Set the time in seconds for how long to wait before deleting command messages")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  @commands.bot_has_guild_permissions(manage_channels=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def delete_commands_after(self, ctx, time: typing.Optional[int] = 0):
    if time < 0:
      await ctx.reply(embed=embed(title="time has to be above 0"))
      return
    async with ctx.typing():
      mydb = mydb_connect()
      query(mydb, "UPDATE servers SET autoDeleteMSGs=%s WHERE id=%s", time, ctx.guild.id)
      self.bot.change_guild_delete(ctx.guild.id, time)
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

  @commands.command(name="rolecall", aliases=["rc"], description="Moves everyone with a specific role to a voicechannel. Objects that can be exluded are voicechannels,roles,and members")
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

  @commands.command(name="massmove", aliases=["move"])
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

  @commands.command(name="lock", description="Sets your voice channels user limit to the current number of occupants", hidden=True)
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

  @commands.command(name="begone", description="Delete unwanted message that I send")
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
            webhook=self.bot.log_chat
        ),
        message.delete(),
        ctx.reply(embed=embed(title="Message has been removed"), delete_after=20),
        ctx.message.delete(delay=20)
    )

  @commands.Cog.listener()
  async def on_message(self, msg):
    if msg.author.bot:
      return

    if not msg.guild:
      return

    if msg.guild.id != 215346091321720832:
      return

    if not validators.url(msg.clean_content) and len(msg.attachments) == 0:
      return

    ctx = await self.bot.get_context(msg)
    if ctx.command:
      return

    async for message in msg.channel.history(limit=None, after=datetime.datetime.today() - datetime.timedelta(days=14), oldest_first=False):
      if message.id != msg.id:
        if len(msg.attachments) > 0 and len(message.attachments) > 0:
          for msg_att in msg.attachments:
            for att in message.attachments:
              if msg_att.url == att.url:
                return await msg.add_reaction("🔁")
        if message.content == msg.content and message.content != "" and msg.content != "":
          return await msg.add_reaction("🔁")


def setup(bot):
  bot.add_cog(ServerManage(bot))
