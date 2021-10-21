import nextcord as discord
from nextcord.ext import commands

from functions import embed, MyContext, MessageColors

import typing

if typing.TYPE_CHECKING:
  from index import Friday as Bot


class Welcome(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.bot = bot

  def __repr__(self):
    return "<cogs.Welcome>"

  # async def setup(self):
  #   if not hasattr(self, "welcome"):
  #     self.welcome, welcome = {}, await self.bot.db.query("SELECT * FROM welcome")
  #     for guild_id, role_id, channel_id, message in welcome:
  #       self.welcome[int(guild_id)] = {"role_id": int(role_id) if role_id is not None else None, "channel_id": int(channel_id) if channel_id is not None else None, "message": str(message) if message is not None else None}

  def cog_check(self, ctx: MyContext) -> bool:
    return ctx.guild is not None

  async def cog_command_error(self, ctx, error):
    if isinstance(error, commands.CheckFailure):
      return commands.NoPrivateMessage()

  @commands.Cog.listener()
  async def on_member_join(self, member: discord.Member):
    if member.pending is not False:
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
    welcome = await self.bot.db.query("SELECT channel_id,message FROM welcome WHERE guild_id=$1 LIMIT 1", str(member.guild.id))
    if welcome is None:
      return
    channel_id, message = welcome
    if channel_id is None or message is None:
      return
    channel = self.bot.get_channel(int(channel_id))
    if channel is None:
      return
    message_variables = [r"{user}", r"{server}"]
    if any(var in message.lower() for var in message_variables):
      for var in message_variables:
        if var == r"{user}":
          message = f"{member.mention}".join(message.split(var))
        elif var == r"{server}":
          message = f"{member.guild.name}".join(message.split(var))
    await channel.send(message, allowed_mentions=discord.AllowedMentions(users=True))

  async def add_welcome_role(self, member: discord.Member) -> None:
    role_id = await self.bot.db.query("SELECT role_id FROM welcome WHERE guild_id=$1 LIMIT 1", str(member.guild.id))
    if role_id is None or str(role_id).lower() == "null" or str(role_id).lower() == "none":
      return
    role = member.guild.get_role(int(role_id))
    if role is None:
      return await self.bot.db.query("UPDATE welcome SET role_id=NULL WHERE guild_id=$1", str(member.guild.id))
    await member.add_roles(role, reason="Welcome Role")

  @commands.group(name="welcome", invoke_without_command=True, case_insensitive=True, help="Friday's settings for welcomeing new members to your servers")
  @commands.has_guild_permissions(manage_roles=True, manage_guild=True, manage_channels=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def _welcome(self, ctx: "MyContext"):
    return await self._welcome_display(ctx)

  @_welcome.command(name="display", aliases=["list", "show"], help="Shows the servers current welcome settings")
  @commands.has_guild_permissions(manage_roles=True, manage_guild=True, manage_channels=True)
  async def _welcome_display(self, ctx: "MyContext"):
    guild_id, role_id, channel_id, message = await self.bot.db.query("SELECT guild_id,role_id,channel_id,message FROM welcome WHERE guild_id=$1 LIMIT 1", str(ctx.guild.id))
    if str(ctx.guild.id) != guild_id:
      return await ctx.reply(embed=embed(title="This server hasn't set any welcome settings", color=MessageColors.ERROR))
    await ctx.reply(embed=embed(
        title="Current Welcome Settings",
        fieldstitle=["Role", "Channel", "Message"],
        fieldsval=[f"<@&{role_id}>"if str(role_id) != str(None) else "None", f"<#{channel_id}>" if str(channel_id) != str(None) else "None", f"{message}" if message != "" else "None"],
        fieldsin=[False, False, False]
    ))

  @_welcome.command(name="role", extras={"examples": ["@default", "12345678910"]}, help="Set the role that is given to new members when they join the server")
  @commands.has_guild_permissions(manage_roles=True, manage_guild=True, manage_channels=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def _welcome_role(self, ctx: "MyContext", role: typing.Optional[discord.Role] = None):
    role_id = role.id if role is not None else None
    await self.bot.db.query("INSERT INTO welcome (guild_id,role_id) VALUES ($1,$2) ON CONFLICT(guild_id) DO UPDATE SET role_id=$2", str(ctx.guild.id), str(role_id))
    await ctx.reply(embed=embed(title=f"New members will now receive the role `{role}`"))

  @_welcome.command(name="channel", extras={"examples": ["#welcome", "#general", "707458929696702525"]}, help="Setup a welcome channel for Friday to welcome new memebers in")
  @commands.has_guild_permissions(manage_guild=True, manage_channels=True)
  async def _welcome_channel(self, ctx: "MyContext", channel: typing.Optional[discord.TextChannel] = None):
    if channel is not None:
      if channel.permissions_for(ctx.guild.me).send_messages is False:
        return await ctx.reply(embed=embed(title=f"I don't have send_permissions in {channel}", color=MessageColors.ERROR))
    channel_id = channel.id if channel is not None else None
    await self.bot.db.query("INSERT INTO welcome (guild_id,channel_id) VALUES ($1,$2) ON CONFLICT(guild_id) DO UPDATE SET channel_id=$2", str(ctx.guild.id), str(channel_id))
    message = await self.bot.db.query("SELECT message FROM welcome WHERE guild_id=$1 LIMIT 1", str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"Welcome message will be sent to `{channel}`", description="" if message is not None else "Don't forget to set a welcome message"))

  @_welcome.command(name="message", extras={"examples": [r"Welcome to the server {user}, stay a while!", r"Welcome {user} to {server}", "A new member has joined the server!"]}, help="Set a message to greet new members to your server, message variables are `{user}`,`{server}`")
  @commands.has_guild_permissions(manage_guild=True, manage_channels=True)
  async def _welcome_message(self, ctx: "MyContext", *, message: typing.Optional[str] = None):
    if message is not None and len(message) > 255:
      await ctx.reply(embed=embed(title="Welcome messages can't be longer than 255 characters", color=MessageColors.ERROR))
    await self.bot.db.query("INSERT INTO welcome (guild_id,message) VALUES ($1,$2) ON CONFLICT(guild_id) DO UPDATE SET message=$2", str(ctx.guild.id), message)
    formated_message, message_variables = message, [r"{user}", r"{server}"]
    if message is not None and any(var in message.lower() for var in message_variables):
      for var in message_variables:
        if var == r"{user}":
          formated_message = f"@{ctx.author.name}".join(formated_message.split(var))
        elif var == r"{server}":
          formated_message = f"{ctx.guild.name}".join(formated_message.split(var))
    channel_id = await self.bot.db.query("SELECT channel_id FROM welcome WHERE guild_id=$1 LIMIT 1", str(ctx.guild.id))
    await ctx.reply(embed=embed(title="This servers welcome message is now", description=f"```{message}```\n\nThis will look like\n```{formated_message}```" + ("" if channel_id is not None else "\n\n**Don't forget to set a welcome channel**")))


def setup(bot):
  bot.add_cog(Welcome(bot))
