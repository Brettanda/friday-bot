import asyncio
import typing
import re
# import datetime
# import validators
from slugify import slugify
import pycountry

import discord
# import datetime

# from PIL import Image, ImageDraw
# https://code-maven.com/create-images-with-python-pil-pillow
from discord.ext import commands
from discord_slash import SlashContext, cog_ext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option
from typing_extensions import TYPE_CHECKING

from cogs.help import cmd_help
from functions import MessageColors, embed, checks, relay_info, config, MyContext

if TYPE_CHECKING:
  from index import Friday as Bot


class Moderation(commands.Cog):
  """Manage your server with these commands"""

  def __init__(self, bot: "Bot"):
    self.bot = bot

    self.invite_reg = r"(https?:\/\/)?(www\.)?(discord(app|)\.(gg)(\/invite|))\/[a-zA-Z0-9\-]+"

    self.bot.loop.create_task(self.setup())

    if not hasattr(self, "message_spam_control"):
      self.message_spam_control = {}

    if not hasattr(self, "message_spam_control_counter"):
      self.message_spam_control_counter = {}

  async def setup(self) -> None:
    if not hasattr(self, "to_remove_invites"):
      self.to_remove_invites = {}
      for guild_id, to_remove in await self.bot.db.query("SELECT id,remove_invites FROM servers"):
        self.to_remove_invites.update({int(guild_id): bool(to_remove)})

    if self.bot.cluster_idx == 0:
      await self.bot.db.query("""CREATE TABLE IF NOT EXISTS welcome
                                        (guild_id bigint PRIMARY KEY NOT NULL,
                                        role_id bigint DEFAULT NULL,
                                        channel_id bigint DEFAULT NULL,
                                        message text DEFAULT NULL)""")
      await self.bot.db.query("""CREATE TABLE IF NOT EXISTS blacklist
                                        (id bigint,
                                        word text)""")

    if not hasattr(self, "welcome"):
      self.welcome, welcome = {}, await self.bot.db.query("SELECT * FROM welcome")
      for guild_id, role_id, channel_id, message in welcome:
        self.welcome[int(guild_id)] = {"role_id": int(role_id) if role_id is not None else None, "channel_id": int(channel_id) if channel_id is not None else None, "message": str(message) if message is not None else None}

    if not hasattr(self, "blacklist"):
      blacklists = await self.bot.db.query("SELECT * FROM blacklist")
      self.blacklist = {}
      for server, word in blacklists:
        if server not in self.blacklist:
          self.blacklist[int(server)] = [word]
        else:
          self.blacklist[int(server)].append(word)

  def cog_check(self, ctx):
    if ctx.guild is None:
      raise commands.NoPrivateMessage("This command can only be used within a guild")
    return True

  @commands.Cog.listener()
  async def on_member_join(self, member: discord.Member):
    if member.pending:
      return
    await self.add_welcome_role(member)
    await self.send_welcome_message(member)

  @commands.Cog.listener()
  async def on_member_update(self, before: discord.Member, after: discord.Member):
    if before.pending is not True or after.pending is not False:
      return
    await self.add_welcome_role(after)
    await self.send_welcome_message(after)

  async def send_welcome_message(self, member: discord.Member) -> None:
    if member.guild.id not in self.welcome:
      return
    welcome = self.welcome[member.guild.id]
    channel = self.bot.get_channel(welcome.get("channel_id", None))
    if channel is None:
      return
    message = welcome["message"]
    message_variables = [r"{user}", r"{server}"]
    if any(var in message.lower() for var in message_variables):
      for var in message_variables:
        if var == r"{user}":
          message = f"{member.mention}".join(message.split(var))
        elif var == r"{server}":
          message = f"{member.guild.name}".join(message.split(var))
    await channel.send(message, allowed_mentions=discord.AllowedMentions.none())

  async def add_welcome_role(self, member: discord.Member) -> None:
    if member.guild.id not in self.welcome:
      return
    role_id = self.welcome[member.guild.id]["role_id"]
    if role_id is None or str(role_id).lower() == "null":
      return
    else:
      role = member.guild.get_role(role_id)
      if role is None:
        # await member.guild.owner.send(f"The default role that was chosen for me to add to members when they join yours server \"{member.guild.name}\" could not be found, please update the default role at https://friday-self.bot.com")
        await self.bot.db.query("UPDATE welcome SET role_id=NULL WHERE guild_id=$1", member.guild.id)
      else:
        await member.add_roles(role, reason="Welcome Role")

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
  @commands.has_guild_permissions(administrator=True)
  async def _prefix(self, ctx: "MyContext", new_prefix: typing.Optional[str] = config.defaultPrefix):
    new_prefix = new_prefix.lower()
    if len(new_prefix) > 5:
      return await ctx.reply(embed=embed(title="Can't set a prefix with more than 5 characters", color=MessageColors.ERROR))
    await self.bot.db.query("UPDATE servers SET prefix=$1 WHERE id=$2", str(new_prefix), int(ctx.guild.id))
    self.bot.prefixes[ctx.guild.id] = str(new_prefix)
    await ctx.reply(embed=embed(title=f"My new prefix is `{new_prefix}`"))

  # @commands.group(name="set", invoke_without_command=True, case_insensitive=True)
  # @commands.guild_only()
  # @commands.has_guild_permissions(manage_channels=True)
  # async def settings_bot(self, ctx):
  #   await cmd_help(ctx, ctx.command)

  # @cog_ext.cog_slash(name="bot", description="Bot settings")
  # @commands.has_guild_permissions(manage_channels=True)
  # @checks.slash(user=True, private=False)
  # async def slash_settings_bot(self, ctx):
  #   print("askjdhla")

  @commands.group(name="welcome", invoke_without_command=True, case_insensitive=True, help="Friday's settings for welcomeing new members to your servers")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_roles=True, manage_guild=True, manage_channels=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def _welcome(self, ctx: "MyContext"):
    await ctx.send_help(ctx.command)

  @_welcome.command(name="display", aliases=["list", "show"], help="Shows the servers current welcome settings")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_roles=True, manage_guild=True, manage_channels=True)
  async def _welcome_display(self, ctx: "MyContext"):
    if ctx.guild.id not in self.welcome:
      return await ctx.reply(embed=embed(title="This server hasn't set any welcome settings", color=MessageColors.ERROR))
    guild = self.welcome[ctx.guild.id]
    role_id, channel_id, message = guild['role_id'], guild['channel_id'], guild["message"]
    await ctx.reply(embed=embed(
        title="Current Welcome Settings",
        fieldstitle=["Role", "Channel", "Message"],
        fieldsval=[f"<@&{role_id}>"if role_id is not None else None, f"<#{channel_id}>" if channel_id is not None else None, f"{message}"],
        fieldsin=[False, False, False]
    ))

  @_welcome.command(name="role", extras={"examples": ["@default", "12345678910"]}, help="Set the role that is given to new members when they join the server")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_roles=True, manage_guild=True, manage_channels=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def _welcome_role(self, ctx: "MyContext", role: typing.Optional[discord.Role] = None):
    role_id = role.id if role is not None else None
    await self.bot.db.query("INSERT INTO welcome (guild_id,role_id) VALUES ($1,$2) ON CONFLICT(guild_id) DO UPDATE SET role_id=$3", ctx.guild.id, role_id, role_id)
    if ctx.guild.id in self.welcome:
      self.welcome[ctx.guild.id]["role_id"] = role_id
    else:
      self.welcome.update({"role_id": role_id, "channel_id": None, "message": None})
    await ctx.reply(embed=embed(title=f"New members will now receive the role `{role}`"))

  @_welcome.command(name="channel", extras={"examples": ["#welcome", "#general", "707458929696702525"]}, help="Setup a welcome channel for Friday to welcome new memebers in")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_guild=True, manage_channels=True)
  async def _welcome_channel(self, ctx: "MyContext", channel: typing.Optional[discord.TextChannel] = None):
    if channel is not None:
      if channel.permissions_for(ctx.guild.me).send_messages is False:
        return await ctx.reply(embed=embed(title=f"I don't have send_permissions in {channel}", color=MessageColors.ERROR))
    channel_id = channel.id if channel is not None else None
    await self.bot.db.query("INSERT INTO welcome (guild_id,channel_id) VALUES ($1,$2) ON CONFLICT(guild_id) DO UPDATE SET channel_id=$3", ctx.guild.id, channel_id, channel_id)
    if ctx.guild.id in self.welcome:
      self.welcome[ctx.guild.id]["channel_id"] = channel_id
    else:
      self.welcome.update({"role_id": None, "channel_id": channel_id, "message": None})
    await ctx.reply(embed=embed(title=f"Welcome message will be sent to `{channel}`", description="" if self.welcome[ctx.guild.id]["message"] is not None else "Don't forget to set a welcome message"))

  @_welcome.command(name="message", extras={"examples": [r"Welcome to the server {user}, stay a while!", r"Welcome {user} to {server}", "A new member has joined the server!"]}, help="Set a message to greet new members to your server, message variables are `{user}`,`{server}`")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_guild=True, manage_channels=True)
  async def _welcome_message(self, ctx: "MyContext", *, message: typing.Optional[str] = None):
    if len(message) > 255:
      await ctx.reply(embed=embed(title="Welcome messages can't be longer than 255 characters", color=MessageColors.ERROR))
    await self.bot.db.query("INSERT INTO welcome (guild_id,message) VALUES ($1,$2) ON CONFLICT(guild_id) DO UPDATE SET message=$3", ctx.guild.id, message, message)
    if ctx.guild.id in self.welcome:
      self.welcome[ctx.guild.id]["message"] = message
    else:
      self.welcome.update({"role_id": None, "channel_id": None, "message": message})
    formated_message, message_variables = message, [r"{user}", r"{server}"]
    if any(var in message.lower() for var in message_variables):
      for var in message_variables:
        if var == r"{user}":
          formated_message = f"@{ctx.author.name}".join(formated_message.split(var))
        elif var == r"{server}":
          formated_message = f"{ctx.guild.name}".join(formated_message.split(var))
    await ctx.reply(embed=embed(title="This servers welcome message is now", description=f"```{message}```\n\nThis will look like\n```{formated_message}```" + ("" if self.welcome[ctx.guild.id]["channel_id"] is not None else "\n\n**Don't forget to set a welcome channel**")))

  @commands.command(name="chatchannel", help="Set the current channel so that I will always try to respond with something")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def norm_chatchannel(self, ctx):
    post = await self.settings_bot_chat_channel(ctx)
    await ctx.reply(**post)

  @cog_ext.cog_slash(name="chatchannel", description="Set the current text channel so that I will always try to respond")
  @commands.has_guild_permissions(manage_channels=True)
  @checks.slash(user=True, private=False)
  async def slash_chatchannel(self, ctx):
    await ctx.defer()
    post = await self.settings_bot_chat_channel(ctx)
    await ctx.send(**post)

  async def settings_bot_chat_channel(self, ctx):
    chat_channel = await self.bot.db.query("SELECT chatChannel FROM servers WHERE id=$1", ctx.guild.id)
    if chat_channel is None:
      await self.bot.db.query("UPDATE servers SET chatChannel=$1 WHERE id=$2", ctx.channel.id, ctx.guild.id)
      self.bot.log.change_guild_chat_channel(ctx.guild.id, ctx.channel.id)
      return dict(embed=embed(title="I will now respond to every message in this channel"))
    else:
      await self.bot.db.query("UPDATE servers SET chatChannel=$1 WHERE id=$2", None, ctx.guild.id)
      self.bot.log.change_guild_chat_channel(ctx.guild.id, None)
      return dict(embed=embed(title="I will no longer respond to all messages from this channel"))

  @commands.command(name="removeinvites", help="Automaticaly remove Discord invites from text channels", hidden=True)
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  @commands.bot_has_guild_permissions(manage_messages=True)
  async def norm_remove_discord_invites(self, ctx):
    check = await self.bot.db.query("SELECT remove_invites FROM servers WHERE id=$1", ctx.guild.id)
    if bool(check) is True:
      await self.bot.db.query("UPDATE servers SET remove_invites=$1 WHERE id=$2", False, ctx.guild.id)
      self.to_remove_invites[ctx.guild.id] = False
      await ctx.reply(embed=embed(title="I will no longer remove invites"))
    else:
      await self.bot.db.query("UPDATE servers SET remove_invites=$1 WHERE id=$2", True, ctx.guild.id)
      self.to_remove_invites[ctx.guild.id] = True
      await ctx.reply(embed=embed(title="I will begin to remove invites"))

  async def msg_remove_invites(self, msg: discord.Message):
    if not msg.guild or msg.author.bot:
      return

    try:
      if self.to_remove_invites[msg.guild.id] is True:
        reg = re.match(self.invite_reg, msg.clean_content, re.RegexFlag.MULTILINE + re.RegexFlag.IGNORECASE)
        check = bool(reg)
        if check:
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

  @commands.command(name="musicchannel", help="Set the channel where I can join and play music. If none then I will join any VC", hidden=True)
  @commands.is_owner()
  @commands.has_guild_permissions(manage_channels=True)
  async def music_channel(self, ctx, voicechannel: typing.Optional[discord.VoiceChannel] = None):
    async with ctx.typing():
      await self.bot.db.query("UPDATE servers SET musicChannel=$1 WHERE id=$2", voicechannel.id if voicechannel is not None else None, ctx.guild.id)
    if voicechannel is None:
      await ctx.reply(embed=embed(title="All the voice channels are my music channels 😈 (jk)"))
    else:
      await ctx.reply(embed=embed(title=f"`{voicechannel}` is now my music channel"))

  @commands.command(name="deletecommandsafter", extras={"examples": ["0", "180"]}, aliases=["deleteafter", "delcoms"], help="Set the time in seconds for how long to wait before deleting command messages")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def delete_commands_after(self, ctx, time: typing.Optional[int] = 0):
    if time < 0:
      await ctx.reply(embed=embed(title="time has to be above 0"))
      return
    async with ctx.typing():
      await self.bot.db.query("UPDATE servers SET autoDeleteMSGs=$1 WHERE id=$2", time, ctx.guild.id)
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
              await relay_info(f"Error when trying to remove message {type(e).__name__}: {e}", self.bot, logger=self.bot.log.log_errors)
    except Exception as e:
      await relay_info(f"Error when trying to remove message (big) {type(e).__name__}: {e}", self.bot, logger=self.bot.log.log_errors)

  @commands.group(name="blacklist", aliases=["bl"], invoke_without_command=True, case_insensitive=True, help="Blacklist words from being sent in text channels")
  @commands.guild_only()
  async def _blacklist(self, ctx: "MyContext"):
    await ctx.send_help(ctx.command)
    # await cmd_help(ctx, ctx.command)

  @_blacklist.command(name="add", aliases=["+"], extras={"examples": ["penis", "shit"]})
  @commands.guild_only()
  @commands.has_guild_permissions(manage_guild=True)
  async def _blacklist_add_word(self, ctx, *, word: str):
    cleansed_word = self.do_slugify(word)
    await self.bot.db.query("INSERT INTO blacklist VALUES ($1,$2) ON CONFLICT DO NOTHING", ctx.guild.id, cleansed_word)
    try:
      self.blacklist[ctx.guild.id].append(cleansed_word)
    except KeyError:
      self.blacklist[ctx.guild.id] = [cleansed_word]
    word = word
    await ctx.reply(embed=embed(title=f"Added `{word}` to the blacklist"))

  @_blacklist.command(name="remove", aliases=["-"], extras={"examples": ["penis", "shit"]})
  @commands.guild_only()
  @commands.has_guild_permissions(manage_guild=True)
  async def _blacklist_remove_word(self, ctx, *, word: str):
    cleansed_word = word
    if cleansed_word not in self.blacklist[ctx.guild.id]:
      return await ctx.reply(embed=embed(title="You don't seem to blacklisting that word"))
    await self.bot.db.query("DELETE FROM blacklist WHERE (id=$1 AND word=$2)", ctx.guild.id, cleansed_word)
    self.blacklist[ctx.guild.id].remove(cleansed_word)
    word = word
    await ctx.reply(embed=embed(title=f"Removed `{word}` from the blacklist"))

  @_blacklist.command(name="display", aliases=["list", "show"])
  @commands.guild_only()
  @commands.has_guild_permissions(manage_guild=True)
  async def _blacklist_display_words(self, ctx):
    words = await self.bot.db.query("SELECT word FROM blacklist WHERE id=$1", ctx.guild.id, rlist=True)
    if words == [] or words is None:
      return await ctx.reply(embed=embed(title=f"No blacklisted words yet, use `{ctx.prefix}blacklist add <word>` to get started"))
    await ctx.reply(embed=embed(title="Blocked words", description='\n'.join(x[0] for x in words)))

  @_blacklist.command(name="clear")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_guild=True)
  async def _blacklist_clear(self, ctx):
    await self.bot.db.query("DELETE FROM blacklist WHERE id=$1", ctx.guild.id)
    self.blacklist[ctx.guild.id] = []
    await ctx.reply(embed=embed(title="Removed all blacklisted words"))

  @commands.command(name="kick", extras={"examples": ["@username @someone @someoneelse", "@thisguy", "12345678910 10987654321 @someone", "@someone I just really didn't like them", "@thisguy 12345678910 They were spamming general"]})
  @commands.bot_has_guild_permissions(kick_members=True)
  @commands.has_guild_permissions(kick_members=True)
  async def norm_kick(self, ctx, members: commands.Greedy[discord.Member], *, reason: typing.Optional[str] = None):
    await self.kick(ctx, members, reason)

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
  async def slash_kick(self, ctx, member: discord.Member, reason=None):
    await self.kick(ctx, [member], reason, True)

  async def kick(self, ctx, members, reason=None, slash: bool = False):
    if isinstance(members, list) and len(members) == 0 and not slash:
      await cmd_help(ctx, ctx.command)

    tokick = []

    if not isinstance(members, list):
      members = list(members)

    if self.bot.user in members:
      if slash:
        return await ctx.send(hidden=True, content="But I don't want to kick myself 😭")
      return await ctx.reply(embed=embed(title="But I don't want to kick myself 😭", color=MessageColors.ERROR))

    if ctx.author in members:
      if slash:
        return await ctx.send(hidden=True, content="Failed to kick yourself")
      return await ctx.reply(embed=embed(title="Failed to kick yourself", color=MessageColors.ERROR))

    for member in members:
      pos = ctx.guild.me.top_role.position
      uspos = member.top_role.position

      if pos == uspos:
        if slash:
          return await ctx.send(hidden=True, content="I am not able to kick a member in the same highest role as me.")
        return await ctx.reply(embed=embed(title="I am not able to kick a member in the same highest role as me.", color=MessageColors.ERROR))

      if pos < uspos:
        if slash:
          return await ctx.send(hidden=True, content="I am not able to kick a member with a role higher than my own permissions role(s)")
        return await ctx.reply(embed=embed(title="I am not able to kick a member with a role higher than my own permissions role(s)", color=MessageColors.ERROR))

    if self.bot.user in members and not slash:
      try:
        await ctx.add_reaction("😢")
      except BaseException:
        pass
      return

    kicks = []
    for member in members:
      tokick.append(member.name)
      kicks.append(member.kick(reason=f"{ctx.author}: {reason}"))
    await asyncio.gather(*kicks)

    if slash:
      return await ctx.send(embed=embed(title=f"Kicked `{', '.join(tokick)}`{(' for reason `' + reason+'`') if reason is not None else ''}"))
    return await ctx.reply(embed=embed(title=f"Kicked `{', '.join(tokick)}`{(' for reason `' + reason+'`') if reason is not None else ''}"))

  @commands.command(name="ban", extras={"examples": ["@username @someone @someoneelse Spam", "@thisguy The most spam i have ever seen", "12345678910 10987654321 @someone", "@someone They were annoying me", "123456789 2 Sus"]})
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

  @commands.command(name="rolecall", aliases=["rc"], extras={"examples": ["@mods vc-1", "123456798910 vc-2 vc-1 10987654321", "@admins general @username @username"]}, help="Moves everyone with a specific role to a voicechannel. Objects that can be exluded are voicechannels,roles,and members")
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

  @commands.command(name="massmove", aliases=["move"], extras={"examples": ["general", "vc-2 general", "'long voice channel' general"]}, help="Move everyone from one voice channel to another")
  @commands.guild_only()
  @commands.has_guild_permissions(move_members=True)
  @commands.bot_has_guild_permissions(move_members=True)
  async def norm_massmove(self, ctx, tochannel: typing.Union[discord.VoiceChannel, discord.StageChannel] = None, fromchannel: typing.Optional[typing.Union[discord.VoiceChannel, discord.StageChannel]] = None):
    await self.mass_move(ctx, tochannel, fromchannel)

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
  async def slash_massmove(self, ctx, tochannel, fromchannel=None):
    await self.mass_move(ctx, tochannel, fromchannel)

  async def mass_move(self, ctx: "MyContext", toChannel: discord.VoiceChannel, fromChannel: discord.VoiceChannel = None):
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

  @commands.command(name="begone", extras={"examples": ["https://discord.com/channels/707441352367013899/707458929696702525/707520808448294983", "707520808448294983"]}, help="Delete unwanted message that I send")
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
    await self.msg_remove_invites(after)
    await self.check_blacklist(after)

  @commands.Cog.listener()
  async def on_message(self, msg: discord.Message):
    if not msg.guild or msg.author.bot:
      return
    bypass = msg.author.guild_permissions.manage_guild if isinstance(msg.author, discord.Member) else False
    if bypass:
      return
    await self.msg_remove_invites(msg)
    await self.check_blacklist(msg)

  @commands.command(name="mute", extras={"examples": ["@Motostar @steve", "@steve 9876543210", "@Motostar", "0123456789"]}, help="Mute a member from text channels")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True, manage_roles=True)
  @commands.bot_has_guild_permissions(view_channel=True, manage_channels=True, manage_roles=True)
  async def norm_mute(self, ctx: "MyContext", members: commands.Greedy[discord.Member]):
    if len(members) == 0:
      return await cmd_help(ctx, ctx.command, "You're missing some arguments, here is how the command should look")
    async with ctx.typing():
      await self.mute(ctx, members)

  @cog_ext.cog_slash(
      name="mute",
      description="Mute a member from text channels",
      options=[
          create_option(name="member", description="The member to mute", option_type=SlashCommandOptionType.USER, required=True)
      ]
  )
  @commands.has_guild_permissions(manage_channels=True, manage_roles=True)
  @checks.bot_has_guild_permissions(view_channel=True, manage_channels=True, manage_roles=True)
  @checks.slash(user=True, private=False)
  async def slash_mute(self, ctx: SlashContext, member: discord.Member):
    await ctx.defer(hidden=True)
    await self.mute(ctx, [member], True)

  async def mute(self, ctx: "MyContext", members: [discord.Member], slash: bool = False):
    if len(members) == 0:
      if slash:
        return await ctx.send(hidden=True, embed=embed(title="Failed to find that member", color=MessageColors.ERROR))
      return await ctx.send(embed=embed(title="Failed to find that member", color=MessageColors.ERROR))
    roles = [r for r in await ctx.guild.fetch_roles() if r.name == "Muted" and not r.is_bot_managed() and not r.managed and not r.is_premium_subscriber() and not r.is_integration()]
    muted_role: discord.Role = roles[0] if len(roles) > 0 else None
    if muted_role is None:
      muted_role: discord.Role = await ctx.guild.create_role(name="Muted", permissions=discord.Permissions.none(), colour=discord.Colour.light_grey(), hoist=False, mentionable=False)
      try:
        for channel in ctx.guild.channels:
          await channel.set_permissions(muted_role, send_messages=False, use_private_threads=False, use_threads=False, speak=False, add_reactions=False)
      except discord.Forbidden:
        await muted_role.delete()
        return await ctx.send(embed=embed(title="I require Administrator permissions to build this `Muted` role.", color=MessageColors.ERROR))
    has_been_muted, not_muted = [], []
    for member in members:
      if muted_role in member.roles:
        not_muted.append(member.name)
      else:
        try:
          await member.add_roles(muted_role)
        except Exception as e:
          raise e
        else:
          has_been_muted.append(member.name)
    if len(has_been_muted) == 0 and len(not_muted) > 0:
      if slash:
        return await ctx.send(hidden=True, embed=embed(title=f"Already muted: `{', '.join(not_muted)}`", color=MessageColors.ERROR))
      return await ctx.send(embed=embed(title=f"Already muted: `{', '.join(not_muted)}`", color=MessageColors.ERROR))
    if slash:
      return await ctx.send(hidden=True, embed=embed(title=f"`{', '.join(has_been_muted)}` {'has' if len(has_been_muted) <= 1 else 'have'} been muted.", description="" if len(not_muted) == 0 else ("Already muted: " + ", ".join(not_muted) + "`")))
    await ctx.send(embed=embed(title=f"`{', '.join(has_been_muted)}` {'has' if len(has_been_muted) <= 1 else 'have'} been muted.", description="" if len(not_muted) == 0 else ("Already muted: `" + ", ".join(not_muted) + "`")))

  @commands.command(name="unmute", extras={"examples": ["@Motostar @steve", "@steve 9876543210", "@Motostar", "0123456789"]}, help="Unmute a member from text channels")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True, manage_roles=True)
  @commands.bot_has_guild_permissions(manage_channels=True, manage_roles=True)
  async def norm_unmute(self, ctx: "MyContext", members: commands.Greedy[discord.Member]):
    if len(members) == 0:
      return await cmd_help(ctx, ctx.command, "You're missing some arguments, here is how the command should look")
    async with ctx.typing():
      await self.unmute(ctx, members)

  @cog_ext.cog_slash(
      name="unmute",
      description="Unmute a member from text channels",
      options=[
          create_option(name="member", description="The member to unmute", option_type=SlashCommandOptionType.USER, required=True)
      ]
  )
  @checks.slash(user=True, private=False)
  async def slash_unmute(self, ctx, member: discord.Member):
    await ctx.defer(hidden=True)
    await self.unmute(ctx, [member], True)

  async def unmute(self, ctx, members: [discord.Member], slash: bool = False):
    roles = [r for r in await ctx.guild.fetch_roles() if r.name == "Muted" and not r.is_bot_managed() and not r.managed and not r.is_premium_subscriber() and not r.is_integration()]
    muted_role: discord.Role = roles[0] if len(roles) > 0 else None
    if not muted_role:
      return await ctx.send(embed=embed(title="No one has been muted yet", colors=MessageColors.ERROR))
    has_been_unmuted, not_unmuted = [], []
    for member in members:
      if muted_role not in member.roles:
        not_unmuted.append(member.name)
      else:
        try:
          await member.remove_roles(muted_role)
        except Exception as e:
          raise e
        else:
          has_been_unmuted.append(member.name)
    if len(has_been_unmuted) == 0 and len(not_unmuted) > 0:
      if slash:
        return await ctx.send(hidden=True, embed=embed(title=f"Wasn't muted: `{', '.join(not_unmuted)}`", color=MessageColors.ERROR))
      return await ctx.send(embed=embed(title=f"Wasn't muted: `{', '.join(not_unmuted)}`", color=MessageColors.ERROR))
    if slash:
      return await ctx.send(hidden=True, embed=embed(title=f"`{', '.join(has_been_unmuted)}` {'has' if len(has_been_unmuted) <= 1 else 'have'} been unmuted.", description="" if len(not_unmuted) == 0 else ("Wasn't muted: " + ", ".join(not_unmuted) + "`")))
    await ctx.send(embed=embed(title=f"`{', '.join(has_been_unmuted)}` {'has' if len(has_been_unmuted) <= 1 else 'have'} been unmuted.", description="" if len(not_unmuted) == 0 else ("Wasn't muted: " + ", ".join(not_unmuted) + "`")))

  @commands.command(name="language", extras={"examples": ["en", "es", "english", "spanish"]}, aliases=["lang"], help="Change the language that I will speak")
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
    await self.bot.db.query("UPDATE servers SET lang=$1 WHERE id=$2", final_lang, ctx.guild.id)
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
