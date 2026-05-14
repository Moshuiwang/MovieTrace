-- Migration 013: Normalize any bare TMDb external_ids to prefixed format.
-- P1.9-hotfix-E (migration 011) added tv:/movie: prefixes, but match_upstream_program()
-- continued to write bare IDs post-011. This migration catches any remaining bare IDs.
-- Data-only: no schema changes. Idempotent: re-running is a no-op.

-- Remove bare IDs that would collide with an already-prefixed TV ID.
DELETE FROM external_ids
WHERE source = 'tmdb'
  AND external_id NOT LIKE 'tv:%'
  AND external_id NOT LIKE 'movie:%'
  AND external_id NOT LIKE 'unknown:%'
  AND canonical_item_id IN (
      SELECT id FROM canonical_items WHERE content_type = 'tv'
  )
  AND EXISTS (
      SELECT 1 FROM external_ids existing
      WHERE existing.source = 'tmdb'
        AND existing.external_id = 'tv:' || external_ids.external_id
  );

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

-- Remove bare IDs that would collide with an already-prefixed movie ID.
DELETE FROM external_ids
WHERE source = 'tmdb'
  AND external_id NOT LIKE 'tv:%'
  AND external_id NOT LIKE 'movie:%'
  AND external_id NOT LIKE 'unknown:%'
  AND canonical_item_id IN (
      SELECT id FROM canonical_items WHERE content_type = 'movie'
  )
  AND EXISTS (
      SELECT 1 FROM external_ids existing
      WHERE existing.source = 'tmdb'
        AND existing.external_id = 'movie:' || external_ids.external_id
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

-- Remove remaining bare IDs that would collide with an already-prefixed unknown ID.
DELETE FROM external_ids
WHERE source = 'tmdb'
  AND external_id NOT LIKE 'tv:%'
  AND external_id NOT LIKE 'movie:%'
  AND external_id NOT LIKE 'unknown:%'
  AND EXISTS (
      SELECT 1 FROM external_ids existing
      WHERE existing.source = 'tmdb'
        AND existing.external_id = 'unknown:' || external_ids.external_id
  );

-- Any remaining bare IDs (no canonical_item or unknown content_type) → "unknown:"
UPDATE external_ids
SET external_id = 'unknown:' || external_id
WHERE source = 'tmdb'
  AND external_id NOT LIKE 'tv:%'
  AND external_id NOT LIKE 'movie:%'
  AND external_id NOT LIKE 'unknown:%';
