from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from movietrace.db.schema import connect_database


@dataclass(frozen=True)
class CanonicalPromotionResult:
    eligible_candidates: int
    promoted_baseline_items: int
    created_canonical_items: int
    created_external_ids: int


@dataclass(frozen=True)
class MatchCandidateRow:
    baseline_item_id: int
    source: str
    external_id: str
    title: str
    media_type: str | None
    year: int | None
    confidence: str
    raw_payload: dict[str, Any]


def promote_match_candidates(
    db_path: str | Path,
    *,
    confidences: tuple[str, ...] = ("high",),
) -> CanonicalPromotionResult:
    with connect_database(db_path) as conn:
        candidates = _load_eligible_candidates(conn, confidences)
        created_canonical_items = 0
        created_external_ids = 0
        promoted_baseline_items = 0

        for candidate in candidates:
            canonical_item_id, created_item = _get_or_create_canonical_item(
                conn, candidate
            )
            created_canonical_items += int(created_item)
            created_external_ids += int(
                _insert_external_id(conn, canonical_item_id, candidate)
            )
            promoted_baseline_items += int(
                _update_baseline_item(conn, canonical_item_id, candidate)
            )

        conn.commit()

    return CanonicalPromotionResult(
        eligible_candidates=len(candidates),
        promoted_baseline_items=promoted_baseline_items,
        created_canonical_items=created_canonical_items,
        created_external_ids=created_external_ids,
    )


def _load_eligible_candidates(
    conn: sqlite3.Connection, confidences: tuple[str, ...]
) -> list[MatchCandidateRow]:
    placeholders = ",".join("?" for _ in confidences)
    rows = conn.execute(
        f"""
        select baseline_item_id, source, external_id, title, media_type, year,
               confidence, raw_payload_json
        from match_candidates
        where confidence in ({placeholders})
          and source != 'none'
          and external_id is not null
        order by baseline_item_id
        """,
        confidences,
    ).fetchall()
    return [
        MatchCandidateRow(
            baseline_item_id=row[0],
            source=row[1],
            external_id=row[2],
            title=row[3],
            media_type=row[4],
            year=row[5],
            confidence=row[6],
            raw_payload=_load_json_object(row[7]),
        )
        for row in rows
    ]


def _get_or_create_canonical_item(
    conn: sqlite3.Connection, candidate: MatchCandidateRow
) -> tuple[int, bool]:
    canonical_item_key = _canonical_item_key(candidate)
    existing = conn.execute(
        "select id from canonical_items where canonical_item_key = ?",
        (canonical_item_key,),
    ).fetchone()
    if existing:
        return int(existing[0]), False

    conn.execute(
        """
        insert into canonical_items(
            canonical_item_key, title, original_title, content_type,
            content_granularity, year
        )
        values (?, ?, ?, ?, ?, ?)
        """,
        (
            canonical_item_key,
            candidate.title,
            _original_title(candidate),
            _content_type(candidate.media_type),
            _external_granularity(candidate.media_type),
            candidate.year,
        ),
    )
    canonical_item_id = conn.execute("select last_insert_rowid()").fetchone()[0]
    return int(canonical_item_id), True


def _insert_external_id(
    conn: sqlite3.Connection,
    canonical_item_id: int,
    candidate: MatchCandidateRow,
) -> bool:
    before = conn.total_changes
    conn.execute(
        """
        insert or ignore into external_ids(
            canonical_item_id, source, external_id, external_granularity
        )
        values (?, ?, ?, ?)
        """,
        (
            canonical_item_id,
            candidate.source,
            candidate.external_id,
            _external_granularity(candidate.media_type),
        ),
    )
    return conn.total_changes > before


def _update_baseline_item(
    conn: sqlite3.Connection,
    canonical_item_id: int,
    candidate: MatchCandidateRow,
) -> bool:
    before = conn.total_changes
    conn.execute(
        """
        update baseline_items
        set canonical_item_id = ?,
            match_status = 'matched',
            match_confidence = ?
        where id = ?
        """,
        (canonical_item_id, candidate.confidence, candidate.baseline_item_id),
    )
    return conn.total_changes > before


def _canonical_item_key(candidate: MatchCandidateRow) -> str:
    return (
        f"{candidate.source}:"
        f"{_content_type(candidate.media_type) or 'unknown'}:"
        f"{candidate.external_id}"
    )


def _content_type(media_type: str | None) -> str | None:
    if media_type == "tv":
        return "tv"
    if media_type == "movie":
        return "movie"
    return media_type


def _external_granularity(media_type: str | None) -> str:
    if media_type == "tv":
        return "series"
    if media_type == "movie":
        return "movie"
    return "unknown"


def _original_title(candidate: MatchCandidateRow) -> str | None:
    for key in ("original_name", "original_title"):
        value = candidate.raw_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _load_json_object(value: object) -> dict[str, Any]:
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Promote confirmed match candidates into canonical items"
    )
    parser.add_argument("--db", default="data/movietrace.db")
    parser.add_argument(
        "--confidence",
        action="append",
        default=None,
        help="Confidence value to promote. Defaults to high. Repeatable.",
    )
    args = parser.parse_args()

    result = promote_match_candidates(
        args.db,
        confidences=tuple(args.confidence or ["high"]),
    )
    print(
        "eligible="
        f"{result.eligible_candidates}; "
        f"promoted={result.promoted_baseline_items}; "
        f"canonical_created={result.created_canonical_items}; "
        f"external_ids_created={result.created_external_ids}"
    )


if __name__ == "__main__":
    main()
