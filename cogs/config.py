from __future__ import annotations

import logging
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

log = logging.getLogger(__name__)

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
    log.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
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
  # @commands.command(name="language", extras={"examples": ["en", "es", "english", "spanish"]}, aliases=["lang"], help="Change the language that I will speak. This currently only applies to the chatbot messages not the commands.")
  # # @commands.cooldown(1, 3600, commands.BucketType.guild)
  # @commands.has_guild_permissions(administrator=True)
  # async def new_language(self, ctx: GuildContext):
  #   langs = self.bot.languages.items()

  #   confirm = await ctx.multi_select(
  #       "Select the language you would like me to speak in",
  #       options=[{
  #           "label": la[1]["_lang_name"],
  #           "value": la[0],
  #           "emoji": la[1]["_lang_emoji"],
  #           "default": la[0] == ctx.lang[0],
  #       } for la in langs],
  #       placeholder=ctx.lang[1]["_lang_name"]
  #   )
  #   if not confirm:
  #     return await ctx.reply(embed=embed(title="Cancelled"))

  #   await ctx.db.execute("UPDATE servers SET lang=$1 WHERE id=$2", confirm[0], str(ctx.guild.id))

  #   chat: Optional[Chat] = self.bot.get_cog("Chat")  # type: ignore
  #   if chat is not None:
  #     chat.get_guild_config.invalidate(chat, ctx.guild.id)
  #   log = self.bot.log
  #   if log is not None:
  #     log.get_guild_config.invalidate(log, ctx.guild.id)
  #   ctx._lang = confirm[0], self.bot.languages[confirm[0]]
  #   await ctx.reply(embed=embed(title=f"{ctx.lang[1]['config']['lang']['new_lang']}`{self.bot.languages[confirm[0]]['_lang_name']}`"))

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

  # async def _bulk_ignore_entries(self, ctx: MyContext, entries):
  #   async with ctx.acquire():
  #     async with ctx.db.transaction():
  #       query = "SELECT entity_id FROM plonks WHERE guild_id=$1;"
  #       records = await ctx.db.fetch(query, ctx.guild.id)

  #       current_plonks = {r[0] for r in records}
  #       guild_id = ctx.guild.id
  #       to_insert = [(guild_id, e.id) for e in entries if e.id not in current_plonks]

  #       await ctx.db.copy_records_to_table("plonks", columns=("guild_id", "entity_id"), records=to_insert)

  #       self.is_plonked.invalidate_containing(f"{ctx.guild.id!r}:")

  # @commands.group("modrole", aliases=["modroles"], invoke_without_command=True)
  # @commands.has_guild_permissions(administrator=True)
  # async def modrole(self, ctx: GuildContext, *roles: discord.Role):
  #   """Sets the mod role for the server.
  #      Members with this role will be able to use ALL mod commands."""
  #   if not roles:
  #     db_roles = await ctx.db.fetchval("SELECT mod_roles FROM servers WHERE id=$1;", str(ctx.guild.id))
  #     db_roles = [ctx.guild.get_role(int(role, base=10)) for role in db_roles]
  #     db_roles = [role for role in db_roles if role is not None]
  #     return await ctx.send(embed=embed(title="Mod Roles", description="\n".join(role.mention for role in db_roles) if db_roles else "There are no mod roles."))

  #   query = "UPDATE servers SET mod_roles=$1 WHERE id=$2;"
  #   await ctx.db.execute(query, [str(role.id) for role in roles], str(ctx.guild.id))
  #   self.get_guild_config.invalidate(self, ctx.guild.id)
  #   await ctx.send(embed=embed(title="Mod Roles", description="\n".join(role.mention for role in roles) if roles else "There are no mod roles."))

  # @modrole.command("clear", aliases=["reset"])
  # @commands.has_guild_permissions(administrator=True)
  # async def modrole_clear(self, ctx: GuildContext):
  #   """Clears the mod role for the server."""
  #   query = "UPDATE servers SET mod_roles=array[]::text[] WHERE id=$1;"
  #   await ctx.db.execute(query, str(ctx.guild.id))
  #   self.get_guild_config.invalidate(self, ctx.guild.id)
  #   await ctx.send(embed=embed(title="Mod Roles", description="There are no mod roles."))

  # @commands.command("canrun", aliases=["diagnose"], help="Let's you know if you can use/run a command in channel.", hidden=True)
  # # @commands.is_owner()
  # async def canrun(self, ctx: GuildContext, *, command: Annotated[commands.Command, Command]):
  #   checkup = {
  #       True: "\N{WHITE HEAVY CHECK MARK}",
  #       False: "\N{CROSS MARK}",
  #       None: "\N{HORIZONTAL ELLIPSIS}"
  #   }
  #   e = discord.Embed(title=f"Diagnose for `{command.qualified_name}`", colour=MessageColors.default())

  #   e.add_field(name=f"{checkup[ctx.guild.me.top_role.position > ctx.author.top_role.position]} Role Hierarchy", value="```" + ('Bot\'s role is high enough' if ctx.guild.me.top_role.position > ctx.author.top_role.position else 'Bot\'s role is not high enough') + "```")

  #   required_perms = [("send_messages", True), ("read_messages", True), ("embed_links", True), ("add_reactions", True)]
  #   me = ctx.guild.me if ctx.guild is not None else ctx.bot.user
  #   permissions = ctx.channel.permissions_for(me)
  #   missing = [perm for perm, value in required_perms if getattr(permissions, perm) != value]
  #   e.add_field(name=f"{checkup[len(missing) == 0]} Required Bot Permissions", value=f"```{', '.join(missing) if missing else 'No missing permissions'}```")

  #   disabled, restricted, botchannel = await ctx.db.fetchrow("SELECT disabled_commands, restricted_commands, botchannel FROM servers WHERE id=$1;", str(ctx.guild.id))
  #   e.add_field(name=f"{checkup[command.qualified_name not in disabled]} Command Disabled", value=f"```{'Command has not been disabled' if command.qualified_name not in disabled else 'Command is disabled'}```")

  #   botchannel = "#" + ctx.guild.get_channel(int(botchannel, base=10)).name if botchannel else "None"
  #   e.add_field(name=f"{checkup[command.qualified_name not in restricted]} Command Restricted", value="```" + ('Command has not been restricted' if command.qualified_name not in restricted else ('Command is restricted to ' + botchannel)) + "```")

  #   command_perms = await command.can_run(ctx)
  #   e.add_field(name=f"{checkup[command_perms]} Command Permissions", value="```" + ('Command has all required permissions' if command_perms else 'Command does not have all required permissions') + "```")

  #   await ctx.send(embed=e)


async def setup(bot: Friday):
  # if not hasattr(bot, "languages") or len(bot.languages) == 0:
  #   bot.languages["en"] = ReadOnly("i18n/source/commands.json")
  #   for lang in os.listdir("./i18n/translations"):
  #     bot.languages[lang] = ReadOnly(f"i18n/translations/{lang}/commands.json")

  # if not hasattr(bot, "language_config"):
  #   bot.language_config = ConfigFile("languages.json")

  await bot.add_cog(Config(bot))
