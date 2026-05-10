"""单元测试：SUP-C 匹配逻辑（无网络调用）"""
from __future__ import annotations
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

from sup_c_flixpatrol_matching import (
    _classify_confidence,
    _deduplicate_flixpatrol_items,
    _select_best_tmdb_result,
)
from movietrace.pipeline.entity_matching import ExternalSearchResult


def _make_result(title: str, year: int | None = None, score: float = 1.0) -> ExternalSearchResult:
    return ExternalSearchResult(
        source="tmdb",
        external_id="123",
        title=title,
        media_type="movie",
        year=year,
        score=score,
    )


# ── _classify_confidence ─────────────────────────────────────────────────────

def test_high_confidence_above_85():
    assert _classify_confidence(0.90, None, None) == "high"

def test_medium_confidence_60_to_85():
    assert _classify_confidence(0.70, None, None) == "medium"

def test_low_confidence_40_to_60():
    assert _classify_confidence(0.50, None, None) == "low"

def test_no_match_below_40():
    assert _classify_confidence(0.30, None, None) == "no_match"

def test_year_match_upgrades_medium_to_high():
    assert _classify_confidence(0.70, 2024, 2024) == "high"

def test_year_match_upgrades_low_to_medium():
    assert _classify_confidence(0.50, 2023, 2024) == "medium"  # 相差1年也算

def test_year_mismatch_does_not_upgrade():
    assert _classify_confidence(0.70, 2020, 2024) == "medium"  # 相差4年，不升档

def test_missing_year_does_not_upgrade():
    assert _classify_confidence(0.70, None, 2024) == "medium"


# ── _deduplicate_flixpatrol_items ────────────────────────────────────────────

def test_dedup_merges_same_title_different_platforms():
    items = [
        {"title": "Swapped", "content_type": "movie", "platform": "netflix", "region": "global"},
        {"title": "Swapped", "content_type": "movie", "platform": "netflix", "region": "us"},
    ]
    deduped = _deduplicate_flixpatrol_items(items)
    assert len(deduped) == 1
    assert set(deduped[0]["platforms"]) == {"netflix"}

def test_dedup_keeps_different_titles_separate():
    items = [
        {"title": "Swapped", "content_type": "movie", "platform": "netflix", "region": "global"},
        {"title": "Apex",    "content_type": "movie", "platform": "netflix", "region": "global"},
    ]
    deduped = _deduplicate_flixpatrol_items(items)
    assert len(deduped) == 2

def test_dedup_collects_all_platforms():
    items = [
        {"title": "Send Help", "content_type": "movie", "platform": "disney",  "region": "world"},
        {"title": "Send Help", "content_type": "movie", "platform": "hulu",    "region": "us"},
    ]
    deduped = _deduplicate_flixpatrol_items(items)
    assert len(deduped) == 1
    assert set(deduped[0]["platforms"]) == {"disney", "hulu"}


# ── _select_best_tmdb_result ─────────────────────────────────────────────────

def test_select_best_picks_highest_similarity():
    results = [
        _make_result("Swapped", year=2024),
        _make_result("The Swap", year=2024),
    ]
    best, sim = _select_best_tmdb_result("Swapped", results)
    assert best.title == "Swapped"
    assert sim >= 0.99

def test_select_best_returns_none_on_empty():
    best, sim = _select_best_tmdb_result("Anything", [])
    assert best is None
    assert sim == 0.0

def test_select_best_exact_match_similarity_is_1():
    results = [_make_result("Squid Game")]
    best, sim = _select_best_tmdb_result("Squid Game", results)
    assert sim == 1.0
