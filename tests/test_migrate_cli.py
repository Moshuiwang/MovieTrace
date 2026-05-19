"""Tests for `movietrace migrate` CLI (P1.31).

Covers:
- Fresh DB → applies all migrations through 017
- Pre-existing v15 DB (simulates 2026-05-19 prod state minus one) → upgraded to 017
- Idempotency: second run is a no-op with exit 0
- Failure path: initialize_database raising → exit 1 with stderr message
"""
import argparse
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


MIGRATION_FILES = {
    2: "002_flixpatrol_top10.sql",
    3: "003_candidates.sql",
    4: "004_candidate_matches.sql",
    5: "005_upstream_tables.sql",
    6: "006_virtual_series.sql",
    7: "007_multi_source_trending.sql",
    8: "008_api_usage_log.sql",
    9: "009_tmdb_structured_fields.sql",
    10: "010_multi_source_structured_fields.sql",
    11: "011_external_id_namespace.sql",
    12: "012_source_fetch_runs.sql",
    13: "013_tmdb_namespace_cleanup.sql",
    14: "014_content_updates_event_history.sql",
    15: "015_api_cache_unique_key.sql",
}


def _seed_db_at_version(db_path: Path, target_version: int) -> None:
    """Build a DB with SCHEMA_SQL baseline + migrations 2..target_version (inclusive)."""
    from movietrace.db.schema import (
        SCHEMA_SQL,
        _apply_migration,
        _load_migration_sql,
        connect_database,
    )
    with connect_database(str(db_path)) as conn:
        conn.executescript(SCHEMA_SQL)
        for version in range(2, target_version + 1):
            _apply_migration(conn, version, _load_migration_sql(MIGRATION_FILES[version]))
        conn.commit()


def _versions(db_path: Path) -> list[int]:
    from movietrace.db.schema import connect_database
    with connect_database(str(db_path)) as conn:
        return sorted(row[0] for row in conn.execute("select version from schema_migrations"))


def _canonical_items_sql(db_path: Path) -> str:
    from movietrace.db.schema import connect_database
    with connect_database(str(db_path)) as conn:
        return conn.execute(
            "select sql from sqlite_master where name='canonical_items'"
        ).fetchone()[0]


class MigrateCLITest(unittest.TestCase):
    def test_fresh_db_migrates_to_v17(self):
        from movietrace.cli import cmd_migrate
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "fresh.db"
            ns = argparse.Namespace(db=str(db))

            rc = cmd_migrate(ns)

            self.assertEqual(rc, 0)
            versions = _versions(db)
            self.assertEqual(max(versions), 17)
            sql = _canonical_items_sql(db)
            for col in ("title_zh", "overview_zh", "genres_json", "networks_json"):
                self.assertIn(col, sql, f"{col} missing after migrate")

    def test_v15_db_upgrades_to_v17(self):
        """Simulates the 2026-05-19 production scenario (modulo one version)."""
        from movietrace.cli import cmd_migrate
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "v15.db"
            _seed_db_at_version(db, 15)
            self.assertEqual(max(_versions(db)), 15)

            ns = argparse.Namespace(db=str(db))
            rc = cmd_migrate(ns)

            self.assertEqual(rc, 0)
            versions_after = _versions(db)
            self.assertEqual(max(versions_after), 17)
            self.assertIn(16, versions_after)
            self.assertIn(17, versions_after)

    def test_migrate_is_idempotent_on_v17(self):
        from movietrace.cli import cmd_migrate
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "v17.db"
            ns = argparse.Namespace(db=str(db))

            self.assertEqual(cmd_migrate(ns), 0)
            first = _versions(db)

            self.assertEqual(cmd_migrate(ns), 0)
            second = _versions(db)

            self.assertEqual(first, second)
            self.assertEqual(max(second), 17)

    def test_migrate_returns_1_on_failure(self):
        from movietrace import cli as cli_mod
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "broken.db"
            ns = argparse.Namespace(db=str(db))

            with mock.patch.object(cli_mod, "initialize_database",
                                   side_effect=RuntimeError("disk full")):
                buf = []
                real_stderr = sys.stderr
                try:
                    import io
                    sys.stderr = io.StringIO()
                    rc = cli_mod.cmd_migrate(ns)
                    err = sys.stderr.getvalue()
                finally:
                    sys.stderr = real_stderr

            self.assertEqual(rc, 1)
            self.assertIn("disk full", err)
            self.assertIn("migrate failed", err)


if __name__ == "__main__":
    unittest.main()
