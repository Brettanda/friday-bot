from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional, Union

import asyncpg
from discord.ext import commands

if TYPE_CHECKING:
  from index import Friday as Bot


log = logging.getLogger(__name__)


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
            "max_mentions jsonb NULL DEFAULT NULL",
            "max_messages jsonb NULL DEFAULT NULL",
            "max_content jsonb NULL DEFAULT NULL",
            "remove_invites boolean DEFAULT false",
            "bot_manager text DEFAULT NULL",
            "persona text DEFAULT 'default'",
            "customjoinleave text NULL",
            "chatchannel text NULL DEFAULT NULL",
            "chatstoprepeating boolean DEFAULT true",
            "botchannel text NULL DEFAULT NULL",
            "musicchannel text NULL DEFAULT NULL",
            "disabled_commands text[] DEFAULT array[]::text[]",
            "restricted_commands text[] DEFAULT array[]::text[]",
            "mute_role text NULL DEFAULT NULL",
            "mod_roles text[] NOT NULL DEFAULT array[]::text[]",
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
        "joined": [
            "time TIMESTAMP WITH TIME ZONE",
            "guild_id text",
            "joined boolean DEFAULT NULL",
            "current_count bigint DEFAULT NULL",
        ],
        "voting_streaks": [
          "user_id bigint PRIMARY KEY NOT NULL",
          "created timestamp NOT NULL DEFAULT (now() at time zone 'utc')",
          "last_vote timestamp NOT NULL DEFAULT (now() at time zone 'utc')",
          "days bigint NOT NULL DEFAULT 1",
          "expires timestamp NOT NULL",
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
        "commands": [
            "id bigserial PRIMARY KEY NOT NULL",
            "guild_id text NOT NULL",
            "channel_id text NOT NULL",
            "author_id text NOT NULL",
            "used TIMESTAMP WITH TIME ZONE",
            "prefix text",
            "command text",
            "failed boolean",
        ],
        "chats": [
            "id bigserial PRIMARY KEY NOT NULL",
            "guild_id text NOT NULL",
            "channel_id text NOT NULL",
            "author_id text NOT NULL",
            "used TIMESTAMP WITH TIME ZONE",
            "user_msg text",
            "bot_msg text",
            "prompt text",
            "failed boolean",
            "filtered int NULL",
            "persona text DEFAULT 'friday'",
        ],
        "scheduledevents": [
            "id bigserial PRIMARY KEY NOT NULL",
            "guild_id bigint NOT NULL",
            "event_id bigint UNIQUE NOT NULL",
            "role_id bigint UNIQUE NOT NULL",
            "subscribers bigint[] NOT NULL DEFAULT array[]::bigint[]",
        ],
        "starboard": [
            "id bigserial PRIMARY KEY NOT NULL",
            "channel_id bigint",
            "threshold int NOT NULL DEFAULT 1",
            "locked boolean NOT NULL DEFAULT false",
        ],
        "starboard_entries": [
            "id bigserial PRIMARY KEY NOT NULL",
            "bot_message_id bigint",
            "message_id bigint UNIQUE NOT NULL",
            "channel_id bigint",
            "author_id bigint",
            "guild_id bigint NOT NULL REFERENCES starboard (id) ON DELETE CASCADE ON UPDATE NO ACTION",
        ],
        "starrers": [
            "id bigserial PRIMARY KEY NOT NULL",
            "author_id bigint NOT NULL",
            "entry_id bigint NOT NULL REFERENCES starboard_entries (id) ON DELETE CASCADE ON UPDATE NO ACTION",
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
    self.indexes = [
        "CREATE UNIQUE INDEX IF NOT EXISTS starrers_uniq_idx ON starrers (author_id, entry_id);",
    ]

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def cog_load(self):
    if self.bot.cluster_idx == 0:
      self.loop.create_task(self.create_tables())
      self.loop.create_task(self.sync_table_columns())

  @property
  def pool(self) -> asyncpg.Pool:
    return self.bot.pool

  async def create_tables(self):
    query = ""
    async with self.pool.acquire(timeout=300.0) as conn:
      for table in self.columns:
        query = query + f"CREATE TABLE IF NOT EXISTS {table} ({','.join(self.columns[table])});"
      for index in self.indexes:
        query = query + index
      await conn.execute(query)
      log.debug(f"PostgreSQL Query: {query}")

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
      log.debug(f"PostgreSQL Query: \"{query}\" + {params}")
    if "select" in query.lower():
      if isinstance(result, list) and len(result) == 1 and "limit 1" in query.lower():  # type: ignore
        result = [tuple(i) for i in result][0]
        if len(result) == 1:
          return result[0]
        return result  # type: ignore
      if isinstance(result, list) and len(result) > 0 and "limit 1" not in query.lower():  # type: ignore
        return [tuple(i) for i in result]
      elif isinstance(result, list) and len(result) == 0 and "limit 1" in query.lower():  # type: ignore
        return None
      return result  # type: ignore


async def setup(bot):
  await bot.add_cog(Database(bot))
