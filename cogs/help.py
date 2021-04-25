from discord import Embed
from discord.ext import commands
from discord.ext.commands import Cog
from discord.ext.menus import ListPageSource, MenuPages
from discord.utils import get

from discord_slash import cog_ext, SlashContext

# from cogs.cleanup import get_delete_time
from functions import MessageColors, embed, checks


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


class Menu(MenuPages):
  async def send_initial_message(self, ctx: commands.Context or SlashContext, channel):
    page = await self._source.get_page(0)
    kwargs = await self._get_kwargs_from_page(page)
    if isinstance(ctx, SlashContext):
      return await ctx.send(**kwargs)
    return await ctx.reply(**kwargs)


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
        description="If you would like to make a suggestion for a command please join the Friday Discord and explain your suggestion. Here's a list of all my commands:",
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


class Help(Cog):
  def __init__(self, bot):
    self.bot = bot
    self.bot.remove_command("help")

  @commands.command(name="help", aliases=["?", "commands"], usage="<command/group>")
  @commands.bot_has_permissions(add_reactions=True)
  async def norm_show_help(self, ctx, group: str = None, cmd: str = None):
    await self.show_help(ctx, group, cmd)

  @cog_ext.cog_slash(name="help")
  @checks.slash(user=True, private=True)
  async def slash_show_help(self, ctx, group: str = None, cmd: str = None):
    await ctx.defer()
    await self.show_help(ctx, group, cmd)

  async def show_help(self, ctx, group: str = None, cmd: str = None):
    """Shows this message."""

    if cmd is None:
      cmd = group

    delay = self.bot.get_guild_delete_commands(ctx.guild)
    if delay is not None and delay > 0:
      await ctx.message.delete(delay=delay)
    if cmd is not None:
      for item in self.bot.commands:
        if cmd in item.aliases:
          cmd = item.name

    commands = []
    for com in self.bot.commands:
      if com.hidden is not True and com.enabled is not False:
        commands.append(com)

    if cmd is None:
      menu = Menu(source=HelpMenu(ctx, commands),
                  delete_message_after=True,
                  clear_reactions_after=True,
                  timeout=delay if delay is not None and delay > 0 else None)
      await menu.start(ctx)

    else:
      if (command := get(self.bot.commands, name=cmd)):
        await cmd_help(ctx, command)
      else:
        if isinstance(ctx, SlashContext):
          await ctx.send(embed=embed(title=f"The command `{cmd}` does not exist", color=MessageColors.ERROR))
        else:
          await ctx.reply(embed=embed(title=f"The command `{cmd}` does not exist", color=MessageColors.ERROR))


def setup(bot):
  bot.add_cog(Help(bot))
