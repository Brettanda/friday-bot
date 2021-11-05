import nextcord as discord
from nextcord.ext import commands

from functions import embed, MyContext, MessageColors, cache

from typing import Optional
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class Config:
  __slots__ = ("bot", "id", "channel_id", "role_id", "message",)

  @classmethod
  def from_record(cls, record, bot):
    self = cls()

    self.bot: "Bot" = bot
    self.id: int = int(record["guild_id"], base=10)
    self.channel_id: Optional[int] = int(record["channel_id"], base=10) if record["channel_id"] is not None else None
    self.role_id: Optional[int] = int(record["role_id"], base=10) if record["role_id"] is not None else None
    self.message: Optional[str] = record["message"]
    return self

  @property
  def channel(self) -> Optional[discord.TextChannel]:
    guild = self.bot.get_guild(self.id)
    return guild and self.channel_id and guild.get_channel(self.channel_id)

  @property
  def role(self) -> Optional[discord.Role]:
    guild = self.bot.get_guild(self.id)
    return guild and self.role_id and guild.get_role(self.role_id)


class Welcome(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.bot = bot

  def __repr__(self):
    return "<cogs.Welcome>"

  def cog_check(self, ctx: MyContext) -> bool:
    return ctx.guild is not None

  async def cog_command_error(self, ctx, error):
    if isinstance(error, commands.CheckFailure):
      raise commands.NoPrivateMessage()

  @cache()
  async def get_guild_config(self, guild_id: int) -> Optional[Config]:
    query = "SELECT * FROM welcome WHERE guild_id=$1 LIMIT 1"
    async with self.bot.db.pool.acquire(timeout=300.0) as conn:
      record = await conn.fetchrow(query, str(guild_id))
      self.bot.logger.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
      if record is None:
        return None
      return Config.from_record(record, self.bot)

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
    config = await self.get_guild_config(member.guild.id)
    if config is None:
      return
    message, channel = config.message, config.channel
    if message is None or channel is None:
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
    config = await self.get_guild_config(member.guild.id)
    if config is None:
      return

    role = config.role
    if role is None:
      self.get_guild_config.invalidate(self, member.guild.id)
      return await self.bot.db.query("UPDATE welcome SET role_id=NULL WHERE guild_id=$1", str(member.guild.id))
    await member.add_roles(role, reason="Welcome Role")

  @commands.group(name="welcome", invoke_without_command=True, case_insensitive=True, help="Friday's settings for welcomeing new members to your servers")
  @commands.has_guild_permissions(manage_roles=True, manage_guild=True, manage_channels=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def _welcome(self, ctx: "MyContext"):
    return await ctx.invoke(self._welcome_display)

  @_welcome.command(name="display", aliases=["list", "show"], help="Shows the servers current welcome settings")
  @commands.has_guild_permissions(manage_roles=True, manage_guild=True, manage_channels=True)
  async def _welcome_display(self, ctx: "MyContext"):
    config = await self.get_guild_config(ctx.guild.id)
    if config is None:
      return await ctx.send(embed=embed(title="Welcome", description="Welcome is not enabled for this server.", color=MessageColors.ERROR))
    await ctx.reply(embed=embed(
        title="Current Welcome Settings",
        fieldstitle=["Role", "Channel", "Message"],
        fieldsval=[f"<@&{config.role_id}>"if str(config.role_id) != str(None) else "None", f"<#{config.channel_id}>" if str(config.channel_id) != str(None) else "None", f"{config.message}" if config.message != "" else "None"],
        fieldsin=[False, False, False]
    ))

  @_welcome.command(name="role", extras={"examples": ["@default", "12345678910"]}, help="Set the role that is given to new members when they join the server")
  @commands.has_guild_permissions(manage_roles=True, manage_guild=True, manage_channels=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def _welcome_role(self, ctx: "MyContext", role: Optional[discord.Role] = None):
    role_id = role.id if role is not None else None
    await self.bot.db.query("INSERT INTO welcome (guild_id,role_id) VALUES ($1,$2) ON CONFLICT(guild_id) DO UPDATE SET role_id=$2", str(ctx.guild.id), str(role_id) if role_id else None)
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.reply(embed=embed(title=f"New members will now receive the role `{role}`"))

  @_welcome.command(name="channel", extras={"examples": ["#welcome", "#general", "707458929696702525"]}, help="Setup a welcome channel for Friday to welcome new memebers in")
  @commands.has_guild_permissions(manage_guild=True, manage_channels=True)
  async def _welcome_channel(self, ctx: "MyContext", channel: Optional[discord.TextChannel] = None):
    if channel is not None and channel.permissions_for(ctx.guild.me).send_messages is False:
      return await ctx.reply(embed=embed(title=f"I don't have send_permissions in {channel}", color=MessageColors.ERROR))
    channel_id = channel.id if channel is not None else None
    await self.bot.db.query("INSERT INTO welcome (guild_id,channel_id) VALUES ($1,$2) ON CONFLICT(guild_id) DO UPDATE SET channel_id=$2", str(ctx.guild.id), str(channel_id) if channel_id else None)
    message = await self.bot.db.query("SELECT message FROM welcome WHERE guild_id=$1 LIMIT 1", str(ctx.guild.id))
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.reply(embed=embed(title=f"Welcome message will be sent to `{channel}`", description="" if message is not None else "Don't forget to set a welcome message"))

  @_welcome.command(name="message", extras={"examples": [r"Welcome to the server {user}, stay a while!", r"Welcome {user} to {server}", "A new member has joined the server!"]}, help="Set a message to greet new members to your server, message variables are `{user}`,`{server}`")
  @commands.has_guild_permissions(manage_guild=True, manage_channels=True)
  async def _welcome_message(self, ctx: "MyContext", *, message: Optional[str] = None):
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
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.reply(embed=embed(title="This servers welcome message is now", description=f"```{message}```\n\nThis will look like\n```{formated_message}```" + ("" if channel_id is not None else "\n\n**Don't forget to set a welcome channel**")))


def setup(bot):
  bot.add_cog(Welcome(bot))
