# import itertools
# import math
import discord
from discord import Embed
from discord.ext import commands, flags
from discord.ext.menus import ListPageSource
# from discord.utils import get

from discord_slash import SlashContext, cog_ext, SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option
from typing_extensions import TYPE_CHECKING
# from cogs.cleanup import get_delete_time
# import typing
from functions import MessageColors, checks, Menu, config  # , embed

if TYPE_CHECKING:
  from index import Friday as Bot


def syntax(command, quotes: bool = True):
  cmd_and_aliases = "|".join([str(command), *command.aliases])

  def get_params(com):
    params = []
    for key, value in com.params.items():
      if key not in ("self", "ctx"):
        if com.usage is not None:
          # params.append(f"[{command.usage}]" if "NoneType" in str(value) else f"<{command.usage}>")
          params = f"{com.usage}" if "NoneType" in str(value) else f"{com.usage}"
        else:
          post_key = "..." if "_Greedy" in str(value) else ""
          equals = str(value).split(' = ')[1] if len(str(value).split(' = ')) > 1 else str(None)
          follow_key = f"={equals}" if equals != str(None) else ""
          params.append(f"[{key}{follow_key}]{post_key}" if "_Greedy" in str(value) or "NoneType" in str(value) else f"<{key}>")
    if isinstance(params, list):
      params = " ".join(params)
    return params

  sub_commands = ""
  if hasattr(command, "commands"):
    for com in command.commands:
      sub_commands += f"\n{cmd_and_aliases} {com.name} {get_params(com)}"
  # sub_commands = "".join(str(command.commands) if hasattr(command,"commands") else "")

  if quotes:
    return f"```{cmd_and_aliases} {get_params(command)}{sub_commands}```"
  else:
    return f"{cmd_and_aliases} {get_params(command)}{sub_commands}"


class HelpMenu(ListPageSource):
  def __init__(self, ctx, data):
    self.ctx = ctx

    super().__init__(data, per_page=6)

  async def write_page(self, menu, fields=None):
    if fields is None:
      fields = []
    offset = (menu.current_page * self.per_page) + 1
    len_data = len(self.entries)

    embed = Embed(
        title="Friday - Help",
        description="If you would like to make a suggestion for a command please join the [Friday's Development](https://discord.gg/NTRuFjU) and explain your suggestion.\n\nFor more info on how commands work and how to format them please check out [docs.friday-bot.com](https://docs.friday-bot.com/).\n\n**Some commands will only show if you have the correct permissions to use them.**",
        colour=MessageColors.DEFAULT
    )
    embed.set_thumbnail(url=self.ctx.bot.user.avatar_url)
    embed.set_footer(text=f"{offset:,} - {min(len_data, offset+self.per_page-1):,} of {len_data:,} commands.")

    for name, value in fields:
      embed.add_field(name=name, value=value, inline=False)

    return embed

  async def format_page(self, menu, entries):
    fields = []

    for entry in entries:
      fields.append((entry.cog_name or "No description", syntax(entry)))

    return await self.write_page(menu, fields)


async def cmd_help(ctx: commands.Context or SlashContext, command, message: str = None):
  embed = Embed(
      title=message or f"Help with `{command}`",
      description=syntax(command),
      color=MessageColors.DEFAULT if message is None else MessageColors.ERROR
  )
  # embed.add_field(name="Command description", value=command.help)
  embed.add_field(name="Command description", value=command.description or "None")
  if isinstance(ctx, SlashContext):
    await ctx.send(embed=embed)
  else:
    await ctx.reply(embed=embed)


class Help(commands.HelpCommand):
  def __init__(self):
    super().__init__(command_attrs={"help": "Show help about the bot, a command, or a category."}, case_insensitive=True)

  async def on_help_command_error(self, ctx, error):
    if isinstance(error, commands.CommandInvokeError):
      await ctx.reply(str(error.original))

  def make_page_embed(self, commands, title="Friday - Help", description=discord.Embed.Empty):
    embed = Embed(color=MessageColors.DEFAULT)
    embed.title = title
    embed.description = description
    # embed.set_footer()

    for command in commands:
      signature = self.clean_prefix + command.qualified_name + " "

      signature += (
          "[args...]" if isinstance(command, flags.FlagCommand) else command.signature
      )

      embed.add_field(
          name=signature,
          value=command.help or "No help found...",
          inline=False,
      )

    return embed

  def make_default_embed(self, cogs: [commands.Cog], title="Friday - Help", description=discord.Embed.Empty):
    embed = Embed(color=MessageColors.DEFAULT)
    embed.title = title
    embed.description = description

    x = 0
    for cog in cogs:
      cog, description, command_list = cog
      description = f"{description or 'No description'} \n {''.join([f'`{command.qualified_name}` ' for command in command_list])}"
      embed.add_field(name=cog.qualified_name, value=description, inline=False)
      x += 1

    return embed

  async def command_callback(self, ctx, *, command=None):
    # await self.prepare_help_command(ctx, command)
    # bot: "Bot" = ctx.bot

    # if command is None:
    #   return await self.send_bot_help(self.get_bot_mapping())

    # cogs = []
    # for cog in bot.cogs:
    #   cogs.append(cog)
    # # cogs = [cog.lower() for cog in bot.cogs]
    # cog = bot.get_cog(command)
    # # if cog is None:
    # #   cog =
    return await super().command_callback(ctx, command=command)

  async def send_bot_help(self, mapping):
    ctx = self.context
    ctx.invoked_with = "help"
    bot: "Bot" = ctx.bot

    # def get_category(command):
    #   cog = command.cog
    #   return cog.qualified_name if cog is not None else "\u200bNo Category"

    # embed_pages, total = [], 0

    # filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)

    # for cog_name, commands in itertools.groupby(filtered, key=get_category):
    #   commands = sorted(commands, key=lambda c: c.name)

    #   if len(commands) == 0:
    #     continue

    #   total += len(commands)
    #   cog = bot.get_cog(cog_name)
    #   description = (
    #       (cog and cog.description)
    #       if (cog and cog.description) is not None
    #       else discord.Embed.Empty
    #   )
    #   embed_pages.append((cog, description, commands))

    # async def get_page(source, menu, pidx):
    #   cogs = embed_pages[
    #       min(len(embed_pages) - 1, pidx * 6): min(len(embed_pages) - 1, pidx * 6 + 6)
    #   ]

    #   embed = self.make_default_embed(
    #       cogs,
    #       title=f"Friday Command Categories (Page {pidx+1}/{len(embed_pages)//6+1})",
    #       description=(
    #           f"Use `{self.clean_prefix}help <command>` for more info on a command.\n"
    #           f"Use `{self.clean_prefix}help <category>` for more info on a category.\n"
    #       )
    #   )

    #   return embed

    delay = bot.log.get_guild_delete_commands(ctx.guild)
    if delay is not None and delay > 0:  # and not slash:
      await ctx.message.delete(delay=delay)
    # if cmd is not None:
    #   for item in self.bot.commands:
    #     if cmd in item.aliases:
    #       cmd = item.name

    commands = []
    for com in bot.commands:
      try:
        if await com.can_run(ctx) and com.hidden is not True and com.enabled is not False:
          commands.append(com)
      except Exception:
        pass
    if delay is not None and delay > 0:  # and not slash:
      await ctx.message.delete(delay=delay)
    menu = Menu(source=HelpMenu(ctx, commands),
                delete_message_after=True,
                clear_reactions_after=True,
                timeout=delay if delay is not None and delay > 0 else 60,
                extra_rows=[config.useful_buttons()])
    await menu.start(ctx)

  async def send_cog_help(self, cog):
    ctx = self.context
    ctx.invoked_with = "help"
    # bot: "Bot" = ctx.bot

    filtered = await self.filter_commands(cog.get_commands(), sort=True)

    embed = self.make_page_embed(
        filtered,
        title=(cog and cog.qualified_name or "Other") + " Commands",
        description=discord.Embed.Empty if cog is None else cog.description
    )

    await ctx.reply(embed=embed)

  async def send_group_help(self, group):
    ctx = self.context
    ctx.invoked_with = "help"
    # bot: "Bot" = ctx.bot

    subcommands = group.commands
    if len(subcommands) == 0:
      return await self.send_command_help(group)

    filtered = await self.filter_commands(subcommands, sort=True)

    embed = self.make_page_embed(
        filtered,
        title=group.qualified_name,
        description=f"{group.description}\n\n{group.help}"
        if group.description
        else group.help or "No help found..."
    )

    await ctx.reply(embed=embed)

  async def send_command_help(self, command: commands.Command):
    embed = Embed(color=MessageColors.DEFAULT)
    embed.title = self.clean_prefix + command.qualified_name

    if command.description:
      embed.description = f"{command.description}\n\n{command.help}"
    else:
      embed.description = command.help or "No help found..."

    embed.add_field(name="Signature", value=self.get_command_signature(command))

    await self.context.reply(embed=embed)

  # def command_not_found()


def setup(bot):
  bot.old_help_command = bot.help_command
  bot.help_command = Help()


def teardown(bot):
  bot.help_command = bot.old_help_command
# class Help(commands.Cog):
#   """The help command"""

#   def __init__(self, bot: "Bot"):
#     self.bot = bot
#     self.bot.remove_command("help")

#   @commands.command(name="help", aliases=["?", "commands"])  # , usage="<command/group>")
#   async def norm_show_help(self, ctx, group: typing.Optional[str] = None, cmd: typing.Optional[str] = None):
#     await self.show_help(ctx, group, cmd)

#   @cog_ext.cog_slash(name="help")
#   @checks.slash(user=True, private=True)
#   async def slash_show_help(self, ctx, group: str = None, cmd: str = None):
#     await ctx.defer()
#     await self.show_help(ctx, group, cmd, True)

#   async def show_help(self, ctx, group: str = None, cmd: str = None, slash: bool = False):
#     """Shows this message."""

#     if cmd is None:
#       cmd = group

#     delay = self.bot.log.get_guild_delete_commands(ctx.guild)
#     if delay is not None and delay > 0 and not slash:
#       await ctx.message.delete(delay=delay)
#     if cmd is not None:
#       for item in self.bot.commands:
#         if cmd in item.aliases:
#           cmd = item.name

#     commands = []
#     for com in self.bot.commands:
#       try:
#         if await com.can_run(ctx) and com.hidden is not True and com.enabled is not False:
#           commands.append(com)
#       except Exception:
#         pass

#     if cmd is None:
#       menu = Menu(source=HelpMenu(ctx, commands),
#                   delete_message_after=True,
#                   clear_reactions_after=True,
#                   timeout=delay if delay is not None and delay > 0 else 60)
#       await menu.start(ctx)

#     else:
#       if (command := get(self.bot.commands, name=cmd)):
#         await cmd_help(ctx, command)
#       else:
#         if slash:
#           return await ctx.send(embed=embed(title=f"The command `{cmd}` does not exist", color=MessageColors.ERROR))
#         await ctx.reply(embed=embed(title=f"The command `{cmd}` does not exist", color=MessageColors.ERROR))

# def setup(bot):
#   bot.add_cog(Help(bot))
