from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4
from contextlib import redirect_stdout
from traceback import format_exc
from io import StringIO

from discord.ext import commands


if TYPE_CHECKING:
  from index import Friday

log = logging.getLogger(__name__)


class Event:
  def __init__(self, command_id: str, *, output=None, scope: Literal["bot", "launcher"] = None, action: str = None, args: dict = {}):
    self.command_id = command_id

    self.scope = scope
    self.action = action
    self.args = args

    self.output = output

  def __repr__(self) -> str:
    return f"<Event command_id=\"{self.command_id}\">"


class Sharding(commands.Cog):
  def __init__(self, bot: Friday):
    self.bot: Friday = bot

    self._messages: dict[str, Any] = dict()

    self.tasks_to_launcher = self.bot.tasks
    self.tasks_from_launcher = self.bot.tasks_to_complete
    self.executer = self.bot.task_executer

    self.router = None

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def cog_load(self):
    if self.tasks_from_launcher is None:
      return
    self.router = asyncio.create_task(self.handle_tasks_received())

  async def cog_unload(self):
    if self.router and not self.router.cancelled:
      self.router.cancel()

  async def handle_tasks_received(self):
    if self.tasks_from_launcher is None:
      return
    while not self.bot.is_closed():
      task: Event = await self.bot.loop.run_in_executor(self.executer, self.tasks_from_launcher.get)
      if task.action:
        if task.scope != "bot":
          continue
        if task.args:
          asyncio.create_task(
              getattr(self, task.action)(
                  **task.args,
                  command_id=task.command_id
              )
          )
        else:
          asyncio.create_task(
              getattr(self, task.action)(
                  command_id=task.command_id
              )
          )
      if task.output and task.command_id in self._messages:
        for fut in self._messages[task.command_id]:
          if not fut.done():
            fut.set_result(task.output)
            break

  async def evaluate(self, body: str, command_id: str):
    async def _eval(_body):
      env = {
          'bot': self.bot,
          'self': self,
      }

      env.update(globals())
      stdout = StringIO()
      try:
        exec(_body, env)
      except Exception as e:
        return f"```py\n{e.__class__.__name__}: {e}\n```"

      func = env['func']
      try:
        with redirect_stdout(stdout):
          ret = await func()
      except Exception:
        value = stdout.getvalue()
        return f"```py\n{value}{format_exc()}\n```"
      else:
        value = stdout.getvalue()

        if ret is None:
          if value:
            return f"```py\n{value}\n```"
        else:
          return f"```py\n{value}{ret}\n```"
      return "```py\nNone\n```"

    e = Event(command_id, output=await _eval(body))
    if self.tasks_to_launcher:
      await self.bot.loop.run_in_executor(self.executer, self.tasks_to_launcher.put, e)

  async def handler(
      self,
      action: str,
      args: dict = {},
      _timeout: int = 2,
      scope: Literal["bot", "launcher"] = "bot"
  ) -> list:
    command_id = f"{uuid4()}"
    results = []
    self._messages[command_id] = [
        asyncio.Future() for _ in range(self.bot.shard_count)
    ]

    if self.tasks_to_launcher is None:
      raise RuntimeError("tasks_to_launcher is None")
    await self.bot.loop.run_in_executor(self.executer, self.tasks_to_launcher.put, Event(command_id, scope=scope, action=action, args=args))

    try:
      done, _ = await asyncio.wait(
          self._messages[command_id], timeout=_timeout
      )
      for fut in done:
        results.append(fut.result())
    except asyncio.TimeoutError:
      pass
    del self._messages[command_id]
    return results

  # async def send_event(self, action: Literal["statuses", "reload_cog"], scope: Literal["all"] = "all", _input: Any = None):
  #   if self.tasks_to_launcher is None:
  #     raise RuntimeError("tasks_to_launcher is None")
  #   event = Event(action, scope, _input)
  #   await self.bot.loop.run_in_executor(self.executer, self.tasks_to_launcher.put, event)


async def setup(bot):
  ...
  # await bot.add_cog(Sharding(bot))
