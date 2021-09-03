import asyncpg
import os

from discord.ext import commands
from typing_extensions import TYPE_CHECKING
from typing import Union

if TYPE_CHECKING:
  from index import Friday as Bot


class Database(commands.Cog):
  """Database Stuffs and Tings"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.loop = bot.loop
    self.columns = {
        "servers": [
            "id bigint PRIMARY KEY NOT NULL",
            "tier text NULL",
            "prefix varchar(5) NOT NULL DEFAULT '!'",
            "patreon_user bigint NULL DEFAULT NULL",
            "lang varchar(2) NULL DEFAULT NULL",
            "autodeletemsgs smallint NOT NULL DEFAULT 0",
            "max_mentions int NULL DEFAULT NULL",
            "max_messages text NULL",
            "remove_invites boolean DEFAULT false",
            "bot_manager bigint DEFAULT NULL",
            "persona text DEFAULT 'friday'",
            "customjoinleave text NULL",
            "botmasterrole bigint NULL DEFAULT NULL",
            "chatchannel bigint NULL DEFAULT NULL",
            "musicchannel bigint NULL DEFAULT NULL",
            "customsounds text NULL",
        ],
        "votes": [
            "id bigint PRIMARY KEY NOT NULL",
            "to_remind boolean NOT NULL DEFAULT false",
            "has_reminded boolean NOT NULL DEFAULT false",
            "voted_time timestamp NULL DEFAULT NULL"
        ],
        "countdowns": [
            "guild bigint NULL",
            "channel bigint NOT NULL",
            "message bigint NOT NULL",
            "title text NULL",
            "time bigint NOT NULL"
        ],
        "welcome": [
            "guild_id bigint PRIMARY KEY NOT NULL",
            "role_id bigint DEFAULT NULL",
            "channel_id bigint DEFAULT NULL",
            "message text DEFAULT NULL"
        ],
        "blacklist": [
            "id bigint",
            "guild_id bigint",
            "word text"
        ],
    }
    self.loop.run_until_complete(self.setup())
    if self.bot.cluster_idx == 0:
      self.loop.run_until_complete(self.create_tables())
      self.loop.run_until_complete(self.sync_table_columns())

  async def setup(self):
    hostname = 'localhost' if self.bot.prod or self.bot.canary else os.environ["DBHOSTNAME"]
    username = os.environ["DBUSERNAMECANARY"] if self.bot.canary else os.environ["DBUSERNAME"] if self.bot.prod else os.environ["DBUSERNAMELOCAL"]
    password = os.environ["DBPASSWORDCANARY"] if self.bot.canary else os.environ["DBPASSWORD"] if self.bot.prod else os.environ["DBPASSWORDLOCAL"]
    database = os.environ["DBDATABASECANARY"] if self.bot.canary else os.environ["DBDATABASE"] if self.bot.prod else os.environ["DBDATABASELOCAL"]
    self.connection: asyncpg.Pool = await asyncpg.create_pool(host=hostname, user=username, password=password, database=database, loop=self.loop)

  @commands.Cog.listener()
  async def on_ready(self):
    actual_guilds, checked_guilds = [guild.id for guild in self.bot.guilds], []
    for guild_id in await self.query("SELECT id FROM servers"):
      if int(guild_id[0]) in actual_guilds:
        checked_guilds.append(guild_id)
    if len(checked_guilds) == len(self.bot.guilds):
      self.bot.logger.info("All guilds are in the Database")

  async def create_tables(self):
    for table in self.columns:
      await self.query(f"CREATE TABLE IF NOT EXISTS {table} ({','.join(self.columns[table])});")

  async def sync_table_columns(self):
    # https://stackoverflow.com/questions/9991043/how-can-i-test-if-a-column-exists-in-a-table-using-an-sql-statement
    ...

  async def query(self, query: str, *params) -> Union[str, None, list]:
    async with self.connection.acquire() as mycursor:
      if "select" in query.lower():
        result = await mycursor.fetch(query, *params)
      else:
        await mycursor.execute(query, *params)
    if hasattr(self.bot, "logger"):
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


def setup(bot):
  bot.add_cog(Database(bot))
