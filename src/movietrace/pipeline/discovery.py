from __future__ import annotations

import json
import logging
import sqlite3
from datetime import date
from typing import Any

from movietrace.db.schema import connect_database
from movietrace.pipeline.scoring import (
    DEFAULT_WEIGHTS,
    compute_hot_score,
    load_weights_config,
    map_priority,
)

logger = logging.getLogger("movietrace.pipeline.discovery")


def collect_flixpatrol_candidates(
    conn: sqlite3.Connection, snapshot_date: str | None = None
) -> list[dict]:
    """Read flixpatrol_top10 rows and link to canonical_items via tmdb_id.

    Returns raw candidate dicts before scoring.
    """
    if snapshot_date:
        rows = conn.execute(
            """select fp_id, title, content_type, platform, country,
                      snapshot_date, ranking, ranking_last, value, days_total,
                      tmdb_id, imdb_id
               from flixpatrol_top10
               where snapshot_date = ?
               order by ranking""",
            (snapshot_date,),
        ).fetchall()
    else:
        rows = conn.execute(
            """select fp_id, title, content_type, platform, country,
                      snapshot_date, ranking, ranking_last, value, days_total,
                      tmdb_id, imdb_id
               from flixpatrol_top10
               order by snapshot_date desc, ranking""",
        ).fetchall()

    if not rows:
        logger.warning("No flixpatrol_top10 rows found%s", f" for {snapshot_date}" if snapshot_date else "")
        return []

    return [_build_raw_candidate(row) for row in rows]


def _build_raw_candidate(row: tuple) -> dict:
    return {
        "fp_id": row[0],
        "title": row[1],
        "content_type": row[2],
        "platform": row[3],
        "country": row[4],
        "snapshot_date": row[5],
        "ranking": row[6],
        "ranking_last": row[7],
        "value": row[8],
        "days_total": row[9],
        "tmdb_id": row[10],
        "imdb_id": row[11],
    }


def merge_by_external_id(items: list[dict]) -> list[dict]:
    """Merge FP items by tmdb_id (preferred) or imdb_id.

    For merged items, picks best ranking across platforms.
    """
    merged: dict[str, dict] = {}
    tmdb_used: set[int] = set()

    for item in items:
        key = None
        if item.get("tmdb_id"):
            key = f"tmdb:{item['tmdb_id']}"
        elif item.get("imdb_id"):
            key = f"imdb:{item['imdb_id']}"
        else:
            key = f"title:{item['title']}:{item['content_type']}"

        if key not in merged:
            merged[key] = {
                "tmdb_id": item.get("tmdb_id"),
                "imdb_id": str(item["imdb_id"]) if item.get("imdb_id") else None,
                "title": item["title"],
                "content_type": item["content_type"],
                "snapshot_date": item["snapshot_date"],
                "fp_items": [],
                "platform": "",
            }

        m = merged[key]
        m["fp_items"].append(item)

        # Track which tmdb_ids we've seen
        if item.get("tmdb_id"):
            tmdb_used.add(item["tmdb_id"])

        # Use the earlier snapshot_date
        if item["snapshot_date"] < m["snapshot_date"]:
            m["snapshot_date"] = item["snapshot_date"]

        # Pick title from highest-ranked item
        cur_best = min(
            (i.get("ranking") or 99 for i in m["fp_items"]), default=99,
        )
        if item.get("ranking", 99) <= cur_best:
            m["title"] = item["title"]

    # Detect cross-source conflict: same imdb_id but different tmdb_id
    imdb_to_tmdb: dict[str, set] = {}
    for item in items:
        if item.get("imdb_id") and item.get("tmdb_id"):
            imdb_key = str(item["imdb_id"])
            if imdb_key not in imdb_to_tmdb:
                imdb_to_tmdb[imdb_key] = set()
            imdb_to_tmdb[imdb_key].add(item["tmdb_id"])

    for imdb_key, tmdb_set in imdb_to_tmdb.items():
        if len(tmdb_set) > 1:
            logger.warning(
                "Cross-source conflict: imdb_id=%s maps to tmdb_ids=%s",
                imdb_key, tmdb_set,
            )

    # Set primary platform from best-ranked FP item
    for m in merged.values():
        fp_sorted = sorted(
            (i for i in m["fp_items"] if i.get("ranking") is not None),
            key=lambda x: x["ranking"],
        )
        if fp_sorted:
            m["platform"] = fp_sorted[0]["platform"]
            m["ranking"] = fp_sorted[0]["ranking"]

    return list(merged.values())


def assign_discovery_source(candidate: dict, in_baseline: bool) -> str:
    """Classify candidate as new_release / global_hot / both.

    Uses FP ranking ≤ 5 and days_total ≥ 7 as hot signals.
    """
    ranking = candidate.get("ranking", 99) or 99
    days = max(
        (item.get("days_total") or 0 for item in candidate.get("fp_items", [])),
        default=0,
    )

    is_hot = ranking <= 5 or days >= 7
    is_new = not in_baseline

    if is_new and is_hot:
        return "both"
    if is_new:
        return "new_release"
    return "global_hot"


def build_reason_text(breakdown: dict, candidate: dict) -> str:
    """Build human-readable reason text for a candidate."""
    parts = []
    fp_items = candidate.get("fp_items", [])
    if fp_items:
        best = min(fp_items, key=lambda x: x.get("ranking", 99))
        parts.append(
            f"进入 FlixPatrol {best['platform'].title()} Top 10（排名 #{best['ranking']}）"
        )

    if breakdown.get("tmdb_popularity_score"):
        parts.append(f"TMDb 热度 {breakdown['tmdb_popularity_score']}")

    if breakdown.get("imdb_rating_score"):
        parts.append(f"IMDb {_fmt_rating(breakdown['imdb_rating_score'])}")

    if not parts:
        parts.append("FlixPatrol 在榜（评分数据不足）")

    return "。".join(parts) + "。"


def _fmt_rating(score: float) -> str:
    return f"{score / 100 * 10:.1f}/10"


def write_candidates(candidates: list[dict], conn: sqlite3.Connection) -> int:
    """Write scored candidates to DB. Returns count of inserted rows."""
    count = 0
    for c in candidates:
        canonical_id = c.get("canonical_item_id")
        snapshot_date = c.get("snapshot_date", "")

        # Check for existing (canonical_item_id, snapshot_date)
        if canonical_id:
            existing = conn.execute(
                "select id from candidates where canonical_item_id = ? and snapshot_date = ?",
                (canonical_id, snapshot_date),
            ).fetchone()
            if existing:
                logger.debug(
                    "Skipping duplicate candidate: canonical_item_id=%s date=%s",
                    canonical_id, snapshot_date,
                )
                continue

        conn.execute(
            """insert or ignore into candidates
               (canonical_item_id, tmdb_id, imdb_id, title, content_type,
                hot_score, priority, discovery_source,
                score_breakdown_json, reason_text, snapshot_date)
               values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                canonical_id,
                c.get("tmdb_id"),
                str(c["imdb_id"]) if c.get("imdb_id") else None,
                c.get("title", ""),
                c.get("content_type", "movie"),
                c.get("hot_score", 0),
                c.get("priority", "P3"),
                c.get("discovery_source", "new_release"),
                json.dumps(c.get("score_breakdown", {}), ensure_ascii=False),
                c.get("reason_text", ""),
                snapshot_date,
            ),
        )
        count += 1
    conn.commit()
    return count


def run_discovery(
    date_from: str | None = None,
    dry_run: bool = False,
    weights_path: str = "config/scoring_weights.yaml",
    db_path: str = "data/movietrace.db",
) -> dict:
    """End-to-end discovery pipeline.

    1. Read FP data from flixpatrol_top10
    2. Link to canonical_items via external_ids
    3. Score candidates
    4. If not dry_run, write to candidates table

    Returns {"candidates": [...], "stats": {...}}.
    """
    cfg = load_weights_config(weights_path)
    conn = connect_database(db_path)

    try:
        # If date_from provided and no data, try to fetch from API
        if date_from:
            _ensure_fp_data(conn, date_from)

        # Collect raw items
        raw_items = collect_flixpatrol_candidates(conn, date_from)
        if not raw_items:
            return {"candidates": [], "stats": {"error": "no_flixpatrol_data"}}

        # Merge by external_id
        merged = merge_by_external_id(raw_items)

        # Build baseline membership set
        baseline_canonical_ids = set(
            row[0] for row in conn.execute(
                "select distinct canonical_item_id from baseline_items "
                "where canonical_item_id is not null"
            ).fetchall()
        )

        # Enrich with canonical_item data
        candidates = []
        for m in merged:
            c = dict(m)
            c = _enrich_candidate(c, conn, baseline_canonical_ids)
            candidates.append(c)

        # Score
        for c in candidates:
            hot, breakdown = compute_hot_score(c, cfg)
            c["hot_score"] = hot
            c["score_breakdown"] = breakdown
            c["priority"] = map_priority(hot, cfg.get("priority_thresholds"))
            c["reason_text"] = build_reason_text(breakdown, c)

        # Sort by hot_score descending
        candidates.sort(key=lambda x: x.get("hot_score", 0), reverse=True)

        stats = _compute_stats(candidates)

        if not dry_run:
            written = write_candidates(candidates, conn)
            stats["written"] = written

        return {"candidates": candidates, "stats": stats}
    finally:
        conn.close()


def _enrich_candidate(
    c: dict, conn: sqlite3.Connection, baseline_ids: set[int]
) -> dict:
    """Look up canonical_item_id and metadata via tmdb_id → external_ids."""
    tmdb_id = c.get("tmdb_id")
    canonical_id = None

    if tmdb_id:
        row = conn.execute(
            """select canonical_item_id from external_ids
               where source = 'tmdb' and external_id = ?""",
            (str(tmdb_id),),
        ).fetchone()
        if row:
            canonical_id = row[0]

    c["canonical_item_id"] = canonical_id
    c["in_baseline"] = canonical_id in baseline_ids if canonical_id else False
    c["discovery_source"] = assign_discovery_source(c, c["in_baseline"])

    # Enrich from canonical_items
    if canonical_id:
        ci = conn.execute(
            """select title, content_type, year, release_date, language
               from canonical_items where id = ?""",
            (canonical_id,),
        ).fetchone()
        if ci:
            if not c.get("title") or c.get("title") == c.get("fp_items", [{}])[0].get("title"):
                pass  # Keep FP title as primary
            c["canonical_title"] = ci[0]
            if not c.get("content_type") or c["content_type"] not in ("movie", "tv_show"):
                c["content_type"] = ci[1]
            c["year"] = ci[2]
            c["release_date"] = ci[3]
            c["language"] = ci[4]

    # Use FP content_type as fallback
    if not c.get("content_type") or c["content_type"] not in ("movie", "tv_show"):
        c["content_type"] = "movie"

    return c


def _ensure_fp_data(conn: sqlite3.Connection, date_from: str) -> None:
    """Populate flixpatrol_top10 from API if no data exists for the date."""
    existing = conn.execute(
        "select count(*) from flixpatrol_top10 where snapshot_date >= ?",
        (date_from,),
    ).fetchone()[0]
    if existing > 0:
        return

    logger.info("No FP data for %s, fetching from API...", date_from)
    try:
        from movietrace.sources.flixpatrol_api import FlixPatrolClient, load_api_key

        client = FlixPatrolClient(load_api_key())
        results = client.fetch_all_platforms(date_from=date_from)

        count = 0
        for platform_key, items in results.items():
            for item in items:
                try:
                    conn.execute(
                        """insert or ignore into flixpatrol_top10
                           (fp_id, title, content_type, platform, country,
                            snapshot_date, ranking, ranking_last, value,
                            days_total, tmdb_id, imdb_id, raw_payload_json)
                           values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            item.get("fp_id"),
                            item.get("title", ""),
                            item.get("content_type", "movie"),
                            item.get("platform", platform_key),
                            item.get("country", "united-states"),
                            item.get("snapshot_date", date_from),
                            item.get("ranking"),
                            item.get("ranking_last"),
                            item.get("value"),
                            item.get("days_total"),
                            item.get("tmdb_id"),
                            item.get("imdb_id"),
                            json.dumps(item, ensure_ascii=False),
                        ),
                    )
                    count += 1
                except Exception as exc:
                    logger.warning("Failed to insert FP row: %s", exc)
        conn.commit()
        logger.info("Inserted %d rows into flixpatrol_top10", count)
    except Exception as exc:
        logger.error("Failed to fetch FP data from API: %s", exc)


def _compute_stats(candidates: list[dict]) -> dict[str, Any]:
    p0 = sum(1 for c in candidates if c.get("priority") == "P0")
    p1 = sum(1 for c in candidates if c.get("priority") == "P1")
    p2 = sum(1 for c in candidates if c.get("priority") == "P2")
    p3 = sum(1 for c in candidates if c.get("priority") == "P3")
    with_baseline = sum(1 for c in candidates if c.get("in_baseline"))
    new_release = sum(1 for c in candidates if c.get("discovery_source") == "new_release")
    global_hot = sum(1 for c in candidates if c.get("discovery_source") == "global_hot")
    both = sum(1 for c in candidates if c.get("discovery_source") == "both")

    return {
        "total": len(candidates),
        "P0": p0,
        "P1": p1,
        "P2": p2,
        "P3": p3,
        "in_baseline": with_baseline,
        "not_in_baseline": len(candidates) - with_baseline,
        "new_release": new_release,
        "global_hot": global_hot,
        "both": both,
    }
