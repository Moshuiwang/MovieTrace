-- Migration 015: enforce unique cache_key in api_cache

-- 1. Dedupe existing rows: keep the row with max(id) for each cache_key
DELETE FROM api_cache
WHERE id NOT IN (
  SELECT MAX(id) FROM api_cache GROUP BY cache_key
);

-- 2. Create unique index
CREATE UNIQUE INDEX IF NOT EXISTS ux_api_cache_key ON api_cache(cache_key);

INSERT OR IGNORE INTO schema_migrations(version) VALUES (15);
