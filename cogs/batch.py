from discord.ext import commands  # , tasks
import asyncio
# from functions import query
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class BatchUpdates(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.bot = bot

    if not hasattr(self.bot, "_updates"):
      self.bot._updates = []
    self.lock = asyncio.Lock()
    # self.bulker.start()

  # [{123456: [{"prefix": ")"}]}]

  # async def do_bulk(self):
  #   if len(self.bot._updates) != 0:
  #     changes_to_make = len(self.bot._updates)
  #     for guild_id, changes in self.bot._updates:
  #       args = [f"{change}={val}" for change, val in changes]
  #       query(self.bot.log.mydb, "UPDATE servers SET ? WHERE id=?", ", ".join(args), guild_id)
  #       self.bot._updates.pop(guild_id)
  #     print(f"Updated DB with {changes_to_make} changes")
  #     self.bot.logger.info(f"Updated DB with {changes_to_make} changes")

  # @tasks.loop(seconds=10.0)
  # async def bulker(self):
  #   async with self.lock:
  #     await self.do_bulk()

  # @bulker.after_loop
  # async def on_bulker_cancel(self):
  #   if self.bulker.is_being_cancelled() and len(self.bot._updates) != 0:
  #     await self.do_bulk()


def setup(bot):
  bot.add_cog(BatchUpdates(bot))
