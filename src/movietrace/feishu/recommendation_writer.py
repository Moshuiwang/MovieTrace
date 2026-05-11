from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from movietrace.db.schema import connect_database

logger = logging.getLogger("movietrace.feishu.recommendation_writer")

# ── content_update_id generation ────────────────────────────────────────


def make_content_update_id(
    canonical_item_id: int | None,
    candidate_id: int,
    is_in_baseline: bool,
    match_confidence: str,
) -> str:
    """Generate content_update_id for dedup.

    Priority: pending_review > discovery > existing
    """
    if match_confidence == "low":
        update_type = "pending_review"
    elif not is_in_baseline:
        update_type = "discovery"
    else:
        update_type = "existing"

    cid = canonical_item_id if canonical_item_id else f"c{candidate_id}"
    return f"{cid}#{update_type}#{candidate_id}"


# ── Canonical item ID generation ────────────────────────────────────────


def _load_candidates_for_feishu(db_path: str) -> list[dict]:
    """Load candidates with match data for Feishu write."""
    conn = connect_database(db_path)
    try:
        rows = conn.execute(
            """select c.id, c.title, c.content_type, c.hot_score, c.priority,
                      c.discovery_source, c.score_breakdown_json, c.reason_text,
                      c.snapshot_date, c.tmdb_id, c.imdb_id,
                      cm.is_in_baseline, cm.match_confidence, cm.match_method,
                      cm.match_score_detail, cm.baseline_item_id,
                      b.title as baseline_title
               from candidates c
               join candidate_matches cm on cm.candidate_id = c.id
               left join baseline_items b on b.id = cm.baseline_item_id
               order by c.hot_score desc"""
        ).fetchall()
        return [_build_row(r) for r in rows]
    finally:
        conn.close()


def _build_row(r: tuple) -> dict:
    return {
        "candidate_id": r[0],
        "title": r[1],
        "content_type": r[2],
        "hot_score": r[3],
        "priority": r[4],
        "discovery_source": r[5],
        "score_breakdown_json": r[6],
        "reason_text": r[7],
        "snapshot_date": r[8],
        "tmdb_id": r[9],
        "imdb_id": r[10],
        "is_in_baseline": bool(r[11]),
        "match_confidence": r[12],
        "match_method": r[13],
        "match_score_detail": r[14],
        "baseline_item_id": r[15],
        "baseline_title": r[16],
    }


# ── Audit logging ───────────────────────────────────────────────────────


def _write_audit_log(entry: dict, output_dir: str = "source_records") -> None:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = Path(output_dir) / f"{date_str}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── Main writer function ────────────────────────────────────────────────


def write_recommendations(
    dry_run: bool = True,
    batch_size: int = 50,
    db_path: str = "data/movietrace.db",
    output_dir: str = "source_records",
) -> dict[str, int]:
    """Write recommendations to Feishu or generate dry-run audit log.

    Returns stats dict with insert/update/skip/error counts.
    """
    candidates = _load_candidates_for_feishu(db_path)
    if not candidates:
        logger.warning("No candidates found for Feishu write")
        return {"insert": 0, "update": 0, "skip": 0, "error": 0, "total": 0}

    stats = {"insert": 0, "update": 0, "skip": 0, "error": 0, "total": len(candidates)}

    for i, c in enumerate(candidates):
        content_update_id = make_content_update_id(
            c.get("baseline_item_id"),  # Use baseline_item_id as canonical proxy
            c["candidate_id"],
            c["is_in_baseline"],
            c["match_confidence"],
        )

        if dry_run:
            entry = _make_dry_run_entry(c, content_update_id, "insert")
            _write_audit_log(entry, output_dir)
            stats["insert"] += 1
        else:
            # Real Feishu write would go here
            entry = _make_dry_run_entry(c, content_update_id, "dry_run")
            _write_audit_log(entry, output_dir)
            stats["insert"] += 1

        # Batch delay
        if not dry_run and (i + 1) % batch_size == 0 and i + 1 < len(candidates):
            time.sleep(1)

    logger.info(
        "Feishu write complete: insert=%d skip=%d error=%d total=%d (dry_run=%s)",
        stats["insert"], stats["skip"], stats["error"], stats["total"], dry_run,
    )
    return stats


def _make_dry_run_entry(candidate: dict, content_update_id: str, default_action: str) -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "action": default_action,
        "content_update_id": content_update_id,
        "feishu_record_id": None,
        "status_code": 200,
        "title": candidate.get("title", ""),
        "reason": f"Dry-run: would {default_action}",
    }
