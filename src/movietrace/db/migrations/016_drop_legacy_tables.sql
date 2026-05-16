-- Migration 016: drop ADR-0007 pre-flip legacy tables
-- Audit (2026-05-16): source_records/feishu_import_runs/baseline_items/candidates/
-- candidate_matches/match_candidates have no active CLI write path; drop all.
-- baseline_quality_issues kept (entity_matching.py writes, standalone, no FK deps).

DROP TABLE IF EXISTS match_candidates;
DROP TABLE IF EXISTS candidate_matches;
DROP TABLE IF EXISTS candidates;
DROP TABLE IF EXISTS baseline_items;
DROP TABLE IF EXISTS source_records;
DROP TABLE IF EXISTS feishu_import_runs;

INSERT OR IGNORE INTO schema_migrations(version) VALUES (16);
