# import discord
from discord import Embed
from discord.utils import get
from discord.ext.menus import MenuPages, ListPageSource
from discord.ext.commands import Cog
from discord.ext import commands

from cogs.cleanup import get_delete_time
from functions import embed,MessageColors

def syntax(command):
  cmd_and_aliases = "|".join([str(command), *command.aliases])
  params = []

  for key, value in command.params.items():
    if key not in ("self", "ctx"):
      if command.usage is not None:
        # params.append(f"[{command.usage}]" if "NoneType" in str(value) else f"<{command.usage}>")
        params = f"{command.usage}" if "NoneType" in str(value) else f"{command.usage}"
      else:
        params.append(f"[{key}]" if "NoneType" in str(value) else f"<{key}>")
  if isinstance(params,list):
    params = " ".join(params)

  return f"```{cmd_and_aliases} {params}```"


class HelpMenu(ListPageSource):
  def __init__(self, ctx, data):
    self.ctx = ctx

    super().__init__(data, per_page=4)

  async def write_page(self, menu, fields=[]):
    offset = (menu.current_page*self.per_page) + 1
    len_data = len(self.entries)

    embed = Embed(
      title="Friday - Help",
      description="If you would like to make a suggestion for a command please join the Friday Discord and explain your suggestion. Here's a list of all my commands:",
      colour=MessageColors.DEFAULT
    )
    embed.set_thumbnail(url=self.ctx.me.avatar_url)
    embed.set_footer(text=f"{offset:,} - {min(len_data, offset+self.per_page-1):,} of {len_data:,} commands.")

    for name, value in fields:
      embed.add_field(name=name, value=value, inline=False)

    return embed
  
  async def format_page(self, menu, entries):
    fields = []

    for entry in entries:
      fields.append((entry.cog_name or "No description", syntax(entry)))

    return await self.write_page(menu, fields)

async def cmd_help(ctx, command, message:str=None):
  embed = Embed(
    title=message or f"Help with `{command}`",
    description=syntax(command),
    color=MessageColors.DEFAULT if message is None else MessageColors.ERROR
  )
  # embed.add_field(name="Command description", value=command.help)
  embed.add_field(name="Command description", value=command.description or "None")
  await ctx.reply(embed=embed)

class Help(Cog):
# class Help(commands.HelpCommand):
  def __init__(self, bot):
    self.bot = bot
    self.bot.remove_command("help")


  @commands.command(name="help",aliases=["?","commands"],usage="<command/group>")
  async def show_help(self, ctx, cmd:str=None):
    """Shows this message."""

    delay = await get_delete_time()
    await ctx.message.delete(delay=delay)
    if cmd is not None:
      for item in self.bot.commands:
        if cmd in item.aliases:
          cmd = item.name

    commands = []
    for com in self.bot.commands:
      if com.hidden != True and com.enabled != False:
        commands.append(com)

    if cmd is None:
      menu = MenuPages(source=HelpMenu(ctx, commands),
        delete_message_after=True,
        clear_reactions_after=True,
        timeout=delay)
      await menu.start(ctx)

    else:
      if (command := get(self.bot.commands, name=cmd)):
        await cmd_help(ctx, command)
      else:
        await ctx.reply(embed=embed(title="The command `{}` does not exist".format(cmd),color=MessageColors.ERROR))

def setup(bot):
  bot.add_cog(Help(bot))