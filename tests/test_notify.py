"""Tests for feishu/notify.py — P1.37: _build_card progress section."""
from __future__ import annotations

import pytest

from movietrace.feishu.notify import _build_card


class TestBuildCardProgressSection:
    """P1.37: _build_card must include a progress section in elements."""

    def _make_discover_stats(self, **overrides) -> dict:
        base = {
            "source_status": {
                "flixpatrol": {"status": "fallback", "snapshot_date": "2026-05-13"},
                "tmdb": {"status": "fresh", "snapshot_date": "2026-05-20"},
                "trakt": {"status": "fresh", "snapshot_date": "2026-05-20"},
            },
            "tmdb_fetched": 60,
            "trakt_fetched": 40,
            "flixpatrol_fetched": 0,
            "total_merged": 165,
            "total_passed": 98,
            "written": 98,
            "priority": {"P0": 2, "P1": 5, "P2": 91},
            "enrich_imdb_backfill": {"backfilled": 20, "total": 165, "errors": []},
            "enrich_omdb": {"enriched": 143, "api_calls": 17, "cache_hits": 138, "errors": 0},
            "enrich_tmdb_detail": {"enriched": 136, "api_calls": 2, "cache_hits": 134, "errors": 0},
        }
        base.update(overrides)
        return base

    def test_progress_section_present_in_elements(self):
        """Card elements must contain a section with '运行进度' heading."""
        card = _build_card(
            run_date="2026-05-20",
            discover_stats=self._make_discover_stats(),
            sync_stats={"total": 98, "created": 3, "updated": 95, "errors": 0},
            top_items=[],
        )
        elements = card["elements"]
        # Find a div element whose text content contains '运行进度'
        prog_elements = [
            el for el in elements
            if el.get("tag") == "div"
            and "运行进度" in (el.get("text", {}).get("content", ""))
        ]
        assert prog_elements, "Expected a '运行进度' section in card elements"

    def test_progress_section_contains_step_lines(self):
        """Progress section must contain [1/8] through [8/8] step lines."""
        card = _build_card(
            run_date="2026-05-20",
            discover_stats=self._make_discover_stats(),
            sync_stats={"total": 98, "created": 3, "updated": 95, "errors": 0},
            top_items=[],
        )
        elements = card["elements"]
        prog_content = ""
        for el in elements:
            if el.get("tag") == "div":
                content = el.get("text", {}).get("content", "")
                if "运行进度" in content:
                    prog_content = content
                    break

        assert "[1/8]" in prog_content
        assert "[2/8]" in prog_content
        assert "[3/8]" in prog_content
        assert "[5/8]" in prog_content
        assert "[6/8]" in prog_content
        assert "[8/8]" in prog_content

    def test_progress_section_shows_fallback_tag(self):
        """If source is fallback, progress section should show ⚠️ and cache date."""
        stats = self._make_discover_stats()
        card = _build_card(
            run_date="2026-05-20",
            discover_stats=stats,
            sync_stats={},
            top_items=[],
        )
        elements = card["elements"]
        prog_content = ""
        for el in elements:
            if el.get("tag") == "div":
                content = el.get("text", {}).get("content", "")
                if "运行进度" in content:
                    prog_content = content
                    break
        # FP is set to fallback with date 2026-05-13
        assert "2026-05-13" in prog_content
        assert "⚠️" in prog_content

    def test_progress_section_enrichment_counts(self):
        """Progress section [6/8] line shows IMDb/OMDb/TMDb enrichment counts."""
        stats = self._make_discover_stats()
        card = _build_card(
            run_date="2026-05-20",
            discover_stats=stats,
            sync_stats={},
            top_items=[],
        )
        elements = card["elements"]
        prog_content = ""
        for el in elements:
            if el.get("tag") == "div":
                content = el.get("text", {}).get("content", "")
                if "运行进度" in content:
                    prog_content = content
                    break
        assert "20/165" in prog_content   # IMDb backfilled/total
        assert "143/165" in prog_content  # OMDb enriched/total_merged
        assert "136/165" in prog_content  # TMDb detail enriched/total_merged

    def test_build_card_without_enrichment_fields(self):
        """_build_card must not crash when enrichment fields are absent (backward compat)."""
        minimal_stats = {
            "source_status": {},
            "total_merged": 50,
            "total_passed": 20,
            "written": 20,
            "priority": {"P0": 0, "P1": 2, "P2": 18},
        }
        card = _build_card(
            run_date="2026-05-20",
            discover_stats=minimal_stats,
            sync_stats={"errors": 0},
            top_items=[],
        )
        assert "elements" in card
