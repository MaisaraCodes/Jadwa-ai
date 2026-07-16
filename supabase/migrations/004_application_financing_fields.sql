-- Migration 004: add financing detail columns to applications
-- Idempotent: safe to run multiple times (ADD COLUMN IF NOT EXISTS).
-- Run via: Supabase SQL editor, or
--   psql "$DATABASE_URL" -f supabase/migrations/004_application_financing_fields.sql

ALTER TABLE public.applications
  ADD COLUMN IF NOT EXISTS amount      numeric,
  ADD COLUMN IF NOT EXISTS purpose     text,
  ADD COLUMN IF NOT EXISTS term_months integer,
  ADD COLUMN IF NOT EXISTS description text;
