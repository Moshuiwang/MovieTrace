"""End-to-end upgrade + rebuild verification tests for current_discovery schema.

Covers:
- v18 DB upgrades to v19 (new tables exist, content_updates preserved)
- Migration idempotency (second run is a no-op)
- new_discovery data backfill populates current_discovery_items + discovery_observations
- export-recommendations does not crash with empty current_discovery_items
- ensure_table_fields dry_run returns the three new current-discovery fields
"""
import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# scripts/ has no __init__.py; load the backfill module via importlib
import importlib.util as _importlib_util

_backfill_spec = _importlib_util.spec_from_file_location(
    "p1_57_backfill_current_discovery",
    ROOT / "scripts" / "p1_57_backfill_current_discovery.py",
)
_backfill_mod = _importlib_util.module_from_spec(_backfill_spec)
_backfill_spec.loader.exec_module(_backfill_mod)
run_backfill = _backfill_mod.run_backfill

# Reuse the helper from test_migrate_cli that knows how to build a v18 DB
# by replaying migrations up to the requested version.
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
    """Build a DB at an older schema version by replaying migrations."""
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


def _table_names(db_path: Path) -> set[str]:
    from movietrace.db.schema import connect_database
    with connect_database(str(db_path)) as conn:
        return {
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type='table'"
            )
        }


def _max_version(db_path: Path) -> int:
    from movietrace.db.schema import connect_database
    with connect_database(str(db_path)) as conn:
        row = conn.execute("select max(version) from schema_migrations").fetchone()
        return row[0] if row and row[0] is not None else 0


def _seed_canonical_item(db_path: Path, *, tmdb_id: int, content_type: str = "tv") -> int:
    """Insert a minimal canonical_items row; returns its id."""
    from movietrace.db.schema import connect_database
    with connect_database(str(db_path)) as conn:
        cur = conn.execute(
            """
            insert into canonical_items
                (canonical_item_key, title, content_type, content_granularity)
            values (?, ?, ?, ?)
            """,
            (f"tmdb:{content_type}:{tmdb_id}", f"Test {content_type} {tmdb_id}", content_type, "series"),
        )
        canonical_id = cur.lastrowid
        conn.commit()
    return canonical_id


def _seed_new_discovery_row(
    db_path: Path,
    *,
    canonical_id: int,
    content_type: str,
    tmdb_id: int,
    obs_date: str,
    priority: str = "P1",
    hot_score: float = 75.0,
) -> None:
    """Insert a content_updates row with update_type='new_discovery'."""
    from movietrace.db.schema import connect_database
    cuid = f"discovery:{content_type}:{tmdb_id}:{obs_date}"
    with connect_database(str(db_path)) as conn:
        conn.execute(
            """
            insert or ignore into content_updates
                (content_update_id, canonical_item_id, update_type,
                 priority, hot_score)
            values (?, ?, 'new_discovery', ?, ?)
            """,
            (cuid, canonical_id, priority, hot_score),
        )
        conn.commit()


class UpgradeV18ToV19Test(unittest.TestCase):
    """v18 DB upgrades correctly to v19."""

    def test_v18_db_has_no_current_discovery_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "v18.db"
            _seed_db_at_version(db, 18)
            tables = _table_names(db)
            self.assertEqual(_max_version(db), 18)
            self.assertIn("feishu_sync_failures", tables)
            self.assertNotIn("current_discovery_items", tables)
            self.assertNotIn("discovery_observations", tables)

    def test_migrate_upgrades_v18_to_v19_new_tables_exist(self):
        from movietrace.cli import cmd_migrate
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "v18.db"
            _seed_db_at_version(db, 18)
            ns = argparse.Namespace(db=str(db))
            rc = cmd_migrate(ns)
            self.assertEqual(rc, 0)
            self.assertEqual(_max_version(db), 19)
            tables = _table_names(db)
            self.assertIn("current_discovery_items", tables)
            self.assertIn("discovery_observations", tables)

    def test_migrate_v18_preserves_content_updates(self):
        """content_updates row count must not change during migration."""
        from movietrace.db.schema import connect_database, initialize_database
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "v18_cu.db"
            _seed_db_at_version(db, 18)

            # Insert a canonical_items row, then a content_updates row
            canonical_id = _seed_canonical_item(db, tmdb_id=12345, content_type="tv")
            _seed_new_discovery_row(
                db, canonical_id=canonical_id,
                content_type="tv", tmdb_id=12345, obs_date="2026-05-01",
            )

            with connect_database(str(db)) as conn:
                before = conn.execute("select count(*) from content_updates").fetchone()[0]

            # Apply migration 019
            initialize_database(db)

            with connect_database(str(db)) as conn:
                after = conn.execute("select count(*) from content_updates").fetchone()[0]

            self.assertEqual(before, after, "content_updates count must not change after migration")
            self.assertGreater(after, 0)


class MigrationIdempotencyTest(unittest.TestCase):
    """Running migration twice is a no-op."""

    def test_migrate_idempotent_on_fresh_v19(self):
        from movietrace.cli import cmd_migrate
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "v19.db"
            ns = argparse.Namespace(db=str(db))
            rc1 = cmd_migrate(ns)
            rc2 = cmd_migrate(ns)
            self.assertEqual(rc1, 0)
            self.assertEqual(rc2, 0)
            self.assertEqual(_max_version(db), 19)

    def test_migrate_idempotent_from_v18(self):
        from movietrace.cli import cmd_migrate
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "v18_twice.db"
            _seed_db_at_version(db, 18)
            ns = argparse.Namespace(db=str(db))
            rc1 = cmd_migrate(ns)
            rc2 = cmd_migrate(ns)
            self.assertEqual(rc1, 0)
            self.assertEqual(rc2, 0)
            self.assertEqual(_max_version(db), 19)


class BackfillTest(unittest.TestCase):
    """Backfill script populates current_discovery_items and discovery_observations."""

    def _make_v19_db_with_new_discovery(self, db: Path) -> int:
        """Create a v19 DB with one canonical_items + two new_discovery rows for the same tmdb_id."""
        from movietrace.db.schema import initialize_database
        initialize_database(db)
        canonical_id = _seed_canonical_item(db, tmdb_id=99001, content_type="tv")
        _seed_new_discovery_row(
            db, canonical_id=canonical_id,
            content_type="tv", tmdb_id=99001, obs_date="2026-05-20", hot_score=80.0,
        )
        _seed_new_discovery_row(
            db, canonical_id=canonical_id,
            content_type="tv", tmdb_id=99001, obs_date="2026-05-21", hot_score=85.0,
        )
        return canonical_id

    def test_backfill_dry_run_does_not_write(self):
        """Dry-run must not insert any rows into current_discovery_items."""
        from movietrace.db.schema import connect_database
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "dry.db"
            self._make_v19_db_with_new_discovery(db)

            stats = run_backfill(db, commit=False)

            self.assertEqual(stats["errors"], 0)
            self.assertGreater(stats["current_items_created"], 0)
            # Nothing written to DB in dry-run
            with connect_database(str(db)) as conn:
                count = conn.execute("select count(*) from current_discovery_items").fetchone()[0]
            self.assertEqual(count, 0)

    def test_backfill_commit_creates_current_item_and_observations(self):
        """--commit must create exactly 1 current_discovery_item and 2 observations."""
        from movietrace.db.schema import connect_database
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "commit.db"
            self._make_v19_db_with_new_discovery(db)

            stats = run_backfill(db, commit=True)

            self.assertEqual(stats["errors"], 0)
            self.assertEqual(stats["current_items_created"], 1)
            self.assertEqual(stats["observations_written"], 2)

            with connect_database(str(db)) as conn:
                cdi = conn.execute("select count(*) from current_discovery_items").fetchone()[0]
                obs = conn.execute("select count(*) from discovery_observations").fetchone()[0]

            self.assertEqual(cdi, 1)
            self.assertEqual(obs, 2)

    def test_backfill_commit_does_not_change_content_updates_count(self):
        """content_updates count must be identical before and after --commit backfill."""
        from movietrace.db.schema import connect_database
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "no_change.db"
            self._make_v19_db_with_new_discovery(db)

            with connect_database(str(db)) as conn:
                before = conn.execute("select count(*) from content_updates").fetchone()[0]

            run_backfill(db, commit=True)

            with connect_database(str(db)) as conn:
                after = conn.execute("select count(*) from content_updates").fetchone()[0]

            self.assertEqual(before, after)

    def test_backfill_idempotent_on_second_run(self):
        """Running backfill twice must not duplicate rows."""
        from movietrace.db.schema import connect_database
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "idem.db"
            self._make_v19_db_with_new_discovery(db)

            run_backfill(db, commit=True)
            run_backfill(db, commit=True)

            with connect_database(str(db)) as conn:
                cdi = conn.execute("select count(*) from current_discovery_items").fetchone()[0]
                obs = conn.execute("select count(*) from discovery_observations").fetchone()[0]

            self.assertEqual(cdi, 1)
            self.assertEqual(obs, 2)

    def test_backfill_empty_db_no_crash(self):
        """Backfill on a DB with no new_discovery rows must return 0 items and no errors."""
        from movietrace.db.schema import initialize_database
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "empty.db"
            initialize_database(db)

            stats = run_backfill(db, commit=True)

            self.assertEqual(stats["errors"], 0)
            self.assertEqual(stats["rows_read"], 0)
            self.assertEqual(stats["current_items_created"], 0)


class ExportRecommendationsTest(unittest.TestCase):
    """export-recommendations must not crash with empty current_discovery_items."""

    def test_export_dry_run_empty_db_no_crash(self):
        """dry_run=True with an empty DB must return without raising."""
        from movietrace.db.schema import initialize_database
        from movietrace.reports.export_writer import export_recommendations
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "empty.db"
            initialize_database(db)
            result = export_recommendations(
                db_path=str(db),
                output_dir=str(Path(tmp) / "reports"),
                days=30,
                dry_run=True,
            )
            # dry_run=True must set dry_run key in result
            self.assertTrue(result.get("dry_run"))

    def test_export_dry_run_with_content_updates_no_crash(self):
        """export dry_run works even with existing content_updates rows."""
        from movietrace.db.schema import initialize_database
        from movietrace.reports.export_writer import export_recommendations
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "has_cu.db"
            initialize_database(db)
            canonical_id = _seed_canonical_item(db, tmdb_id=77001, content_type="movie")
            _seed_new_discovery_row(
                db, canonical_id=canonical_id,
                content_type="movie", tmdb_id=77001, obs_date="2026-05-20",
            )
            result = export_recommendations(
                db_path=str(db),
                output_dir=str(Path(tmp) / "reports"),
                days=30,
                dry_run=True,
            )
            self.assertTrue(result.get("dry_run"))


class FeishuEnsureFieldsDryRunTest(unittest.TestCase):
    """ensure_table_fields dry_run must include the three new current-discovery fields."""

    NEW_CURRENT_DISCOVERY_FIELDS = {"首次发现日期", "最近发现日期", "发现次数"}

    def _mock_feishu_no_existing_fields(self) -> mock.MagicMock:
        """Return a mock patch that simulates Feishu returning no existing fields."""
        return mock.patch(
            "movietrace.feishu.schema_setup.list_table_fields",
            return_value=[],
        )

    def _mock_token(self) -> mock.MagicMock:
        return mock.patch(
            "movietrace.feishu.schema_setup.fetch_tenant_access_token",
            return_value="mock_token_12345",
        )

    def test_dry_run_includes_three_new_fields_when_no_existing(self):
        """When the table has no existing fields, all REQUIRED_FIELDS are in 'created'."""
        from movietrace.feishu.schema_setup import ensure_table_fields, REQUIRED_FIELDS_FOR_DISCOVERY_TABLE

        with self._mock_token(), self._mock_feishu_no_existing_fields():
            result = ensure_table_fields(
                app_id="app_id",
                app_secret="app_secret",
                app_token="app_token",
                table_id="table_id",
                dry_run=True,
            )

        self.assertEqual(result["errors"], [])
        created_names = {f["field_name"] for f in result["created"]}
        for field_name in self.NEW_CURRENT_DISCOVERY_FIELDS:
            self.assertIn(
                field_name, created_names,
                f"Expected new field '{field_name}' in dry_run created list",
            )

    def test_dry_run_skips_existing_fields(self):
        """When the three new fields already exist, they appear in 'existed' not 'created'."""
        from movietrace.feishu.schema_setup import ensure_table_fields

        existing = [
            {"field_name": "首次发现日期", "field_id": "fld001", "type": 5},
            {"field_name": "最近发现日期", "field_id": "fld002", "type": 5},
            {"field_name": "发现次数", "field_id": "fld003", "type": 2},
        ]
        with self._mock_token(), mock.patch(
            "movietrace.feishu.schema_setup.list_table_fields",
            return_value=existing,
        ):
            result = ensure_table_fields(
                app_id="app_id",
                app_secret="app_secret",
                app_token="app_token",
                table_id="table_id",
                dry_run=True,
            )

        existed_names = {f["field_name"] for f in result["existed"]}
        created_names = {f["field_name"] for f in result["created"]}
        for field_name in self.NEW_CURRENT_DISCOVERY_FIELDS:
            self.assertIn(field_name, existed_names,
                          f"Expected '{field_name}' in existed when already present")
            self.assertNotIn(field_name, created_names,
                             f"Expected '{field_name}' NOT in created when already present")

    def test_dry_run_no_real_api_calls(self):
        """dry_run must never call the real create_table_field."""
        from movietrace.feishu.schema_setup import ensure_table_fields

        with self._mock_token(), self._mock_feishu_no_existing_fields(), mock.patch(
            "movietrace.feishu.schema_setup.create_table_field",
        ) as mock_create:
            ensure_table_fields(
                app_id="app_id",
                app_secret="app_secret",
                app_token="app_token",
                table_id="table_id",
                dry_run=True,
            )

        mock_create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
