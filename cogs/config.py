from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands
from typing_extensions import Annotated

from functions import MessageColors, cache, config, embed
from functions.custom_contexts import MyContext

if TYPE_CHECKING:
  from functions.custom_contexts import GuildContext
  from index import Friday

log = logging.getLogger(__name__)

UPDATES_CHANNEL = 744652167142441020


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

  def __init__(self, *, record: asyncpg.Record, bot: Friday):
    self.bot: Friday = bot
    self.id: int = int(record["id"], base=10)
    self.mod_role_ids: list = record["mod_roles"]

  @property
  def mod_roles(self) -> list:
    guild = self.bot.get_guild(self.id)
    return guild and self.mod_role_ids and [guild.get_role(int(id_, base=10)) for id_ in self.mod_role_ids]  # type: ignore


class Config(commands.Cog, command_attrs=dict(extras={"permissions": ["manage_guild"]})):
  """The general configuration commands for Friday"""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  @cache.cache(ignore_kwargs=True)
  async def get_guild_config(self, guild_id: int, *, connection: Optional[asyncpg.Pool | asyncpg.Connection] = None) -> Optional[ConfigConfig]:
    query = "SELECT * FROM servers WHERE id=$1 LIMIT 1;"
    conn = connection or self.bot.pool
    record = await conn.fetchrow(query, str(guild_id))
    log.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
    if record is not None:
      return ConfigConfig(record=record, bot=self.bot)
    return None

  @commands.command(name="prefix", extras={"examples": ["?", "f!"]})
  @commands.has_guild_permissions(manage_guild=True)
  async def prefix(self, ctx: GuildContext, new_prefix: str = config.defaultPrefix):
    """Sets the prefix for Fridays commands"""
    prefix = new_prefix.lower()
    if len(prefix) > 5:
      return await ctx.reply(embed=embed(title=ctx.lang.config.prefix.max_chars, color=MessageColors.error()))
    await ctx.db.execute("UPDATE servers SET prefix=$1 WHERE id=$2", str(prefix), str(ctx.guild.id))
    self.bot.prefixes[ctx.guild.id] = prefix
    await ctx.reply(embed=embed(title=ctx.lang.config.prefix.new_prefix.format(new_prefix=prefix)))

  @commands.hybrid_command("updates")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_guild=True)
  @commands.has_permissions(manage_webhooks=True)
  @commands.bot_has_permissions(manage_webhooks=True)
  @app_commands.describe(channel="The channel to get updates")
  async def updates(self, ctx: GuildContext, channel: discord.TextChannel):
    """Recieve updates on new features and changes for Friday"""
    updates_channel: discord.TextChannel = self.bot.get_channel(UPDATES_CHANNEL)  # type: ignore

    if updates_channel.id in [w.source_channel and w.source_channel.id for w in await channel.webhooks()]:
      confirm = await ctx.prompt(ctx.lang.config.updates.prompt)
      if not confirm:
        return await ctx.reply(embed=embed(title=ctx.lang.config.updates.cancelled))

    await updates_channel.follow(destination=channel, reason=ctx.lang.config.updates.reason)
    await ctx.reply(embed=embed(title=ctx.lang.config.updates.followed))

  #
  # TODO: Add the cooldown back to the below command but check if the command fails then reset the cooldown
  #

  @commands.hybrid_command(name="userlanguage", aliases=["userlang"])
  async def user_language(self, ctx: MyContext):
    """Change the language that I will speak to you as a user. This doesn't affect application commands"""
    current_code = self.bot.languages.get(ctx.author.id, "en")
    lang = self.bot.language_files.get(current_code, self.bot.language_files["en"])
    choice = await ctx.multi_select(
        embed=embed(title=lang.config.userlanguage.select_title, description=lang.config.userlanguage.select_description),
        options=[
            {
                "label": x["_lang_name"],
                "value": c,
                "emoji": x["_lang_emoji"],
                "description": x["_translator"] if x["_translator"] != f"{self.bot.owner.display_name}#{self.bot.owner.discriminator}" else None,
                "default": bool(c == current_code)
            } for c, x in self.bot.language_files.items()
        ], delete_after=False)
    if not choice:
      return await ctx.edit(content=None, view=None, embed=embed(title=lang.errors.canceled))

    await self.bot.languages.put(ctx.author.id, choice[0])
    lang = self.bot.language_files.get(choice[0], self.bot.language_files["en"])
    await ctx.edit(content=None, view=None, embed=embed(title=lang.config.userlanguage.new_lang.format(new_language=lang._lang_name), description=lang.config.userlanguage.new_lang_desc))

  @commands.hybrid_command(name="serverlanguage", aliases=["serverlang", "guildlang", "guildlanguage"])
  @commands.guild_only()
  @commands.has_guild_permissions(manage_guild=True)
  async def guild_language(self, ctx: GuildContext):
    """Change the default language that I will speak in a server. Doesn't affect application commands"""
    current_code = self.bot.languages.get(ctx.guild.id, "en")
    lang = self.bot.language_files.get(current_code, self.bot.language_files["en"])
    choice = await ctx.multi_select(
        embed=embed(title=lang.config.serverlanguage.select_title, description=lang.config.serverlanguage.select_description),
        options=[
            {
                "label": x["_lang_name"],
                "value": c,
                "emoji": x["_lang_emoji"],
                "description": x["_translator"] if x["_translator"] != f"{self.bot.owner.display_name}#{self.bot.owner.discriminator}" else None,
                "default": bool(c == current_code)
            } for c, x in self.bot.language_files.items()
        ], delete_after=False)
    if not choice:
      return await ctx.edit(content=None, view=None, embed=embed(title=lang.errors.canceled))

    await self.bot.languages.put(ctx.guild.id, choice[0])
    lang = self.bot.language_files.get(choice[0], self.bot.language_files["en"])
    await ctx.edit(content=None, view=None, embed=embed(title=lang.config.serverlanguage.new_lang.format(new_language=lang._lang_name), description=lang.config.serverlanguage.new_lang_desc))

  @commands.group("botchannel", invoke_without_command=True, case_insensitive=True, extras={"examples": ["#botspam"]})
  @commands.has_guild_permissions(manage_guild=True)
  async def botchannel(self, ctx: GuildContext, *, channel: discord.abc.GuildChannel = None):
    """The channel where bot commands live."""
    if channel is None:
      return await ctx.send_help(ctx.command)
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title=ctx.lang.errors.try_again_later, color=MessageColors.error()))

    query = "UPDATE servers SET botchannel=$2 WHERE id=$1;"

    await ctx.db.execute(query, str(ctx.guild.id), str(channel.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(f"{channel.mention}", embed=embed(title=ctx.lang.config.botchannel.title))

  @botchannel.command("clear")
  @commands.has_guild_permissions(manage_guild=True)
  async def botchannel_clear(self, ctx: GuildContext):
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title=ctx.lang.errors.try_again_later, color=MessageColors.error()))

    await ctx.db.execute("UPDATE servers SET botchannel=NULL WHERE id=$1;", str(ctx.guild.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title=ctx.lang.config.botchannelclear))

  @commands.group("restrict", invoke_without_command=True)
  @commands.has_guild_permissions(manage_guild=True)
  async def restrict(self, ctx: GuildContext, *, command: Annotated[commands.Command, Command]):
    """Restricts the selected command to the bot channel. Ignored with manage server permission."""
    query = "UPDATE servers SET restricted_commands=array_append(restricted_commands, $1) WHERE id=$2 AND NOT ($1=any(restricted_commands));"
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title=ctx.lang.errors.try_again_later, color=MessageColors.error()))
    await ctx.db.execute(query, command.qualified_name, str(ctx.guild.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title=ctx.lang.config.restrict.title.format(command.qualified_name)))

  @restrict.command("list")
  @commands.has_guild_permissions(manage_guild=True)
  async def restrict_list(self, ctx: GuildContext):
    """Lists the restricted commands."""
    query = "SELECT restricted_commands FROM servers WHERE id=$1;"
    restricted_commands = await ctx.db.fetchval(query, str(ctx.guild.id))
    if restricted_commands is None:
      restricted_commands = []
    await ctx.send(embed=embed(title=ctx.lang.config.restrict.commands.list.response_title, description="\n".join(restricted_commands) or ctx.lang.config.restrict.commands.list.response_no_commands))

  @commands.command("unrestrict")
  @commands.has_guild_permissions(manage_guild=True)
  async def unrestrict(self, ctx: GuildContext, *, command: Annotated[commands.Command, Command]):
    """Unrestricts the selected command."""
    query = "UPDATE servers SET restricted_commands=array_remove(restricted_commands, $1) WHERE id=$2;"
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title=ctx.lang.errors.try_again_later, color=MessageColors.error()))

    await ctx.db.execute(query, command.qualified_name, str(ctx.guild.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title=ctx.lang.config.unrestrict.title.format(command.qualified_name)))

  @commands.group("enable", invoke_without_command=True)
  @commands.has_guild_permissions(manage_guild=True)
  async def enable(self, ctx: GuildContext, *, command: Annotated[commands.Command, Command]):
    """Enables the selected command(s)."""
    query = "UPDATE servers SET disabled_commands=array_remove(disabled_commands, $1) WHERE id=$2;"
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title=ctx.lang.errors.try_again_later, color=MessageColors.error()))

    await ctx.db.execute(query, command.qualified_name, str(ctx.guild.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title=ctx.lang.config.enable.title.format(command.qualified_name)))

  @commands.group(name="disable", extras={"examples": ["ping", "ping last", "\"blacklist add\" ping"]}, aliases=["disablecmd"], invoke_without_command=True)
  @commands.has_guild_permissions(manage_guild=True)
  async def disable(self, ctx: GuildContext, *, command: Annotated[commands.Command, Command]):
    """Disable a command"""
    query = "UPDATE servers SET disabled_commands=array_append(disabled_commands, $1) WHERE id=$2 AND NOT ($1=any(disabled_commands));"
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title=ctx.lang.errors.try_again_later, color=MessageColors.error()))

    await ctx.db.execute(query, command.qualified_name, str(ctx.guild.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title=ctx.lang.config.disable.title.format(command.qualified_name)))

  @disable.command("list")
  @commands.has_guild_permissions(manage_guild=True)
  async def disable_list(self, ctx: GuildContext):
    """Lists all disabled commands."""
    query = "SELECT disabled_commands FROM servers WHERE id=$1;"
    disabled_commands = await ctx.db.fetchval(query, str(ctx.guild.id))
    if disabled_commands is None:
      return await ctx.send(embed=embed(title=ctx.lang.config.disablelist.none_found))
    await ctx.send(embed=embed(title=ctx.lang.config.disablelist.title, description="\n".join(disabled_commands) or ctx.lang.config.disablelist.none_found))

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
  await bot.add_cog(Config(bot))
