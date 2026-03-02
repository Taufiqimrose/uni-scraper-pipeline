-- Migration 002: Add major_name and search_type to scrape_jobs
-- These fields exist in the Python model but were missing from the DB schema.

ALTER TABLE scrape_jobs ADD COLUMN IF NOT EXISTS major_name TEXT;
ALTER TABLE scrape_jobs ADD COLUMN IF NOT EXISTS search_type TEXT NOT NULL DEFAULT 'direct_url';
