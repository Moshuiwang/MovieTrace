-- Migration 014: Replace (canonical_item_id, update_type) unique constraint
-- with content_update_id event-level uniqueness.
-- ADR-0012: content_updates is now an event history table, not a global dedup pool.
-- Safety: if duplicate content_update_id values exist, the CREATE UNIQUE INDEX
-- below will fail with a UNIQUE constraint error — manual cleanup is then required.

-- 1. Drop the old global-dedup index
DROP INDEX IF EXISTS ux_content_updates_item_type;

-- 2. Namespace legacy discovery event ids by TMDb media type before the unique
-- index is created. Old ids looked like discovery:{tmdb_id}:{snapshot_date};
-- movie and tv share TMDb's numeric id space, so the event id must include the
-- media namespace to avoid collisions.
UPDATE content_updates
SET content_update_id =
    'discovery:' ||
    CASE
        WHEN ci.content_type IN ('tv', 'show') THEN 'tv'
        ELSE 'movie'
    END ||
    substr(content_update_id, length('discovery') + 1)
FROM canonical_items ci
WHERE content_updates.canonical_item_id = ci.id
  AND content_updates.update_type = 'new_discovery'
  AND content_updates.content_update_id GLOB 'discovery:[0-9]*:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]';

-- 3. Create the new event-level unique index
CREATE UNIQUE INDEX IF NOT EXISTS ux_content_updates_update_id
ON content_updates(content_update_id);
