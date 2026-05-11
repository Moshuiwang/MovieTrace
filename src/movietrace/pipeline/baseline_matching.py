from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Any

from movietrace.db.schema import connect_database
from movietrace.pipeline.entity_matching import parse_title

logger = logging.getLogger("movietrace.pipeline.baseline_matching")


def run_baseline_matching(
    db_path: str = "data/movietrace.db",
) -> dict[str, Any]:
    """Match candidates against baseline_items and write to candidate_matches.

    Returns stats dict with confidence distribution.
    """
    conn = connect_database(db_path)
    try:
        candidates = _load_candidates(conn)
        baseline = _load_baseline_items(conn)

        if not candidates:
            logger.warning("No candidates found")
            return {"error": "no_candidates", "total": 0}

        if not baseline:
            logger.warning("No baseline items found — all candidates marked no_match")
            for c in candidates:
                _write_match(conn, c["id"], None, "no_match", "no_baseline_data", 0.0)
            conn.commit()
            return {"total": len(candidates), "high": 0, "medium": 0, "low": 0, "no_match": len(candidates)}

        # Clear previous matches for idempotency
        conn.execute("delete from candidate_matches")
        conn.commit()

        counts = {"high": 0, "medium": 0, "low": 0, "no_match": 0}

        for candidate in candidates:
            best = _find_best_baseline_match(candidate, baseline)
            _write_match(
                conn,
                candidate["id"],
                best["baseline_item_id"],
                best["confidence"],
                best["method"],
                best["score"],
                best.get("reason", ""),
            )
            counts[best["confidence"]] += 1

        conn.commit()
        return {"total": len(candidates), **counts}
    finally:
        conn.close()


def _load_candidates(conn) -> list[dict]:
    rows = conn.execute(
        """select id, title, content_type, tmdb_id, imdb_id, hot_score,
                  priority, discovery_source, snapshot_date
           from candidates
           order by hot_score desc"""
    ).fetchall()
    return [
        {
            "id": r[0],
            "title": r[1],
            "content_type": r[2],
            "tmdb_id": r[3],
            "imdb_id": r[4],
            "hot_score": r[5],
            "priority": r[6],
            "discovery_source": r[7],
            "snapshot_date": r[8],
        }
        for r in rows
    ]


def _load_baseline_items(conn) -> list[dict]:
    rows = conn.execute(
        """select id, title, content_type, year
           from baseline_items
           order by id"""
    ).fetchall()
    return [
        {"id": r[0], "title": r[1], "content_type": r[2], "year": r[3]} for r in rows
    ]


def _find_best_baseline_match(candidate: dict, baseline: list[dict]) -> dict:
    """Find best matching baseline_item for a candidate.

    Returns dict with baseline_item_id, confidence, method, score, reason.
    """
    candidate_title = candidate.get("title", "")
    candidate_type = candidate.get("content_type", "")
    parsed = parse_title(candidate_title)

    best_score = 0.0
    best_item = None
    best_method = "no_match"

    for item in baseline:
        item_title = item.get("title", "")
        if not item_title:
            continue

        # Type filter: movie vs tv_show
        item_type = item.get("content_type", "")
        if candidate_type and item_type and candidate_type != item_type:
            continue

        score = _title_similarity(candidate_title, item_title)

        # Year bonus
        candidate_year = parsed.year
        item_year = item.get("year")
        if candidate_year and item_year and candidate_year == item_year:
            score = min(1.0, score + 0.15)

        if score > best_score:
            best_score = score
            best_item = item
            best_method = _classify_method(score, candidate_year, item_year)

    if best_item is None:
        return {
            "baseline_item_id": None,
            "confidence": "no_match",
            "method": "no_match",
            "score": 0.0,
            "reason": "no_baseline_items_of_same_type",
        }

    confidence, requires_review = _classify_confidence(
        best_score, parsed.year, best_item.get("year")
    )

    reason_parts = []
    if confidence == "high":
        reason_parts.append("title_exact_match" if best_score >= 0.92 else "title_high_similarity")
        if parsed.year and best_item.get("year") == parsed.year:
            reason_parts.append("year_matches")
    elif confidence == "medium":
        reason_parts.append("title_partial_match")
    elif confidence == "low":
        reason_parts.append("title_low_similarity_or_year_mismatch")
    else:
        reason_parts.append("no_confident_match")

    return {
        "baseline_item_id": best_item["id"],
        "confidence": confidence,
        "method": best_method,
        "score": round(best_score, 3),
        "reason": "; ".join(reason_parts),
    }


def _classify_confidence(
    similarity: float, candidate_year: int | None, baseline_year: int | None
) -> tuple[str, bool]:
    """Classify match confidence and whether human review is needed.

    high: similarity >= 0.92, year matches if both present
    medium: similarity >= 0.78
    low: similarity >= 0.60
    no_match: similarity < 0.60
    """
    year_match = (
        candidate_year is not None
        and baseline_year is not None
        and candidate_year == baseline_year
    )

    if similarity >= 0.92 and (year_match or candidate_year is None or baseline_year is None):
        return "high", False
    if similarity >= 0.78:
        return "medium", False
    if similarity >= 0.60:
        return "low", True
    return "no_match", False


def _classify_method(
    similarity: float, candidate_year: int | None, baseline_year: int | None
) -> str:
    if similarity >= 0.92:
        if candidate_year and baseline_year and candidate_year == baseline_year:
            return "exact_title_year"
        return "exact_title"
    if similarity >= 0.78:
        return "fuzzy_title"
    return "edit_distance"


def _title_similarity(left: str, right: str) -> float:
    """Compute normalized title similarity (0.0-1.0)."""
    left_norm = _normalize_title(left)
    right_norm = _normalize_title(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def _normalize_title(value: str) -> str:
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore")
    text = normalized.decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _write_match(
    conn,
    candidate_id: int,
    baseline_item_id: int | None,
    confidence: str,
    method: str,
    score: float,
    reason: str = "",
) -> None:
    is_in_baseline = 1 if confidence in ("high", "medium") else 0
    requires_review = 1 if confidence == "low" else 0

    conn.execute(
        """insert into candidate_matches
           (candidate_id, is_in_baseline, baseline_item_id, match_confidence,
            match_method, match_score_detail, requires_human_review, reason_text)
           values (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            candidate_id,
            is_in_baseline,
            baseline_item_id,
            confidence,
            method,
            score,
            requires_review,
            reason,
        ),
    )
