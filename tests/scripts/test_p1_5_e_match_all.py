import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class MockTmdbClient:
    """Mock TMDb client for testing without API calls."""

    def __init__(self, results=None):
        self.results = results or []
        self.search_calls: list[tuple[str, object]] = []

    def search(self, query, baseline_item):
        self.search_calls.append((query, baseline_item))
        return self.results


def _make_tmdb_tv_result(tmdb_id="1399", title="Game of Thrones", year=2011):
    from movietrace.pipeline.entity_matching import ExternalSearchResult

    return ExternalSearchResult(
        source="tmdb",
        external_id=tmdb_id,
        title=title,
        media_type="tv",
        year=year,
        score=100.0,
        raw_payload={
            "id": int(tmdb_id),
            "name": title,
            "original_name": title,
            "first_air_date": f"{year}-04-17",
            "media_type": "tv",
            "popularity": 100.0,
        },
    )


def _make_tmdb_movie_result(tmdb_id="76600", title="Avatar: The Way of Water", year=2022):
    from movietrace.pipeline.entity_matching import ExternalSearchResult

    return ExternalSearchResult(
        source="tmdb",
        external_id=tmdb_id,
        title=title,
        media_type="movie",
        year=year,
        score=100.0,
        raw_payload={
            "id": int(tmdb_id),
            "title": title,
            "original_title": title,
            "release_date": f"{year}-12-16",
            "media_type": "movie",
            "popularity": 100.0,
        },
    )


def _make_low_confidence_tv_result(tmdb_id="99999", title="Something Completely Different", year=1999):
    from movietrace.pipeline.entity_matching import ExternalSearchResult

    return ExternalSearchResult(
        source="tmdb",
        external_id=tmdb_id,
        title=title,
        media_type="tv",
        year=year,
        score=1.0,
        raw_payload={
            "id": int(tmdb_id),
            "name": title,
            "first_air_date": f"{year}-01-01",
            "media_type": "tv",
            "popularity": 1.0,
        },
    )


class P1Dot5EMatchAllTest(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.db"
        initialize_database(self.db_path)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _insert_upstream_program(self, pid, name, online_flag="1"):
        from movietrace.db.schema import connect_database

        with connect_database(self.db_path) as conn:
            conn.execute(
                """insert or ignore into upstream_programs(id, name, online_flag)
                   values (?, ?, ?)""",
                (pid, name, online_flag),
            )

    def _get_canonical_count(self):
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        count = conn.execute("select count(*) from canonical_items").fetchone()[0]
        conn.close()
        return count

    def _get_quality_issues(self):
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "select issue_type, confidence from baseline_quality_issues"
        ).fetchall()
        conn.close()
        return rows

    def test_match_tv_season_from_upstream_name(self):
        from movietrace.db.schema import connect_database
        from movietrace.pipeline.entity_matching import (
            _ensure_quality_issues_table,
            match_upstream_program,
        )

        self._insert_upstream_program(1, "Better Call Saul S01")

        mock = MockTmdbClient([_make_tmdb_tv_result("60059", "Better Call Saul")])

        with connect_database(self.db_path) as conn:
            _ensure_quality_issues_table(conn)
            result = match_upstream_program(conn, 1, mock)
            conn.commit()

        self.assertIsNotNone(result)
        self.assertTrue(result.get("matched"))
        self.assertEqual(result.get("content_type"), "tv")
        self.assertEqual(result.get("season_number"), 1)

        # Verify external_ids created
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        ext_rows = conn.execute(
            "select source, external_id from external_ids where canonical_item_id = ?",
            (result["canonical_item_id"],),
        ).fetchall()
        conn.close()

        sources = {r[0] for r in ext_rows}
        self.assertIn("upstream", sources)
        self.assertIn("tmdb", sources)
        # Verify TMDb external_id uses namespace prefix
        tmdb_ext = [r[1] for r in ext_rows if r[0] == "tmdb"][0]
        self.assertTrue(
            tmdb_ext.startswith("tv:") or tmdb_ext.startswith("movie:"),
            f"TMDb external_id '{tmdb_ext}' should have tv:/movie: prefix",
        )

    def test_match_movie_from_upstream_name(self):
        from movietrace.db.schema import connect_database
        from movietrace.pipeline.entity_matching import (
            _ensure_quality_issues_table,
            match_upstream_program,
        )

        self._insert_upstream_program(2, "Avatar The Way of Water")

        mock = MockTmdbClient([_make_tmdb_movie_result()])

        with connect_database(self.db_path) as conn:
            _ensure_quality_issues_table(conn)
            result = match_upstream_program(conn, 2, mock)
            conn.commit()

        self.assertIsNotNone(result)
        self.assertTrue(result.get("matched"))
        self.assertEqual(result.get("content_type"), "movie")

        # Verify TMDb external_id uses movie: prefix
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        ext_rows = conn.execute(
            "select source, external_id from external_ids where canonical_item_id = ?",
            (result["canonical_item_id"],),
        ).fetchall()
        conn.close()
        tmdb_ext = [r[1] for r in ext_rows if r[0] == "tmdb"][0]
        self.assertTrue(
            tmdb_ext.startswith("movie:"),
            f"Movie TMDb external_id '{tmdb_ext}' should have movie: prefix",
        )

    def test_match_low_confidence_creates_quality_issue(self):
        from movietrace.db.schema import connect_database
        from movietrace.pipeline.entity_matching import (
            _ensure_quality_issues_table,
            match_upstream_program,
        )

        self._insert_upstream_program(3, "Obscure Show S01")

        mock = MockTmdbClient([_make_low_confidence_tv_result()])

        with connect_database(self.db_path) as conn:
            _ensure_quality_issues_table(conn)
            result = match_upstream_program(conn, 3, mock)
            conn.commit()

        self.assertIsNotNone(result)

        issues = self._get_quality_issues()
        self.assertGreaterEqual(len(issues), 1)

        issue_types = {i[0] for i in issues}
        self.assertTrue(
            any("low_confidence" in t for t in issue_types)
        )

    def test_match_skips_already_matched(self):
        from movietrace.db.schema import connect_database
        from movietrace.pipeline.entity_matching import (
            _ensure_quality_issues_table,
            match_upstream_program,
        )

        self._insert_upstream_program(4, "Friends S01")

        mock = MockTmdbClient([_make_tmdb_tv_result("1668", "Friends")])

        with connect_database(self.db_path) as conn:
            _ensure_quality_issues_table(conn)
            result1 = match_upstream_program(conn, 4, mock)
            conn.commit()

        self.assertTrue(result1.get("matched"))

        # Second call should reuse existing canonical_item (idempotent)
        mock2 = MockTmdbClient([_make_tmdb_tv_result("1668", "Friends")])

        with connect_database(self.db_path) as conn:
            result2 = match_upstream_program(conn, 4, mock2)
            conn.commit()

        self.assertTrue(result2.get("matched"))
        self.assertEqual(
            result1["canonical_item_id"], result2["canonical_item_id"]
        )
        self.assertFalse(result2.get("created"))

        # Only one canonical_item should exist
        self.assertEqual(self._get_canonical_count(), 1)

    def test_no_results_creates_quality_issue(self):
        from movietrace.db.schema import connect_database
        from movietrace.pipeline.entity_matching import (
            _ensure_quality_issues_table,
            match_upstream_program,
        )

        self._insert_upstream_program(5, "Very Obscure Title")

        mock = MockTmdbClient([])  # No search results

        with connect_database(self.db_path) as conn:
            _ensure_quality_issues_table(conn)
            result = match_upstream_program(conn, 5, mock)
            conn.commit()

        self.assertIsNotNone(result)
        self.assertFalse(result.get("matched"))
        self.assertEqual(result.get("confidence"), "no_match")

        issues = self._get_quality_issues()
        self.assertGreaterEqual(len(issues), 1)


if __name__ == "__main__":
    unittest.main()
