import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class CanonicalPromotionTest(unittest.TestCase):
    def test_promotes_high_tv_matches_to_one_series_canonical_item(self):
        from movietrace.db.schema import connect_database, initialize_database
        from movietrace.pipeline.canonical_promotion import promote_match_candidates

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "movietrace.db"
            initialize_database(db_path)

            with connect_database(db_path) as conn:
                for title in ("Jack Ryan S01", "Jack Ryan S02"):
                    conn.execute(
                        """
                        insert into baseline_items(title, content_granularity, raw_fields_json)
                        values (?, 'season', '{}')
                        """,
                        (title,),
                    )
                    baseline_id = conn.execute(
                        "select last_insert_rowid()"
                    ).fetchone()[0]
                    conn.execute(
                        """
                        insert into match_candidates(
                            baseline_item_id, source, external_id, title,
                            media_type, year, score, confidence, reason,
                            raw_payload_json
                        )
                        values (?, 'tmdb', '73375', "Tom Clancy's Jack Ryan",
                                'tv', 2018, 1.0, 'high', 'core_title_matches',
                                '{"original_name":"Tom Clancy''s Jack Ryan"}')
                        """,
                        (baseline_id,),
                    )
                conn.commit()

            result = promote_match_candidates(db_path)

            with connect_database(db_path) as conn:
                canonical_rows = conn.execute(
                    """
                    select canonical_item_key, title, original_title,
                           content_type, content_granularity, year
                    from canonical_items
                    """
                ).fetchall()
                external_rows = conn.execute(
                    """
                    select e.source, e.external_id, e.external_granularity
                    from external_ids e
                    join canonical_items c on c.id = e.canonical_item_id
                    """
                ).fetchall()
                baseline_rows = conn.execute(
                    """
                    select title, canonical_item_id, match_status, match_confidence
                    from baseline_items
                    order by title
                    """
                ).fetchall()

        self.assertEqual(result.promoted_baseline_items, 2)
        self.assertEqual(result.created_canonical_items, 1)
        self.assertEqual(result.created_external_ids, 1)
        self.assertEqual(
            canonical_rows,
            [
                (
                    "tmdb:tv:73375",
                    "Tom Clancy's Jack Ryan",
                    "Tom Clancy's Jack Ryan",
                    "tv",
                    "series",
                    2018,
                )
            ],
        )
        self.assertEqual(external_rows, [("tmdb", "73375", "series")])
        self.assertEqual(baseline_rows[0][2:], ("matched", "high"))
        self.assertEqual(baseline_rows[1][2:], ("matched", "high"))
        self.assertEqual(baseline_rows[0][1], baseline_rows[1][1])

    def test_ignores_low_and_no_match_candidates(self):
        from movietrace.db.schema import connect_database, initialize_database
        from movietrace.pipeline.canonical_promotion import promote_match_candidates

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "movietrace.db"
            initialize_database(db_path)

            with connect_database(db_path) as conn:
                conn.execute(
                    """
                    insert into baseline_items(title, content_granularity, raw_fields_json)
                    values ('Special Ops Lioness S01', 'season', '{}')
                    """
                )
                baseline_id = conn.execute("select last_insert_rowid()").fetchone()[0]
                conn.execute(
                    """
                    insert into match_candidates(
                        baseline_item_id, source, external_id, title,
                        media_type, year, score, confidence, reason,
                        raw_payload_json
                    )
                    values (?, 'tmdb', '113962', 'Lioness', 'tv', 2023,
                            0.5, 'low', 'title_similarity=0.54', '{}')
                    """,
                    (baseline_id,),
                )
                conn.commit()

            result = promote_match_candidates(db_path)

            with connect_database(db_path) as conn:
                canonical_count = conn.execute(
                    "select count(*) from canonical_items"
                ).fetchone()[0]
                baseline_row = conn.execute(
                    "select canonical_item_id, match_status, match_confidence from baseline_items"
                ).fetchone()

        self.assertEqual(result.promoted_baseline_items, 0)
        self.assertEqual(canonical_count, 0)
        self.assertEqual(baseline_row, (None, "unmatched", None))


if __name__ == "__main__":
    unittest.main()
