-- Revises: V5
-- Creation Date: 2023-04-05 00:45:54.291109 UTC
-- Reason: multiple personas and chat channels


CREATE TABLE IF NOT EXISTS chatchannels (
  id TEXT PRIMARY KEY,
  guild_id TEXT NOT NULL,
  webhook_url TEXT,
  persona TEXT NOT NULL DEFAULT 'default',
  persona_custom VARCHAR(100),
  FOREIGN KEY (guild_id) REFERENCES servers(id)
);


ALTER TABLE servers ADD COLUMN IF NOT EXISTS chatchannel TEXT NULL DEFAULT NULL;
ALTER TABLE servers ADD COLUMN IF NOT EXISTS chatchannel_webhook TEXT NULL DEFAULT NULL;
ALTER TABLE servers ADD COLUMN IF NOT EXISTS persona TEXT NOT NULL DEFAULT 'default';
ALTER TABLE servers ADD COLUMN IF NOT EXISTS persona_custom TEXT NULL DEFAULT NULL;

INSERT INTO chatchannels (id, guild_id, webhook_url, persona) 
  SELECT chatchannel, id, chatchannel_webhook, persona
  FROM servers
  WHERE chatchannel IS NOT NULL
  ON CONFLICT DO NOTHING;

ALTER TABLE servers DROP COLUMN IF EXISTS chatchannel;
ALTER TABLE servers DROP COLUMN IF EXISTS chatchannel_webhook;
ALTER TABLE servers DROP COLUMN IF EXISTS persona;
ALTER TABLE servers DROP COLUMN IF EXISTS persona_custom;
