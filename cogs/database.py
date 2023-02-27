from __future__ import annotations

import logging
from typing import TYPE_CHECKING

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
            "prefix varchar(5) NOT NULL DEFAULT '!'",
            "max_mentions jsonb NULL DEFAULT NULL",
            "max_messages jsonb NULL DEFAULT NULL",
            "max_content jsonb NULL DEFAULT NULL",
            "remove_invites boolean DEFAULT false",
            "bot_manager text DEFAULT NULL",
            "persona text DEFAULT 'default'",
            # "default_event_role_id bigint DEFAULT NULL",
            "customjoinleave text NULL",
            "chatchannel text NULL DEFAULT NULL",
            "chatchannel_webhook text NULL",
            "chatstoprepeating boolean DEFAULT true",
            "botchannel text NULL DEFAULT NULL",
            "musicchannel text NULL DEFAULT NULL",
            "disabled_commands text[] DEFAULT array[]::text[]",
            "restricted_commands text[] DEFAULT array[]::text[]",
            "mute_role text NULL DEFAULT NULL",
            "mod_roles text[] NOT NULL DEFAULT array[]::text[]",
            "report_channel text NULL DEFAULT NULL",
            "automod_whitelist text[] DEFAULT array[]::text[]",
            "mod_log_channel text NULL DEFAULT NULL",
            "mod_log_events text[] DEFAULT array['bans', 'mutes', 'unbans', 'unmutes', 'kicks', 'timeouts']::text[]",
            r"muted_members text[] DEFAULT array[]::text[]",
            "raid_mode smallint NOT NULL DEFAULT 0",
            "raid_mode_reason text NOT NULL DEFAULT 'Raid Mode enabled'",
            "raid_mode_auto smallint[] DEFAULT NULL",
            r"customsounds jsonb[] NOT NULL DEFAULT array[]::jsonb[]",
            "tags jsonb[] DEFAULT array[]::jsonb[]",
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
        "logs": [
            "id bigserial PRIMARY KEY NOT NULL",
            "id_specific bigint NOT NULL DEFAULT 0",
            "guild_id text NOT NULL",
            "channel_id text NOT NULL",
            "message_id text NOT NULL",
            "target text NOT NULL",
            "moderator text NOT NULL",
            "action text NOT NULL",
            "reason text NOT NULL",
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
        "embeds": [
            "id bigserial PRIMARY KEY NOT NULL",
            "name text NOT NULL",
            "guild_id bigint NOT NULL",
            "channel_id bigint NOT NULL",
            "message_id bigint NOT NULL",
            "embed jsonb NOT NULL",
        ],
        "plonks": [
            "id bigserial PRIMARY KEY NOT NULL",
            "guild_id bigint NOT NULL",
            "entity_id bigint UNIQUE NOT NULL",
        ],
        "command_config": [
            "id bigserial PRIMARY KEY NOT NULL",
            "guild_id bigint NOT NULL",
            "channel_id bigint NOT NULL",
            "name text",
            "ignore boolean",
            "whitelist boolean",
            "restrict boolean",
            "modonly boolean"
        ],
        "countdowns": [
            "guild text NULL",
            "channel text NOT NULL",
            "message text PRIMARY KEY NOT NULL",
            "title text NULL",
            "time bigint NOT NULL"
        ],
        "tags": [
            "id bigserial PRIMARY KEY NOT NULL",
            "name text",
            "content text",
            "owner_id bigint",
            "uses int NOT NULL DEFAULT 0",
            "location_id bigint",
            "created timestamp DEFAULT (now() at time zone 'utc')",
        ],
        "tag_lookup": [
            "id bigserial PRIMARY KEY NOT NULL",
            "name text",
            "location_id bigint",
            "owner_id bigint",
            "created_at timestamp DEFAULT (now() at time zone 'utc')",
            "tag_id bigint NOT NULL REFERENCES tags (id) ON DELETE CASCADE ON UPDATE NO ACTION",
        ],
        "welcome": [
            "guild_id text PRIMARY KEY NOT NULL",
            "role_id text DEFAULT NULL",
            "channel_id text DEFAULT NULL",
            "message text DEFAULT NULL",
            "image_background_url text DEFAULT NULL",
            "image_background_dimensions text DEFAULT NULL",
        ],
        "blacklist": [
            "guild_id text PRIMARY KEY NOT NULL",
            "punishments text[] DEFAULT array['delete']::text[]",
            "dmuser bool DEFAULT true",
            "words text[]"
        ],
    }
    self.indexes = [
        "CREATE UNIQUE INDEX IF NOT EXISTS command_config_uniq_idx ON command_config (channel_id, name, whitelist);",
        "CREATE UNIQUE INDEX IF NOT EXISTS starrers_uniq_idx ON starrers (author_id, entry_id);",
        # Extension 'cogs.database' raised an error: UndefinedObjectError: operator class "gin_trgm_ops" does not exist for access method "gin"
        # "CREATE INDEX IF NOT EXISTS tags_name_trgm_idx ON tags USING GIN (name gin_trgm_ops);",
        # "CREATE INDEX IF NOT EXISTS tag_lookup_name_trgm_idx ON tag_lookup USING GIN (name gin_trgm_ops);",

        "CREATE INDEX IF NOT EXISTS tags_name_lower_idx ON tags (LOWER(name));",
        "CREATE UNIQUE INDEX IF NOT EXISTS tags_uniq_idx ON tags (LOWER(name), location_id);",
        "CREATE INDEX IF NOT EXISTS tag_lookup_name_lower_idx ON tag_lookup (LOWER(name));",
        "CREATE UNIQUE INDEX IF NOT EXISTS tag_lookup_uniq_idx ON tag_lookup (LOWER(name), location_id);",
        "CREATE UNIQUE INDEX IF NOT EXISTS scheduledevents_event_id_role_id ON scheduledevents (event_id, role_id);",
    ]

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"


async def setup(bot):
    ...
#   await bot.add_cog(Database(bot))
