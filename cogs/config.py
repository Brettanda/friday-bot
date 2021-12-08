import discord
from discord.ext import commands

from functions import embed, MyContext, config, MessageColors

from typing import Optional
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class CommandName(commands.Converter):
  async def convert(self, ctx: "MyContext", argument):
    lowered = argument.lower()

    valid_commands = {
        c.qualified_name
        for c in ctx.bot.walk_commands()
        if c.cog_name not in ("Dev", "Config")
    }

    if lowered not in valid_commands:
      raise commands.BadArgument(f"Command {lowered!r} does not exist.")

    return lowered


class Config(commands.Cog):
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

  async def cog_command_error(self, ctx: "MyContext", error: Exception):
    if isinstance(error, commands.BadArgument):
      await ctx.send(embed=embed(title=f"{error}", color=MessageColors.ERROR))

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

  @commands.command("restrict", help="Restricts the selected command to the bot channel. Ignored with manage server permission.")
  async def restrict(self, ctx: "MyContext", *, command: CommandName):
    query = "UPDATE servers SET restricted_commands=array_append(restricted_commands, $1) WHERE id=$2 AND NOT ($1=any(restricted_commands));"
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title="This functionality is not currently available. Try again later?", color=MessageColors.ERROR))
    await ctx.pool.execute(query, command, str(ctx.guild.id))
    log_cog.get_guild_config.invalidate(log_cog, ctx.guild.id)
    await ctx.send(embed=embed(title=f"**{command}** has been restricted to the bot channel."))

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

  @commands.group(name="disable", extras={"examples": ["ping", "ping last", "\"blacklist add\" ping"]}, aliases=["disablecmd"], help="Disable a command", invoke_without_command=True)
  async def disable(self, ctx: "MyContext", *, command: CommandName):
    query = "UPDATE servers SET disabled_commands=array_append(disabled_commands, $1) WHERE id=$2 AND NOT ($1=any(disabled_commands));"
    log_cog = self.bot.log
    if log_cog is None:
      return await ctx.send(embed=embed(title="This functionality is not currently available. Try again later?", color=MessageColors.ERROR))

    await ctx.pool.execute(query, command, str(ctx.guild.id))
    await ctx.send(embed=embed(title=f"**{command}** has been disabled."))


def setup(bot):
  bot.add_cog(Config(bot))
