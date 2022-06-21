from __future__ import annotations

import asyncio
import os
from datetime import date
from typing import TYPE_CHECKING

from discord.ext import commands, tasks

if TYPE_CHECKING:
  from index import Friday


original_image = "assets\\friday-logo.png"


class DatedEvents(commands.Cog):
  def __init__(self, bot: Friday):
    self.bot: Friday = bot
    # self.events = bot.loop.create_task(self.dated_events(),name="Dated events")

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def cog_load(self) -> None:
    self.dated_events.start()

  async def cog_unload(self) -> None:
    if self.dated_events.is_running():
      self.dated_events.cancel()

  @tasks.loop(hours=1.0)
  async def dated_events(self):
    if not self.bot.prod:
      return
    today = date.today()
    month = today.strftime("%m")
    day = today.strftime("%d")
    guild = self.bot.get_guild(707441352367013899)
    if not guild:
      return
    user = self.bot.user
    thispath = os.getcwd()
    if "\\" in thispath:
      seperator = "\\\\"
    else:
      seperator = "/"
    if int(month) == 4 and int(day) == 1:
      print("april fools")
      self.bot.logger.info("april fools")
      with open(f"{thispath}{seperator}assets{seperator}friday_april_fools.png", "rb") as image:
        f = image.read()
        await user.edit(avatar=f)
        await guild.edit(icon=f, reason="April Fools")
        image.close()
      await asyncio.sleep(43200.0)
    elif int(month) == 4 and int(day) == 2:
      print("post-april fools")
      self.bot.logger.info("post-april fools")
      with open(f"{thispath}{seperator}assets{seperator}friday-logo.png", "rb") as image:
        f = image.read()
        await guild.edit(icon=f, reason="Post-april fools")
        await user.edit(avatar=f)
        image.close()
      await asyncio.sleep(43200.0)

  @dated_events.before_loop
  async def before_dated_events(self):
    await self.bot.wait_until_ready()


async def setup(bot: Friday):
  await bot.add_cog(DatedEvents(bot))
