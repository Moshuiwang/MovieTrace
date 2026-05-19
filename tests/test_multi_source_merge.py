import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class MultiSourceMergeTest(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_merge.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def _seed_fp(self, items: list[dict]):
        for item in items:
            self.conn.execute(
                """insert into flixpatrol_top10
                   (fp_id, title, content_type, platform, country, snapshot_date,
                    ranking, days_total, tmdb_id, imdb_id, raw_payload_json)
                   values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item.get("fp_id", "fp1"),
                    item.get("title", "Test"),
                    item.get("content_type", "movie"),
                    item.get("platform", "netflix"),
                    "united-states",
                    item.get("snapshot_date", "2026-05-13"),
                    item.get("ranking", 1),
                    item.get("days_total", 10),
                    item.get("tmdb_id"),
                    item.get("imdb_id"),
                    "{}",
                ),
            )
        self.conn.commit()

    def _seed_tmdb(self, items: list[dict]):
        for item in items:
            self.conn.execute(
                """insert into tmdb_trending
                   (tmdb_id, media_type, title, popularity, source_endpoint,
                    source_page, snapshot_date, raw_payload_json)
                   values (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item.get("tmdb_id"),
                    item.get("media_type", "movie"),
                    item.get("title", "Test"),
                    item.get("popularity", 100.0),
                    item.get("source_endpoint", "trending/day"),
                    item.get("source_page", 1),
                    item.get("snapshot_date", "2026-05-13"),
                    "{}",
                ),
            )
        self.conn.commit()

    def _seed_trakt(self, items: list[dict]):
        for item in items:
            self.conn.execute(
                """insert into trakt_trending
                   (trakt_id, tmdb_id, imdb_id, media_type, title, watchers,
                    source_endpoint, snapshot_date, raw_payload_json)
                   values (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item.get("trakt_id", 999),
                    item.get("tmdb_id"),
                    item.get("imdb_id"),
                    item.get("media_type", "movie"),
                    item.get("title", "Test"),
                    item.get("watchers", 500),
                    item.get("source_endpoint", "movies/trending"),
                    item.get("snapshot_date", "2026-05-13"),
                    "{}",
                ),
            )
        self.conn.commit()

    def test_single_source_fp_only(self):
        from movietrace.pipeline.multi_source_merge import merge_three_sources
        self._seed_fp([{"tmdb_id": 100, "title": "Only FP", "snapshot_date": "2026-05-13"}])
        candidates = merge_three_sources(self.conn, "2026-05-13")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].tmdb_id, 100)
        self.assertIn("fp", candidates[0].source_flags)
        self.assertIsNone(candidates[0].tmdb_data)

    def test_same_tmdb_id_in_all_three_sources_merged(self):
        from movietrace.pipeline.multi_source_merge import merge_three_sources
        self._seed_fp([{"tmdb_id": 76479, "title": "The Boys FP", "content_type": "tv_show",
                        "snapshot_date": "2026-05-13"}])
        self._seed_tmdb([{"tmdb_id": 76479, "media_type": "tv", "title": "The Boys TMDb",
                          "popularity": 569.2, "vote_average": 8.45, "vote_count": 12247,
                          "snapshot_date": "2026-05-13"}])
        self._seed_trakt([{"trakt_id": 1, "tmdb_id": 76479, "media_type": "show",
                           "title": "The Boys Trakt", "watchers": 5520,
                           "snapshot_date": "2026-05-13"}])
        candidates = merge_three_sources(self.conn, "2026-05-13")
        self.assertEqual(len(candidates), 1)
        c = candidates[0]
        self.assertEqual(c.tmdb_id, 76479)
        self.assertIn("fp", c.source_flags)
        self.assertIn("tmdb", c.source_flags)
        self.assertIn("trakt", c.source_flags)
        self.assertEqual(c.title, "The Boys TMDb")
        self.assertIsNotNone(c.tmdb_data)
        self.assertIsNotNone(c.trakt_data)
        self.assertEqual(len(c.fp_items), 1)

    def test_fp_media_type_conflict_uses_tmdb_type(self):
        from movietrace.pipeline.multi_source_merge import merge_three_sources
        self._seed_fp([{"tmdb_id": 1658982, "title": "The Roast of Kevin Hart FP",
                        "content_type": "tv_show", "snapshot_date": "2026-05-13"}])
        self._seed_tmdb([{"tmdb_id": 1658982, "media_type": "movie",
                          "title": "The Roast of Kevin Hart",
                          "snapshot_date": "2026-05-13"}])

        candidates = merge_three_sources(self.conn, "2026-05-13")

        self.assertEqual(len(candidates), 1)
        c = candidates[0]
        self.assertEqual(c.media_type, "movie")
        self.assertIn("fp", c.source_flags)
        self.assertIn("tmdb", c.source_flags)
        self.assertEqual(c.fp_items[0]["media_type"], "movie")

    def test_fp_media_type_conflict_uses_cached_tmdb_detail_type(self):
        from movietrace.pipeline.multi_source_merge import merge_three_sources
        self._seed_fp([{"tmdb_id": 1658982, "title": "The Roast of Kevin Hart FP",
                        "content_type": "tv_show", "snapshot_date": "2026-05-13"}])
        self.conn.execute(
            """insert into api_cache(source, cache_key, response_json)
               values ('tmdb', 'tmdb:detail:1658982:movie', '{"title": "The Roast of Kevin Hart FP"}')"""
        )
        self.conn.commit()

        candidates = merge_three_sources(self.conn, "2026-05-13")

        self.assertEqual(len(candidates), 1)
        c = candidates[0]
        self.assertEqual(c.media_type, "movie")
        self.assertEqual(c.fp_items[0]["media_type"], "movie")

    def test_fp_media_type_conflict_ignores_cached_type_for_different_title(self):
        from movietrace.pipeline.multi_source_merge import merge_three_sources
        self._seed_fp([{"tmdb_id": 42, "title": "A Real TV Show",
                        "content_type": "tv_show", "snapshot_date": "2026-05-13"}])
        self.conn.execute(
            """insert into api_cache(source, cache_key, response_json)
               values ('tmdb', 'tmdb:detail:42:movie', '{"title": "Different Movie"}')"""
        )
        self.conn.commit()

        candidates = merge_three_sources(self.conn, "2026-05-13")

        self.assertEqual(len(candidates), 1)
        c = candidates[0]
        self.assertEqual(c.media_type, "tv")
        self.assertEqual(c.fp_items[0]["media_type"], "tv")

    def test_imdb_id_fallback_merging(self):
        from movietrace.pipeline.multi_source_merge import merge_three_sources
        self._seed_fp([{"imdb_id": "tt1234567", "title": "ImdbOnly", "snapshot_date": "2026-05-13"}])
        self._seed_trakt([{"trakt_id": 2, "imdb_id": "tt1234567", "media_type": "movie",
                           "title": "ImdbOnly Trakt", "watchers": 300,
                           "snapshot_date": "2026-05-13"}])
        candidates = merge_three_sources(self.conn, "2026-05-13")
        self.assertEqual(len(candidates), 1)
        self.assertIn("fp", candidates[0].source_flags)
        self.assertIn("trakt", candidates[0].source_flags)

    def test_title_fallback_when_no_ids(self):
        from movietrace.pipeline.multi_source_merge import merge_three_sources
        self._seed_fp([{"title": "No ID Movie", "snapshot_date": "2026-05-13"}])
        self._seed_trakt([{"trakt_id": 3, "title": "No ID Movie", "media_type": "movie",
                           "watchers": 100, "snapshot_date": "2026-05-13"}])
        candidates = merge_three_sources(self.conn, "2026-05-13")
        self.assertEqual(len(candidates), 1)
        self.assertIn("fp", candidates[0].source_flags)
        self.assertIn("trakt", candidates[0].source_flags)

    def test_source_dates_per_source_different_dates(self):
        from movietrace.pipeline.multi_source_merge import merge_three_sources
        # FP data on 05-14, TMDb on 05-13, Trakt on 05-12
        self._seed_fp([{"tmdb_id": 100, "title": "FP Today", "snapshot_date": "2026-05-14"}])
        self._seed_tmdb([{"tmdb_id": 100, "media_type": "movie", "title": "TMDb Yesterday",
                          "popularity": 100.0, "snapshot_date": "2026-05-13"}])
        self._seed_trakt([{"trakt_id": 1, "tmdb_id": 100, "media_type": "movie",
                           "title": "Trakt Older", "watchers": 500, "snapshot_date": "2026-05-12"}])
        source_dates = {"flixpatrol": "2026-05-14", "tmdb": "2026-05-13", "trakt": "2026-05-12"}
        candidates = merge_three_sources(self.conn, "2026-05-14", source_dates)
        self.assertEqual(len(candidates), 1)
        c = candidates[0]
        self.assertEqual(c.tmdb_id, 100)
        self.assertIn("fp", c.source_flags)
        self.assertIn("tmdb", c.source_flags)
        self.assertIn("trakt", c.source_flags)

    def test_source_dates_none_skips_source(self):
        from movietrace.pipeline.multi_source_merge import merge_three_sources
        self._seed_fp([{"tmdb_id": 200, "title": "FP Only", "snapshot_date": "2026-05-14"}])
        source_dates = {"flixpatrol": "2026-05-14", "tmdb": None, "trakt": None}
        candidates = merge_three_sources(self.conn, "2026-05-14", source_dates)
        self.assertEqual(len(candidates), 1)
        c = candidates[0]
        self.assertIn("fp", c.source_flags)
        self.assertNotIn("tmdb", c.source_flags)

    def test_source_dates_defaults_to_snapshot_date(self):
        from movietrace.pipeline.multi_source_merge import merge_three_sources
        self._seed_fp([{"tmdb_id": 300, "title": "Default Date", "snapshot_date": "2026-05-14"}])
        candidates = merge_three_sources(self.conn, "2026-05-14")
        self.assertEqual(len(candidates), 1)


if __name__ == "__main__":
    unittest.main()
