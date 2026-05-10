import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class SourceClientsTest(unittest.TestCase):
    def test_parse_tmdb_search_results_keeps_movie_and_tv(self):
        from movietrace.sources.tmdb import parse_tmdb_search_results

        results = parse_tmdb_search_results(
            {
                "results": [
                    {
                        "id": 125988,
                        "media_type": "tv",
                        "name": "Silo",
                        "first_air_date": "2023-05-04",
                    },
                    {
                        "id": 603692,
                        "media_type": "movie",
                        "title": "John Wick: Chapter 4",
                        "release_date": "2023-03-22",
                    },
                    {"id": 1, "media_type": "person", "name": "Someone"},
                ]
            }
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].external_id, "125988")
        self.assertEqual(results[0].title, "Silo")
        self.assertEqual(results[0].media_type, "tv")
        self.assertEqual(results[0].year, 2023)
        self.assertEqual(results[1].media_type, "movie")

    def test_parse_tmdb_search_results_retains_original_titles(self):
        from movietrace.sources.tmdb import parse_tmdb_search_results

        results = parse_tmdb_search_results(
            {
                "results": [
                    {
                        "id": 71446,
                        "media_type": "tv",
                        "name": "Money Heist",
                        "original_name": "La casa de papel",
                        "first_air_date": "2017-05-02",
                    },
                    {
                        "id": 764541,
                        "media_type": "movie",
                        "title": "River of Desire",
                        "original_title": "O Rio do Desejo",
                        "release_date": "2023-03-23",
                    },
                ]
            }
        )

        self.assertEqual(results[0].raw_payload["original_name"], "La casa de papel")
        self.assertEqual(results[1].raw_payload["original_title"], "O Rio do Desejo")

    def test_parse_omdb_detail_result_maps_rating_votes_and_series(self):
        from movietrace.sources.omdb import parse_omdb_detail_result

        result = parse_omdb_detail_result(
            {
                "Response": "True",
                "Title": "Money Heist",
                "Year": "2017–2021",
                "imdbID": "tt6468322",
                "Type": "series",
                "totalSeasons": "5",
                "imdbRating": "8.2",
                "imdbVotes": "604,616",
            }
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.external_id, "tt6468322")
        self.assertEqual(result.title, "Money Heist")
        self.assertEqual(result.media_type, "tv")
        self.assertEqual(result.year, 2017)
        self.assertEqual(result.raw_payload["totalSeasons"], "5")
        self.assertEqual(result.raw_payload["imdbRating"], "8.2")
        self.assertEqual(result.raw_payload["imdbVotes"], "604,616")

    def test_parse_omdb_detail_result_returns_none_for_no_match(self):
        from movietrace.sources.omdb import parse_omdb_detail_result

        result = parse_omdb_detail_result(
            {"Response": "False", "Error": "Movie not found!"}
        )

        self.assertIsNone(result)

    def test_parse_trakt_search_results_maps_show_and_movie_ids(self):
        from movietrace.sources.trakt import parse_trakt_search_results

        results = parse_trakt_search_results(
            [
                {
                    "type": "show",
                    "score": 99.0,
                    "show": {
                        "title": "Silo",
                        "year": 2023,
                        "ids": {"trakt": 170695, "tmdb": 125988, "imdb": "tt14688458"},
                    },
                },
                {
                    "type": "movie",
                    "score": 80.0,
                    "movie": {
                        "title": "Narappa",
                        "year": 2021,
                        "ids": {"trakt": 620685, "tmdb": 666564},
                    },
                },
            ]
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].source, "trakt")
        self.assertEqual(results[0].external_id, "170695")
        self.assertEqual(results[0].media_type, "tv")
        self.assertEqual(results[0].raw_payload["ids"]["tmdb"], 125988)
        self.assertEqual(results[1].media_type, "movie")


if __name__ == "__main__":
    unittest.main()
