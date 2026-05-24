"""Tests for `movietrace migrate` CLI (P1.31).

Covers:
- Fresh DB → applies all migrations through 019
- Pre-existing v15 DB (simulates 2026-05-19 prod state minus one) → upgraded to 019
- Pre-existing v18 DB → upgraded to 019
- Idempotency: second run is a no-op with exit 0
- Failure path: initialize_database raising → exit 1 with stderr message
"""
import argparse
import sqlite3
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
    16: "016_drop_legacy_tables.sql",
    17: "017_canonical_zh_fields.sql",
    18: "018_feishu_sync_failures.sql",
}


def _seed_db_at_version(db_path: Path, target_version: int) -> None:
    """Build a DB at an older schema version by replaying migrations.

    Current SCHEMA_SQL is cumulative for fresh installs, so using it directly
    would pre-create newer additive tables and make upgrade tests false-positive.
    """
    from movietrace.db.schema import (
        SCHEMA_SQL,
        _apply_migration,
        _load_migration_sql,
        connect_database,
    )
    baseline_sql = SCHEMA_SQL.split("create table if not exists feishu_sync_failures")[0]
    with connect_database(str(db_path)) as conn:
        conn.executescript(baseline_sql)
        for version in range(2, target_version + 1):
            _apply_migration(conn, version, _load_migration_sql(MIGRATION_FILES[version]))
        conn.commit()


def _versions(db_path: Path) -> list[int]:
    from movietrace.db.schema import connect_database
    with connect_database(str(db_path)) as conn:
        return sorted(row[0] for row in conn.execute("select version from schema_migrations"))


def _table_sql(db_path: Path, table_name: str) -> str:
    from movietrace.db.schema import connect_database
    with connect_database(str(db_path)) as conn:
        return conn.execute(
            "select sql from sqlite_master where name=?", (table_name,)
        ).fetchone()[0]


def _table_names(db_path: Path) -> set[str]:
    from movietrace.db.schema import connect_database
    with connect_database(str(db_path)) as conn:
        return {
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type='table'"
            )
        }


def _index_names(db_path: Path) -> set[str]:
    from movietrace.db.schema import connect_database
    with connect_database(str(db_path)) as conn:
        return {
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type='index'"
            )
        }


def _assert_current_discovery_schema(testcase: unittest.TestCase, db_path: Path) -> None:
    tables = _table_names(db_path)
    testcase.assertIn("current_discovery_items", tables)
    testcase.assertIn("discovery_observations", tables)

    indexes = _index_names(db_path)
    for index_name in (
        "ux_current_discovery_items_key",
        "ux_current_discovery_items_type_tmdb",
        "ix_current_discovery_items_last_discovered_date",
        "ix_current_discovery_items_priority_score",
        "ux_discovery_observations_key_date",
        "ix_discovery_observations_observed_date",
    ):
        testcase.assertIn(index_name, indexes)

    from movietrace.db.schema import connect_database
    with connect_database(str(db_path)) as conn:
        conn.execute(
            """
            insert into current_discovery_items
                (discovery_key, content_type, tmdb_id,
                 first_discovered_date, last_discovered_date)
            values (?, ?, ?, ?, ?)
            """,
            ("discovery:tv:123", "tv", 123, "2026-05-24", "2026-05-24"),
        )
        conn.execute(
            """
            insert into discovery_observations
                (discovery_key, observed_date, hot_score, priority)
            values (?, ?, ?, ?)
            """,
            ("discovery:tv:123", "2026-05-24", 88.5, "P1"),
        )

        with testcase.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                """
                insert into discovery_observations
                    (discovery_key, observed_date, hot_score, priority)
                values (?, ?, ?, ?)
                """,
                ("discovery:tv:123", "2026-05-24", 90.0, "P0"),
            )

        with testcase.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                """
                insert into current_discovery_items
                    (discovery_key, content_type, tmdb_id,
                     first_discovered_date, last_discovered_date)
                values (?, ?, ?, ?, ?)
                """,
                (
                    "discovery:tv:123:2026-05-24",
                    "tv",
                    123,
                    "2026-05-24",
                    "2026-05-24",
                ),
            )


class MigrateCLITest(unittest.TestCase):
    def test_fresh_db_migrates_to_v19(self):
        from movietrace.cli import cmd_migrate
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "fresh.db"
            ns = argparse.Namespace(db=str(db))

            rc = cmd_migrate(ns)

            self.assertEqual(rc, 0)
            versions = _versions(db)
            self.assertEqual(max(versions), 19)
            sql = _table_sql(db, "canonical_items")
            for col in ("title_zh", "overview_zh", "genres_json", "networks_json"):
                self.assertIn(col, sql, f"{col} missing after migrate")
            self.assertIn("current_discovery_items", _table_names(db))
            self.assertIn("discovery_observations", _table_names(db))

    def test_v15_db_upgrades_to_v19(self):
        """Simulates the 2026-05-19 production scenario (modulo one version)."""
        from movietrace.cli import cmd_migrate
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "v15.db"
            _seed_db_at_version(db, 15)
            self.assertEqual(max(_versions(db)), 15)
            self.assertNotIn("feishu_sync_failures", _table_names(db))
            self.assertNotIn("current_discovery_items", _table_names(db))
            self.assertNotIn("discovery_observations", _table_names(db))

            ns = argparse.Namespace(db=str(db))
            rc = cmd_migrate(ns)

            self.assertEqual(rc, 0)
            versions_after = _versions(db)
            self.assertEqual(max(versions_after), 19)
            self.assertIn(16, versions_after)
            self.assertIn(17, versions_after)
            self.assertIn(18, versions_after)
            self.assertIn(19, versions_after)
            self.assertIn("current_discovery_items", _table_names(db))
            self.assertIn("discovery_observations", _table_names(db))

    def test_v18_db_upgrades_to_v19(self):
        from movietrace.cli import cmd_migrate
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "v18.db"
            _seed_db_at_version(db, 18)
            self.assertEqual(max(_versions(db)), 18)
            self.assertIn("feishu_sync_failures", _table_names(db))
            self.assertNotIn("current_discovery_items", _table_names(db))
            self.assertNotIn("discovery_observations", _table_names(db))

            ns = argparse.Namespace(db=str(db))
            rc = cmd_migrate(ns)

            self.assertEqual(rc, 0)
            versions_after = _versions(db)
            self.assertEqual(max(versions_after), 19)
            _assert_current_discovery_schema(self, db)

    def test_migration_019_sql_upgrades_v18_db(self):
        from movietrace.db.schema import (
            _apply_migration,
            _load_migration_sql,
            connect_database,
        )
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "v18_direct_019.db"
            _seed_db_at_version(db, 18)
            self.assertEqual(max(_versions(db)), 18)
            self.assertNotIn("current_discovery_items", _table_names(db))
            self.assertNotIn("discovery_observations", _table_names(db))

            with connect_database(str(db)) as conn:
                _apply_migration(
                    conn,
                    19,
                    _load_migration_sql("019_current_discovery_observations.sql"),
                )
                conn.commit()

            self.assertEqual(max(_versions(db)), 19)
            _assert_current_discovery_schema(self, db)

    def test_migrate_is_idempotent_on_v19(self):
        from movietrace.cli import cmd_migrate
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "v19.db"
            ns = argparse.Namespace(db=str(db))

            self.assertEqual(cmd_migrate(ns), 0)
            first = _versions(db)

            self.assertEqual(cmd_migrate(ns), 0)
            second = _versions(db)

            self.assertEqual(first, second)
            self.assertEqual(max(second), 19)

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
