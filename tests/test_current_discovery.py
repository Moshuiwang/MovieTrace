"""P1.57b: Tests for current discovery / observation helpers."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def _make_db():
    from movietrace.db.schema import initialize_database, connect_database
    d = tempfile.mkdtemp()
    db_path = Path(d) / "test_cd.db"
    initialize_database(db_path)
    return connect_database(db_path), d


class TestBuildDiscoveryKey(unittest.TestCase):
    def test_valid_movie_key(self):
        from movietrace.pipeline.current_discovery import build_discovery_key
        self.assertEqual(build_discovery_key("movie", 12345), "discovery:movie:12345")

    def test_valid_tv_key(self):
        from movietrace.pipeline.current_discovery import build_discovery_key
        self.assertEqual(build_discovery_key("tv", 67890), "discovery:tv:67890")

    def test_invalid_content_type_raises(self):
        from movietrace.pipeline.current_discovery import build_discovery_key
        with self.assertRaises(ValueError):
            build_discovery_key("show", 123)

    def test_missing_tmdb_id_raises(self):
        from movietrace.pipeline.current_discovery import build_discovery_key
        with self.assertRaises(ValueError):
            build_discovery_key("tv", 0)

    def test_none_tmdb_id_raises(self):
        from movietrace.pipeline.current_discovery import build_discovery_key
        with self.assertRaises(ValueError):
            build_discovery_key("movie", None)


class TestUpsertCurrentDiscoveryItem(unittest.TestCase):
    def setUp(self):
        self.conn, self._tmpdir = _make_db()

    def tearDown(self):
        self.conn.close()
        import shutil
        shutil.rmtree(self._tmpdir)

    def _upsert(self, key, content_type, tmdb_id, date, **kwargs):
        from movietrace.pipeline.current_discovery import upsert_current_discovery_item
        upsert_current_discovery_item(
            self.conn,
            discovery_key=key,
            content_type=content_type,
            tmdb_id=tmdb_id,
            observed_date=date,
            **kwargs,
        )
        self.conn.commit()

    def _get(self, key):
        from movietrace.pipeline.current_discovery import get_current_discovery_item
        return get_current_discovery_item(self.conn, key)

    def test_first_upsert_creates_item_with_count_1(self):
        self._upsert("discovery:movie:100", "movie", 100, "2024-01-01", hot_score=70.0, priority="P1")
        item = self._get("discovery:movie:100")
        self.assertIsNotNone(item)
        self.assertEqual(item["discovery_count"], 1)
        self.assertEqual(item["first_discovered_date"], "2024-01-01")
        self.assertEqual(item["last_discovered_date"], "2024-01-01")

    def test_next_day_upsert_increments_count(self):
        self._upsert("discovery:tv:200", "tv", 200, "2024-01-01", hot_score=60.0, priority="P2")
        self._upsert("discovery:tv:200", "tv", 200, "2024-01-02", hot_score=65.0, priority="P2")
        item = self._get("discovery:tv:200")
        self.assertEqual(item["discovery_count"], 2)
        self.assertEqual(item["first_discovered_date"], "2024-01-01")
        self.assertEqual(item["last_discovered_date"], "2024-01-02")

    def test_same_day_repeat_does_not_increment_count(self):
        self._upsert("discovery:movie:300", "movie", 300, "2024-01-01", hot_score=55.0)
        self._upsert("discovery:movie:300", "movie", 300, "2024-01-01", hot_score=57.0)
        item = self._get("discovery:movie:300")
        self.assertEqual(item["discovery_count"], 1)
        self.assertEqual(item["latest_hot_score"], 57.0)

    def test_scores_updated_on_same_day_repeat(self):
        self._upsert("discovery:tv:400", "tv", 400, "2024-03-01", hot_score=50.0, priority="P2")
        self._upsert("discovery:tv:400", "tv", 400, "2024-03-01", hot_score=80.0, priority="P0")
        item = self._get("discovery:tv:400")
        self.assertEqual(item["latest_hot_score"], 80.0)
        self.assertEqual(item["latest_priority"], "P0")

    def test_invalid_content_type_raises(self):
        from movietrace.pipeline.current_discovery import upsert_current_discovery_item
        with self.assertRaises(ValueError):
            upsert_current_discovery_item(
                self.conn,
                discovery_key="discovery:show:100",
                content_type="show",
                tmdb_id=100,
                observed_date="2024-01-01",
            )

    def test_missing_tmdb_id_raises(self):
        from movietrace.pipeline.current_discovery import upsert_current_discovery_item
        with self.assertRaises(ValueError):
            upsert_current_discovery_item(
                self.conn,
                discovery_key="discovery:movie:0",
                content_type="movie",
                tmdb_id=0,
                observed_date="2024-01-01",
            )

    def test_source_summary_stored_as_json(self):
        summary = {"fp": {"ranking": 3}, "tmdb": {"popularity": 120.5}}
        self._upsert(
            "discovery:movie:500", "movie", 500, "2024-02-01",
            source_summary=summary,
        )
        item = self._get("discovery:movie:500")
        import json
        stored = json.loads(item["latest_source_summary_json"])
        self.assertEqual(stored["fp"]["ranking"], 3)

    def test_title_fields_stored(self):
        self._upsert(
            "discovery:tv:600", "tv", 600, "2024-02-01",
            title="Test Show", original_title="Test Show Original", title_zh="测试剧",
        )
        item = self._get("discovery:tv:600")
        self.assertEqual(item["title"], "Test Show")
        self.assertEqual(item["title_zh"], "测试剧")


class TestUpsertDiscoveryObservation(unittest.TestCase):
    def setUp(self):
        self.conn, self._tmpdir = _make_db()
        # Seed a current item first (observations require FK)
        from movietrace.pipeline.current_discovery import upsert_current_discovery_item
        upsert_current_discovery_item(
            self.conn,
            discovery_key="discovery:tv:777",
            content_type="tv",
            tmdb_id=777,
            observed_date="2024-01-01",
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        import shutil
        shutil.rmtree(self._tmpdir)

    def _obs(self, key, date, **kwargs):
        from movietrace.pipeline.current_discovery import upsert_discovery_observation
        upsert_discovery_observation(self.conn, discovery_key=key, observed_date=date, **kwargs)
        self.conn.commit()

    def test_insert_observation(self):
        self._obs("discovery:tv:777", "2024-01-01", hot_score=70.0, priority="P1")
        row = self.conn.execute(
            "SELECT hot_score, priority FROM discovery_observations WHERE discovery_key=? AND observed_date=?",
            ("discovery:tv:777", "2024-01-01"),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row[0], 70.0)
        self.assertEqual(row[1], "P1")

    def test_same_day_idempotent_upsert(self):
        self._obs("discovery:tv:777", "2024-01-01", hot_score=60.0)
        self._obs("discovery:tv:777", "2024-01-01", hot_score=75.0)
        count = self.conn.execute(
            "SELECT count(*) FROM discovery_observations WHERE discovery_key='discovery:tv:777'",
        ).fetchone()[0]
        self.assertEqual(count, 1)
        score = self.conn.execute(
            "SELECT hot_score FROM discovery_observations WHERE discovery_key='discovery:tv:777'",
        ).fetchone()[0]
        self.assertAlmostEqual(score, 75.0)

    def test_different_days_create_separate_rows(self):
        # Need to upsert current item for day 2 first
        from movietrace.pipeline.current_discovery import upsert_current_discovery_item
        upsert_current_discovery_item(
            self.conn,
            discovery_key="discovery:tv:777",
            content_type="tv",
            tmdb_id=777,
            observed_date="2024-01-02",
        )
        self.conn.commit()
        self._obs("discovery:tv:777", "2024-01-01", hot_score=60.0)
        self._obs("discovery:tv:777", "2024-01-02", hot_score=70.0)
        count = self.conn.execute(
            "SELECT count(*) FROM discovery_observations WHERE discovery_key='discovery:tv:777'",
        ).fetchone()[0]
        self.assertEqual(count, 2)

    def test_json_fields_stored(self):
        breakdown = {"flixpatrol_score": 30.0, "tmdb_popularity_score": 20.0}
        self._obs("discovery:tv:777", "2024-01-01", score_breakdown=breakdown)
        row = self.conn.execute(
            "SELECT score_breakdown_json FROM discovery_observations WHERE discovery_key='discovery:tv:777'",
        ).fetchone()
        import json
        stored = json.loads(row[0])
        self.assertAlmostEqual(stored["flixpatrol_score"], 30.0)


class TestGetCurrentDiscoveryItem(unittest.TestCase):
    def setUp(self):
        self.conn, self._tmpdir = _make_db()

    def tearDown(self):
        self.conn.close()
        import shutil
        shutil.rmtree(self._tmpdir)

    def test_returns_none_for_missing_key(self):
        from movietrace.pipeline.current_discovery import get_current_discovery_item
        result = get_current_discovery_item(self.conn, "discovery:movie:999")
        self.assertIsNone(result)

    def test_returns_dict_for_existing_key(self):
        from movietrace.pipeline.current_discovery import (
            upsert_current_discovery_item,
            get_current_discovery_item,
        )
        upsert_current_discovery_item(
            self.conn,
            discovery_key="discovery:movie:888",
            content_type="movie",
            tmdb_id=888,
            observed_date="2024-05-01",
            hot_score=85.0,
        )
        self.conn.commit()
        item = get_current_discovery_item(self.conn, "discovery:movie:888")
        self.assertIsInstance(item, dict)
        self.assertEqual(item["discovery_key"], "discovery:movie:888")
        self.assertAlmostEqual(item["latest_hot_score"], 85.0)


class TestGetStableMetadata(unittest.TestCase):
    """B2: get_stable_metadata helper unit tests."""

    def setUp(self):
        self.conn, self._tmpdir = _make_db()

    def tearDown(self):
        self.conn.close()
        import shutil
        shutil.rmtree(self._tmpdir)

    def _insert_item_with_stable_meta(self, key: str, stable_meta_json: str | None):
        # parse content_type / tmdb_id from key to satisfy schema CHECK constraint
        parts = key.split(":")
        content_type = parts[1]
        tmdb_id = int(parts[2])
        self.conn.execute(
            """INSERT INTO current_discovery_items
               (discovery_key, content_type, tmdb_id,
                first_discovered_date, last_discovered_date, stable_metadata_json)
               VALUES (?, ?, ?, '2024-01-01', '2024-01-01', ?)""",
            (key, content_type, tmdb_id, stable_meta_json),
        )
        self.conn.commit()

    def test_returns_dict_when_stable_meta_present(self):
        import json
        from movietrace.pipeline.current_discovery import get_stable_metadata
        meta = {"original_language": "en", "last_air_date": "2024-06-01"}
        self._insert_item_with_stable_meta("discovery:tv:5001", json.dumps(meta))
        result = get_stable_metadata(self.conn, "discovery:tv:5001")
        self.assertIsNotNone(result)
        self.assertEqual(result["original_language"], "en")
        self.assertEqual(result["last_air_date"], "2024-06-01")

    def test_returns_none_when_row_missing(self):
        from movietrace.pipeline.current_discovery import get_stable_metadata
        result = get_stable_metadata(self.conn, "discovery:tv:99999")
        self.assertIsNone(result)

    def test_returns_none_when_stable_meta_null(self):
        from movietrace.pipeline.current_discovery import get_stable_metadata
        self._insert_item_with_stable_meta("discovery:tv:5002", None)
        result = get_stable_metadata(self.conn, "discovery:tv:5002")
        self.assertIsNone(result)

    def test_returns_none_when_stable_meta_invalid_json(self):
        from movietrace.pipeline.current_discovery import get_stable_metadata
        self._insert_item_with_stable_meta("discovery:tv:5003", "not-valid-json{")
        result = get_stable_metadata(self.conn, "discovery:tv:5003")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
