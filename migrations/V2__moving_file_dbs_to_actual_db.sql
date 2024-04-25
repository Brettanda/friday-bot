-- Revises: V1
-- Creation Date: 2023-02-05 22:08:42.441343 UTC
-- Reason: moving file db's to actual db

ALTER TABLE servers ADD COLUMN IF NOT EXISTS lang text;