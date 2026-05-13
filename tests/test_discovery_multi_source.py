import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class DiscoveryMultiSourceTest(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_disc.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

        # Seed data
        self._seed_all()

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def _seed_all(self):
        # FP
        self.conn.execute(
            """insert into flixpatrol_top10
               (fp_id, title, content_type, platform, country, snapshot_date,
                ranking, days_total, tmdb_id, imdb_id, raw_payload_json)
               values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("fp1", "The Boys", "tv_show", "netflix", "us", "2026-05-13",
             1, 32, 76479, "1190634", "{}"),
        )
        # TMDb
        self.conn.execute(
            """insert into tmdb_trending
               (tmdb_id, media_type, title, popularity, vote_average, vote_count,
                release_date, original_language, source_endpoint, source_page,
                snapshot_date, raw_payload_json)
               values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (76479, "tv", "The Boys", 569.2, 8.45, 12247,
             "2019-07-26", "en", "trending/day", 1, "2026-05-13", "{}"),
        )
        # Trakt
        self.conn.execute(
            """insert into trakt_trending
               (trakt_id, tmdb_id, imdb_id, media_type, title, watchers, rating, votes,
                source_endpoint, snapshot_date, raw_payload_json)
               values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (139960, 76479, "tt1190634", "show", "The Boys", 5520, 8.38, 36983,
             "shows/trending", "2026-05-13", "{}"),
        )
        # Another movie-only TMDb entry (no FP/Trakt)
        self.conn.execute(
            """insert into tmdb_trending
               (tmdb_id, media_type, title, popularity, vote_average, vote_count,
                release_date, original_language, source_endpoint, source_page,
                snapshot_date, raw_payload_json)
               values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (603692, "movie", "John Wick 4", 310.5, 7.6, 5500,
             "2023-03-22", "en", "trending/day", 1, "2026-05-13", "{}"),
        )
        # Seed external_ids so canonical lookup works
        self.conn.execute(
            "insert into canonical_items (canonical_item_key, title, content_type, content_granularity) "
            "values (?, ?, ?, ?)",
            ("tmdb:tv:76479", "The Boys", "tv", "season"),
        )
        self.conn.execute(
            "insert into external_ids (canonical_item_id, source, external_id) values (?, 'tmdb', ?)",
            (1, "76479"),
        )
        self.conn.execute(
            "insert into canonical_items (canonical_item_key, title, content_type, content_granularity) "
            "values (?, ?, ?, ?)",
            ("tmdb:movie:603692", "John Wick: Chapter 4", "movie", "movie"),
        )
        self.conn.execute(
            "insert into external_ids (canonical_item_id, source, external_id) values (?, 'tmdb', ?)",
            (2, "603692"),
        )
        self.conn.commit()

    def test_end_to_end_discovery_writes_content_updates(self):
        from movietrace.pipeline.discovery import run_discovery

        # Mock OMDb to avoid real API call (will skip because no OMDb key by default)
        # Mock _load_secrets to provide fake keys
        with patch("movietrace.pipeline.discovery._load_secrets", return_value={
            "omdb": {"api_key": "fake-omdb-key"},
            "tmdb": {"api_read_access_token": "fake-tmdb-token"},
        }):
            with patch("movietrace.pipeline.omdb_enrichment.enrich_with_omdb", return_value={
                "api_calls": 1, "cache_hits": 0, "enriched": 1,
            }):
                with patch("movietrace.pipeline.omdb_enrichment.enrich_with_tmdb_details", return_value={
                    "api_calls": 1, "cache_hits": 0, "enriched": 1,
                }):
                    result = run_discovery(
                        date_from="2026-05-13",
                        dry_run=False,
                        db_path=str(self.db_path),
                    )

        stats = result.get("stats", {})
        self.assertGreaterEqual(stats.get("total_merged", 0), 2)
        self.assertGreaterEqual(stats.get("total_passed", 0), 1)
        self.assertGreaterEqual(stats.get("written", 0), 1)

        # Verify content_updates written
        written = self.conn.execute(
            "select count(*) from content_updates"
        ).fetchone()[0]
        self.assertGreaterEqual(written, 1)

    def test_source_summary_json_structure(self):
        from movietrace.pipeline.discovery import _build_source_summary

        c_dict = {
            "tmdb_id": 76479, "title": "The Boys", "media_type": "tv",
            "fp_items": [{"platform": "netflix", "ranking": 1, "days_total": 32}],
            "tmdb_data": {"popularity": 569.2, "vote_average": 8.45, "vote_count": 12247},
            "trakt_data": {"watchers": 5520, "rating": 8.38, "votes": 36983},
            "imdb_rating": 8.6, "imdb_votes": 853757,
        }
        summary = _build_source_summary(c_dict)
        self.assertIn("fp", summary)
        self.assertIn("tmdb", summary)
        self.assertIn("trakt", summary)
        self.assertIn("imdb", summary)
        self.assertEqual(summary["fp"]["ranking"], 1)

    def test_threshold_filters_low_scores(self):
        from movietrace.pipeline.scoring import compute_hot_score, map_priority, DEFAULT_WEIGHTS

        # A candidate with no data → very low score
        candidate = {
            "title": "Unknown", "content_type": "movie", "platform": "hulu",
            "fp_items": [], "ext_data": {}, "release_date": None, "language": None,
        }
        hot, _ = compute_hot_score(candidate, DEFAULT_WEIGHTS)
        priority = map_priority(hot)
        # Should be P3 (below P2 threshold of 50)
        self.assertEqual(priority, "P3")

    def test_baseline_tracking_not_destroyed(self):
        """Verify that baseline_tracking module is still importable and functional."""
        from movietrace.pipeline.baseline_tracking import run_baseline_tracking

        with patch("movietrace.pipeline.baseline_tracking.TmdbDetailClient"):
            with patch("movietrace.pipeline.poll_scheduler.build_daily_poll_plan", return_value=[]):
                result = run_baseline_tracking(
                    db_path=str(self.db_path),
                    tmdb_token="fake-token",
                    dry_run=True,
                )
        self.assertIn("written", result)
        self.assertEqual(result["written"], 0)


if __name__ == "__main__":
    unittest.main()
