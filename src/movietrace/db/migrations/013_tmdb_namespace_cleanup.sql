-- Migration 013: Normalize any bare TMDb external_ids to prefixed format.
-- P1.9-hotfix-E (migration 011) added tv:/movie: prefixes, but match_upstream_program()
-- continued to write bare IDs post-011. This migration catches any remaining bare IDs.
-- Data-only: no schema changes. Idempotent: re-running is a no-op.

-- TV items: prefix bare IDs with "tv:"
UPDATE external_ids
SET external_id = 'tv:' || external_id
WHERE source = 'tmdb'
  AND external_id NOT LIKE 'tv:%'
  AND external_id NOT LIKE 'movie:%'
  AND external_id NOT LIKE 'unknown:%'
  AND canonical_item_id IN (
      SELECT id FROM canonical_items WHERE content_type = 'tv'
  );

-- Movie items: prefix bare IDs with "movie:"
UPDATE external_ids
SET external_id = 'movie:' || external_id
WHERE source = 'tmdb'
  AND external_id NOT LIKE 'tv:%'
  AND external_id NOT LIKE 'movie:%'
  AND external_id NOT LIKE 'unknown:%'
  AND canonical_item_id IN (
      SELECT id FROM canonical_items WHERE content_type = 'movie'
  );

-- Any remaining bare IDs (no canonical_item or unknown content_type) → "unknown:"
UPDATE external_ids
SET external_id = 'unknown:' || external_id
WHERE source = 'tmdb'
  AND external_id NOT LIKE 'tv:%'
  AND external_id NOT LIKE 'movie:%'
  AND external_id NOT LIKE 'unknown:%';
