-- Revises: V3
-- Creation Date: 2023-03-27 02:47:46.467391 UTC
-- Reason: timezones
CREATE TABLE IF NOT EXISTS user_settings (
    id BIGINT PRIMARY KEY, -- The discord user ID
    timezone TEXT -- The user's timezone
);

ALTER TABLE reminders ADD COLUMN timezone TEXT NOT NULL DEFAULT 'UTC';