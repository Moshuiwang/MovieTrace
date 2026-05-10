import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class EntityMatchingTest(unittest.TestCase):
    def test_choose_best_match_uses_tmdb_original_name(self):
        from movietrace.pipeline.entity_matching import (
            BaselineItem,
            ExternalSearchResult,
            choose_best_match,
            parse_title,
        )

        item = BaselineItem(
            214, "La casa de papel S01", None, "season", None, None, None, None
        )
        decision = choose_best_match(
            item,
            parse_title(item.title),
            [
                ExternalSearchResult(
                    source="tmdb",
                    external_id="71446",
                    title="Money Heist",
                    media_type="tv",
                    year=2017,
                    score=26.4,
                    raw_payload={"original_name": "La casa de papel"},
                ),
                ExternalSearchResult(
                    source="tmdb",
                    external_id="308014",
                    title="Berlin and the Lady with an Ermine",
                    media_type="tv",
                    year=2026,
                    score=6.7,
                    raw_payload={"original_name": "Berlín y la dama del armiño"},
                ),
            ],
        )

        self.assertEqual(decision.result.external_id, "71446")
        self.assertEqual(decision.confidence, "high")
        self.assertIn("matched_field=original_name", decision.reason)

    def test_choose_best_match_uses_tmdb_original_title_for_movie(self):
        from movietrace.pipeline.entity_matching import (
            BaselineItem,
            ExternalSearchResult,
            choose_best_match,
            parse_title,
        )

        item = BaselineItem(
            344, "O Rio do DESEJO", None, None, None, None, None, None
        )
        decision = choose_best_match(
            item,
            parse_title(item.title),
            [
                ExternalSearchResult(
                    source="tmdb",
                    external_id="764541",
                    title="River of Desire",
                    media_type="movie",
                    year=2023,
                    score=1.0,
                    raw_payload={"original_title": "O Rio do Desejo"},
                )
            ],
        )

        self.assertEqual(decision.result.external_id, "764541")
        self.assertEqual(decision.confidence, "high")
        self.assertIn("matched_field=original_title", decision.reason)

    def test_choose_best_match_allows_author_prefix_core_title(self):
        from movietrace.pipeline.entity_matching import (
            BaselineItem,
            ExternalSearchResult,
            choose_best_match,
            parse_title,
        )

        item = BaselineItem(
            210, "Jack Ryan S01", None, "season", None, None, None, None
        )
        decision = choose_best_match(
            item,
            parse_title(item.title),
            [
                ExternalSearchResult(
                    source="tmdb",
                    external_id="73375",
                    title="Tom Clancy's Jack Ryan",
                    media_type="tv",
                    year=2018,
                    score=12.0,
                    raw_payload={},
                )
            ],
        )

        self.assertEqual(decision.result.external_id, "73375")
        self.assertNotEqual(decision.confidence, "low")
        self.assertIn("core_title_matches", decision.reason)

    def test_parse_title_removes_known_noise_terms_but_records_warning(self):
        from movietrace.pipeline.entity_matching import parse_title

        parsed = parse_title("Wedding Plan S01 interview")

        self.assertEqual(parsed.query, "Wedding Plan")
        self.assertEqual(parsed.season_number, 1)
        self.assertEqual(parsed.removed_noise_terms, ("interview",))

    def test_parse_title_decodes_url_encoded_title(self):
        from movietrace.pipeline.entity_matching import parse_title

        parsed = parse_title("Love%2C Death %26 Robots S01")

        self.assertEqual(parsed.query, "Love, Death & Robots")
        self.assertEqual(parsed.season_number, 1)
        self.assertTrue(parsed.decoded_url_encoding)

    def test_cross_source_agreement_promotes_medium_tmdb_to_high(self):
        from movietrace.pipeline.entity_matching import (
            BaselineItem,
            ExternalSearchResult,
            choose_best_match,
            parse_title,
        )

        item = BaselineItem(
            413, "sitting in bars with cake S01", None, "season", None, None, None, None
        )
        decision = choose_best_match(
            item,
            parse_title(item.title),
            [
                ExternalSearchResult(
                    source="tmdb",
                    external_id="936952",
                    title="Sitting in Bars with Cake",
                    media_type="movie",
                    year=2023,
                    score=1.0,
                    raw_payload={},
                ),
                ExternalSearchResult(
                    source="omdb",
                    external_id="tt8452344",
                    title="Sitting in Bars with Cake",
                    media_type="movie",
                    year=2023,
                    score=1.0,
                    raw_payload={"imdbID": "tt8452344"},
                ),
            ],
        )

        self.assertEqual(decision.result.source, "tmdb")
        self.assertEqual(decision.result.external_id, "936952")
        self.assertEqual(decision.confidence, "high")
        self.assertIn("cross_source=tmdb_omdb_consistent", decision.reason)
        self.assertIn("data_quality_warning=season_title_matched_movie", decision.reason)

    def test_cross_source_conflict_keeps_candidate_for_human_review(self):
        from movietrace.pipeline.entity_matching import (
            BaselineItem,
            ExternalSearchResult,
            choose_best_match,
            parse_title,
        )

        item = BaselineItem(
            481,
            "Bleach Thousand Year Blood War S01",
            None,
            "season",
            None,
            None,
            None,
            None,
        )
        decision = choose_best_match(
            item,
            parse_title(item.title),
            [
                ExternalSearchResult(
                    source="tmdb",
                    external_id="1669841",
                    title="Bleach: Thousand-Year Blood War - The Calamity",
                    media_type="movie",
                    year=2026,
                    score=1.0,
                    raw_payload={},
                ),
                ExternalSearchResult(
                    source="omdb",
                    external_id="tt14986406",
                    title="Bleach: Thousand-Year Blood War",
                    media_type="tv",
                    year=2022,
                    score=1.0,
                    raw_payload={"imdbID": "tt14986406"},
                ),
            ],
        )

        self.assertEqual(decision.confidence, "medium")
        self.assertIn("cross_source=tmdb_omdb_conflict", decision.reason)
        self.assertIn("tmdb=Bleach: Thousand-Year Blood War - The Calamity", decision.reason)
        self.assertIn("omdb=Bleach: Thousand-Year Blood War", decision.reason)

    def test_same_title_tv_candidates_prefer_newer_version_without_local_year(self):
        from movietrace.pipeline.entity_matching import (
            BaselineItem,
            ExternalSearchResult,
            choose_best_match,
            parse_title,
        )

        item = BaselineItem(
            219, "Lost in Space S01", None, "season", None, None, None, None
        )
        decision = choose_best_match(
            item,
            parse_title(item.title),
            [
                ExternalSearchResult(
                    source="tmdb",
                    external_id="3051",
                    title="Lost in Space",
                    media_type="tv",
                    year=1965,
                    score=23.8,
                    raw_payload={},
                ),
                ExternalSearchResult(
                    source="tmdb",
                    external_id="75758",
                    title="Lost in Space",
                    media_type="tv",
                    year=2018,
                    score=14.8,
                    raw_payload={},
                ),
                ExternalSearchResult(
                    source="omdb",
                    external_id="tt5232792",
                    title="Lost in Space",
                    media_type="tv",
                    year=2018,
                    score=1.0,
                    raw_payload={},
                ),
            ],
        )

        self.assertEqual(decision.result.external_id, "75758")
        self.assertEqual(decision.confidence, "high")
        self.assertIn("version_disambiguation=newer_entity_preferred", decision.reason)

    def test_explicit_local_year_overrides_newer_version_preference(self):
        from movietrace.pipeline.entity_matching import (
            BaselineItem,
            ExternalSearchResult,
            choose_best_match,
            parse_title,
        )

        item = BaselineItem(
            999, "Lost in Space 1965 S01", None, "season", None, None, None, None
        )
        decision = choose_best_match(
            item,
            parse_title(item.title),
            [
                ExternalSearchResult(
                    source="tmdb",
                    external_id="3051",
                    title="Lost in Space",
                    media_type="tv",
                    year=1965,
                    score=1.0,
                    raw_payload={},
                ),
                ExternalSearchResult(
                    source="tmdb",
                    external_id="75758",
                    title="Lost in Space",
                    media_type="tv",
                    year=2018,
                    score=1.0,
                    raw_payload={},
                ),
            ],
        )

        self.assertEqual(decision.result.external_id, "3051")
        self.assertIn("year_matches", decision.reason)

    def test_match_baseline_items_writes_candidates_and_report(self):
        from movietrace.db.schema import connect_database, initialize_database
        from movietrace.pipeline.entity_matching import (
            ExternalSearchResult,
            match_baseline_items,
        )

        class FakeSearcher:
            def search(self, query, baseline_item):
                if query == "Silo":
                    return [
                        ExternalSearchResult(
                            source="tmdb",
                            external_id="125988",
                            title="Silo",
                            media_type="tv",
                            year=2023,
                            score=1.0,
                            raw_payload={"id": 125988},
                        )
                    ]
                return [
                    ExternalSearchResult(
                        source="tmdb",
                        external_id="999",
                        title="Wrong Turn",
                        media_type="movie",
                        year=2003,
                        score=0.42,
                        raw_payload={"id": 999},
                    )
                ]

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "movietrace.db"
            report_path = Path(tmpdir) / "full_entity_matching_report.md"
            initialize_database(db_path)

            with connect_database(db_path) as conn:
                conn.execute(
                    """
                    insert into baseline_items(title, content_granularity, raw_fields_json)
                    values ('Silo S01', 'season', '{}')
                    """
                )
                conn.execute(
                    """
                    insert into baseline_items(title, content_granularity, raw_fields_json)
                    values ('Ambiguous Title', 'unknown', '{}')
                    """
                )
                conn.commit()

            result = match_baseline_items(db_path, FakeSearcher(), report_path)

            with connect_database(db_path) as conn:
                rows = conn.execute(
                    """
                    select b.title, m.source, m.external_id, m.title, m.confidence
                    from match_candidates m
                    join baseline_items b on b.id = m.baseline_item_id
                    order by b.title
                    """
                ).fetchall()

            report = report_path.read_text(encoding="utf-8")

        self.assertEqual(result.total_items, 2)
        self.assertEqual(result.confidence_counts["high"], 1)
        self.assertEqual(result.confidence_counts["low"], 1)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1], ("Silo S01", "tmdb", "125988", "Silo", "high"))
        self.assertIn("# MovieTrace 全量实体匹配报告", report)
        self.assertIn("| high | 1 | 50.0% |", report)
        self.assertIn("Ambiguous Title", report)

    def test_match_baseline_items_reports_removed_noise_terms(self):
        from movietrace.db.schema import connect_database, initialize_database
        from movietrace.pipeline.entity_matching import (
            ExternalSearchResult,
            match_baseline_items,
        )

        class FakeSearcher:
            def search(self, query, baseline_item):
                self.last_query = query
                return [
                    ExternalSearchResult(
                        source="tmdb",
                        external_id="229242",
                        title="Wedding Plan",
                        media_type="tv",
                        year=2023,
                        score=4.7,
                        raw_payload={"id": 229242},
                    )
                ]

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "movietrace.db"
            report_path = Path(tmpdir) / "full_entity_matching_report.md"
            searcher = FakeSearcher()
            initialize_database(db_path)

            with connect_database(db_path) as conn:
                conn.execute(
                    """
                    insert into baseline_items(title, content_granularity, raw_fields_json)
                    values ('Wedding Plan S01 interview', 'season', '{}')
                    """
                )
                conn.commit()

            match_baseline_items(db_path, searcher, report_path)

            with connect_database(db_path) as conn:
                row = conn.execute(
                    "select external_id, confidence, reason from match_candidates"
                ).fetchone()

        self.assertEqual(searcher.last_query, "Wedding Plan")
        self.assertEqual(row[0], "229242")
        self.assertEqual(row[1], "high")
        self.assertIn("removed_noise_terms=interview", row[2])

    def test_report_separates_tmdb_and_imdb_ids_from_difference(self):
        from movietrace.db.schema import connect_database, initialize_database
        from movietrace.pipeline.entity_matching import (
            ExternalSearchResult,
            match_baseline_items,
        )

        class FakeSearcher:
            def search(self, query, baseline_item):
                return [
                    ExternalSearchResult(
                        source="tmdb",
                        external_id="936952",
                        title="Sitting in Bars with Cake",
                        media_type="movie",
                        year=2023,
                        score=1.0,
                        raw_payload={},
                    ),
                    ExternalSearchResult(
                        source="omdb",
                        external_id="tt8452344",
                        title="Sitting in Bars with Cake",
                        media_type="movie",
                        year=2023,
                        score=1.0,
                        raw_payload={},
                    ),
                ]

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "movietrace.db"
            report_path = Path(tmpdir) / "full_entity_matching_report.md"
            initialize_database(db_path)

            with connect_database(db_path) as conn:
                conn.execute(
                    """
                    insert into baseline_items(title, content_granularity, raw_fields_json)
                    values ('sitting in bars with cake S01', 'season', '{}')
                    """
                )
                conn.commit()

            match_baseline_items(db_path, FakeSearcher(), report_path)
            report = report_path.read_text(encoding="utf-8")

        self.assertIn("## 3. TMDB / OMDb 全量建议与差异", report)
        self.assertIn("TMDB ID 与 IMDb ID 属于不同编号体系，不参与冲突判断。", report)
        self.assertIn("TMDB ID | IMDb ID", report)
        self.assertIn("936952 | tt8452344", report)
        self.assertIn("compatible", report)


if __name__ == "__main__":
    unittest.main()
