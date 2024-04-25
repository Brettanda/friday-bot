-- Revises: V0
-- Creation Date: 2022-09-03 22:44:25.049320 UTC
-- Reason: Initial migration
CREATE TABLE IF NOT EXISTS servers (
  id text PRIMARY KEY NOT NULL,
  prefix varchar(5) NOT NULL DEFAULT '!',
  max_mentions jsonb NULL DEFAULT NULL,
  max_messages jsonb NULL DEFAULT NULL,
  max_content jsonb NULL DEFAULT NULL,
  remove_invites boolean DEFAULT false,
  bot_manager text DEFAULT NULL,
  persona text DEFAULT 'default',
  customjoinleave text NULL,
  chatchannel text NULL DEFAULT NULL,
  chatchannel_webhook text NULL,
  chatstoprepeating boolean DEFAULT true,
  botchannel text NULL DEFAULT NULL,
  disabled_commands text [] DEFAULT array []::text [],
  restricted_commands text [] DEFAULT array []::text [],
  mute_role text NULL DEFAULT NULL,
  mod_roles text [] NOT NULL DEFAULT array []::text [],
  automod_whitelist text [] DEFAULT array []::text [],
  mod_log_channel text NULL DEFAULT NULL,
  mod_log_events text [] DEFAULT array ['bans', 'mutes', 'unbans', 'unmutes', 'kicks', 'timeouts']::text [],
  muted_members text [] DEFAULT array []::text [],
  customsounds jsonb [] NOT NULL DEFAULT array []::jsonb [],
  reddit_extract boolean DEFAULT false
);
CREATE TABLE IF NOT EXISTS joined (
  time TIMESTAMP WITH TIME ZONE,
  guild_id text,
  joined boolean DEFAULT NULL,
  current_count bigint DEFAULT NULL
);
CREATE TABLE IF NOT EXISTS voting_streaks (
  user_id bigint PRIMARY KEY NOT NULL,
  created timestamp NOT NULL DEFAULT (now() at time zone 'utc'),
  last_vote timestamp NOT NULL DEFAULT (now() at time zone 'utc'),
  days bigint NOT NULL DEFAULT 1,
  expires timestamp NOT NULL
);
CREATE TABLE IF NOT EXISTS reminders (
  id bigserial PRIMARY KEY NOT NULL,
  expires timestamp NOT NULL,
  created timestamp NOT NULL DEFAULT (now() at time zone 'utc'),
  event text,
  extra jsonb DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS reminders_expires_idx ON reminders (expires);
CREATE TABLE IF NOT EXISTS patrons (
  user_id text PRIMARY KEY NOT NULL,
  tier smallint NOT NULL DEFAULT 0,
  guild_ids text [] NOT NULL DEFAULT array []::text []
);
CREATE TABLE IF NOT EXISTS commands (
  id bigserial PRIMARY KEY NOT NULL,
  guild_id text NOT NULL,
  channel_id text NOT NULL,
  author_id text NOT NULL,
  used TIMESTAMP WITH TIME ZONE,
  prefix text,
  command text,
  failed boolean
);
CREATE INDEX IF NOT EXISTS commands_guild_id_idx ON commands (guild_id);
CREATE INDEX IF NOT EXISTS commands_author_id_idx ON commands (author_id);
CREATE INDEX IF NOT EXISTS commands_used_idx ON commands (used);
CREATE INDEX IF NOT EXISTS commands_command_idx ON commands (command);
CREATE INDEX IF NOT EXISTS commands_failed_idx ON commands (failed);
CREATE TABLE IF NOT EXISTS chats (
  id bigserial PRIMARY KEY NOT NULL,
  guild_id text NOT NULL,
  channel_id text NOT NULL,
  author_id text NOT NULL,
  used TIMESTAMP WITH TIME ZONE,
  user_msg text,
  bot_msg text,
  prompt text,
  failed boolean,
  filtered int NULL,
  persona text DEFAULT 'friday'
);
CREATE INDEX IF NOT EXISTS chats_guild_id_idx ON chats (guild_id);
CREATE INDEX IF NOT EXISTS chats_author_id_idx ON chats (author_id);
CREATE INDEX IF NOT EXISTS chats_used_idx ON chats (used);
CREATE INDEX IF NOT EXISTS chats_failed_idx ON chats (failed);
CREATE TABLE IF NOT EXISTS scheduledevents (
  id bigserial PRIMARY KEY NOT NULL,
  guild_id bigint NOT NULL,
  event_id bigint UNIQUE NOT NULL,
  role_id bigint UNIQUE NOT NULL,
  subscribers bigint [] NOT NULL DEFAULT array []::bigint []
);
CREATE UNIQUE INDEX IF NOT EXISTS scheduledevents_event_id_role_id ON scheduledevents (event_id, role_id);
CREATE TABLE IF NOT EXISTS starboard (
  id bigserial PRIMARY KEY NOT NULL,
  channel_id bigint,
  threshold int NOT NULL DEFAULT 1,
  locked boolean NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS starboard_entries (
  id bigserial PRIMARY KEY NOT NULL,
  bot_message_id bigint,
  message_id bigint UNIQUE NOT NULL,
  channel_id bigint,
  author_id bigint,
  guild_id bigint NOT NULL REFERENCES starboard (id) ON DELETE CASCADE ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS starboard_entries_bot_message_id_idx ON starboard_entries (bot_message_id);
CREATE INDEX IF NOT EXISTS starboard_entries_message_id_idx ON starboard_entries (message_id);
CREATE INDEX IF NOT EXISTS starboard_entries_guild_id_idx ON starboard_entries (guild_id);
CREATE TABLE IF NOT EXISTS starrers (
  id bigserial PRIMARY KEY NOT NULL,
  author_id bigint NOT NULL,
  entry_id bigint NOT NULL REFERENCES starboard_entries (id) ON DELETE CASCADE ON UPDATE NO ACTION
);
CREATE INDEX IF NOT EXISTS starrers_entry_id_idx ON starrers (entry_id);
CREATE UNIQUE INDEX IF NOT EXISTS starrers_uniq_idx ON starrers (author_id, entry_id);
CREATE TABLE IF NOT EXISTS countdowns (
  guild text NULL,
  channel text NOT NULL,
  message text PRIMARY KEY NOT NULL,
  title text NULL,
  time bigint NOT NULL
);
CREATE TABLE IF NOT EXISTS welcome (
  guild_id text PRIMARY KEY NOT NULL,
  role_id text DEFAULT NULL,
  channel_id text DEFAULT NULL,
  message text DEFAULT NULL
);
CREATE TABLE IF NOT EXISTS blacklist (
  guild_id text PRIMARY KEY NOT NULL,
  punishments text [] DEFAULT array ['delete']::text [],
  dmuser bool DEFAULT true,
  words text []
);