import asyncpg
import asyncio
import os
# import json

# import discord
# from discord.ext import commands
from typing_extensions import TYPE_CHECKING
from typing import Optional, Union
# import collections

if TYPE_CHECKING:
  from index import Friday as Bot


# class TableMeta(type):
#   @classmethod
#   def __prepare__(mcs, name, bases, **kwargs):
#     return collections.OrderedDict()

#   def __new__(cls, name, parents, dct, **kwargs):
#     columns = []

#     try:
#       table_name = kwargs['table_name']
#     except KeyError:
#       table_name = name.lower()

#     dct['__tablename__'] = table_name

#     for elem, value in dct.items():
#       if isinstance(value, Column):
#         if value.name is None:
#           value.name = elem

#         if value.index:
#           value.index_name = '%s_%s_idx' % (table_name, value.name)

#         columns.append(value)

#     dct['columns'] = columns
#     return super().__new__(cls, name, parents, dct)

#   def __init__(self, name, parents, dct, **kwargs):
#     super().__init__(name, parents, dct)


# class Table(metaclass=TableMeta):
#   @classmethod
#   async def create_pool(cls, uri, **kwargs):

#     cls._pool = pool = await asyncpg.create_pool(uri, **kwargs)
#     return pool

#   @classmethod
#   def all_tables(cls) -> list:
#     return cls.__subclasses__()


COLUMNS = {
    "servers": [
        "id text PRIMARY KEY NOT NULL",
        "tier text NULL",
        "prefix varchar(5) NOT NULL DEFAULT '!'",
        "patreon_user text NULL DEFAULT NULL",
        "lang varchar(2) NULL DEFAULT NULL",
        "max_mentions json NULL DEFAULT NULL",
        "max_messages json NULL DEFAULT NULL",
        "max_content json NULL DEFAULT NULL",
        "remove_invites boolean DEFAULT false",
        "bot_manager text DEFAULT NULL",
        "persona text DEFAULT 'friday'",
        "customjoinleave text NULL",
        "chatchannel text NULL DEFAULT NULL",
        "musicchannel text NULL DEFAULT NULL",
        "mute_role text NULL DEFAULT NULL",
        "mod_log_channel text NULL DEFAULT NULL",
        "mod_log_events text[] DEFAULT array['bans', 'mutes', 'unbans', 'unmutes', 'kicks']::text[]",
        r"muted_members text[] DEFAULT array[]::text[]",
        # "raid_mode smallint NOT NULL DEFAULT 0",
        r"customsounds json[] NOT NULL DEFAULT array[]::json[]",
        r"toprole json NOT NULL DEFAULT '{}'::json",
        r"roles json[] NOT NULL DEFAULT array[]::json[]",
        r"text_channels json[] NOT NULL DEFAULT array[]::json[]",
        "starboard_stars smallint NOT NULL DEFAULT 5",
        "starboard_channel text NULL DEFAULT NULL",
        "reddit_extract boolean DEFAULT false",
    ],
    # "stats": [
    #   "cluster_id serial PRIMARY KEY NOT NULL",
    #   "shard_id serial NOT NULL",
    #   "latency int NOT NULL",
    #  # "status boolean"
    #   "guild_count int NOT NULL",
    #   "last_update timestamp NOT NULL",
    # ],
    "votes": [
        "id text PRIMARY KEY NOT NULL",
        "to_remind boolean NOT NULL DEFAULT false",
        "has_reminded boolean NOT NULL DEFAULT false",
        "voted_time timestamp NULL DEFAULT NULL"
    ],
    "countdowns": [
        "guild text NULL",
        "channel text NOT NULL",
        "message text PRIMARY KEY NOT NULL",
        "title text NULL",
        "time bigint NOT NULL"
    ],
    "welcome": [
        "guild_id text PRIMARY KEY NOT NULL",
        "role_id text DEFAULT NULL",
        "channel_id text DEFAULT NULL",
        "message text DEFAULT NULL"
    ],
    "blacklist": [
        "guild_id text PRIMARY KEY NOT NULL",
        "ignoreadmins bool DEFAULT true",
        "punishments text[] DEFAULT array['delete']::text[]",
        "dmuser bool DEFAULT true",
        "words text[]"
    ],
    "usage": [
        "id BIGSERIAL PRIMARY KEY",
        "guild_id text NOT NULL",
        "action text NOT NULL",
        "timestamp timestamp DEFAULT CURRENT_TIMESTAMP"
    ],
    "nicknames": [
        "id text PRIMARY KEY NOT NULL",
        "guild_id text NOT NULL",
        "user_id text NOT NULL",
        "name text"
    ]
}


class Database:
  """Database Stuffs and Tings"""

  @classmethod
  async def create(cls, *, bot: "Bot", loop: asyncio.AbstractEventLoop = None):
    self = cls()
    self.bot = bot
    self.loop = loop or asyncio.get_event_loop()

    hostname = 'localhost' if bot.prod or bot.canary else os.environ["DBHOSTNAME"]
    username = os.environ["DBUSERNAMECANARY"] if bot.canary else os.environ["DBUSERNAME"] if bot.prod else os.environ["DBUSERNAMELOCAL"]
    password = os.environ["DBPASSWORDCANARY"] if bot.canary else os.environ["DBPASSWORD"] if bot.prod else os.environ["DBPASSWORDLOCAL"]
    database = os.environ["DBDATABASECANARY"] if bot.canary else os.environ["DBDATABASE"] if bot.prod else os.environ["DBDATABASELOCAL"]
    kwargs = {
        'command_timeout': 60,
        'max_size': 20,
        'min_size': 20,
    }
    self._connection: asyncpg.Pool = bot.loop.run_until_complete(asyncpg.create_pool(host=hostname, user=username, password=password, database=database, loop=self.loop, **kwargs))

    if bot.cluster_idx == 0:
      bot.loop.create_task(self.create_tables())
      bot.loop.create_task(self.sync_table_columns())
    return self

  def __repr__(self):
    return "<Database>"

  @property
  def pool(self) -> asyncpg.Pool:
    return self._connection

  async def create_tables(self):
    async with self.pool.acquire(timeout=300.0) as conn:
      async with conn.transaction():
        for table in self.columns:
          await conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({','.join(self.columns[table])});")

  async def sync_table_columns(self):
    # https://stackoverflow.com/questions/9991043/how-can-i-test-if-a-column-exists-in-a-table-using-an-sql-statement
    async with self.pool.acquire(timeout=300.0) as conn:
      async with conn.transaction():
        for table in self.columns:
          for column in self.columns[table]:
            result = await conn.fetch(f"SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='{table}' AND column_name='{column.split(' ')[0]}') LIMIT 1")
            if not result[0].get("exists"):
              await conn.execute(f"ALTER TABLE {table} ADD COLUMN {column};")

  async def get_many(self, query: str, *params) -> Optional[Union[str, list]]:
    async with self.pool.acquire(timeout=300.0) as conn:
      result = await conn.fetch(query, *params)
    if hasattr(self.bot, "logger"):
      self.bot.logger.debug(f"PostgreSQL Query: \"{query}\" + {params}")
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

  async def query(self, query: str, *params) -> Optional[Union[str, list]]:
    async with self.pool.acquire(timeout=300.0) as mycursor:
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
