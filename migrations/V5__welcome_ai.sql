-- Revises: V4
-- Creation Date: 2023-03-28 05:34:33.464061 UTC
-- Reason: welcome ai

ALTER TABLE welcome ADD COLUMN IF NOT EXISTS ai BOOLEAN DEFAULT FALSE;