import asyncio
import copy
import importlib
import io
import os
import re
import shutil
import subprocess
import sys
import textwrap
import traceback
from typing import Optional, Union

import discord
from discord.ext import commands
from dotenv import load_dotenv
from typing_extensions import TYPE_CHECKING

import cogs
from cogs.help import syntax
from functions import (MessageColors, MyContext,  # , query  # , MessageColors
                       build_docs, embed, views, time)

if TYPE_CHECKING:
  from index import Friday as Bot


class GlobalChannel(commands.Converter):
  async def convert(self, ctx, argument):
    try:
      return await commands.TextChannelConverter().convert(ctx, argument)
    except commands.BadArgument:
      # Not found... so fall back to ID + global lookup
      try:
        channel_id = int(argument, base=10)
      except ValueError:
        raise commands.BadArgument(f'Could not find a channel by ID {argument!r}.')
      else:
        channel = ctx.bot.get_channel(channel_id)
        if channel is None:
          raise commands.BadArgument(f'Could not find a channel by ID {argument!r}.')
        return channel


class RawMessage(commands.Converter):
  async def convert(self, ctx, argument):
    try:
      return await commands.MessageConverter().convert(ctx, argument)
    except commands.BadArgument:
      try:
        message_id = int(argument, base=10)
      except ValueError:
        raise commands.BadArgument(f'Could not find a message by ID {argument!r}.')
      else:
        return await ctx.channel.fetch_message(message_id)


class RawEmoji(commands.Converter):
  reg = re.compile(r"""[^a-zA-Z0-9\s.!@#$%^&*()_+-+,./<>?;':"{}[\]\\|]{1}""")

  async def convert(self, ctx, argument):
    try:
      return await commands.EmojiConverter().convert(ctx, argument)
    except commands.BadArgument:
      try:
        return self.reg.match(argument)[0].strip(" ")
      except TypeError:
        raise commands.BadArgument(f'Could not find an emoji by name {argument!r}.')


class Dev(commands.Cog, command_attrs=dict(hidden=True)):
  """Commands used by and for the developer"""

  def __init__(self, bot: "Bot") -> None:
    self.bot = bot
    self._last_result = None

  def __repr__(self) -> str:
    return f"<cogs.Dev owner={self.bot.owner_id}>"

  async def cog_check(self, ctx: "MyContext") -> bool:
    if ctx.author.id == 892865928520413245:
      return True
    if not await self.bot.is_owner(ctx.author):
      raise commands.NotOwner()
    return True

  async def cog_command_error(self, ctx: "MyContext", error):
    ignore = (commands.MissingRequiredArgument, commands.BadArgument,)
    if isinstance(error, ignore):
      return

    if isinstance(error, commands.CheckFailure):
      self.bot.logger.warning("Someone found a dev command")
    else:
      await ctx.send(f"```py\n{error}\n```")

  def cleanup_code(self, content: str):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
      return '\n'.join(content.split('\n')[1:-1])

    # remove `foo`
    return content.strip('` \n')

  async def run_process(self, command):
    try:
      process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      result = await process.communicate()
    except NotImplementedError:
      process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      result = await self.bot.loop.run_in_executor(None, process.communicate)

    return [output.decode() for output in result]

  @commands.group(name="dev", invoke_without_command=True, case_insensitive=True)
  async def norm_dev(self, ctx):
    await ctx.send_help(ctx.command)

  @norm_dev.command("chain")
  async def norm_dev_chain(self, ctx, *, commands: str):
    commands = commands.split("&&")
    await ctx.message.add_reaction("\N{OK HAND SIGN}")

    for command in commands:
      await ctx.invoke(self.bot.get_command(command))

  @norm_dev.command(name="say", rest_is_raw=True,)
  async def say(self, ctx, channel: Optional[GlobalChannel] = None, *, say: str):
    channel = ctx.channel if channel is None else channel
    try:
      await ctx.message.delete()
    except BaseException:
      pass
    await channel.send(f"{say}")

  @norm_dev.command(name="edit")
  async def edit(self, ctx, message: RawMessage, *, edit: str):
    try:
      await ctx.message.delete()
    except BaseException:
      pass
    if message.id == 707520808448294983:
      return await message.edit(content=edit, view=views.SupportIntroRoles())
    await message.edit(content=edit)

  @norm_dev.command(name="react")
  async def react(self, ctx, messages: commands.Greedy[RawMessage], reactions: commands.Greedy[RawEmoji]):
    try:
      await ctx.message.delete()
    except BaseException:
      pass
    for msg in messages:
      for reaction in reactions:
        try:
          await msg.add_reaction(reaction)
        except BaseException:
          pass

  @norm_dev.command(name="quit")
  async def quit(self, ctx, *, force: bool = False):
    if self.bot.restartPending is True and force is False:
      await ctx.reply(embed=embed(title="A restart is already pending"))
      return
    self.bot.restartPending = True
    stat = await ctx.reply(embed=embed(title="Pending"))
    if len(self.bot.voice_clients) > 0 and force is False:
      await stat.edit(embed=embed(title=f"{len(self.bot.voice_clients)} guilds are playing music"))
      while len(self.bot.voice_clients) > 0:
        await stat.edit(embed=embed(title=f"{len(self.bot.voice_clients)} guilds are playing music"))
        await asyncio.sleep(1)
      await stat.edit(embed=embed(title=f"{len(self.bot.voice_clients)} guilds are playing music"))
    try:
      wait = 5
      while wait > 0:
        await stat.edit(embed=embed(title=f"Quiting in {wait} seconds"))
        await asyncio.sleep(1)
        wait = wait - 1
    finally:
      await ctx.message.delete()
      await stat.delete()
      self.bot.restartPending = False
      await self.bot.logout()

  @norm_dev.command(name="restart")
  async def restart(self, ctx, force: bool = False):
    if self.bot.restartPending is True and force is False:
      await ctx.reply(embed=embed(title="A restart is already pending"))
      return

    self.bot.restartPending = True
    stat = await ctx.reply(embed=embed(title="Pending"))
    if len(self.bot.voice_clients) > 0 and force is False:
      await stat.edit(embed=embed(title=f"{len(self.bot.voice_clients)} guilds are playing music"))
      while len(self.bot.voice_clients) > 0:
        await stat.edit(embed=embed(title=f"{len(self.bot.voice_clients)} guilds are playing music"))
        await asyncio.sleep(1)
      await stat.edit(embed=embed(title=f"{len(self.bot.voice_clients)} guilds are playing music"))
    # if len(songqueue) is 0 or force is True:
    try:
      wait = 5
      while wait > 0:
        await stat.edit(embed=embed(title=f"Restarting in {wait} seconds"))
        await asyncio.sleep(1)
        wait = wait - 1
    finally:
      await ctx.message.delete()
      await stat.delete()
      self.bot.restartPending = False
      stdout, stderr = await self.run_process("systemctl daemon-reload && systemctl restart friday.service")
      await ctx.send(f"```sh\n{stdout}\n{stderr}```")

  @norm_dev.group(name="reload", invoke_without_command=True)
  async def reload(self, ctx, *, modules: str):
    modules = [mod.strip("\"") for mod in modules.split(" ")]
    await ctx.trigger_typing()
    ret = []
    for module in modules:
      if module.startswith("cogs"):
        ret.append((0, module.replace("/", ".")))  # root.count("/") - 1 # if functions moves to cog folder
      elif module.startswith("functions"):
        ret.append((1, module.replace("/", ".")))
      elif module.startswith("spice/cogs") or module.startswith("spice.cogs"):
        ret.append((0, module.replace("/", ".")))
      elif module.startswith("spice/functions") or module.startswith("spice.functions"):
        ret.append((1, module.replace("/", ".")))
      elif module.replace("/", ".") in sys.modules:
        ret.append((1, module.replace("/", ".")))
      elif self.bot.get_cog(module.capitalize()) is not None:
        ret.append((0, "cogs." + module.replace("/", ".")))
      elif self.bot.get_command(module) is not None:
        ret.append((0, "cogs." + self.bot.get_command(module).cog_name.lower()))
      else:
        ret.append((1, module.replace("/", ".")))

    statuses = []
    for is_func, module in ret:
      if is_func:
        try:
          actual_module = sys.modules[module]
        except KeyError:
          statuses.append((":zzz:", module))
        else:
          try:
            importlib.reload(actual_module)
          except Exception:
            statuses.append((":x:", module))
          else:
            statuses.append((":white_check_mark:", module))
      else:
        try:
          self.reload_or_load_extention(module)
        except discord.ExtensionError:
          statuses.append((":x:", module))
        else:
          statuses.append((":white_check_mark:", module))

    await ctx.send(embed=embed(title="Reloading modules", description="\n".join(f"{status} {module}" for status, module in statuses)))

  _GIT_PULL_REGEX = re.compile(r'\s*(?P<filename>.+?)\s*\|\s*[0-9]+\s*[+-]+')

  def modules_from_git(self, output):
    files = self._GIT_PULL_REGEX.findall(output)
    ret = []
    for file in files:
      root, ext = os.path.splitext(file)
      if ext != ".py":
        continue

      if root.startswith("cogs"):
        ret.append((0, root.replace("/", ".")))  # root.count("/") - 1 # if functions moves to cog folder
      elif root.startswith("functions"):
        ret.append((1, root.replace("/", ".")))
      elif root.startswith("spice/cogs"):
        ret.append((0, root.replace("/", ".")))
      elif root.startswith("spice/functions"):
        ret.append((1, root.replace("/", ".")))

    ret.sort(reverse=True)
    return ret

  def reload_or_load_extention(self, module):
    try:
      self.bot.reload_extension(module)
    except discord.ExtensionNotLoaded:
      self.bot.load_extension(module)

  @reload.command(name="all")
  async def reload_all(self, ctx):
    async with ctx.typing():
      if self.bot.canary:
        stdout, stderr = await self.run_process("git pull origin canary && git submodule update")
      elif self.bot.prod:
        stdout, stderr = await self.run_process("git pull origin master && git submodule update")
      else:
        return await ctx.reply(embed=embed(title="You are not on a branch", color=MessageColors.ERROR))

    load_dotenv()

    if stdout.startswith("Already up-to-date."):
      return await ctx.send(stdout)

    confirm = await ctx.prompt("Would you like to run pip install upgrade?")
    if confirm:
      pstdout, pstderr = await self.run_process("python -m pip install --upgrade pip && python -m pip install -r requirements.txt --upgrade --no-cache-dir")
      if pstderr:
        self.bot.logger.error(pstderr)
      await ctx.safe_send(pstdout)

    modules = self.modules_from_git(stdout)
    mods_text = "\n".join(f"{index}. `{module}`" for index, (_, module) in enumerate(modules, start=1))
    confirm = await ctx.prompt(f"This will update the following modules, are you sure?\n{mods_text}")
    if not confirm:
      return await ctx.send("Aborting.")

    statuses = []
    for is_func, module in modules:
      if is_func:
        try:
          actual_module = sys.modules[module]
        except KeyError:
          statuses.append((":zzz:", module))
        else:
          try:
            importlib.reload(actual_module)
          except Exception:
            statuses.append((":x:", module))
          else:
            statuses.append((":white_check_mark:", module))
      else:
        try:
          self.reload_or_load_extention(module)
        except discord.ExtensionError:
          statuses.append((":x:", module))
        else:
          statuses.append((":white_check_mark:", module))

    await ctx.send(embed=embed(title="Reloading modules", description="\n".join(f"{status} {module}" for status, module in statuses)))
    # async with ctx.typing():
    #   await self.bot.reload_cogs()
    # await ctx.reply(embed=embed(title="All cogs have been reloaded"))

  @reload.command("env")
  async def reload_env(self, ctx):
    load_dotenv()
    await ctx.reply(embed=embed(title="Reloaded .env"))

  @reload.command("module")
  async def reload_module(self, ctx, *, module: str):
    try:
      importlib.reload(sys.modules[module])
    except KeyError:
      return await ctx.reply(embed=embed(title=f"Module {module} not found", color=MessageColors.ERROR))
    except Exception:
      return await ctx.reply(embed=embed(title=f"Failed to reload module {module}", color=MessageColors.ERROR))
    else:
      await ctx.reply(embed=embed(title=f"Reloaded module {module}"))

  @reload.command(name="slash")
  async def reload_slash(self, ctx):
    async with ctx.typing():
      await self.bot.slash.sync_all_commands()
    await ctx.reply(embed=embed(title="Slash commands synced"))

  @norm_dev.command(name="load")
  async def load(self, ctx, command: str):
    async with ctx.typing():
      path = "spice.cogs." if command.lower() in cogs.spice else "cogs."
      self.bot.load_extension(f"{path}{command.lower()}")
    await ctx.reply(embed=embed(title=f"Cog *{command}* has been loaded"))

  @norm_dev.command(name="unload")
  async def unload(self, ctx, command: str):
    async with ctx.typing():
      path = "spice.cogs." if command.lower() in cogs.spice else "cogs."
      self.bot.unload_extension(f"{path}{command.lower()}")
    await ctx.reply(embed=embed(title=f"Cog *{command}* has been unloaded"))

  # @reload.error
  # @load.error
  # @unload.error
  # async def reload_error(self, ctx, error):
  #   if not isinstance(error, commands.NotOwner):
  #     await ctx.reply(embed=embed(title=f"Failed to reload *{str(''.join(ctx.message.content.split(ctx.prefix+ctx.command.name+' ')))}*", color=MessageColors.ERROR))
  #     print(error)
  #     self.bot.logger.error(error)

  @norm_dev.command(name="block")
  async def block(self, ctx, object_id: int):
    await self.bot.blacklist.put(object_id, True)
    await ctx.send(embed=embed(title=f"{object_id} has been blocked"))

  @norm_dev.command(name="unblock")
  async def unblock(self, ctx, object_id: int):
    try:
      await self.bot.blacklist.remove(object_id)
    except KeyError:
      pass
    await ctx.send(embed=embed(title=f"{object_id} has been unblocked"))

  @norm_dev.command(name="voice")
  async def voice(self, ctx):
    await ctx.send(embed=embed(title=f"I am in `{len(self.bot.voice_clients)}` voice channels"))

  @norm_dev.command(name="update")
  async def update(self, ctx):
    await ctx.trigger_typing()
    if self.bot.canary:
      stdout, stderr = await self.run_process("git reset --hard && git pull origin canary && git submodule update")
    elif self.bot.prod:
      stdout, stderr = await self.run_process("git reset --hard && git pull origin master && git submodule update")
    else:
      return await ctx.reply(embed=embed(title="You are not on a branch", color=MessageColors.ERROR))

    await ctx.send(stdout)
    if stdout.startswith("Already up-to-date."):
      return
    await ctx.trigger_typing()
    stdout, stderr = await self.run_process("python -m pip install --upgrade pip && python -m pip install -r requirements.txt --upgrade --no-cache-dir")
    await ctx.safe_send(stdout)

  @norm_dev.command(name="cogs")
  async def cogs(self, ctx):
    cogs = ", ".join(self.bot.cogs)
    await ctx.reply(embed=embed(title=f"{len(self.bot.cogs)} total cogs", description=f"{cogs}"))

  @norm_dev.command(name="log")
  async def log(self, ctx):
    await ctx.trigger_typing()
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

  @norm_dev.command("time")
  async def time(self, ctx, *, time: time.TimeWithTimezone):
    await ctx.send(f"{discord.utils.format_dt(time.dt)} ({discord.utils.format_dt(time.dt, style='R')})")

  @norm_dev.command(name="sudo")
  async def sudo(self, ctx: "MyContext", channel: Optional[GlobalChannel], user: Union[discord.Member, discord.User], *, command: str):
    msg = copy.copy(ctx.message)
    channel = channel or ctx.channel
    msg.channel = channel
    msg.author = user
    msg.content = ctx.prefix + command
    new_ctx = await self.bot.get_context(msg, cls=type(ctx))
    await self.bot.invoke(new_ctx)

  @norm_dev.command(name="do", aliases=["repeat"])
  async def do(self, ctx: "MyContext", times: int, *, command: str):
    msg = copy.copy(ctx.message)
    msg.content = ctx.prefix + command

    new_ctx = await self.bot.get_context(msg, cls=type(ctx))

    for i in range(times):
      await new_ctx.reinvoke()

  @norm_dev.command(name="mysql")
  async def mysql(self, ctx, *, string: str):
    async with ctx.channel.typing():
      response = await self.bot.db.query(string)
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

  @norm_dev.command(name="graph")
  async def graph(self, ctx):
    async with ctx.typing():
      channel = self.bot.get_channel(713270475031183390)

      def predicate(message):
        return message.author.display_name == "Friday" \
            and message.author.id in (476303446547365891, 836186774270902333)   # Bot, Bot webhook ids

      w = "time,count,ads\n"
      async for msg in channel.history(limit=None, oldest_first=True).filter(predicate):
        content = discord.utils.remove_markdown(msg.content)
        time = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        title = msg.embeds[0].title if len(msg.embeds) != 0 else discord.Embed.Empty
        ads = ["2021-05-26 05:14:31", "2021-06-12 03:26:15", "2021-07-01 19:46:52", "2021-09-20 16:15:57"]
        description = msg.embeds[0].description if len(msg.embeds) != 0 else discord.Embed.Empty
        count = description.split(" ")[-1] if not isinstance(description, discord.embeds._EmptyEmbed) else title.split(" ")[-1] if not isinstance(title, discord.embeds._EmptyEmbed) else None
        count = content.split(" ")[-1] if content != "" else count
        w += f"{time},{count}{',Ad'if time in ads else ''}\n"
    fp = io.BytesIO(w.encode())
    await ctx.reply(file=discord.File(fp=fp, filename="join_sheet.csv"))

  @norm_dev.command("pirate")
  async def pirate(self, ctx):
    pattern = r'completion.:.\s(.+)\\n.}'
    async with ctx.typing():
      with open("spice/ml/openai/default-persona.jsonl", "r") as f:
        with open("spice/ml/openai/pirate-persona.jsonl", "w") as f2:
          for line in f.readlines():
            this = re.findall(pattern, line)
            if len(this) != 0:
              async with self.bot.session.post(f"https://pirate.monkeyness.com/api/translate?english={this[0]}") as r:
                if r.status == 200:
                  text = await r.text()
                  if "Hellohow fares yer day?" in text:
                    text = "Hello how fares yer day?"
                  new = re.sub(pattern, f"""completion":" {text}""" + r'\\n"}', line)
                  f2.write(new)
    await ctx.send("Done")

  # @norm_dev.command(name="joinleave")
  # async def norm_dev_join_leave(self, ctx):
  #   channel = self.bot.get_guild(707441352367013899).get_channel(713270475031183390)
  #   messages = await channel.history(limit=None, oldest_first=True).flatten()

  #   # for msg in messages:

  @norm_dev.command(name="eval")
  async def _eval(self, ctx, *, body: str):
    """Evaluates a code"""

    env = {
        'bot': self.bot,
        'ctx': ctx,
        'embed': embed,
        'channel': ctx.channel,
        'author': ctx.author,
        'guild': ctx.guild,
        'message': ctx.message,
        'self': self,
        '_': self._last_result
    }

    env.update(globals())

    body = self.cleanup_code(body)
    stdout = io.StringIO()

    to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

    try:
      exec(to_compile, env)
    except Exception as e:
      return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

    func = env['func']
    try:
      # with redirect_stdout(stdout):
      ret = await func()
    except Exception:
      value = stdout.getvalue()
      await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
    else:
      value = stdout.getvalue()
      try:
        await ctx.message.add_reaction('\u2705')
      except BaseException:
        pass

      if ret is None:
        if value:
          await ctx.send(f'```py\n{value}\n```')
      else:
        self._last_result = ret
        await ctx.send(f'```py\n{value}{ret}\n```')


def setup(bot):
  bot.add_cog(Dev(bot))
