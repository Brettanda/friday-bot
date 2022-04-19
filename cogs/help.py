# import itertools
# import math
import discord
from discord import Embed
from discord.ext import commands
from discord.ext.menus import ListPageSource, ButtonMenuPages
# from discord.utils import get

# from interactions import Context as SlashContext
# import typing
from typing_extensions import TYPE_CHECKING
# from cogs.cleanup import get_delete_time
from functions import MessageColors, views, MyContext, embed

if TYPE_CHECKING:
  from index import Friday as Bot


def get_examples(command: commands.command, prefix: str = "!") -> list:
  if command.extras != {} and "examples" in command.extras:
    examples, x, ay, gy = [], 0, 0, 0
    alias, aliases, group_aliases = None, [command.name, *command.aliases], [command.parent.name, *command.parent.aliases] if command.parent is not None else []
    if len(list(command.clean_params)) > 0 and "NoneType" in str(list(command.clean_params.items())[0][1]):
      ay = divmod(x, len(aliases))
      alias = aliases[x - (ay[0] * len(aliases))]
      gy = divmod(x, len(group_aliases)) if command.parent is not None else 0
      group = group_aliases[x - (gy[0] * len(group_aliases))] + " " if command.parent is not None else ""
      x += 1
      examples.append(f"{prefix}{group}{alias}")
    for ex in command.extras["examples"]:
      ay = divmod(x, len(aliases))
      alias = aliases[x - (ay[0] * len(aliases))]
      gy = divmod(x, len(group_aliases)) if command.parent is not None else 0
      group = group_aliases[x - (gy[0] * len(group_aliases))] + " " if command.parent is not None else ""
      examples.append(f"{prefix}{group}{alias} {ex}")
      x += 1
    return examples
  return []


def get_params(com):
  params = []
  for key, value in com.params.items():
    if key not in ("self", "ctx"):
      if com.usage is not None:
        # params.append(f"[{command.usage}]" if "NoneType" in str(value) else f"<{command.usage}>")
        params = f"{com.usage}" if "NoneType" in str(value) else f"{com.usage}"
      else:
        post_key = "..." if "Greedy" in str(value) else ""
        equals = str(value).split(' = ')[1] if len(str(value).split(' = ')) > 1 else str(None)
        follow_key = f"={equals}" if equals != str(None) else ""
        # params.append(f"[{key}{follow_key}]{post_key}" if "_Greedy" in str(value) or "NoneType" in str(value) else f"<{key}>")
        params.append(f"[{key}{follow_key}]{post_key}" if "NoneType" in str(value) else f"<{key}>{post_key}")
  if isinstance(params, list):
    params = " ".join(params)
  return params


def syntax(command, prefix: str = "!", quotes: bool = True, *, subcommands: list = None):
  cmd_and_aliases = "|".join([str(command), *command.aliases])

  sub_commands = ""
  if hasattr(command, "commands"):
    for com in sorted(subcommands or command.commands, key=lambda x: x.qualified_name):
      if not com.hidden and com.enabled is not False:
        sub_commands += f"\n{prefix}{cmd_and_aliases} {com.name} {get_params(com)}"
  # sub_commands = "".join(str(command.commands) if hasattr(command,"commands") else "")

  if quotes:
    return f"```{prefix}{cmd_and_aliases} {get_params(command)}{sub_commands}```"
  else:
    return f"{prefix}{cmd_and_aliases} {get_params(command)}{sub_commands}"


class MyMenuPages(ButtonMenuPages):
  def __init__(self, source, **kwargs):
    super().__init__(source=source, timeout=60.0, **kwargs)
    self._source = source
    self.current_page = 0
    self.ctx = None
    self.message = None
    for item in views.Links().links:
      self.add_item(item)

  async def start(self, ctx, *, channel: discord.TextChannel = None, wait=False) -> None:
    await self._source._prepare_once()
    self.ctx = ctx
    self.message = await self.send_initial_message(ctx, ctx.channel)

  async def send_initial_message(self, ctx: "MyContext", channel: discord.TextChannel):
    page = await self._source.get_page(0)
    kwargs = await self._get_kwargs_from_page(page)
    return await ctx.send(**kwargs)

  async def _get_kwargs_from_page(self, page):
    value = await super()._get_kwargs_from_page(page)
    if "view" not in value:
      value.update({"view": self})
    return value

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if interaction.user and interaction.user == self.ctx.author:
      return True
    else:
      await interaction.response.send_message('This help menu is not for you.', ephemeral=True)
      return False

  def stop(self):
    try:
      self.ctx.bot.loop.create_task(self.message.delete())
    except discord.NotFound:
      pass
    super().stop()

  async def on_timeout(self) -> None:
    self.stop()


class HelpMenu(ListPageSource):
  def __init__(self, ctx, data, *, title="Commands", description="", missing_perms=False):
    self.ctx = ctx
    self.title = title
    self.description = description
    self.missing_perms = missing_perms

    super().__init__(data, per_page=6)

  async def write_page(self, menu: MyMenuPages, fields: list = None):
    if fields is None:
      fields = []
    offset = (menu.current_page * self.per_page) + 1
    len_data = len(self.entries)

    embed = Embed(
        title=self.title,
        description=self.description,
        colour=MessageColors.DEFAULT
    )
    embed.set_thumbnail(url=self.ctx.bot.user.display_avatar.url)
    embed.set_footer(text=f"{offset:,} - {min(len_data, offset+self.per_page-1):,} of {len_data:,} commands | Use `{self.ctx.clean_prefix}help command` to get more info on a command.")

    for name, value in fields:
      embed.add_field(name=name, value=value, inline=False)

    return embed

  async def format_page(self, menu: MyMenuPages, entries: [commands.Command]):
    fields = []

    for entry in entries:
      fields.append((entry.cog_name or "No description", syntax(entry, self.ctx.clean_prefix)))

    return await self.write_page(menu, fields)


class Help(commands.HelpCommand):
  def __init__(self):
    super().__init__(command_attrs={"help": "Show help about the bot, a command, or a category.", "case_insensitive": True}, case_insensitive=True)

  async def send_error_message(self, error):
    return await self.context.reply(embed=embed(title=str(error), color=MessageColors.ERROR))

  def get_command_signature(self, command: commands.command, *, subcommands: list = None) -> str:
    return '\n'.join(syntax(command, self.context.clean_prefix, quotes=False, subcommands=subcommands).split('\n'))

  def make_page_embed(self, commands, title="Friday - Help", description="If you would like to make a suggestion for a command please join the [Friday's Development](https://discord.gg/NTRuFjU) and explain your suggestion.\n\nFor more info on how commands work and how to format them please check out [docs.friday-bot.com](https://docs.friday-bot.com/).\n\n**Some commands will only show if you have the correct permissions to use them.**", missing_perms=False):
    embed = Embed(color=MessageColors.DEFAULT)
    embed.title = title
    embed.description = description
    # embed.set_footer()

    if len(commands) == 0 and missing_perms:
      embed.add_field(
          name="Commands",
          value="No commands that you can use",
          inline=False
      )

    for command in commands:
      signature = (
          self.get_command_signature(command)
      )

      embed.add_field(
          name=signature,
          value=command.short_doc or command.help or "No help found...",
          inline=False,
      )

    return embed

  def make_default_embed(self, cogs: [commands.Cog], title="Friday - Help", description=None):
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

  async def command_callback(self, ctx: "MyContext", *, command=None):
    self.context = ctx
    return await super().command_callback(ctx, command=command)

  async def send_bot_help(self, mapping):
    ctx = self.context
    ctx.invoked_with = "help"
    # bot: "Bot" = ctx.bot

    e = embed(
          title="Friday - Help links",
          description="[Commands](https://docs.friday-bot.com?utm_source=Discord)\n"
          "[Patreon](https://www.patreon.com/join/fridaybot?utm_source=Discord)\n"
          "[Dashboard](https://friday-bot.com?utm_source=Discord)\n"
          "[Support Server](https://discord.gg/NTRuFjU)\n"
          "[Trello](https://trello.com/b/SCI2mZzR/friday-bot)\n",
          color=discord.Colour.random()
    )

    try:
      await ctx.author.send(embed=e)
    except discord.Forbidden:
      await ctx.send(embed=e)
    else:
      await ctx.message.add_reaction("✅")

    # commands, missing_perms = [], False
    # for com in bot.commands:
    #   try:
    #     if await com.can_run(ctx) and com.hidden is not True and com.enabled is not False:
    #       commands.append(com)
    #     else:
    #       missing_perms = True
    #   except Exception:
    #     pass
    # menu = MyMenuPages(
    #     source=HelpMenu(ctx, commands, title="Friday - Help", description="If you would like to make a suggestion for a command please join the [Friday's Development](https://discord.gg/NTRuFjU) and explain your suggestion.\n\nFor more info on how commands work and how to format them please check out [docs.friday-bot.com](https://docs.friday-bot.com/).\n\n**Some commands will only show if you have the correct permissions to use them.**", missing_perms=missing_perms)
    # )
    # await menu.start(ctx)

  async def send_cog_help(self, cog):
    ctx = self.context
    ctx.invoked_with = "help"
    # bot: "Bot" = ctx.bot

    filtered = await self.filter_commands(cog.get_commands(), sort=True)

    embed = self.make_page_embed(
        filtered,
        title=(cog and cog.qualified_name or "Other") + " Commands",
        description=discord.Embed.Empty if cog is None else cog.description,
        missing_perms=len(filtered) != len(cog.get_commands())
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
        title=self.context.clean_prefix + group.qualified_name,
        description=f"{group.description}\n\n{group.help}"
        if group.description
        else group.help or "No help found..."
    )

    if group.extras != {}:
      if "examples" in group.extras:
        embed.add_field(name="Examples", value="```py\n" + "\n".join(get_examples(group, self.context.clean_prefix)) + "```", inline=False)
      if "params" in group.extras:
        embed.add_field(name="Available Parameters", value="```py\n" + ", ".join(group.extras['params']) + "```", inline=False)

    embed.add_field(name="Signature", value="```py\n" + self.get_command_signature(group, subcommands=filtered) + "```", inline=False)

    await ctx.reply(embed=embed)

  async def send_command_help(self, command: commands.Command):
    embed = Embed(color=MessageColors.DEFAULT)
    embed.title = self.context.clean_prefix + command.qualified_name

    if command.description:
      embed.description = f"{command.description}\n\n{command.help}"
    else:
      embed.description = command.help or "No help found..."

    if command.extras != {}:
      if "examples" in command.extras:
        embed.add_field(name="Examples", value="```py\n" + "\n".join(get_examples(command, self.context.clean_prefix)) + "```", inline=False)
      if "params" in command.extras:
        embed.add_field(name="Available Parameters", value="```py\n" + ", ".join(command.extras['params']) + "```", inline=False)

    embed.add_field(name="Signature", value="```py\n" + self.get_command_signature(command) + "```", inline=False)

    await self.context.reply(embed=embed)


def setup(bot: "Bot"):
  bot.old_help_command = bot.help_command
  bot.help_command = Help()


def teardown(bot: "Bot"):
  bot.help_command = bot.old_help_command
