from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import asyncpg
import discord
import pycountry
from discord.ext import commands
from typing_extensions import Annotated

from functions import MessageColors, cache, config, embed

if TYPE_CHECKING:
  from typing_extensions import Self

  from cogs.chat import Chat
  from functions.custom_contexts import GuildContext
  from index import Friday

UPDATES_CHANNEL = 744652167142441020


class ChannelOrMember(commands.Converter):
  async def convert(self, ctx: GuildContext, argument: str):
    try:
      return await commands.TextChannelConverter().convert(ctx, argument)
    except commands.BadArgument:
      return await commands.MemberConverter().convert(ctx, argument)


class CogName(commands.Converter):
  async def convert(self, ctx: GuildContext, argument: str) -> str:
    lowered = argument.lower()

    valid_cogs = {
        n
        for n, c in ctx.bot.cogs
        if n not in ("Dev", "Config")
    }

    if lowered not in valid_cogs:
      raise commands.BadArgument(f"Cog {lowered!r} does not exist.")

    return lowered


class Command(commands.Converter):
  async def convert(self, ctx: GuildContext, argument: str) -> commands.Command:
    lowered = argument.lower()

    valid_commands = {
        c.qualified_name
        for c in ctx.bot.walk_commands()
        if c.cog_name not in ("Dev", "Config")
    }

    reserved_commands = {
        c.qualified_name
        for c in ctx.bot.walk_commands()
        if c.cog_name and c.cog_name in ("Config")
    }

    if lowered in reserved_commands:
      raise commands.BadArgument(f"Command {lowered!r} can't be modified.")

    if lowered not in valid_commands:
      raise commands.BadArgument(f"Command {lowered!r} does not exist. Make sure you're using the full name not an alias.")

    return ctx.bot.get_command(lowered)  # type: ignore


class ConfigConfig:
  __slots__ = ("bot", "id", "mod_role_ids")

  bot: Friday
  id: int
  mod_role_ids: list

  @classmethod
  async def from_record(cls, record: asyncpg.Record, bot: Friday) -> Self:
    self = cls()
    self.bot = bot
    self.id = int(record["id"], base=10)
    self.mod_role_ids = record["mod_roles"]

    return self

  @property
  def mod_roles(self) -> list:
    guild = self.bot.get_guild(self.id)
    return guild and self.mod_role_ids and [guild.get_role(int(id_, base=10)) for id_ in self.mod_role_ids]  # type: ignore


class Config(commands.Cog, command_attrs=dict(extras={"permissions": ["manage_guild"]})):
  def __init__(self, bot: Friday):
    self.bot: Friday = bot

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def cog_check(self, ctx: GuildContext) -> bool:
    if ctx.guild is None:
      raise commands.NoPrivateMessage("This command can only be used within a guild")

    if await ctx.bot.is_owner(ctx.author):
      return True

    if not ctx.author.guild_permissions.manage_guild:
      raise commands.MissingPermissions(["manage_guild"])
    return True

  @cache.cache(ignore_kwargs=True)
  async def get_guild_config(self, guild_id: int, *, connection: Optional[asyncpg.Pool | asyncpg.Connection] = None) -> Optional[ConfigConfig]:
    query = "SELECT * FROM servers WHERE id=$1 LIMIT 1;"
    conn = connection or self.bot.pool
    record = await conn.fetchrow(query, str(guild_id))
    self.bot.logger.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
    if record is not None:
      return await ConfigConfig.from_record(record, self.bot)
    return None

  @commands.command(name="prefix", extras={"examples": ["?", "f!"]}, help="Sets the prefix for Fridays commands")
  async def prefix(self, ctx: GuildContext, new_prefix: str = config.defaultPrefix):
    prefix = new_prefix.lower()
    if len(prefix) > 5:
      return await ctx.reply(embed=embed(title="Can't set a prefix with more than 5 characters", color=MessageColors.error()))
    await ctx.db.execute("UPDATE servers SET prefix=$1 WHERE id=$2", str(prefix), str(ctx.guild.id))
    self.bot.prefixes[ctx.guild.id] = prefix
    await ctx.reply(embed=embed(title=f"My new prefix is `{prefix}`"))

  @commands.command("updates", help="Recieve updates on new features and changes for Friday")
  @commands.has_permissions(manage_webhooks=True)
  @commands.bot_has_permissions(manage_webhooks=True)
  async def updates(self, ctx: GuildContext, channel: discord.TextChannel):
    updates_channel: discord.TextChannel = self.bot.get_channel(UPDATES_CHANNEL)  # type: ignore

    if updates_channel.id in [w.source_channel and w.source_channel.id for w in await channel.webhooks()]:
      confirm = await ctx.prompt("This channel is already subscribed to updates. Are you sure you want to subscribe again?")
      if not confirm:
        return await ctx.reply(embed=embed(title="Cancelled"))

    await updates_channel.follow(destination=channel, reason="Called updates command, for Friday updates")
    await ctx.reply(embed=embed(title="Updates channel followed"))

  #
  # TODO: Add the cooldown back to the below command but check if the command fails then reset the cooldown
  #

  @commands.command(name="language", extras={"examples": ["en", "es", "english", "spanish"]}, aliases=["lang"], help="Change the language that I will speak. This currently only applies to the chatbot messages not the commands.")
  # @commands.cooldown(1, 3600, commands.BucketType.guild)
  @commands.has_guild_permissions(administrator=True)
  async def language(self, ctx: GuildContext, language: Optional[str] = None):
    lang = ctx.guild.preferred_locale.value.split("-")[0]
    new_language = language or lang

    new_lang = pycountry.languages.get(alpha_2=language) if len(new_language) <= 2 else pycountry.languages.get(name=new_language)
    if new_lang is None:
      return await ctx.reply(embed=embed(title=f"Failed to find language: `{language}`", color=MessageColors.ERROR))

    final_lang = new_lang.alpha_2 if new_lang is not None else lang
    final_lang_name = new_lang.name if new_lang is not None else lang
    await ctx.db.execute("UPDATE servers SET lang=$1 WHERE id=$2", final_lang, str(ctx.guild.id))
    await ctx.reply(embed=embed(title=f"New language set to: `{final_lang_name}`"))
    chat: Optional[Chat] = self.bot.get_cog("Chat")  # type: ignore

    if chat is not None:
      chat.get_guild_config.invalidate(chat, ctx.guild.id)
    log = self.bot.log
    if log is not None:
      log.get_guild_config.invalidate(log, ctx.guild.id)
    ctx._lang = final_lang, self.bot.languages[final_lang]

  @commands.group("botchannel", invoke_without_command=True, case_insensitive=True, extras={"examples": ["#botspam"]}, help="The channel where bot commands live.")
  async def botchannel(self, ctx: GuildContext, *, channel: discord.TextChannel = None):
    if channel is None:
      return await ctx.send_help(ctx.command)
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title="This functionality is not currently available. Try again later?", color=MessageColors.error()))

    query = "UPDATE servers SET botchannel=$2 WHERE id=$1;"

    await ctx.db.execute(query, str(ctx.guild.id), str(channel.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title="Bot Channel", description=f"Bot channel set to {channel.mention}."))

  @botchannel.command("clear")
  async def botchannel_clear(self, ctx: GuildContext):
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title="This functionality is not currently available. Try again later?", color=MessageColors.error()))

    await ctx.db.execute("UPDATE servers SET botchannel=NULL WHERE id=$1;", str(ctx.guild.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title="Bot channel cleared"))

  @commands.group("restrict", help="Restricts the selected command to the bot channel. Ignored with manage server permission.", invoke_without_command=True)
  async def restrict(self, ctx: GuildContext, *, command: Annotated[commands.Command, Command]):
    query = "UPDATE servers SET restricted_commands=array_append(restricted_commands, $1) WHERE id=$2 AND NOT ($1=any(restricted_commands));"
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title="This functionality is not currently available. Try again later?", color=MessageColors.error()))
    await ctx.db.execute(query, command.qualified_name, str(ctx.guild.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title=f"**{command.qualified_name}** has been restricted to the bot channel."))

  @restrict.command("list")
  async def restrict_list(self, ctx: GuildContext):
    query = "SELECT restricted_commands FROM servers WHERE id=$1;"
    restricted_commands = await ctx.db.fetchval(query, str(ctx.guild.id))
    if restricted_commands is None:
      restricted_commands = []
    await ctx.send(embed=embed(title="Restricted Commands", description="\n".join(restricted_commands) or "No commands are restricted."))

  @commands.command("unrestrict", help="Unrestricts the selected command.")
  async def unrestrict(self, ctx: GuildContext, *, command: Annotated[commands.Command, Command]):
    query = "UPDATE servers SET restricted_commands=array_remove(restricted_commands, $1) WHERE id=$2;"
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title="This functionality is not currently available. Try again later?", color=MessageColors.error()))

    await ctx.db.execute(query, command.qualified_name, str(ctx.guild.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title=f"**{command.qualified_name}** has been unrestricted."))

  @commands.group("enable", help="Enables the selected command(s).", invoke_without_command=True)
  async def enable(self, ctx: GuildContext, *, command: Annotated[commands.Command, Command]):
    query = "UPDATE servers SET disabled_commands=array_remove(disabled_commands, $1) WHERE id=$2;"
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title="This functionality is not currently available. Try again later?", color=MessageColors.error()))

    await ctx.db.execute(query, command.qualified_name, str(ctx.guild.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title=f"**{command.qualified_name}** has been enabled."))

  @enable.command("all", help="Enables all commands.", hidden=True)
  @commands.is_owner()
  async def enable_all(self, ctx: GuildContext):
    ...

  @commands.group(name="disable", extras={"examples": ["ping", "ping last", "\"blacklist add\" ping"]}, aliases=["disablecmd"], help="Disable a command", invoke_without_command=True)
  async def disable(self, ctx: GuildContext, *, command: Annotated[commands.Command, Command]):
    query = "UPDATE servers SET disabled_commands=array_append(disabled_commands, $1) WHERE id=$2 AND NOT ($1=any(disabled_commands));"
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title="This functionality is not currently available. Try again later?", color=MessageColors.error()))

    await ctx.db.execute(query, command.qualified_name, str(ctx.guild.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title=f"**{command.qualified_name}** has been disabled."))

  @disable.command("list", help="Lists all disabled commands.")
  async def disable_list(self, ctx: GuildContext):
    query = "SELECT disabled_commands FROM servers WHERE id=$1;"
    disabled_commands = await ctx.db.fetchval(query, str(ctx.guild.id))
    if disabled_commands is None:
      return await ctx.send(embed=embed(title="There are no disabled commands."))
    await ctx.send(embed=embed(title="Disabled Commands", description="\n".join(disabled_commands) or "There are no disabled commands."))

  @disable.command("all", help="Disables all commands.", hidden=True)
  @commands.is_owner()
  async def disable_all(self, ctx: GuildContext):
    ...


async def setup(bot: Friday):
  # if not hasattr(bot, "languages") or len(bot.languages) == 0:
  #   bot.languages["en"] = ReadOnly("i18n/source/commands.json")
  #   for lang in os.listdir("./i18n/translations"):
  #     bot.languages[lang] = ReadOnly(f"i18n/translations/{lang}/commands.json")

  # if not hasattr(bot, "language_config"):
  #   bot.language_config = ConfigFile("languages.json")

  await bot.add_cog(Config(bot))
