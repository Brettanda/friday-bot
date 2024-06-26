from __future__ import annotations

import functools
import logging
from typing import TYPE_CHECKING, Optional, Union

import asyncpg
import discord
import openai
from discord.ext import commands

from cogs.chat import Chat
from functions import MessageColors, cache, checks, embed
from functions.config import PremiumTiersNew

if TYPE_CHECKING:
  from functions.custom_contexts import GuildContext, MyContext
  from index import Friday

log = logging.getLogger(__name__)


def format_message(content: str, user: discord.User | discord.Member, guild: discord.Guild) -> str:
  message_variables = [r"{user}", r"{server}"]
  if content and any(var in content.lower() for var in message_variables):
    for var in message_variables:
      if var == r"{user}":
        content = f"{user.mention}".join(content.split(var))
      elif var == r"{server}":
        content = f"{guild.name}".join(content.split(var))
  return content


class Config:
  __slots__ = ("bot", "id", "channel_id", "role_id", "message", "ai",
               )

  def __init__(self, *, record: asyncpg.Record, bot: Friday):
    self.bot: Friday = bot
    self.id: int = int(record["guild_id"], base=10)
    self.channel_id: Optional[int] = int(record["channel_id"], base=10) if record["channel_id"] is not None else None
    self.role_id: Optional[int] = int(record["role_id"], base=10) if record["role_id"] is not None else None
    self.message: str = record["message"]
    self.ai: bool = record["ai"]

  @property
  def channel(self) -> Optional[Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]]:
    if self.channel_id:
      guild = self.bot.get_guild(self.id)
      return guild and guild.get_channel(self.channel_id)  # type: ignore

  @property
  def role(self) -> Optional[discord.Role]:
    if self.role_id:
      guild = self.bot.get_guild(self.id)
      return guild and guild.get_role(self.role_id)


class Welcome(commands.Cog):
  def __init__(self, bot: Friday):
    self.bot: Friday = bot

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  def cog_check(self, ctx: MyContext) -> bool:
    return ctx.guild is not None

  async def cog_command_error(self, ctx: MyContext, error: commands.CommandError):
    if isinstance(error, commands.CheckFailure):
      raise commands.NoPrivateMessage()

  @cache.cache(ignore_kwargs=True)
  async def get_guild_config(self, guild_id: int, *, connection=None) -> Optional[Config]:
    conn = connection or self.bot.pool

    query = "SELECT * FROM welcome WHERE guild_id=$1 LIMIT 1"
    record = await conn.fetchrow(query, str(guild_id))
    log.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
    if record is None:
      return None
    return Config(record=record, bot=self.bot)

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

  @commands.Cog.listener()
  async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
    if channel.type is not discord.ChannelType.text:
      return

    config = await self.get_guild_config(channel.guild.id)
    if config is None:
      return

    if config.channel_id == channel.id:
      await self.bot.pool.execute("UPDATE welcome SET channel_id=NULL WHERE guild_id=$1", str(channel.guild.id))
      log.info(f"removed welcome channel for {channel.guild} (ID:{channel.guild.id})")

  async def send_ai_welcome_message(self, config: Config, member: discord.Member) -> None:
    if self.bot.chat is None:
      log.error("Chat cog not loaded")
      return
    async with self.bot.chat.api_lock:
      response = await self.bot.chat.openai.chat.completions.create(
                  model="gpt-3.5-turbo",
                  messages=[
                      {'role': 'user', 'content': f"You're WelcomeGPT. You welcome new users to the Discord server '{member.guild.name}' with at very short and unique messages with a joke about their name and include their user mention as their name at least once. Don't include quotation marks.\n Now welcome, {member.display_name} to the server, with the user mention {member.mention}."},
                  ],
                  max_tokens=75,
                  user=str(member.id)
              )
    if response is None:
      return None
    message = response.choices[0].message.content
    assert message is not None
    if member.mention not in message:
      message = member.mention + " " + message
    if config.channel:
      try:
        await config.channel.send(message, allowed_mentions=discord.AllowedMentions(users=True))
        log.info(f"sent welcome message to {config.channel} (ID:{config.channel.id}): {message}")
      except discord.Forbidden:
        await self.bot.pool.execute("UPDATE welcome SET ai=FALSE WHERE guild_id=$1", str(member.guild.id))
        log.warn("missing permission to send welcome message in {config.channel} (ID:{config.channel.id})")

  async def send_welcome_message(self, member: discord.Member) -> None:
    config = await self.get_guild_config(member.guild.id)
    if config is None:
      return
    message, channel = config.message, config.channel
    if channel is None:
      return
    if not channel.permissions_for(member.guild.me).send_messages:
      log.warning(f"no permission to send welcome message in {channel} (ID:{channel.id})")
      return
    if config.ai:
      return await self.send_ai_welcome_message(config, member)
    if message is None:
      return
    message = format_message(message, member, member.guild)
    if not isinstance(config.channel, discord.TextChannel):
      await self.bot.pool.execute("UPDATE welcome SET channel_id=NULL WHERE guild_id=$1", str(member.guild.id))
      self.get_guild_config.invalidate(self, member.guild.id)
      return
    await channel.send(message, allowed_mentions=discord.AllowedMentions(users=True))

  async def add_welcome_role(self, member: discord.Member) -> None:
    config = await self.get_guild_config(member.guild.id)
    if config is None:
      return

    role = config.role
    if role is None:
      self.get_guild_config.invalidate(self, member.guild.id)
      await self.bot.pool.execute("UPDATE welcome SET role_id=NULL WHERE guild_id=$1", str(member.guild.id))
      return
    try:
      await member.add_roles(role, reason="Welcome Role")
    except discord.Forbidden:
      await self.bot.pool.execute("UPDATE welcome SET role_id=NULL WHERE guild_id=$1", str(member.guild.id))

  @commands.group(name="welcome", invoke_without_command=True, case_insensitive=True, help="Friday's settings for welcoming new members to your servers")
  @commands.has_guild_permissions(manage_roles=True, manage_guild=True, manage_channels=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def _welcome(self, ctx: GuildContext):
    return await ctx.invoke(self._welcome_display)  # type: ignore

  @_welcome.command(name="display", aliases=["list", "show"], help="Shows the servers current welcome settings")
  @commands.has_guild_permissions(manage_roles=True, manage_guild=True, manage_channels=True)
  async def _welcome_display(self, ctx: GuildContext):
    config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
    if config is None:
      return await ctx.send(embed=embed(title="Welcome", description="Welcome is not enabled for this server.", color=MessageColors.error()))
    await ctx.reply(embed=embed(
        title="Current Welcome Settings",
        fieldstitle=["Role", "Channel", "Message"],
        fieldsval=[f"<@&{config.role_id}>"if str(config.role_id) != str(None) else "None", f"<#{config.channel_id}>" if str(config.channel_id) != str(None) else "None", f"```\n{config.message}\n```" if config.message != "" else "None"],
        fieldsin=[True, True, False]
    ))

  @_welcome.command(name="role", extras={"examples": ["@default", "12345678910"]}, help="Set the role that is given to new members when they join the server")
  @commands.has_guild_permissions(manage_roles=True, manage_guild=True, manage_channels=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  async def _welcome_role(self, ctx: GuildContext, role: Optional[discord.Role] = None):
    role_id = role and role.id
    await self.bot.pool.execute("INSERT INTO welcome (guild_id,role_id) VALUES ($1,$2) ON CONFLICT(guild_id) DO UPDATE SET role_id=$2", str(ctx.guild.id), str(role_id) if role_id else None)
    self.get_guild_config.invalidate(self, ctx.guild.id)
    if role_id is None:
      return await ctx.send(embed=embed(title="Welcome role removed"))
    await ctx.reply(embed=embed(title=f"New members will now receive the role `{role}`"))

  @_welcome.command(name="channel", extras={"examples": ["#welcome", "#general", "707458929696702525"]}, help="Setup a welcome channel for Friday to welcome new memebers in")
  @commands.has_guild_permissions(manage_guild=True, manage_channels=True)
  async def _welcome_channel(self, ctx: GuildContext, channel: Optional[discord.TextChannel] = None):
    if channel is not None and channel.permissions_for(ctx.guild.me).send_messages is False:
      return await ctx.reply(embed=embed(title=f"I don't have send_permissions in {channel}", color=MessageColors.error()))
    channel_id = channel and channel.id
    await self.bot.pool.execute("INSERT INTO welcome (guild_id,channel_id) VALUES ($1,$2) ON CONFLICT(guild_id) DO UPDATE SET channel_id=$2", str(ctx.guild.id), str(channel_id) if channel_id else None)
    config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
    message = config and config.message
    self.get_guild_config.invalidate(self, ctx.guild.id)
    if channel_id is None:
      return await ctx.send(embed=embed(title="Welcome channel removed"))
    await ctx.reply(embed=embed(title=f"Welcome message will be sent to `{channel}`", description="" if message is not None else "Don't forget to set a welcome message"))

  @_welcome.command(name="message", extras={"examples": [r"Welcome to the server {user}, stay a while!", r"Welcome {user} to {server}", "A new member has joined the server!"]}, help="Set a message to greet new members to your server, message variables are `{user}`,`{server}`")
  @commands.has_guild_permissions(manage_guild=True, manage_channels=True)
  async def _welcome_message(self, ctx: GuildContext, *, message: Optional[str] = None):
    if message is not None and len(message) > 255:
      await ctx.reply(embed=embed(title="Welcome messages can't be longer than 255 characters", color=MessageColors.error()))
    await self.bot.pool.execute("INSERT INTO welcome (guild_id,message) VALUES ($1,$2) ON CONFLICT(guild_id) DO UPDATE SET message=$2", str(ctx.guild.id), message)
    config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
    channel_id = config and config.channel_id
    self.get_guild_config.invalidate(self, ctx.guild.id)
    if message is None:
      return await ctx.send(embed=embed(title="Welcome message removed"))
    formated_message = format_message(message, ctx.author, ctx.guild)
    await ctx.reply(embed=embed(
        title="This servers welcome message is now",
        fieldstitle=["Raw", "Formatted Message"],
        fieldsval=[f"```\n{message}\n```", f"{formated_message}"],
        fieldsin=[False] * 2,
        description="" if channel_id is not None else "Don't forget to set a welcome channel"))

  @_welcome.command(name="ai")
  @checks.is_mod_and_min_tier(tier=PremiumTiersNew.tier_2, manage_guild=True)
  async def _welcome_ai(self, ctx: GuildContext, enabled: bool) -> None:
    """Allows Friday to respond with a unique AI generated messages for every new member to the server"""
    await self.bot.pool.execute("INSERT INTO welcome (guild_id,ai) VALUES ($1,$2) ON CONFLICT(guild_id) DO UPDATE SET ai=$2", str(ctx.guild.id), enabled)
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.reply(embed=embed(title=f"AI welcome messages are now {'enabled' if enabled else 'disabled'}", description="When enabled, this disables the welcome message that you set"))

  @_welcome.command(name="test", aliases=["preview"])
  async def _welcome_test(self, ctx: GuildContext, member: discord.Member = commands.Author):
    """Fakes a member joining the server, this is useful for testing your welcome message"""
    config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
    if config is None:
      return await ctx.send(embed=embed(title="Welcome", description="Welcome is not enabled for this server.", color=MessageColors.error()))
    member.pending = False
    await self.on_member_join(member)
    await ctx.send(embed=embed(title="Sent welcome message"), ephemeral=True)


async def setup(bot):
  await bot.add_cog(Welcome(bot))
