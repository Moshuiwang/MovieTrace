"""Tests for FlixPatrol HTML parser (SUP-B).

All tests use fixture HTML files — no network calls.
"""
from __future__ import annotations

import pathlib

import pytest

from movietrace.sources.flixpatrol import parse_top10_page

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "flixpatrol"

FIXTURE_FILES = [
    ("netflix_global.html",      "netflix",      "global"),
    ("netflix_us.html",          "netflix",      "us"),
    ("amazon_prime_world.html",  "amazon-prime", "world"),
    ("disney_world.html",        "disney",       "world"),
    ("apple_tv_world.html",      "apple-tv",     "world"),
    ("hulu_us.html",             "hulu",         "us"),
]


def _load(filename: str) -> str:
    return (FIXTURES / filename).read_text(encoding="utf-8", errors="replace")


# ── Basic parsing (Netflix Global, Format A) ─────────────────────────────────

def test_netflix_global_returns_20_items():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    assert len(items) == 20, f"Expected 20 (10 movies + 10 shows), got {len(items)}"


def test_netflix_global_rank1_movie_is_swapped():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    movies = [i for i in items if i["content_type"] == "movie"]
    rank1 = next((i for i in movies if i["rank"] == 1), None)
    assert rank1 is not None
    assert rank1["title"] == "Swapped"


def test_netflix_global_has_10_movies_and_10_shows():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    assert sum(1 for i in items if i["content_type"] == "movie") == 10
    assert sum(1 for i in items if i["content_type"] == "show") == 10


def test_netflix_global_movie_ranks_are_1_to_10():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    ranks = sorted(i["rank"] for i in items if i["content_type"] == "movie")
    assert ranks == list(range(1, 11))


def test_netflix_global_platform_field():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    assert all(i["platform"] == "netflix" for i in items)


def test_netflix_global_region_field():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    assert all(i["region"] == "global" for i in items)


def test_netflix_global_week_date():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    assert items[0]["week_date"] == "2026-05-10"


def test_netflix_global_points_are_ints():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    for item in items:
        assert isinstance(item["points"], int), f"points should be int, got {type(item['points'])}"


def test_netflix_global_days_in_top10_is_none():
    # Format A pages have no days_in_top10 column
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    assert all(i["days_in_top10"] is None for i in items)


# ── Format B (regional pages with days_in_top10) ──────────────────────────────

def test_netflix_us_returns_20_items():
    items = parse_top10_page(_load("netflix_us.html"), "netflix", "us")
    assert len(items) == 20


def test_netflix_us_rank1_movie_is_swapped():
    items = parse_top10_page(_load("netflix_us.html"), "netflix", "us")
    movies = [i for i in items if i["content_type"] == "movie"]
    rank1 = next((i for i in movies if i["rank"] == 1), None)
    assert rank1 is not None
    assert rank1["title"] == "Swapped"


def test_netflix_us_days_in_top10_are_ints():
    items = parse_top10_page(_load("netflix_us.html"), "netflix", "us")
    for item in items:
        assert isinstance(item["days_in_top10"], int), (
            f"days_in_top10 should be int for regional page, got {item['days_in_top10']!r} "
            f"for '{item['title']}'"
        )


def test_netflix_us_points_are_none():
    # Format B pages have no points column
    items = parse_top10_page(_load("netflix_us.html"), "netflix", "us")
    assert all(i["points"] is None for i in items)


def test_hulu_us_rank1_movie():
    items = parse_top10_page(_load("hulu_us.html"), "hulu", "us")
    movies = [i for i in items if i["content_type"] == "movie"]
    rank1 = next((i for i in movies if i["rank"] == 1), None)
    assert rank1 is not None
    assert rank1["title"] == "Send Help"


def test_hulu_us_overall_table_is_skipped():
    # "TOP 10 Overall" table must be excluded; only Movies and TV Shows included
    items = parse_top10_page(_load("hulu_us.html"), "hulu", "us")
    movies = [i for i in items if i["content_type"] == "movie"]
    shows  = [i for i in items if i["content_type"] == "show"]
    assert len(movies) > 0
    assert len(shows) > 0
    # No item should lack a content_type
    assert all(i["content_type"] in ("movie", "show") for i in items)


# ── Error handling ────────────────────────────────────────────────────────────

def test_empty_html_returns_empty_list():
    assert parse_top10_page("<html><body></body></html>", "netflix", "global") == []


def test_invalid_html_returns_empty_list():
    assert parse_top10_page("not html at all !!!!", "netflix", "global") == []


# ── Cross-platform parametrized tests ────────────────────────────────────────

@pytest.mark.parametrize("filename,platform,region", FIXTURE_FILES)
def test_all_fixtures_return_items(filename, platform, region):
    items = parse_top10_page(_load(filename), platform, region)
    assert len(items) >= 10, f"{filename}: expected ≥10 items, got {len(items)}"


@pytest.mark.parametrize("filename,platform,region", FIXTURE_FILES)
def test_all_fixtures_platform_field(filename, platform, region):
    items = parse_top10_page(_load(filename), platform, region)
    wrong = [i for i in items if i["platform"] != platform]
    assert not wrong, f"{filename}: {len(wrong)} items have wrong platform"


@pytest.mark.parametrize("filename,platform,region", FIXTURE_FILES)
def test_all_fixtures_region_field(filename, platform, region):
    items = parse_top10_page(_load(filename), platform, region)
    wrong = [i for i in items if i["region"] != region]
    assert not wrong, f"{filename}: {len(wrong)} items have wrong region"


@pytest.mark.parametrize("filename,platform,region", FIXTURE_FILES)
def test_all_fixtures_required_fields_present(filename, platform, region):
    items = parse_top10_page(_load(filename), platform, region)
    required = {"rank", "title", "platform", "region", "content_type",
                "points", "week_date", "days_in_top10"}
    for item in items:
        missing = required - set(item.keys())
        assert not missing, f"{filename}: item missing fields {missing}"


@pytest.mark.parametrize("filename,platform,region", FIXTURE_FILES)
def test_all_fixtures_titles_are_nonempty_strings(filename, platform, region):
    items = parse_top10_page(_load(filename), platform, region)
    bad = [i for i in items if not isinstance(i["title"], str) or not i["title"]]
    assert not bad, f"{filename}: {len(bad)} items have empty/invalid title"


# ── Extraction rate ───────────────────────────────────────────────────────────

def test_basic_field_extraction_rate_above_95_percent():
    """rank, title, content_type must be non-None in ≥95% of all items across all fixtures."""
    basic_fields = ["rank", "title", "content_type"]
    total = populated = 0
    for filename, platform, region in FIXTURE_FILES:
        for item in parse_top10_page(_load(filename), platform, region):
            for field in basic_fields:
                total += 1
                if item.get(field) is not None:
                    populated += 1
    rate = populated / total if total > 0 else 0
    assert rate >= 0.95, f"Basic field extraction rate {rate:.1%} < 95% ({populated}/{total})"
