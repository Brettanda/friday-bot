import asyncpg
import os

from typing_extensions import TYPE_CHECKING
from typing import Union

if TYPE_CHECKING:
  from index import Friday as Bot


class Database:
  """Database Stuffs and Tings"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.loop = bot.loop
    self.loop.run_until_complete(self.setup())

  async def setup(self):
    hostname = 'localhost' if self.bot.prod or self.bot.canary else os.environ["DBHOSTNAME"]
    username = os.environ["DBUSERNAMECANARY"] if self.bot.canary else os.environ["DBUSERNAME"] if self.bot.prod else os.environ["DBUSERNAMELOCAL"]
    password = os.environ["DBPASSWORDCANARY"] if self.bot.canary else os.environ["DBPASSWORD"] if self.bot.prod else os.environ["DBPASSWORDLOCAL"]
    database = os.environ["DBDATABASECANARY"] if self.bot.canary else os.environ["DBDATABASE"] if self.bot.prod else os.environ["DBDATABASELOCAL"]
    self.connection = await asyncpg.create_pool(host=hostname, user=username, password=password, database=database, loop=self.loop)

  async def query(self, query: str, *params) -> Union[str, None, list]:
    async with self.connection.acquire() as mycursor:
      if "select" in query.lower():
        result = await mycursor.fetch(query, *params)
      else:
        await mycursor.execute(query, *params)
    self.bot.logger.debug(f"PostgreSQL Query: \"{query}\" + {params}")
    if "select" in query.lower():
      if isinstance(result, list) and len(result) == 1 and "limit 1" in query.lower():
        result = [tuple(i) for i in result][0]
        if len(result) == 1:
          return result[0]
        return result
      if isinstance(result, list) and len(result) > 0 and "limit 1" not in query.lower():
        return [tuple(i) for i in result]
      elif isinstance(result, list) and len(result) == 0 and "limit 1" in query.lower():
        return None
      return result

  async def close(self):
    await self.connection.close()
