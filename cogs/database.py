import asyncpg
import os

from discord.ext import commands
from typing_extensions import TYPE_CHECKING
from typing import Optional, Union

if TYPE_CHECKING:
  from index import Friday as Bot


class Database(commands.Cog):
  """Database Stuffs and Tings"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.loop = bot.loop
    self.columns = {
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
            "botchannel text NULL DEFAULT NULL",
            "musicchannel text NULL DEFAULT NULL",
            "disabled_commands text[] DEFAULT array[]::text[]",
            "restricted_commands text[] DEFAULT array[]::text[]",
            "mute_role text NULL DEFAULT NULL",
            "automod_whitelist text[] DEFAULT array[]::text[]",
            "mod_log_channel text NULL DEFAULT NULL",
            "mod_log_events text[] DEFAULT array['bans', 'mutes', 'unbans', 'unmutes', 'kicks']::text[]",
            r"muted_members text[] DEFAULT array[]::text[]",
            r"customsounds json[] NOT NULL DEFAULT array[]::json[]",
            "reddit_extract boolean DEFAULT false",
        ],
        "votes": [
            "id text PRIMARY KEY NOT NULL",
            "to_remind boolean NOT NULL DEFAULT false",
            "has_reminded boolean NOT NULL DEFAULT false",
            "voted_time timestamp NULL DEFAULT NULL"
        ],
        "reminders": [
            "id bigserial PRIMARY KEY NOT NULL",
            "expires timestamp NOT NULL",
            "created timestamp NOT NULL DEFAULT (now() at time zone 'utc')",
            "event text",
            "extra jsonb DEFAULT '{}'::jsonb",
        ],
        "patrons": [
            "user_id text PRIMARY KEY NOT NULL",
            "tier smallint NOT NULL DEFAULT 0",
            "guild_ids text[] NOT NULL DEFAULT array[]::text[]",
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
            "punishments text[] DEFAULT array['delete']::text[]",
            "dmuser bool DEFAULT true",
            "words text[]"
        ],
    }
    hostname = 'localhost' if self.bot.prod or self.bot.canary else os.environ["DBHOSTNAME"]
    username = os.environ["DBUSERNAMECANARY"] if self.bot.canary else os.environ["DBUSERNAME"] if self.bot.prod else os.environ["DBUSERNAMELOCAL"]
    password = os.environ["DBPASSWORDCANARY"] if self.bot.canary else os.environ["DBPASSWORD"] if self.bot.prod else os.environ["DBPASSWORDLOCAL"]
    database = os.environ["DBDATABASECANARY"] if self.bot.canary else os.environ["DBDATABASE"] if self.bot.prod else os.environ["DBDATABASELOCAL"]
    kwargs = {
        'command_timeout': 60,
        'max_size': 20,
        'min_size': 20,
    }
    self._connection: asyncpg.Pool = self.loop.run_until_complete(asyncpg.create_pool(host=hostname, user=username, password=password, database=database, loop=self.loop, **kwargs))
    if self.bot.cluster_idx == 0:
      self.loop.run_until_complete(self.create_tables())
      self.loop.run_until_complete(self.sync_table_columns())

  def __repr__(self):
    return "<cogs.Database>"

  @property
  def pool(self) -> asyncpg.Pool:
    return self._connection

  @commands.Cog.listener()
  async def on_ready(self):
    actual_guilds, checked_guilds = [str(guild.id) for guild in self.bot.guilds], []
    for guild_id in await self.query("SELECT id FROM servers"):
      if str(guild_id[0]) in actual_guilds:
        checked_guilds.append(guild_id)
    if len(checked_guilds) == len(self.bot.guilds):
      self.bot.logger.info("All guilds are in the Database")

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

  def cog_unload(self):
    self.update_local_values.stop()


def setup(bot):
  bot.add_cog(Database(bot))
