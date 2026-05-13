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

        # Pre-populate cache
        import json
        self.conn.execute(
            "insert into api_cache (source, cache_key, response_json) values (?, ?, ?)",
            ("omdb", "omdb:tt1190634", json.dumps({"imdbRating": "8.6", "imdbVotes": "853,757"})),
        )
        self.conn.commit()

        c = MergedCandidate(tmdb_id=76479, imdb_id="1190634", title="Test", media_type="tv")

        with patch("movietrace.pipeline.omdb_enrichment.time.sleep", return_value=None):
            result = enrich_with_omdb(self.conn, [c], "fake-key")

        self.assertEqual(result["cache_hits"], 1)
        self.assertEqual(result["api_calls"], 0)
        self.assertEqual(c.imdb_rating, 8.6)
        self.assertEqual(c.imdb_votes, 853757)

    def test_enrich_skips_when_no_imdb_id(self):
        from movietrace.pipeline.omdb_enrichment import enrich_with_omdb
        from movietrace.pipeline.multi_source_merge import MergedCandidate

        c = MergedCandidate(tmdb_id=100, imdb_id=None, title="No IMDb", media_type="movie")

        with patch("movietrace.pipeline.omdb_enrichment.time.sleep", return_value=None):
            result = enrich_with_omdb(self.conn, [c], "fake-key")

        self.assertEqual(result["enriched"], 0)

    def test_format_imdb_id_handles_tt_prefix(self):
        from movietrace.sources.omdb import format_imdb_id
        self.assertEqual(format_imdb_id("tt1234567"), "tt1234567")


if __name__ == "__main__":
    unittest.main()
