import discord
from discord.ext import commands

from functions import embed, MyContext, config, MessageColors

from typing import Optional
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class CommandName(commands.Converter):
  async def convert(self, ctx: "MyContext", argument: str):
    lowered = argument.lower()

    valid_commands = {
        c.qualified_name
        for c in ctx.bot.walk_commands()
        if c.cog_name not in ("Dev", "Config")
    }

    if lowered not in valid_commands:
      raise commands.BadArgument(f"Command {lowered!r} does not exist. Make sure you're using the full name not an alias.")

    return lowered


class Config(commands.Cog, command_attrs=dict(extras={"permissions": ["manage_guild"]})):
  def __init__(self, bot: "Bot"):
    self.bot = bot

  def __repr__(self) -> str:
    return "<cogs.Config>"

  async def cog_check(self, ctx: "MyContext"):
    if ctx.guild is None:
      raise commands.NoPrivateMessage("This command can only be used within a guild")

    if not ctx.author.guild_permissions.manage_guild:
      raise commands.MissingPermissions(["manage_guild"])
    return True

  @commands.command(name="prefix", extras={"examples": ["?", "f!"]}, help="Sets the prefix for Fridays commands")
  async def prefix(self, ctx: "MyContext", new_prefix: Optional[str] = config.defaultPrefix):
    new_prefix = new_prefix.lower()
    if len(new_prefix) > 5:
      return await ctx.reply(embed=embed(title="Can't set a prefix with more than 5 characters", color=MessageColors.ERROR))
    await self.bot.db.query("UPDATE servers SET prefix=$1 WHERE id=$2", str(new_prefix), str(ctx.guild.id))
    self.bot.prefixes[ctx.guild.id] = new_prefix
    await ctx.reply(embed=embed(title=f"My new prefix is `{new_prefix}`"))

  @commands.group("botchannel", invoke_without_command=True)
  async def botchannel(self, ctx: "MyContext", *, channel: discord.TextChannel = None):
    if channel is None:
      return await ctx.send_help(ctx.command)
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title="This functionality is not currently available. Try again later?", color=MessageColors.ERROR))

    query = "UPDATE servers SET botchannel=$2 WHERE id=$1;"

    await ctx.pool.execute(query, str(ctx.guild.id), str(channel.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title="Bot Channel", description=f"Bot channel set to {channel.mention}."))

  @botchannel.command("clear")
  async def botchannel_clear(self, ctx: "MyContext"):
    await ctx.pool.execute("UPDATE servers SET botchannel=NULL WHERE id=$1;", str(ctx.guild.id))
    await ctx.send(embed=embed(title="Bot Channel", description="Bot channel cleared."))

  @commands.group("restrict", help="Restricts the selected command to the bot channel. Ignored with manage server permission.", invoke_without_command=True)
  async def restrict(self, ctx: "MyContext", *, command: CommandName):
    query = "UPDATE servers SET restricted_commands=array_append(restricted_commands, $1) WHERE id=$2 AND NOT ($1=any(restricted_commands));"
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title="This functionality is not currently available. Try again later?", color=MessageColors.ERROR))
    await ctx.pool.execute(query, command, str(ctx.guild.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title=f"**{command}** has been restricted to the bot channel."))

  @restrict.command("list")
  async def restrict_list(self, ctx: "MyContext"):
    query = "SELECT restricted_commands FROM servers WHERE id=$1;"
    restricted_commands = await ctx.pool.fetchval(query, str(ctx.guild.id))
    if restricted_commands is None:
      restricted_commands = []
    await ctx.send(embed=embed(title="Restricted Commands", description="\n".join(restricted_commands)))

  @commands.command("unrestrict", help="Unrestricts the selected command.")
  async def unrestrict(self, ctx: "MyContext", *, command: CommandName):
    query = "UPDATE servers SET restricted_commands=array_remove(restricted_commands, $1) WHERE id=$2;"
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title="This functionality is not currently available. Try again later?", color=MessageColors.ERROR))

    await ctx.pool.execute(query, command, str(ctx.guild.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title=f"**{command}** has been unrestricted."))

  @commands.group("enable", help="Enables the selected command(s).", invoke_without_command=True)
  async def enable(self, ctx: "MyContext", *, command: CommandName):
    query = "UPDATE servers SET disabled_commands=array_remove(disabled_commands, $1) WHERE id=$2;"
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title="This functionality is not currently available. Try again later?", color=MessageColors.ERROR))

    await ctx.pool.execute(query, command, str(ctx.guild.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title=f"**{command}** has been enabled."))

  @enable.command("all", help="Enables all commands.", hidden=True)
  @commands.is_owner()
  async def enable_all(self, ctx: "MyContext"):
    ...

  @commands.group(name="disable", extras={"examples": ["ping", "ping last", "\"blacklist add\" ping"]}, aliases=["disablecmd"], help="Disable a command", invoke_without_command=True)
  async def disable(self, ctx: "MyContext", *, command: CommandName):
    query = "UPDATE servers SET disabled_commands=array_append(disabled_commands, $1) WHERE id=$2 AND NOT ($1=any(disabled_commands));"
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title="This functionality is not currently available. Try again later?", color=MessageColors.ERROR))

    await ctx.pool.execute(query, command, str(ctx.guild.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title=f"**{command}** has been disabled."))

  @disable.command("list", help="Lists all disabled commands.")
  async def disable_list(self, ctx: "MyContext"):
    query = "SELECT disabled_commands FROM servers WHERE id=$1;"
    disabled_commands = await ctx.pool.fetchval(query, str(ctx.guild.id))
    if disabled_commands is None:
      return await ctx.send(embed=embed(title="There are no disabled commands."))
    await ctx.send(embed=embed(title="Disabled Commands", description="\n".join(disabled_commands) if len(disabled_commands) > 0 else "There are no disabled commands."))

  @disable.command("all", help="Disables all commands.", hidden=True)
  @commands.is_owner()
  async def disable_all(self, ctx: "MyContext"):
    ...


def setup(bot):
  bot.add_cog(Config(bot))
