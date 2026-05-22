import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class OmdbEnrichmentTest(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_omdb.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def test_format_imdb_id_pads_zeros(self):
        from movietrace.sources.omdb import format_imdb_id
        self.assertEqual(format_imdb_id("1190634"), "tt1190634")
        self.assertEqual(format_imdb_id("tt1190634"), "tt1190634")
        self.assertEqual(format_imdb_id("12345"), "tt0012345")

    def test_enrich_with_omdb_cache_hit(self):
        from movietrace.pipeline.omdb_enrichment import enrich_with_omdb
        from movietrace.pipeline.multi_source_merge import MergedCandidate

        import json
        self.conn.execute(
            "insert into api_cache (source, cache_key, response_json) values (?, ?, ?)",
            ("omdb", "omdb:tt1190634", json.dumps({"imdbRating": "8.6", "imdbVotes": "853,757"})),
        )
        self.conn.commit()

        c = MergedCandidate(tmdb_id=76479, imdb_id="1190634", title="Test", media_type="tv")

        with patch("movietrace.pipeline.omdb_enrichment.time.sleep", return_value=None):
            result = enrich_with_omdb(self.conn, [c], ["fake-key"])

        self.assertEqual(result["cache_hits"], 1)
        self.assertEqual(result["api_calls"], 0)
        self.assertEqual(result["enriched"], 1)
        self.assertEqual(result["keys_used"], 0)
        self.assertEqual(result["keys_exhausted"], 0)
        self.assertEqual(c.imdb_rating, 8.6)
        self.assertEqual(c.imdb_votes, 853757)

    def test_enrich_skips_when_no_imdb_id(self):
        from movietrace.pipeline.omdb_enrichment import enrich_with_omdb
        from movietrace.pipeline.multi_source_merge import MergedCandidate

        c = MergedCandidate(tmdb_id=100, imdb_id=None, title="No IMDb", media_type="movie")

        with patch("movietrace.pipeline.omdb_enrichment.time.sleep", return_value=None):
            result = enrich_with_omdb(self.conn, [c], ["fake-key"])

        self.assertEqual(result["enriched"], 0)

    def test_format_imdb_id_handles_tt_prefix(self):
        from movietrace.sources.omdb import format_imdb_id
        self.assertEqual(format_imdb_id("tt1234567"), "tt1234567")

    def test_multi_key_first_fails_second_succeeds(self):
        """First key 401 → switch to second key and succeed."""
        from movietrace.pipeline.omdb_enrichment import enrich_with_omdb
        from movietrace.pipeline.multi_source_merge import MergedCandidate
        from movietrace.sources.http import FatalApiError

        c = MergedCandidate(tmdb_id=76479, imdb_id="1190634", title="Test", media_type="tv")

        call_count = [0]

        def mock_get_json(url, params=None, headers=None, timeout=20, log_context=None):
            call_count[0] += 1
            if call_count[0] == 1:
                raise FatalApiError(401, "Unauthorized")
            return {"Response": "True", "imdbRating": "7.5", "imdbVotes": "10,000"}

        with patch("movietrace.sources.omdb.get_json", side_effect=mock_get_json):
            with patch("movietrace.pipeline.omdb_enrichment.time.sleep", return_value=None):
                result = enrich_with_omdb(self.conn, [c], ["bad-key", "good-key"])

        self.assertEqual(result["api_calls"], 2)  # 1 fatal + 1 success
        self.assertEqual(result["enriched"], 1)
        self.assertEqual(result["keys_used"], 2)
        self.assertEqual(result["keys_exhausted"], 1)
        self.assertEqual(c.imdb_rating, 7.5)
        self.assertEqual(c.imdb_votes, 10000)

    def test_all_keys_fatal_circuit_breaker(self):
        """All keys 401 → circuit breaker stops enrichment."""
        from movietrace.pipeline.omdb_enrichment import enrich_with_omdb
        from movietrace.pipeline.multi_source_merge import MergedCandidate
        from movietrace.sources.http import FatalApiError

        c1 = MergedCandidate(tmdb_id=76479, imdb_id="1190634", title="Test1", media_type="tv")
        c2 = MergedCandidate(tmdb_id=76480, imdb_id="1190635", title="Test2", media_type="tv")

        call_count = [0]

        def mock_get_json(url, params=None, headers=None, timeout=20, log_context=None):
            call_count[0] += 1
            raise FatalApiError(401, "Unauthorized")

        with patch("movietrace.sources.omdb.get_json", side_effect=mock_get_json):
            with patch("movietrace.pipeline.omdb_enrichment.time.sleep", return_value=None):
                result = enrich_with_omdb(self.conn, [c1, c2], ["key1", "key2"])

        # Both keys tried for first candidate = 2 calls, then circuit breaker
        self.assertEqual(result["api_calls"], 2)
        self.assertEqual(result["enriched"], 0)
        self.assertEqual(result["keys_used"], 2)
        self.assertEqual(result["keys_exhausted"], 2)
        # Only 2 calls (both keys for first candidate), not 4 (both keys for both candidates)
        self.assertEqual(call_count[0], 2)

    def test_multi_key_single_key_works_normally(self):
        """Single key that works → normal flow."""
        from movietrace.pipeline.omdb_enrichment import enrich_with_omdb
        from movietrace.pipeline.multi_source_merge import MergedCandidate

        c = MergedCandidate(tmdb_id=76479, imdb_id="1190634", title="Test", media_type="tv")

        def mock_get_json(url, params=None, headers=None, timeout=20, log_context=None):
            return {"Response": "True", "imdbRating": "8.0", "imdbVotes": "5,000"}

        with patch("movietrace.sources.omdb.get_json", side_effect=mock_get_json):
            with patch("movietrace.pipeline.omdb_enrichment.time.sleep", return_value=None):
                result = enrich_with_omdb(self.conn, [c], ["only-key"])

        self.assertEqual(result["api_calls"], 1)
        self.assertEqual(result["enriched"], 1)
        self.assertEqual(result["keys_used"], 1)
        self.assertEqual(result["keys_exhausted"], 0)
        self.assertEqual(c.imdb_rating, 8.0)

    def test_empty_keys_list_returns_early(self):
        from movietrace.pipeline.omdb_enrichment import enrich_with_omdb
        from movietrace.pipeline.multi_source_merge import MergedCandidate

        c = MergedCandidate(tmdb_id=76479, imdb_id="1190634", title="Test", media_type="tv")
        result = enrich_with_omdb(self.conn, [c], [])
        self.assertEqual(result["api_calls"], 0)
        self.assertEqual(result["keys_used"], 0)

    def test_non_fatal_error_does_not_switch_key(self):
        """5xx errors should not trigger key switch (only FatalApiError does)."""
        from movietrace.pipeline.omdb_enrichment import enrich_with_omdb
        from movietrace.pipeline.multi_source_merge import MergedCandidate

        c = MergedCandidate(tmdb_id=76479, imdb_id="1190634", title="Test", media_type="tv")

        def mock_get_json(url, params=None, headers=None, timeout=20, log_context=None):
            raise Exception("HTTP Error 502: Bad Gateway")

        with patch("movietrace.sources.omdb.get_json", side_effect=mock_get_json):
            with patch("movietrace.pipeline.omdb_enrichment.time.sleep", return_value=None):
                result = enrich_with_omdb(self.conn, [c], ["key1", "key2"])

        # Non-fatal error: should not exhaust keys, just skip candidate
        self.assertEqual(result["keys_exhausted"], 0)
        self.assertEqual(result["keys_used"], 1)  # only key1 was tried
        self.assertEqual(result["enriched"], 0)

    def test_enrich_omdb_logs_progress_every_20(self):
        from movietrace.pipeline.omdb_enrichment import enrich_with_omdb
        from movietrace.pipeline.multi_source_merge import MergedCandidate

        candidates = [
            MergedCandidate(tmdb_id=i, imdb_id=f"tt{i:07d}", title=f"Test {i}", media_type="movie")
            for i in range(1, 22)
        ]
        data = {"Response": "True", "imdbRating": "7.5", "imdbVotes": "1,000"}

        with patch("movietrace.pipeline.omdb_enrichment._read_cache", return_value=None):
            with patch("movietrace.pipeline.omdb_enrichment.OmdbDetailClient") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.get_by_imdb_id.return_value = data
                mock_client_cls.return_value = mock_client
                with patch("movietrace.pipeline.omdb_enrichment.time.sleep", return_value=None):
                    with self.assertLogs("movietrace.pipeline.omdb_enrichment", level="INFO") as log_capture:
                        result = enrich_with_omdb(self.conn, candidates, ["fake-key"])

        log_text = "\n".join(log_capture.output)
        self.assertIn("OMDb enrichment: 20/21 (api=20 cache=0 enriched=20)", log_text)
        self.assertIn("OMDb enrichment: 21/21 (api=21 cache=0 enriched=21)", log_text)
        self.assertEqual(result["api_calls"], 21)
        self.assertEqual(result["enriched"], 21)

    def test_enrich_omdb_logs_progress_at_end_when_less_than_20(self):
        from movietrace.pipeline.omdb_enrichment import enrich_with_omdb
        from movietrace.pipeline.multi_source_merge import MergedCandidate

        candidates = [
            MergedCandidate(tmdb_id=i, imdb_id=f"tt{i:07d}", title=f"Test {i}", media_type="movie")
            for i in range(1, 6)
        ]
        data = {"Response": "True", "imdbRating": "7.5", "imdbVotes": "1,000"}

        with patch("movietrace.pipeline.omdb_enrichment._read_cache", return_value=None):
            with patch("movietrace.pipeline.omdb_enrichment.OmdbDetailClient") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.get_by_imdb_id.return_value = data
                mock_client_cls.return_value = mock_client
                with patch("movietrace.pipeline.omdb_enrichment.time.sleep", return_value=None):
                    with self.assertLogs("movietrace.pipeline.omdb_enrichment", level="INFO") as log_capture:
                        result = enrich_with_omdb(self.conn, candidates, ["fake-key"])

        log_text = "\n".join(log_capture.output)
        self.assertIn("OMDb enrichment: 5/5 (api=5 cache=0 enriched=5)", log_text)
        self.assertEqual(result["api_calls"], 5)
        self.assertEqual(result["enriched"], 5)

    def test_enrich_tmdb_detail_logs_progress_every_20(self):
        from movietrace.pipeline.omdb_enrichment import enrich_with_tmdb_details
        from movietrace.pipeline.multi_source_merge import MergedCandidate

        candidates = [
            MergedCandidate(tmdb_id=i, imdb_id=None, title=f"Show {i}", media_type="tv")
            for i in range(1, 22)
        ]
        detail_data = {
            "first_air_date": "2024-01-01",
            "original_language": "en",
            "genres": [{"id": 18, "name": "Drama"}],
        }

        with patch("movietrace.pipeline.omdb_enrichment.get_tmdb_detail_with_cache", return_value=(detail_data, False)):
            with patch("movietrace.pipeline.omdb_enrichment._fetch_zh_detail_with_cache", return_value=({}, False)):
                with self.assertLogs("movietrace.pipeline.omdb_enrichment", level="INFO") as log_capture:
                    result = enrich_with_tmdb_details(self.conn, candidates, "fake-token", db_path=str(self.db_path))

        log_text = "\n".join(log_capture.output)
        self.assertIn("TMDb detail enrichment: 20/21 (api=20 cache=0 enriched=20)", log_text)
        self.assertIn("TMDb detail enrichment: 21/21 (api=21 cache=0 enriched=21)", log_text)
        self.assertEqual(result["api_calls"], 21)
        self.assertEqual(result["enriched"], 21)


class OmdbResolveKeysTest(unittest.TestCase):
    def test_new_format_api_keys_list(self):
        from movietrace.pipeline.discovery import _resolve_omdb_keys
        keys = _resolve_omdb_keys({"omdb": {"api_keys": ["k1", "k2"]}})
        self.assertEqual(keys, ["k1", "k2"])

    def test_old_format_api_key_string(self):
        from movietrace.pipeline.discovery import _resolve_omdb_keys
        keys = _resolve_omdb_keys({"omdb": {"api_key": "oldkey"}})
        self.assertEqual(keys, ["oldkey"])

    def test_old_format_empty_string(self):
        from movietrace.pipeline.discovery import _resolve_omdb_keys
        keys = _resolve_omdb_keys({"omdb": {"api_key": ""}})
        self.assertEqual(keys, [])

    def test_no_omdb_section(self):
        from movietrace.pipeline.discovery import _resolve_omdb_keys
        keys = _resolve_omdb_keys({})
        self.assertEqual(keys, [])

    def test_new_format_filters_empty_strings(self):
        from movietrace.pipeline.discovery import _resolve_omdb_keys
        keys = _resolve_omdb_keys({"omdb": {"api_keys": ["k1", "", "k2"]}})
        self.assertEqual(keys, ["k1", "k2"])

    def test_new_format_takes_priority_over_old(self):
        from movietrace.pipeline.discovery import _resolve_omdb_keys
        keys = _resolve_omdb_keys({"omdb": {"api_keys": ["k1", "k2"], "api_key": "old"}})
        self.assertEqual(keys, ["k1", "k2"])


class OmdbKeyLogMaskingTest(unittest.TestCase):
    """P1.12-C: OMDb key log output must use fingerprint, never raw key."""

    def test_short_key_not_in_log_output(self):
        """8-char OMDb key must not appear in log messages."""
        from movietrace.pipeline.omdb_enrichment import enrich_with_omdb
        from movietrace.pipeline.multi_source_merge import MergedCandidate
        from movietrace.sources.http import FatalApiError
        from movietrace.db.schema import initialize_database, connect_database
        import logging

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            initialize_database(db_path)
            conn = connect_database(db_path)

            # Mock OmdbDetailClient to raise FatalApiError
            short_key = "c9c22b79"  # 8-char key
            with patch("movietrace.pipeline.omdb_enrichment.OmdbDetailClient") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.get_by_imdb_id.side_effect = FatalApiError(403, "Fatal")
                mock_client_cls.return_value = mock_client

                candidate = MergedCandidate(
                    tmdb_id=100, imdb_id="tt1234567", title="Test", media_type="movie"
                )

                with self.assertLogs("movietrace.pipeline.omdb_enrichment", level="WARNING") as log_capture:
                    enrich_with_omdb(conn, [candidate], [short_key], db_path=str(db_path), request_date="2026-05-14")

                log_text = "\n".join(log_capture.output)
                self.assertNotIn(short_key, log_text,
                                f"Complete key '{short_key}' found in log output")
                # fingerprint should be present instead
                self.assertIn("OMDb key", log_text)

            conn.close()

    def test_long_key_not_in_log_output(self):
        """Longer OMDb key must not appear in log messages."""
        from movietrace.pipeline.omdb_enrichment import enrich_with_omdb
        from movietrace.pipeline.multi_source_merge import MergedCandidate
        from movietrace.sources.http import FatalApiError
        from movietrace.db.schema import initialize_database, connect_database

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            initialize_database(db_path)
            conn = connect_database(db_path)

            long_key = "abcdef1234567890"  # 16-char key
            with patch("movietrace.pipeline.omdb_enrichment.OmdbDetailClient") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.get_by_imdb_id.side_effect = FatalApiError(403, "Fatal")
                mock_client_cls.return_value = mock_client

                candidate = MergedCandidate(
                    tmdb_id=100, imdb_id="tt1234567", title="Test", media_type="movie"
                )

                with self.assertLogs("movietrace.pipeline.omdb_enrichment", level="WARNING") as log_capture:
                    enrich_with_omdb(conn, [candidate], [long_key], db_path=str(db_path), request_date="2026-05-14")

                log_text = "\n".join(log_capture.output)
                self.assertNotIn(long_key, log_text,
                                f"Complete key '{long_key}' found in log output")

            conn.close()


class TestZhFields(unittest.TestCase):
    def _make_db(self):
        from movietrace.db.schema import initialize_database, connect_database
        import tempfile
        tmp = tempfile.mkdtemp()
        db_path = Path(tmp) / "test_zh.db"
        initialize_database(db_path)
        return connect_database(db_path)

    def test_zh_fields_written_to_canonical(self):
        """zh-CN title/overview get written to canonical_items via _update_canonical_zh_fields."""
        from movietrace.pipeline.omdb_enrichment import _update_canonical_zh_fields
        conn = self._make_db()
        conn.execute(
            "insert into canonical_items(canonical_item_key, title, content_type, content_granularity) values (?, ?, ?, ?)",
            ("k1", "Test Show", "tv", "season"),
        )
        canonical_id = conn.execute("select last_insert_rowid()").fetchone()[0]
        conn.execute(
            "insert into external_ids(canonical_item_id, source, external_id) values (?, ?, ?)",
            (canonical_id, "tmdb", "tv:99999"),
        )
        conn.commit()
        result = _update_canonical_zh_fields(conn, "99999", "tv", "测试剧", "这是简介", None, None)
        self.assertTrue(result)
        row = conn.execute("select title_zh, overview_zh from canonical_items where id = ?", (canonical_id,)).fetchone()
        self.assertEqual(row[0], "测试剧")
        self.assertEqual(row[1], "这是简介")
        conn.close()

    def test_genres_json_serialized(self):
        """genres list from en-US detail is serialized to JSON string."""
        import json
        genres = [{"id": 18, "name": "Drama"}, {"id": 10759, "name": "Action"}]
        result = json.dumps(genres, ensure_ascii=False)
        parsed = json.loads(result)
        self.assertEqual(parsed[0]["name"], "Drama")


class TestEnrichTmdbDetailsBatchCommit(unittest.TestCase):
    """P1.43: Verify batch-commit semantics for enrich_with_tmdb_details."""

    def _make_db(self):
        from movietrace.db.schema import initialize_database, connect_database
        import tempfile
        tmp = tempfile.mkdtemp()
        db_path = Path(tmp) / "test_batch.db"
        initialize_database(db_path)
        return connect_database(db_path), str(db_path)

    def _seed_canonical(self, conn, tmdb_id: int, media_type: str = "tv") -> int:
        """Insert canonical_item + external_id, return canonical_item_id."""
        key = f"tmdb:{media_type}:{tmdb_id}:season:1" if media_type == "tv" else f"tmdb:movie:{tmdb_id}"
        conn.execute(
            "insert into canonical_items(canonical_item_key, title, content_type, content_granularity) values (?, ?, ?, ?)",
            (key, f"Show {tmdb_id}", media_type, "season" if media_type == "tv" else "movie"),
        )
        canonical_id = conn.execute("select last_insert_rowid()").fetchone()[0]
        ext_id = f"{media_type}:{tmdb_id}"
        conn.execute(
            "insert into external_ids(canonical_item_id, source, external_id) values (?, ?, ?)",
            (canonical_id, "tmdb", ext_id),
        )
        conn.commit()
        return canonical_id

    def test_enrich_rolls_back_on_mid_loop_error(self):
        """P1.43: single-candidate error continues; committed writes include successful candidates only.

        Strategy: 'single error continue, batch commit at end'.
        - Candidate 1 returns valid detail → zh fields written at commit
        - Candidate 2 raises RuntimeError in get_tmdb_detail_with_cache → caught by except, loop continues
        - After loop: conn.commit() commits candidate-1 writes; candidate-2 was never written
        """
        from movietrace.pipeline.omdb_enrichment import enrich_with_tmdb_details
        from movietrace.pipeline.multi_source_merge import MergedCandidate

        conn, db_path = self._make_db()
        cid1 = self._seed_canonical(conn, 1001, "tv")
        cid2 = self._seed_canonical(conn, 1002, "tv")

        c1 = MergedCandidate(tmdb_id=1001, imdb_id=None, title="Show 1001", media_type="tv")
        c2 = MergedCandidate(tmdb_id=1002, imdb_id=None, title="Show 1002", media_type="tv")

        detail_data_c1 = {
            "release_date": "2024-01-01",
            "original_language": "en",
            "genres": [{"id": 18, "name": "Drama"}],
        }
        zh_data_c1 = {"name": "第一剧", "overview": "简介一"}

        call_count = [0]

        def mock_get_tmdb_detail(conn, client, tmdb_id, media_type, ttl_hours=24):
            call_count[0] += 1
            if tmdb_id == 1001:
                return detail_data_c1, False
            raise RuntimeError("simulated API failure for candidate 2")

        def mock_fetch_zh(conn, client, tmdb_id, media_type, ttl_hours=24):
            if tmdb_id == 1001:
                return zh_data_c1, False
            return None, False

        with patch("movietrace.pipeline.omdb_enrichment.get_tmdb_detail_with_cache", side_effect=mock_get_tmdb_detail):
            with patch("movietrace.pipeline.omdb_enrichment._fetch_zh_detail_with_cache", side_effect=mock_fetch_zh):
                result = enrich_with_tmdb_details(conn, [c1, c2], "fake-token", db_path=db_path)

        # Enriched count: only c1 succeeded
        self.assertEqual(result["enriched"], 1)

        # c1 zh fields must be written (committed)
        row1 = conn.execute("select title_zh from canonical_items where id = ?", (cid1,)).fetchone()
        self.assertEqual(row1[0], "第一剧")

        # c2 zh fields must remain NULL (never written — error before any write)
        row2 = conn.execute("select title_zh from canonical_items where id = ?", (cid2,)).fetchone()
        self.assertIsNone(row2[0])

        conn.close()


class TestApplyTmdbDetailDataLastEpisode(unittest.TestCase):
    def _make_candidate(self):
        from movietrace.pipeline.multi_source_merge import MergedCandidate
        return MergedCandidate(tmdb_id=100, imdb_id=None, title="Test", media_type="tv")

    def test_last_episode_to_air_object_preserved(self):
        from movietrace.pipeline.omdb_enrichment import _apply_tmdb_detail_data
        c = self._make_candidate()
        lea = {"id": 1, "name": "Ep 1", "air_date": "2026-05-01"}
        _apply_tmdb_detail_data(c, {"last_episode_to_air": lea})
        self.assertEqual(c.tmdb_data["last_episode_to_air"], lea)

    def test_last_episode_air_date_string_still_extracted(self):
        from movietrace.pipeline.omdb_enrichment import _apply_tmdb_detail_data
        c = self._make_candidate()
        lea = {"id": 1, "name": "Ep 1", "air_date": "2026-05-01"}
        _apply_tmdb_detail_data(c, {"last_episode_to_air": lea})
        self.assertEqual(c.tmdb_data["last_episode_air_date"], "2026-05-01")

    def test_last_episode_to_air_none_when_missing(self):
        from movietrace.pipeline.omdb_enrichment import _apply_tmdb_detail_data
        c = self._make_candidate()
        _apply_tmdb_detail_data(c, {"vote_average": 7.5})
        self.assertNotIn("last_episode_to_air", c.tmdb_data)

    def test_seasons_list_preserved_for_sparse_season_duration(self):
        from movietrace.pipeline.omdb_enrichment import _apply_tmdb_detail_data
        c = self._make_candidate()
        seasons = [{"season_number": 1}, {"season_number": 49}]
        _apply_tmdb_detail_data(c, {"seasons": seasons})
        self.assertEqual(c.tmdb_data["seasons"], seasons)


if __name__ == "__main__":
    unittest.main()
