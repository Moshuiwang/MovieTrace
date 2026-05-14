-- Migration 014: Replace (canonical_item_id, update_type) unique constraint
-- with content_update_id event-level uniqueness.
-- ADR-0012: content_updates is now an event history table, not a global dedup pool.
-- Safety: if duplicate content_update_id values exist, the CREATE UNIQUE INDEX
-- below will fail with a UNIQUE constraint error — manual cleanup is then required.

-- 1. Drop the old global-dedup index
DROP INDEX IF EXISTS ux_content_updates_item_type;

-- 2. Create the new event-level unique index
CREATE UNIQUE INDEX IF NOT EXISTS ux_content_updates_update_id
ON content_updates(content_update_id);
