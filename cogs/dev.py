from __future__ import annotations

import asyncio
import copy
import importlib
import io
import logging
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time as _time
import traceback
from contextlib import redirect_stdout
from typing import (TYPE_CHECKING, Any, Awaitable, Callable, Literal, Optional,
                    Union)

import discord
from discord.ext import commands
from dotenv import load_dotenv

import cogs
from cogs.help import syntax
from functions import (MessageColors, MyContext,  # , query  # , MessageColors
                       build_docs, embed, time)
from functions.custom_contexts import GuildContext
from functions.formats import TabularData, plural

if TYPE_CHECKING:
  from asyncpg import Record
  from typing_extensions import Self

  from index import Friday

log = logging.getLogger(__name__)


class PerformanceMocker:
  """A mock object that can also be used in await expressions."""

  def __init__(self):
    self.loop = asyncio.get_running_loop()

  def permissions_for(self, obj: Any) -> discord.Permissions:
    # Lie and say we don't have permissions to embed
    # This makes it so pagination sessions just abruptly end on __init__
    # Most checks based on permission have a bypass for the owner anyway
    # So this lie will not affect the actual command invocation.
    perms = discord.Permissions.all()
    perms.administrator = False
    perms.embed_links = False
    perms.add_reactions = False
    return perms

  def __getattr__(self, attr: str) -> Self:
    return self

  def __call__(self, *args: Any, **kwargs: Any) -> Self:
    return self

  def __repr__(self) -> str:
    return '<PerformanceMocker>'

  def __await__(self):
    future: asyncio.Future[Self] = self.loop.create_future()
    future.set_result(self)
    return future.__await__()

  async def __aenter__(self) -> Self:
    return self

  async def __aexit__(self, *args: Any) -> Self:
    return self

  def __len__(self) -> int:
    return 0

  def __bool__(self) -> bool:
    return False


class RawEmoji(commands.Converter):
  reg = re.compile(r"""[^a-zA-Z0-9\s.!@#$%^&*()_+-+,./<>?;':"{}[\]\\|]{1}""")

  async def convert(self, ctx: MyContext, argument: str):
    try:
      return await commands.EmojiConverter().convert(ctx, argument)
    except commands.BadArgument:
      try:
        emoji = self.reg.match(argument)
        return emoji and emoji[0].strip(" ")
      except TypeError:
        raise commands.BadArgument(f'Could not find an emoji by name {argument!r}.')


class Dev(commands.Cog, command_attrs=dict(hidden=True)):
  """Commands used by and for the developer"""

  def __init__(self, bot: Friday) -> None:
    self.bot: Friday = bot
    self._last_result: Optional[Any] = None

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__} owner={self.bot.owner_id}>"

  async def cog_check(self, ctx: MyContext) -> bool:
    if ctx.author.id == 892865928520413245:
      return True
    if not await self.bot.is_owner(ctx.author):
      raise commands.NotOwner()
    return True

  async def cog_command_error(self, ctx: MyContext, error: commands.CommandError):
    ignore = (commands.MissingRequiredArgument, commands.BadArgument,)
    if isinstance(error, ignore):
      return

    if isinstance(error, commands.CheckFailure):
      log.warning("Someone found a dev command")
    else:
      await ctx.send(f"```py\n{error}\n```")

  def cleanup_code(self, content: str):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
      return '\n'.join(content.split('\n')[1:-1])

    # remove `foo`
    return content.strip('` \n')

  async def run_process(self, command: str) -> list[str]:
    try:
      process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      result = await process.communicate()
    except NotImplementedError:
      process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      result = await self.bot.loop.run_in_executor(None, process.communicate)

    return [output.decode() for output in result]

  @commands.Cog.listener()
  async def on_ready(self):
    if self.bot.cluster_idx == 0:
      if not (self.bot.prod or self.bot.canary):
        DIARY = discord.Object(id=243159711237537802)
        await self.bot.tree.sync(guild=DIARY)
        await self.bot.tree.sync()

  @commands.command()
  @commands.guild_only()
  async def sync(self, ctx: GuildContext, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None):
    """Works like:
      `!sync` -> global sync
      `!sync ~` -> sync current guild
      `!sync *` -> copies all global app commands to current guild and syncs
      `!sync ^` -> clears all commands from the current guild target and syncs (removes guild commands)
      `!sync id_1 id_2` -> syncs guilds with id 1 and 2
    """
    if not guilds:
      if spec == "~":
        synced = await ctx.bot.tree.sync(guild=ctx.guild)
      elif spec == "*":
        ctx.bot.tree.copy_global_to(guild=ctx.guild)
        synced = await ctx.bot.tree.sync(guild=ctx.guild)
      elif spec == "^":
        ctx.bot.tree.clear_commands(guild=ctx.guild)
        await ctx.bot.tree.sync(guild=ctx.guild)
        synced = []
      else:
        synced = await ctx.bot.tree.sync()

      await ctx.send(
          f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
      )
      return

    ret = 0
    for guild in guilds:
      try:
        await ctx.bot.tree.sync(guild=guild)
      except discord.HTTPException:
        pass
      else:
        ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

  @commands.group(name="dev", invoke_without_command=True, case_insensitive=True)
  async def dev(self, ctx: MyContext):
    await ctx.send_help(ctx.command)

  @dev.command("chain")
  async def dev_chain(self, ctx: MyContext, *, commands: str):
    commandlist = commands.split("&&")
    if ctx.bot_permissions.add_reactions:
      await ctx.message.add_reaction("\N{OK HAND SIGN}")

    for command in commandlist:
      msg = copy.copy(ctx.message)
      msg.content = ctx.prefix + command

      new_ctx = await self.bot.get_context(msg, cls=type(ctx))

      await new_ctx.reinvoke()

  @dev.command(name="say")
  async def say(self, ctx: MyContext, channel: Optional[discord.TextChannel] = None, *, say: str):
    new_channel = channel or ctx.channel
    try:
      await ctx.message.delete()
    except BaseException:
      pass
    await new_channel.send(f"{say}")

  @dev.group(name="reload", invoke_without_command=True)
  async def reload(self, ctx: MyContext, *, modules: str):
    mods = [mod.strip("\"") for mod in modules.split(" ")]
    ret = []
    for module in mods:
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
      else:
        command = self.bot.get_command(module)
        if command:
          cog_name: str = command.cog_name  # type: ignore
          ret.append((0, "cogs." + cog_name.lower()))
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
          # if self.bot.tasks:
          #   self.bot.tasks.put(Event("reload_cog", "all", module))
          await self.reload_or_load_extention(module)
        except Exception:
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

  async def reload_or_load_extention(self, module):
    try:
      await self.bot.reload_extension(module)
    except commands.ExtensionNotLoaded:
      await self.bot.load_extension(module)

  @reload.command(name="all")
  async def reload_all(self, ctx: MyContext):
    async with ctx.typing():
      if self.bot.canary:
        stdout, stderr = await self.run_process("git pull origin canary && git submodule update")
      elif self.bot.prod:
        stdout, stderr = await self.run_process("git pull origin master && git submodule update")
      else:
        return await ctx.reply(embed=embed(title="You are not on a branch", color=MessageColors.error()))

    load_dotenv()

    confirm = await ctx.prompt("Would you like to run pip install upgrade?")
    if confirm:
      pstdout, pstderr = await self.run_process("python -m pip install --upgrade pip && python -m pip install -r requirements.txt --upgrade --no-cache-dir")
      if pstderr:
        log.error(pstderr)
      await ctx.safe_send(pstdout)

    modules = self.modules_from_git(stdout)
    mods_text = "\n".join(f"{index}. {module}" for index, (_, module) in enumerate(modules, start=1))
    confirm = await ctx.prompt("This will update the following modules, are you sure?", content=f"```\n{mods_text or 'NULL'}\n```", embed=embed(title="This will update the following modules, are you sure?"))
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
          await self.reload_or_load_extention(module)
        except commands.ExtensionError:
          statuses.append((":x:", module))
        else:
          statuses.append((":white_check_mark:", module))

    await ctx.send(embed=embed(title="Reloading modules", description="\n".join(f"{status} {module}" for status, module in statuses)))
    await self.bot.tree.sync()
    # async with ctx.typing():
    #   await self.bot.reload_cogs()
    # await ctx.reply(embed=embed(title="All cogs have been reloaded"))

  @reload.command("env")
  async def reload_env(self, ctx: MyContext):
    load_dotenv()
    await ctx.reply(embed=embed(title="Reloaded .env"))

  @reload.command("module")
  async def reload_module(self, ctx: MyContext, *, module: str):
    try:
      importlib.reload(sys.modules[module])
    except KeyError:
      return await ctx.reply(embed=embed(title=f"Module {module} not found", color=MessageColors.error()))
    except Exception:
      return await ctx.reply(embed=embed(title=f"Failed to reload module {module}", color=MessageColors.error()))
    else:
      await ctx.reply(embed=embed(title=f"Reloaded module {module}"))

  @dev.command(name="load")
  async def load(self, ctx: MyContext, command: str):
    async with ctx.typing():
      path = "spice.cogs." if command.lower() in cogs.spice else "cogs."
      await self.bot.load_extension(f"{path}{command.lower()}")
    await ctx.reply(embed=embed(title=f"Cog *{command}* has been loaded"))

  @dev.command(name="unload")
  async def unload(self, ctx: MyContext, command: str):
    async with ctx.typing():
      path = "spice.cogs." if command.lower() in cogs.spice else "cogs."
      await self.bot.unload_extension(f"{path}{command.lower()}")
    await ctx.reply(embed=embed(title=f"Cog *{command}* has been unloaded"))

  # @reload.error
  # @load.error
  # @unload.error
  # async def reload_error(self, ctx, error):
  #   if not isinstance(error, commands.NotOwner):
  #     await ctx.reply(embed=embed(title=f"Failed to reload *{str(''.join(ctx.message.content.split(ctx.prefix+ctx.command.name+' ')))}*", color=MessageColors.error()))
  #     print(error)
  #     log.error(error)

  @dev.command(name="block")
  async def block(self, ctx: MyContext, object_id: int):
    await self.bot.blacklist.put(object_id, True)
    await ctx.send(embed=embed(title=f"{object_id} has been blocked"))

  @dev.command(name="unblock")
  async def unblock(self, ctx: MyContext, object_id: int):
    try:
      await self.bot.blacklist.remove(object_id)
    except KeyError:
      pass
    await ctx.send(embed=embed(title=f"{object_id} has been unblocked"))

  @dev.command(name="log")
  async def log(self, ctx: MyContext):
    async with ctx.typing():
      thispath = os.getcwd()
      if "\\" in thispath:
        seperator = "\\\\"
      else:
        seperator = "/"
      shutil.copy(f"{thispath}{seperator}logging.log", f"{thispath}{seperator}logging-send.log")
    await ctx.reply(file=discord.File(fp=f"{thispath}{seperator}logging-send.log", filename="logging.log"))

  @dev.command(name="markdown", aliases=["md"])
  async def markdown(self, ctx: MyContext):
    build_docs(self.bot)
    await ctx.reply(embed=embed(title="Commands loaded"))

  @dev.command("time")
  async def time(self, ctx: MyContext, *, _time: time.Time):
    await ctx.send(f"{time.format_dt(_time.dt)} ({time.format_dt(_time.dt, style='R')}) `{time.format_dt(_time.dt)}`")

  @dev.command(name="sudo")
  async def sudo(self, ctx: MyContext, channel: Optional[discord.TextChannel], user: Union[discord.Member, discord.User], *, command: str):
    msg = copy.copy(ctx.message)
    new_channel = channel or ctx.channel
    msg.channel = new_channel
    msg.author = user
    msg.content = ctx.prefix + command
    new_ctx = await self.bot.get_context(msg, cls=type(ctx))
    await self.bot.invoke(new_ctx)

  @dev.command(name="do", aliases=["repeat"])
  async def do(self, ctx: MyContext, times: int, *, command: str):
    msg = copy.copy(ctx.message)
    msg.content = ctx.prefix + command

    new_ctx = await self.bot.get_context(msg, cls=type(ctx))

    for i in range(times):
      await new_ctx.reinvoke()

  @commands.group(invoke_without_command=True)
  async def sql(self, ctx: MyContext, *, query: str):
    """Run some SQL."""
    query = self.cleanup_code(query)

    is_multistatement = query.count(';') > 1
    strategy: Callable[[str], Union[Awaitable[list[Record]], Awaitable[str]]]
    if is_multistatement:
        # fetch does not support multiple statements
      strategy = ctx.db.execute
    else:
      strategy = ctx.db.fetch

    try:
      start = _time.perf_counter()
      results = await strategy(query)
      dt = (_time.perf_counter() - start) * 1000.0
    except Exception:
      return await ctx.send(f'```py\n{traceback.format_exc()}\n```')

    rows = len(results)
    if isinstance(results, str) or rows == 0:
      return await ctx.send(f'`{dt:.2f}ms: {results}`')

    headers = list(results[0].keys())
    table = TabularData()
    table.set_columns(headers)
    table.add_rows(list(r.values()) for r in results)
    render = table.render()

    fmt = f'```\n{render}\n```\n*Returned {plural(rows):row} in {dt:.2f}ms*'
    if len(fmt) > 2000:
      fp = io.BytesIO(fmt.encode('utf-8'))
      await ctx.send('Too many results...', file=discord.File(fp, 'results.txt'))
    else:
      await ctx.send(fmt)

  async def send_sql_results(self, ctx: MyContext, records: list[Any]):
    headers = list(records[0].keys())
    table = TabularData()
    table.set_columns(headers)
    table.add_rows(list(r.values()) for r in records)
    render = table.render()

    fmt = f'```\n{render}\n```'
    if len(fmt) > 2000:
      fp = io.BytesIO(fmt.encode('utf-8'))
      await ctx.send('Too many results...', file=discord.File(fp, 'results.txt'))
    else:
      await ctx.send(fmt)

  @sql.command(name='schema')
  async def sql_schema(self, ctx: MyContext, *, table_name: str):
    """Runs a query describing the table schema."""
    query = """SELECT column_name, data_type, column_default, is_nullable
                  FROM INFORMATION_SCHEMA.COLUMNS
                  WHERE table_name = $1
              """

    results: list[Record] = await ctx.db.fetch(query, table_name)

    if len(results) == 0:
      await ctx.send('Could not find a table with that name')
      return

    await self.send_sql_results(ctx, results)

  @sql.command(name='tables')
  async def sql_tables(self, ctx: MyContext):
    """Lists all SQL tables in the database."""

    query = """SELECT table_name
                  FROM information_schema.tables
                  WHERE table_schema='public' AND table_type='BASE TABLE'
              """

    results: list[Record] = await ctx.db.fetch(query)

    if len(results) == 0:
      await ctx.send('Could not find any tables')
      return

    await self.send_sql_results(ctx, results)

  @sql.command(name='sizes')
  async def sql_sizes(self, ctx: MyContext):
    """Display how much space the database is taking up."""

    # Credit: https://wiki.postgresql.org/wiki/Disk_Usage
    query = """
          SELECT nspname || '.' || relname AS "relation",
              pg_size_pretty(pg_relation_size(C.oid)) AS "size"
            FROM pg_class C
            LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
            WHERE nspname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY pg_relation_size(C.oid) DESC
            LIMIT 20;
      """

    results: list[Record] = await ctx.db.fetch(query)

    if len(results) == 0:
      await ctx.send('Could not find any tables')
      return

    await self.send_sql_results(ctx, results)

  @dev.command(name="html")
  async def html(self, ctx: MyContext):
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

  @dev.command(name="graph")
  async def graph(self, ctx: MyContext):
    async with ctx.typing():
      channel: discord.TextChannel = self.bot.get_channel(713270475031183390)  # type: ignore

      def predicate(message):
        return message.author.display_name == "Friday" \
            and message.author.id in (476303446547365891, 836186774270902333)   # Bot, Bot webhook ids

      w = "time,count,ads\n"
      async for msg in channel.history(limit=None, oldest_first=True):
        if not predicate(msg):
          continue
        content = discord.utils.remove_markdown(msg.content)
        time = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        title = msg.embeds[0].title if len(msg.embeds) != 0 else None
        ads = ["2021-05-26 05:14:31", "2021-06-12 03:26:15", "2021-07-01 19:46:52", "2021-09-20 16:15:57"]
        description = msg.embeds[0].description if len(msg.embeds) != 0 else None
        count = description.split(" ")[-1] if not description else title.split(" ")[-1] if not title else None  # type: ignore
        count = content.split(" ")[-1] if content != "" else count
        w += f"{time},{count}{',Ad'if time in ads else ''}\n"
    fp = io.BytesIO(w.encode())
    await ctx.reply(file=discord.File(fp=fp, filename="join_sheet.csv"))

  @dev.command("pirate")
  async def pirate(self, ctx: MyContext):
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

  # @dev.command(name="joinleave")
  # async def norm_dev_join_leave(self, ctx):
  #   channel = self.bot.get_guild(707441352367013899).get_channel(713270475031183390)
  #   messages = await channel.history(limit=None, oldest_first=True).flatten()

  #   # for msg in messages:

  @dev.command(name="eval")
  async def _eval(self, ctx: MyContext, *, body: str):
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
      with redirect_stdout(stdout):
        ret = await func()
    except Exception:
      value = stdout.getvalue()
      await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
    else:
      value = stdout.getvalue()
      if ctx.bot_permissions.add_reactions:
        await ctx.message.add_reaction('\u2705')

      if ret is None:
        if value:
          await ctx.send(f'```py\n{value}\n```')
      else:
        self._last_result = ret
        await ctx.send(f'```py\n{value}{ret}\n```')

  # @dev.command("evall")
  # async def _evall(self, ctx: MyContext, *, body: str):
  #   """Evaluates a code on all clusters"""

  #   body = self.cleanup_code(body)
  #   to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

  #   sharding = self.bot.sharding
  #   if sharding is None:
  #     return await ctx.send("Sharding cog not found")
  #   data = await sharding.handler(
  #       "evaluate", {"body": to_compile}
  #   )
  #   filtered_data = {instance: data.count(instance) for instance in data}
  #   pretty_data = "".join(
  #       f"```py\n{count}x | {instance[6:]}"
  #       for instance, count in filtered_data.items()
  #   )
  #   if len(pretty_data) > 2000:
  #     pretty_data = pretty_data[:1997] + "..."
  #   await ctx.send(pretty_data)

  @dev.command("perf")
  async def perf(self, ctx: MyContext, *, command: str):
    msg = copy.copy(ctx.message)
    msg.content = ctx.prefix + command

    new_ctx = await self.bot.get_context(msg, cls=type(ctx))

    new_ctx._state = PerformanceMocker()  # type: ignore
    new_ctx.channel = PerformanceMocker()  # type: ignore

    if new_ctx.command is None:
      return await ctx.send("Command not found.")

    start = _time.perf_counter()
    try:
      await new_ctx.command.invoke(new_ctx)
    except commands.CommandError:
      end = _time.perf_counter()
      success = False
      try:
        await ctx.send(f"```py\n{traceback.format_exc()}\n```")
      except discord.HTTPException:
        pass
    else:
      end = _time.perf_counter()
      success = True

    lookup = {
        True: ":white_check_mark:",
        False: ":x:",
        None: ":zzz:"
    }

    await ctx.send(f"Status: {lookup.get(success, ':x:')} Time: {(end - start) * 1000:.2f}ms")


async def setup(bot):
  if not hasattr(bot, "restartPending"):
    bot.restartPending = False

  await bot.add_cog(Dev(bot))
