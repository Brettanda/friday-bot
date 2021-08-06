import asyncio
import os
import shutil
import subprocess
import typing
# import traceback
# import io
# import textwrap
import discord
import asqlite
from discord.ext import commands
# from discord_slash import SlashContext  # , cog_ext
from typing_extensions import TYPE_CHECKING
# from discord_slash.utils.manage_commands import create_option, create_choice

from cogs.help import cmd_help, syntax
from functions import embed, build_docs  # , query  # , MessageColors

if TYPE_CHECKING:
  from index import Friday as Bot


class Dev(commands.Cog, command_attrs=dict(hidden=True)):
  """Commands used by and for the developer"""

  def __init__(self, bot: "Bot"):
    self.bot = bot

  def cog_check(self, ctx):
    if self.bot.owner_id == ctx.author.id:
      return True
    raise commands.NotOwner("You do not own this bot and cannot use this command")

  @commands.group(name="dev", invoke_without_command=True)
  async def norm_dev(self, ctx):
    await cmd_help(ctx, ctx.command)

  # @cog_ext.cog_slash(name="dev",guild_ids=[243159711237537802,805579185879121940])
  # async def slash_dev(self,ctx):
  #   await ctx.defer(True)
  #   await ctx.send("help")

  @norm_dev.command(name="say")
  async def say(self, ctx, channel: typing.Optional[discord.TextChannel] = None, *, say: str):
    channel = ctx.channel if channel is None else channel
    try:
      await ctx.message.delete()
    except BaseException:
      pass
    await channel.send(f"{say}")

  # @cog_ext.cog_subcommand(base="dev",name="say",description="Make me say something",guild_ids=[243159711237537802,805579185879121940])
  # async def slash_say(self,ctx,*,message:str):
  #   await ctx.defer(True)
  #   check = await self.cog_check(ctx)
  #   if check is not True:
  #     return await ctx.send(hidden=True,str(check))
  #   await ctx.send(str(message))

  @norm_dev.command(name="edit")
  async def edit(self, ctx, message: discord.Message, *, edit: str):
    try:
      await ctx.message.delete()
    except BaseException:
      pass
    await message.edit(content=edit)

  # @cog_ext.cog_subcommand(
  #   base="dev",
  #   name="edit",
  #   description="Edit a message I have sent before",
  #   options=[
  #     create_option("message", "The message to edit", 3, required=True),
  #     create_option("edit", "The new text", 3, required=True)
  #   ],
  #   guild_ids=[243159711237537802,805579185879121940])
  # async def slash_edit(self,ctx,message:discord.Message,edit:str):
  #   await ctx.defer(True)
  #   check = await self.cog_check(ctx)
  #   if check is not True:
  #     return await ctx.send(hidden=True,str(check))
  #   message = await commands.MessageConverter.convert(ctx, message)
  #   await asyncio.gather(
  #     message.edit(content=str(edit)),
  #     ctx.send(hidden=True,f"{message.jump_url} has been edited")
  #   )

  @norm_dev.command(name="react")
  async def react(self, ctx, message: discord.Message, *, reactions: str):
    try:
      await ctx.message.delete()
    except BaseException:
      pass
    new_reactions = []
    reactions = reactions.encode('unicode_escape')
    reactions = reactions.replace(b"\\", bytes(b" \\"))
    reactions = reactions.replace(b"<", bytes(b" <"))
    reactions = reactions.decode('unicode_escape')
    for react in reactions.split(" "):
      if react != "":
        new_reactions.append(react)
    for reaction in new_reactions:
      try:
        await message.add_reaction(reaction)
      except BaseException:
        pass

  @norm_dev.command(name="status")
  async def status(self):
    """Sends the status of the machine running Friday"""
    print("")

  @norm_dev.command(name="restart")
  #
  # This could not work when clusters
  #
  async def restart(self, ctx, force: bool = False):
    # global restartPending,songqueue
    if self.bot.restartPending is True and force is False:
      await ctx.reply(embed=embed(title="A restart is already pending"))
      return

    self.bot.restartPending = True
    stat = await ctx.reply(embed=embed(title="Pending"), delete_after=None)
    if len(self.bot.voice_clients) > 0 and force is False:
      await stat.edit(embed=embed(title=f"{len(self.bot.voice_clients)} guilds are playing music"))
      while len(self.bot.voice_clients) > 0:
        await stat.edit(embed=embed(title=f"{len(self.bot.voice_clients)} guilds are playing music"))
        await asyncio.sleep(1)
      await stat.edit(embed=embed(title=f"{len(self.bot.voice_clients)} guilds are playing music"))
    # if len(songqueue) is 0 or force is True:
    thispath = os.getcwd()
    if "\\" in thispath:
      seperator = "\\\\"
    else:
      seperator = "/"
    try:
      wait = 5
      while wait > 0:
        await stat.edit(embed=embed(title=f"Restarting in {wait} seconds"))
        await asyncio.sleep(1)
        wait = wait - 1
    finally:
      await asyncio.gather(
          ctx.message.delete(),
          stat.delete()
      )
      subprocess.Popen([f"{thispath}{seperator}restart.sh"], stdin=subprocess.PIPE)

  @norm_dev.group(name="reload", invoke_without_command=True)
  #
  # This could not work when clusters
  #
  async def reload(self, ctx, command: str):
    async with ctx.typing():
      com = self.bot.get_command(command)
      if com is not None and com.cog_name is not None:
        command = com.cog_name
      self.bot.reload_extension(f"cogs.{command.lower() if command is not None else None}")
    await ctx.reply(embed=embed(title=f"Cog *{command}* has been reloaded"))

  @reload.command(name="all")
  #
  # This could not work when clusters
  #
  async def reload_all(self, ctx):
    async with ctx.typing():
      await self.bot.reload_cogs()
      await self.bot.log.set_all_guilds()
    await ctx.reply(embed=embed(title="All cogs have been reloaded"))

  @reload.command(name="slash")
  #
  # This could not work when clusters
  #
  async def reload_slash(self, ctx):
    async with ctx.typing():
      await self.bot.slash.sync_all_commands()
    await ctx.reply(embed=embed(title="Slash commands synced"))

  @norm_dev.command(name="load")
  #
  # This could not work when clusters
  #
  async def load(self, ctx, command: str):
    async with ctx.typing():
      self.bot.load_extension(f"cogs.{command.lower()}")
    await ctx.reply(embed=embed(title=f"Cog *{command}* has been loaded"))

  @norm_dev.command(name="unload")
  #
  # This could not work when clusters
  #
  async def unload(self, ctx, command: str):
    async with ctx.typing():
      self.bot.unload_extension(f"cogs.{command.lower()}")
    await ctx.reply(embed=embed(title=f"Cog *{command}* has been unloaded"))

  # @reload.error
  # @load.error
  # @unload.error
  # async def reload_error(self, ctx, error):
  #   if not isinstance(error, commands.NotOwner):
  #     await ctx.reply(embed=embed(title=f"Failed to reload *{str(''.join(ctx.message.content.split(ctx.prefix+ctx.command.name+' ')))}*", color=MessageColors.ERROR))
  #     print(error)
  #     self.bot.logger.error(error)

  @norm_dev.command(name="update")
  #
  # This could not work when clusters
  #
  async def update(self, ctx):
    message = await ctx.reply(embed=embed(title="Updating..."))
    thispath = os.getcwd()
    if "\\" in thispath:
      seperator = "\\\\"
    else:
      seperator = "/"
    if self.bot.prod or self.bot.canary:
      subprocess.Popen([f"{thispath}{seperator}update{'' if not self.bot.canary else '_canary'}.sh"], stdin=subprocess.PIPE)
    subprocess.Popen([f"{thispath}{seperator}install.sh"], stdin=subprocess.PIPE)
    await message.edit(embed=embed(title="Update complete!"))

  @norm_dev.command(name="cogs")
  async def cogs(self, ctx):
    cogs = ", ".join(self.bot.cogs)
    await ctx.reply(embed=embed(title=f"{len(self.bot.cogs)} total cogs", description=f"{cogs}"))

  @norm_dev.command(name="log")
  async def log(self, ctx):
    thispath = os.getcwd()
    if "\\" in thispath:
      seperator = "\\\\"
    else:
      seperator = "/"
    shutil.copy(f"{thispath}{seperator}logging.log", f"{thispath}{seperator}logging-send.log")
    await ctx.reply(file=discord.File(fp=f"{thispath}{seperator}logging-send.log", filename="logging.log"))

  @norm_dev.command(name="markdown", aliases=["md"])
  async def markdown(self, ctx):
    build_docs(self.bot)
    await ctx.reply(embed=embed(title="Commands loaded"))
    # with open("docs/commands.md", "w") as f:
    #   f.write("# Commands\n\n")
    #   for cog in cogs:
    #     f.write(f"## {cog}\n\n")
    #     for com in commands:
    #       if com.hidden is False and com.enabled is True and com.cog_name == cog:
    #         # f.write(f"""### {ctx.prefix}{com.name}\n{(f'Aliases: `{ctx.prefix}'+f", {ctx.prefix}".join(com.aliases)+'`') if len(com.aliases) > 0 else ''}\n{f'Description: {com.description}' if com.description != '' else ''}\n""")
    #         f.write(f"### `{ctx.prefix}{com.name}`\n\n")
    #         usage = '\n  '.join(syntax(com, quotes=False).split('\n'))
    #         usage = discord.utils.escape_markdown(usage).replace("<", "\\<")
    #         f.write(f"Usage:\n\n  {usage}\n\n")
    #         f.write("Aliases: ```" + (f'{ctx.prefix}' + f",{ctx.prefix}".join(com.aliases) if len(com.aliases) > 0 else 'None') + "```\n\n")
    #         f.write(f"Description: ```{com.description or 'None'}```\n\n")
    #   f.close()
    # await ctx.reply(file=discord.File(fp=f"{thispath}{seperator}docs{seperator}commands.md", filename="commands.md"))

  @norm_dev.command(name="mysql")
  async def mysql(self, ctx, *, string: str):
    async with ctx.channel.typing():
      async with asqlite.connect("friday.db") as mydb:
        async with mydb.cursor() as mycursor:
          await mycursor.execute(string)
          if "select" in string.lower():
            response = await mycursor.fetchall()
          else:
            await mydb.commit()
    await ctx.reply(f"```mysql\n{[tuple(r) for r in response] if response is not None else 'failed'}\n```")

  @norm_dev.command(name="html")
  async def html(self, ctx):
    commands = self.bot.commands
    header_start = 3
    cogs = []
    for command in commands:
      if command.hidden is False and command.enabled is True and command.cog_name not in cogs:
        cogs.append(command.cog_name)
    with open("commands.html", "w") as f:
      for cog in cogs:
        f.write(f"<h{header_start} class='t-lg'>{cog}</h{header_start}>")
        for com in commands:
          if com.hidden is False and com.enabled is True and com.cog_name == cog:
            f.write(f"<h{header_start+1}>{ctx.prefix}{com.name}</h{header_start+1}>")
            usage = '<br>'.join(syntax(com, quotes=False).replace("<", "&lt;").replace(">", "&gt;").split('\n'))
            # usage = discord.utils.escape_markdown(usage)
            f.write(f"<p>Usage:<br>{usage}</p>")
            f.write("<p>Aliases: " + (f'{ctx.prefix}' + f",{ctx.prefix}".join(com.aliases) if len(com.aliases) > 0 else 'None') + "</p>")
            f.write(f"<p>Description: {com.description or 'None'}</p>")
      f.close()
    thispath = os.getcwd()
    if "\\" in thispath:
      seperator = "\\\\"
    else:
      seperator = "/"
    await ctx.reply(file=discord.File(fp=f"{thispath}{seperator}commands.html", filename="commands.html"))

  @norm_dev.command(name="db")
  async def database(self, ctx: commands.Context):
    thispath = os.getcwd()
    if "\\" in thispath:
      seperator = "\\\\"
    else:
      seperator = "/"
    await ctx.reply(file=discord.File(fp=f"{thispath}{seperator}friday.db", filename="db.db"))

  @norm_dev.command(name="graph")
  async def graph(self, ctx):
    async with ctx.typing():
      channel = self.bot.get_guild(707441352367013899).get_channel(713270475031183390)

      def predicate(message):
        return message.author.id == 476303446547365891

      messages = await channel.history(limit=None, oldest_first=True).filter(predicate).flatten()
      with open("join_sheet.csv", "w") as f:
        f.write("time,count,ads\n")
        for msg in messages:
          content = discord.utils.remove_markdown(msg.content)
          # if msg.author.id != 751680714948214855 and msg.author.id != 760615464300445726:
          time = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
          title = msg.embeds[0].title if len(msg.embeds) != 0 else discord.Embed.Empty
          ads = ["2021-05-26 05:14:31", "2021-06-12 03:26:15", "2021-07-01 19:46:52"]
          description = msg.embeds[0].description if len(msg.embeds) != 0 else discord.Embed.Empty
          count = description.split(" ")[-1] if not isinstance(description, discord.embeds._EmptyEmbed) else title.split(" ")[-1] if not isinstance(title, discord.embeds._EmptyEmbed) else None
          count = content.split(" ")[-1] if content != "" else count
          f.write(f"{time},{count}{',Ad'if time in ads else ''}\n")
        f.close()
    thispath = os.getcwd()
    if "\\" in thispath:
      seperator = "\\\\"
    else:
      seperator = "/"
    await ctx.reply(file=discord.File(fp=f"{thispath}{seperator}join_sheet.csv", filename="join_sheet.csv"))

  # @norm_dev.command(name="joinleave")
  # async def norm_dev_join_leave(self, ctx):
  #   channel = self.bot.get_guild(707441352367013899).get_channel(713270475031183390)
  #   messages = await channel.history(limit=None, oldest_first=True).flatten()

  #   # for msg in messages:

  # @norm_dev.command(name="eval")
  # async def _eval(self, ctx, *, body: str):
  #   """Evaluates a code"""

  #   env = {
  #       'bot': self.bot,
  #       'ctx': ctx,
  #       'channel': ctx.channel,
  #       'author': ctx.author,
  #       'guild': ctx.guild,
  #       'message': ctx.message,
  #       '_': self._last_result
  #   }

  #   env.update(globals())

  #   body = self.cleanup_code(body)
  #   stdout = io.StringIO()

  #   to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

  #   try:
  #     exec(to_compile, env)
  #   except Exception as e:
  #     return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

  #   func = env['func']
  #   try:
  #     # with redirect_stdout(stdout):
  #     ret = await func()
  #   except Exception:
  #     value = stdout.getvalue()
  #     await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
  #   else:
  #     value = stdout.getvalue()
  #     try:
  #       await ctx.message.add_reaction('\u2705')
  #     except BaseException:
  #       pass

  #     if ret is None:
  #       if value:
  #         await ctx.send(f'```py\n{value}\n```')
  #     else:
  #       self._last_result = ret
  #       await ctx.send(f'```py\n{value}{ret}\n```')

  @commands.Cog.listener()
  async def on_message(self, ctx: commands.Context):
    if "process.exit()" in ctx.clean_content or "bot.destroy()" in ctx.clean_content:
      try:
        return await ctx.add_reaction("😡")
      except discord.Forbidden:
        pass


def setup(bot):
  bot.add_cog(Dev(bot))
