from __future__ import annotations

import pytest
from movietrace.pipeline.scoring import (
    compute_flixpatrol_score,
    compute_tmdb_popularity_score,
    compute_trakt_score,
    compute_tmdb_rating_score,
    compute_imdb_rating_score,
    compute_platform_weight_score,
    compute_content_type_score,
    compute_freshness_score,
    compute_language_score,
    compute_hot_score,
    map_priority,
    load_weights_config,
    DEFAULT_WEIGHTS,
)


# ── FlixPatrol score tests ──────────────────────────────────────────────


class TestFlixPatrolScore:
    def test_rank_1_returns_100(self):
        items = [{"ranking": 1, "days_total": 0}]
        assert compute_flixpatrol_score(items) == 100

    def test_rank_10_returns_10(self):
        items = [{"ranking": 10, "days_total": 0}]
        assert compute_flixpatrol_score(items) == 10

    def test_rank_5_returns_60(self):
        items = [{"ranking": 5, "days_total": 0}]
        assert compute_flixpatrol_score(items) == 60

    def test_days_bonus_full_30_days(self):
        items = [{"ranking": 10, "days_total": 30}]
        # rank_score=10 + days_bonus=20 = 30
        assert compute_flixpatrol_score(items) == 30

    def test_days_bonus_capped_at_30(self):
        items = [{"ranking": 10, "days_total": 100}]
        # rank_score=10 + min(100,30)/30*20 = 10 + 20 = 30
        assert compute_flixpatrol_score(items) == 30

    def test_best_rank_across_platforms(self):
        items = [
            {"ranking": 3, "days_total": 0},
            {"ranking": 1, "days_total": 0},
            {"ranking": 5, "days_total": 0},
        ]
        # best rank = 1 → 100
        assert compute_flixpatrol_score(items) == 100

    def test_max_days_across_platforms(self):
        items = [
            {"ranking": 5, "days_total": 5},
            {"ranking": 3, "days_total": 15},
        ]
        # best rank = 3 → 80, max days = 15 → 10 bonus = 90
        assert compute_flixpatrol_score(items) == 90

    def test_empty_items_returns_zero(self):
        assert compute_flixpatrol_score([]) == 0.0

    def test_none_days_total_handled(self):
        items = [{"ranking": 1, "days_total": None}]
        assert compute_flixpatrol_score(items) == 100

    def test_capped_at_100(self):
        items = [{"ranking": 1, "days_total": 60}]
        # rank=100 + days_bonus=20, capped at 100
        assert compute_flixpatrol_score(items) == 100


# ── TMDb popularity tests ──────────────────────────────────────────────


class TestTmdbPopularityScore:
    def test_returns_0_when_no_data(self):
        assert compute_tmdb_popularity_score(None) == 0.0
        assert compute_tmdb_popularity_score({}) == 0.0

    def test_normalizes_popularity(self):
        ext = {"tmdb_popularity": 500}
        assert compute_tmdb_popularity_score(ext) == 50.0

    def test_capped_at_100(self):
        ext = {"tmdb_popularity": 2000}
        assert compute_tmdb_popularity_score(ext) == 100.0


# ── Trakt score tests ──────────────────────────────────────────────────


class TestTraktScore:
    def test_returns_0_when_no_data(self):
        assert compute_trakt_score(None) == 0.0

    def test_normalizes_watchers(self):
        ext = {"trakt_watchers": 2500}
        assert compute_trakt_score(ext) == 50.0


# ── TMDb rating tests ──────────────────────────────────────────────────


class TestTmdbRatingScore:
    def test_returns_0_when_no_data(self):
        assert compute_tmdb_rating_score(None) == 0.0

    def test_high_votes_scales_up(self):
        ext = {"tmdb_vote_average": 8.0, "tmdb_vote_count": 10000}
        score = compute_tmdb_rating_score(ext)
        # raw = 8.0 * log10(10001) ~ 8 * 4 = 32
        # normalized: 32/30 * 100 = ~106.67 → capped at 100
        assert score > 0

    def test_zero_votes(self):
        ext = {"tmdb_vote_average": 7.0, "tmdb_vote_count": 0}
        score = compute_tmdb_rating_score(ext)
        # log10(1) = 0 → raw = 0 → score = 0
        assert score == 0.0


# ── IMDb rating tests ──────────────────────────────────────────────────


class TestImdbRatingScore:
    def test_returns_0_when_no_data(self):
        assert compute_imdb_rating_score(None) == 0.0

    def test_typical_imdb_score(self):
        ext = {"imdb_rating": 8.5, "imdb_votes": 500000}
        score = compute_imdb_rating_score(ext)
        # raw = 8.5 * log10(500001) ~ 8.5 * 5.7 = 48.4
        # normalized: 48.4/40 * 100 = ~121 → capped at 100
        assert score > 0


# ── Platform weight tests ──────────────────────────────────────────────


class TestPlatformWeight:
    def test_netflix_full_weight(self):
        cfg = DEFAULT_WEIGHTS
        assert compute_platform_weight_score("netflix", cfg) == 100.0

    def test_prime_video_full_weight(self):
        cfg = DEFAULT_WEIGHTS
        assert compute_platform_weight_score("prime-video", cfg) == 100.0

    def test_disney_90_percent(self):
        cfg = DEFAULT_WEIGHTS
        assert compute_platform_weight_score("disney-plus", cfg) == 90.0

    def test_hbo_85_percent(self):
        cfg = DEFAULT_WEIGHTS
        assert compute_platform_weight_score("hbo-max", cfg) == 85.0

    def test_apple_80_percent(self):
        cfg = DEFAULT_WEIGHTS
        assert compute_platform_weight_score("apple-tv-plus", cfg) == 80.0

    def test_hulu_80_percent(self):
        cfg = DEFAULT_WEIGHTS
        assert compute_platform_weight_score("hulu", cfg) == 80.0


# ── Content type tests ─────────────────────────────────────────────────


class TestContentType:
    def test_tv_show_100(self):
        assert compute_content_type_score("tv_show") == 100.0

    def test_movie_80(self):
        assert compute_content_type_score("movie") == 80.0


# ── Freshness tests ────────────────────────────────────────────────────


class TestFreshness:
    def test_recent_release_100(self):
        from datetime import date, timedelta
        recent = (date.today() - timedelta(days=30)).isoformat()
        assert compute_freshness_score(recent, DEFAULT_WEIGHTS) == 100.0

    def test_half_score_at_120_days(self):
        from datetime import date, timedelta
        half_date = (date.today() - timedelta(days=120)).isoformat()
        assert compute_freshness_score(half_date, DEFAULT_WEIGHTS) == 50.0

    def test_old_release_0(self):
        from datetime import date, timedelta
        old = (date.today() - timedelta(days=365)).isoformat()
        assert compute_freshness_score(old, DEFAULT_WEIGHTS) == 0.0

    def test_null_date_returns_0(self):
        assert compute_freshness_score(None, DEFAULT_WEIGHTS) == 0.0

    def test_boundary_at_90_days(self):
        from datetime import date, timedelta
        boundary = (date.today() - timedelta(days=90)).isoformat()
        assert compute_freshness_score(boundary, DEFAULT_WEIGHTS) == 100.0

    def test_boundary_at_180_days(self):
        from datetime import date, timedelta
        boundary = (date.today() - timedelta(days=180)).isoformat()
        assert compute_freshness_score(boundary, DEFAULT_WEIGHTS) == 50.0


# ── Language tests ─────────────────────────────────────────────────────


class TestLanguage:
    def test_english_100(self):
        assert compute_language_score("en", None) == 100.0

    def test_english_variants(self):
        assert compute_language_score("english", None) == 100.0
        assert compute_language_score("EN", None) == 100.0

    def test_non_english_high_fp_ranking_returns_80(self):
        assert compute_language_score("ja", 3) == 80.0

    def test_non_english_low_fp_ranking_returns_50(self):
        assert compute_language_score("ja", 8) == 50.0

    def test_null_language_score_50(self):
        assert compute_language_score(None, None) == 50.0


# ── compute_hot_score tests ────────────────────────────────────────────


class TestComputeHotScore:
    def test_deterministic_result(self):
        candidate = {
            "fp_items": [{"ranking": 1, "days_total": 0, "platform": "netflix"}],
            "content_type": "movie",
            "platform": "netflix",
            "release_date": None,
            "language": "en",
            "ext_data": None,
        }
        score1, _ = compute_hot_score(candidate, DEFAULT_WEIGHTS)
        score2, _ = compute_hot_score(candidate, DEFAULT_WEIGHTS)
        assert score1 == score2

    def test_breakdown_has_all_9_fields(self):
        candidate = {
            "fp_items": [{"ranking": 1, "days_total": 0, "platform": "netflix"}],
            "content_type": "movie",
            "platform": "netflix",
            "release_date": None,
            "language": "en",
            "ext_data": None,
        }
        _, breakdown = compute_hot_score(candidate, DEFAULT_WEIGHTS)
        expected_keys = {
            "flixpatrol_score", "tmdb_popularity_score",
            "trakt_score", "tmdb_rating_score", "imdb_rating_score",
            "platform_weight_score", "content_type_score",
            "freshness_score", "language_score",
        }
        assert set(breakdown.keys()) == expected_keys

    def test_top_ranked_netflix_movie_gets_high_score(self):
        candidate = {
            "fp_items": [{"ranking": 1, "days_total": 10, "platform": "netflix"}],
            "content_type": "movie",
            "platform": "netflix",
            "release_date": None,
            "language": "en",
            "ext_data": None,
            "ranking": 1,
        }
        score, _ = compute_hot_score(candidate, DEFAULT_WEIGHTS)
        # FP: 100 + 10/30*20 ≈ 106.7 → 100, plat:100, content:80, lang:100
        # = 100*0.30 + 100*0.10 + 80*0.05 + 100*0.05 = 30+10+4+5 = 49
        assert 45 <= score <= 55

    def test_empty_fp_items_returns_low_score(self):
        candidate = {
            "fp_items": [],
            "content_type": "movie",
            "platform": "hulu",
            "release_date": None,
            "language": None,
            "ext_data": None,
        }
        score, breakdown = compute_hot_score(candidate, DEFAULT_WEIGHTS)
        # FP:0, plat:80, content:80, lang:50
        # = 0 + 8 + 4 + 2.5 = 14.5
        assert score < 20
        assert breakdown["flixpatrol_score"] == 0.0

    def test_ext_data_factors_add_to_score(self):
        candidate = {
            "fp_items": [{"ranking": 1, "days_total": 0, "platform": "netflix"}],
            "content_type": "tv_show",
            "platform": "netflix",
            "release_date": None,
            "language": "en",
            "ext_data": {
                "tmdb_popularity": 1000,
                "trakt_watchers": 5000,
                "tmdb_vote_average": 8.5,
                "tmdb_vote_count": 50000,
                "imdb_rating": 9.0,
                "imdb_votes": 1000000,
            },
            "ranking": 1,
        }
        score, _ = compute_hot_score(candidate, DEFAULT_WEIGHTS)
        # Should be very high with all signals
        assert score >= 80


# ── map_priority tests ─────────────────────────────────────────────────


class TestMapPriority:
    def test_p0_at_85(self):
        assert map_priority(85, {"P0": 85, "P1": 70, "P2": 50}) == "P0"

    def test_p0_at_100(self):
        assert map_priority(100) == "P0"

    def test_p1_at_84(self):
        assert map_priority(84) == "P1"

    def test_p1_at_70(self):
        assert map_priority(70) == "P1"

    def test_p2_at_69(self):
        assert map_priority(69) == "P2"

    def test_p2_at_50(self):
        assert map_priority(50) == "P2"

    def test_p3_at_49(self):
        assert map_priority(49) == "P3"

    def test_p3_at_0(self):
        assert map_priority(0) == "P3"
