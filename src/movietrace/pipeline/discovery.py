from __future__ import annotations

import json
import logging
import sqlite3
from datetime import date, datetime
from typing import Any

from movietrace.db.schema import connect_database
from movietrace.pipeline.scoring import (
    DEFAULT_WEIGHTS,
    compute_hot_score,
    load_weights_config,
    map_priority,
)
from movietrace.pipeline.source_fetch_status import (
    record_source_fetch_run,
)

logger = logging.getLogger("movietrace.pipeline.discovery")


# ── FP data helpers ──────────────────────────────────────────────────────


def _ensure_fp_data(
    conn: sqlite3.Connection,
    date_from: str,
    *,
    db_path: str = "data/movietrace.db",
    fetch_movies: bool = False,
    movie_weekly_day: int = 0,
) -> dict:
    """Populate flixpatrol_top10 from API if no data exists for the date.
    Returns FP fetch stats dict."""
    target_date = datetime.strptime(date_from, "%Y-%m-%d").date()
    should_fetch_movies = fetch_movies
    if fetch_movies and movie_weekly_day is not None:
        should_fetch_movies = target_date.weekday() == movie_weekly_day

    existing = conn.execute(
        "select count(*) from flixpatrol_top10 where snapshot_date = ?",
        (date_from,),
    ).fetchone()[0]
    if existing > 0:
        movie_existing = conn.execute(
            "select count(*) from flixpatrol_top10 where snapshot_date = ? and content_type = 'movie'",
            (date_from,),
        ).fetchone()[0]
        tv_existing = conn.execute(
            "select count(*) from flixpatrol_top10 where snapshot_date = ? and content_type = 'tv_show'",
            (date_from,),
        ).fetchone()[0]
        if tv_existing > 0 and (not should_fetch_movies or movie_existing > 0):
            logger.info("FP data already exists for %s (%d TV, %d movie)", date_from, tv_existing, movie_existing)
            return {"planned_calls": 0, "actual_calls": 0}

    logger.info("Fetching FP data for %s (movies=%s)...", date_from, should_fetch_movies)
    try:
        from movietrace.sources.flixpatrol_api import FlixPatrolClient, load_api_key

        client = FlixPatrolClient(load_api_key(), db_path=db_path, request_date=date_from)
        fp_result = client.fetch_all_platforms(
            date_from=date_from, fetch_movies=should_fetch_movies,
        )

        results = fp_result["results"]
        count = 0
        for key, items in results.items():
            parts = key.split("/")
            country_slug = parts[0] if len(parts) > 0 else "unknown"
            for item in items:
                if item.get("snapshot_date") != date_from:
                    continue
                try:
                    conn.execute(
                        """insert or ignore into flixpatrol_top10
                           (fp_id, title, content_type, platform, country,
                            snapshot_date, ranking, ranking_last, value,
                            days_total, tmdb_id, imdb_id, raw_payload_json,
                            updated_at, country_id, company_id)
                           values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            item.get("fp_id"),
                            item.get("title", ""),
                            item.get("content_type", "movie"),
                            item.get("platform", "unknown"),
                            item.get("country", country_slug),
                            item.get("snapshot_date", date_from),
                            item.get("ranking"),
                            item.get("ranking_last"),
                            item.get("value"),
                            item.get("days_total"),
                            item.get("tmdb_id"),
                            item.get("imdb_id"),
                            json.dumps(item, ensure_ascii=False),
                            item.get("updated_at"),
                            item.get("country_id"),
                            item.get("company_id"),
                        ),
                    )
                    count += 1
                except Exception as exc:
                    logger.warning("Failed to insert FP row: %s", exc)
        conn.commit()
        logger.info(
            "FP: inserted=%d planned=%d actual=%d tv=%d movie=%d monthly_est=%d-%d",
            count,
            fp_result["planned_calls"],
            fp_result["actual_calls"],
            fp_result["tv_calls"],
            fp_result["movie_calls"],
            fp_result["monthly_estimate_low"],
            fp_result["monthly_estimate_high"],
        )
        if count == 0:
            logger.warning("FlixPatrol API returned no usable rows for %s", date_from)
        return fp_result
    except Exception as exc:
        logger.error("Failed to fetch FP data from API: %s", exc)
        return {"planned_calls": 0, "actual_calls": 0, "error": str(exc)}


# ── Source fallback resolution ───────────────────────────────────────────


def _resolve_source_dates_with_fallback(
    conn: sqlite3.Connection,
    target_date: str,
    fallback_cfg: dict | None = None,
    *,
    flixpatrol_rows: int = 0,
    flixpatrol_error: str | None = None,
    tmdb_rows: int = 0,
    tmdb_error: str | None = None,
    trakt_rows: int = 0,
    trakt_error: str | None = None,
) -> dict:
    """Resolve effective source dates with fallback, record status in source_fetch_runs.

    Returns: {source: effective_date | None} — None means source unavailable.
    """
    if fallback_cfg is None:
        fallback_cfg = {}
    enabled = fallback_cfg.get("enabled", True)
    max_staleness = fallback_cfg.get("max_staleness_days", 30)
    sources_cfg = fallback_cfg.get("sources", {})
    fallback_sources = {k for k, v in sources_cfg.items() if v} if sources_cfg else {"flixpatrol", "tmdb", "trakt"}

    source_info = {
        "flixpatrol": (flixpatrol_rows, flixpatrol_error),
        "tmdb": (tmdb_rows, tmdb_error),
        "trakt": (trakt_rows, trakt_error),
    }

    import json

    fallback_cfg_json = json.dumps(fallback_cfg, ensure_ascii=False) if fallback_cfg else None
    effective_dates: dict[str, str | None] = {}

    for source in ["flixpatrol", "tmdb", "trakt"]:
        rows, error = source_info.get(source, (0, None))

        if error:
            # Fetch failed — attempt fallback if enabled
            if enabled and source in fallback_sources:
                snapshot = _find_fallback_snapshot(conn, source, target_date, max_staleness)
                if snapshot:
                    record_source_fetch_run(
                        conn, target_date, source, "fallback",
                        source_snapshot_date=snapshot,
                        rows_fetched=0, rows_inserted=0,
                        error_message=error,
                        config_json=fallback_cfg_json,
                    )
                    effective_dates[source] = snapshot
                else:
                    record_source_fetch_run(
                        conn, target_date, source, "failed_no_fallback",
                        error_message=error,
                        config_json=fallback_cfg_json,
                    )
                    effective_dates[source] = None
            else:
                record_source_fetch_run(
                    conn, target_date, source, "failed_no_fallback",
                    error_message=error,
                    config_json=fallback_cfg_json,
                )
                effective_dates[source] = None
        elif rows == 0:
            # No data — attempt fallback if enabled
            if enabled and source in fallback_sources:
                snapshot = _find_fallback_snapshot(conn, source, target_date, max_staleness)
                if snapshot:
                    record_source_fetch_run(
                        conn, target_date, source, "fallback",
                        source_snapshot_date=snapshot,
                        rows_fetched=0, rows_inserted=0,
                        config_json=fallback_cfg_json,
                    )
                    effective_dates[source] = snapshot
                else:
                    record_source_fetch_run(
                        conn, target_date, source, "failed_no_fallback",
                        error_message="No data and no fallback available",
                        config_json=fallback_cfg_json,
                    )
                    effective_dates[source] = None
            else:
                record_source_fetch_run(
                    conn, target_date, source, "failed_no_fallback",
                    error_message="No data for date",
                    config_json=fallback_cfg_json,
                )
                effective_dates[source] = None
        else:
            # Success — record fresh
            record_source_fetch_run(
                conn, target_date, source, "fresh",
                source_snapshot_date=target_date,
                rows_fetched=rows, rows_inserted=rows,
                config_json=fallback_cfg_json,
            )
            effective_dates[source] = target_date

    conn.commit()
    return effective_dates


def _find_fallback_snapshot(
    conn: sqlite3.Connection,
    source: str,
    target_date: str,
    max_staleness_days: int,
) -> str | None:
    """Find the most recent available snapshot for a source within staleness window."""
    from datetime import datetime, timedelta

    table_map = {
        "flixpatrol": "flixpatrol_top10",
        "tmdb": "tmdb_trending",
        "trakt": "trakt_trending",
    }
    date_col = "snapshot_date"
    table = table_map.get(source)
    if not table:
        return None

    cutoff = (
        datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=max_staleness_days)
    ).strftime("%Y-%m-%d")

    row = conn.execute(
        f"""select {date_col} from {table}
            where {date_col} < ? and {date_col} >= ?
            order by {date_col} desc limit 1""",
        (target_date, cutoff),
    ).fetchone()
    return row[0] if row else None


# ── Multi-source discovery ──────────────────────────────────────────────


def run_discovery(
    date_from: str | None = None,
    dry_run: bool = False,
    weights_path: str = "config/scoring_weights.yaml",
    db_path: str = "data/movietrace.db",
    *,
    fetch_movies: bool = False,
    movie_weekly_day: int = 0,
    tmdb_fetch_result: dict | None = None,
    trakt_fetch_result: dict | None = None,
    fallback_cfg: dict | None = None,
) -> dict:
    """End-to-end multi-source discovery pipeline (P1.8/P1.10).

    1. Ensure FP/TMDb/Trakt data for date_from
    2. Resolve source dates with fallback (P1.10-D)
    3. Merge three sources
    4. Enrich with IMDb backfill + OMDb + TMDb detail
    5. Score + threshold filter
    6. Write content_updates
    """
    cfg = load_weights_config(weights_path)
    conn = connect_database(db_path)
    snapshot_date = date_from or date.today().isoformat()

    try:
        # Step 1: Ensure FP data
        fp_stats = _ensure_fp_data(
            conn, snapshot_date, db_path=db_path,
            fetch_movies=fetch_movies, movie_weekly_day=movie_weekly_day,
        )
        fp_error = fp_stats.get("error") if isinstance(fp_stats, dict) else None

        # Step 1.5: Resolve source dates with fallback (P1.10-D)
        fp_rows_count = conn.execute(
            "select count(*) from flixpatrol_top10 where snapshot_date = ?",
            (snapshot_date,),
        ).fetchone()[0]
        tmdb_rows_count = conn.execute(
            "select count(*) from tmdb_trending where snapshot_date = ?",
            (snapshot_date,),
        ).fetchone()[0]
        trakt_rows_count = conn.execute(
            "select count(*) from trakt_trending where snapshot_date = ?",
            (snapshot_date,),
        ).fetchone()[0]

        source_dates = _resolve_source_dates_with_fallback(
            conn, snapshot_date, fallback_cfg,
            flixpatrol_rows=fp_rows_count,
            flixpatrol_error=fp_error,
            tmdb_rows=tmdb_rows_count,
            tmdb_error=(tmdb_fetch_result or {}).get("error"),
            trakt_rows=trakt_rows_count,
            trakt_error=(trakt_fetch_result or {}).get("error"),
        )

        fallback_used = any(
            d and d != snapshot_date
            for d in source_dates.values()
        )
        source_status = {
            source: {
                "status": "fresh" if (d == snapshot_date) else ("fallback" if d else "failed_no_fallback"),
                "snapshot_date": d,
            }
            for source, d in source_dates.items()
        }

        # Step 2: Multi-source merge
        from movietrace.pipeline.multi_source_merge import merge_three_sources, MergedCandidate
        candidates = merge_three_sources(conn, snapshot_date, source_dates)
        if not candidates:
            return {
                "candidates": [],
                "stats": {
                    "error": "no_data",
                    "source_status": source_status,
                    "source_effective_dates": source_dates,
                    "source_fallback_used": fallback_used,
                },
            }

        # Step 3: Enrichment
        secrets = _load_secrets()
        omdb_key = (secrets.get("omdb") or {}).get("api_key", "")
        tmdb_token = (secrets.get("tmdb") or {}).get("api_read_access_token", "")

        enrich_stats = {}

        # P1.8-F/G: Pre-score IMDb ID backfill via TMDb external_ids
        if tmdb_token:
            from movietrace.pipeline.omdb_enrichment import backfill_imdb_ids
            enrich_stats["imdb_backfill"] = backfill_imdb_ids(
                candidates, tmdb_token, db_path=db_path, request_date=snapshot_date,
            )

        if omdb_key:
            from movietrace.pipeline.omdb_enrichment import enrich_with_omdb
            enrich_stats["omdb"] = enrich_with_omdb(conn, candidates, omdb_key, db_path=db_path, request_date=snapshot_date)

        if tmdb_token:
            from movietrace.pipeline.omdb_enrichment import enrich_with_tmdb_details
            enrich_stats["tmdb_detail"] = enrich_with_tmdb_details(conn, candidates, tmdb_token, db_path=db_path, request_date=snapshot_date)

        # Step 4: Score
        scored = []
        for c in candidates:
            sc = _to_scoring_dict(c)
            hot, breakdown = compute_hot_score(sc, cfg)
            c_dict = _candidate_to_dict(c)
            c_dict["hot_score"] = hot
            c_dict["score_breakdown"] = breakdown
            c_dict["priority"] = map_priority(hot, cfg.get("priority_thresholds"))
            c_dict["reason_text"] = _build_reason_text(c, breakdown)
            c_dict["snapshot_date"] = snapshot_date
            scored.append(c_dict)

        # Sort by hot_score desc
        scored.sort(key=lambda x: x.get("hot_score", 0), reverse=True)

        # Step 5: Threshold filter
        threshold = (cfg.get("priority_thresholds") or {}).get("P2", 50)
        passed = [s for s in scored if s.get("hot_score", 0) >= threshold]

        stats = _compute_discovery_stats(scored, passed, enrich_stats, fp_stats)
        stats["source_status"] = source_status
        stats["source_effective_dates"] = source_dates
        stats["source_fallback_used"] = fallback_used

        # P1.9: Auto-register candidates without canonical_item
        auto_registered = 0
        for c in passed:
            tmdb_id = c.get("tmdb_id")
            media_type = c.get("media_type", "movie")
            if tmdb_id and not _lookup_canonical_id(conn, tmdb_id, media_type):
                cid = _ensure_canonical_item(conn, c)
                if cid:
                    auto_registered += 1
        if auto_registered:
            logger.info("Auto-registered %d new canonical_items", auto_registered)
            conn.commit()

        # Step 6: Write to content_updates
        if not dry_run:
            written = _write_content_updates(conn, passed, snapshot_date, source_status)
            stats["written"] = written
        stats["auto_registered"] = auto_registered

        return {"candidates": passed, "all_scored": scored, "stats": stats}
    finally:
        conn.close()


# ── Candidate conversion ────────────────────────────────────────────────


def _to_scoring_dict(c) -> dict:
    """Convert MergedCandidate to scoring-compatible dict."""
    from movietrace.pipeline.multi_source_merge import MergedCandidate

    ext_data: dict[str, Any] = {}
    if c.tmdb_data:
        ext_data["tmdb_popularity"] = c.tmdb_data.get("popularity")
        ext_data["tmdb_vote_average"] = c.tmdb_data.get("vote_average")
        ext_data["tmdb_vote_count"] = c.tmdb_data.get("vote_count")
    if c.trakt_data:
        ext_data["trakt_watchers"] = c.trakt_data.get("watchers")
    if hasattr(c, "imdb_rating") and c.imdb_rating is not None:
        ext_data["imdb_rating"] = c.imdb_rating
    if hasattr(c, "imdb_votes") and c.imdb_votes is not None:
        ext_data["imdb_votes"] = c.imdb_votes

    content_type = "tv_show" if c.media_type in ("tv", "show") else "movie"
    platform = "unknown"
    ranking = None
    if c.fp_items:
        best = min((i for i in c.fp_items if i.get("ranking") is not None),
                   key=lambda x: x["ranking"], default=None)
        if best:
            platform = best.get("platform", "hulu")
            ranking = best.get("ranking")

    release_date = None
    language = None
    if c.tmdb_data:
        language = c.tmdb_data.get("original_language")
        # P1.8-C: TV freshness uses last_air_date, not first_air_date
        if content_type == "tv_show":
            release_date = (
                c.tmdb_data.get("last_air_date")
                or c.tmdb_data.get("last_episode_air_date")
                or c.tmdb_data.get("first_air_date")
                or c.tmdb_data.get("release_date")
            )
        else:
            release_date = (
                c.tmdb_data.get("movie_release_date")
                or c.tmdb_data.get("release_date")
            )

    return {
        "title": c.title,
        "content_type": content_type,
        "platform": platform,
        "fp_items": c.fp_items,
        "ext_data": ext_data,
        "release_date": release_date,
        "language": language,
        "ranking": ranking,
    }


def _candidate_to_dict(c) -> dict:
    """Convert MergedCandidate to a plain dict for serialization/storage."""
    from movietrace.pipeline.multi_source_merge import MergedCandidate

    d = {
        "tmdb_id": c.tmdb_id,
        "imdb_id": c.imdb_id,
        "title": c.title,
        "media_type": c.media_type,
        "fp_items": c.fp_items,
        "tmdb_data": c.tmdb_data,
        "trakt_data": c.trakt_data,
        "source_flags": list(c.source_flags),
        "imdb_rating": getattr(c, "imdb_rating", None),
        "imdb_votes": getattr(c, "imdb_votes", None),
    }
    return d


# ── Source summary / reason text ────────────────────────────────────────


def _build_source_summary(c_dict: dict, source_status: dict | None = None) -> dict:
    """Build source_summary_json from candidate data.
    Optionally includes source_data_status for P1.10-E fallback visibility."""
    summary: dict[str, Any] = {}

    fp_items = c_dict.get("fp_items", [])
    if fp_items:
        best = min((i for i in fp_items if i.get("ranking") is not None),
                   key=lambda x: x["ranking"], default=None)
        if best:
            summary["fp"] = {
                "platform": best.get("platform"),
                "ranking": best.get("ranking"),
                "days_total": best.get("days_total"),
            }

    tmdb_data = c_dict.get("tmdb_data")
    if tmdb_data:
        summary["tmdb"] = {
            "popularity": tmdb_data.get("popularity"),
            "vote_average": tmdb_data.get("vote_average"),
            "vote_count": tmdb_data.get("vote_count"),
        }

    trakt_data = c_dict.get("trakt_data")
    if trakt_data:
        summary["trakt"] = {
            "watchers": trakt_data.get("watchers"),
            "rating": trakt_data.get("rating"),
            "votes": trakt_data.get("votes"),
        }

    if c_dict.get("imdb_rating"):
        summary["imdb"] = {
            "rating": str(c_dict["imdb_rating"]),
            "votes": str(c_dict.get("imdb_votes", "")),
        }

    if tmdb_data:
        summary["release_date"] = tmdb_data.get("release_date")
        summary["language"] = tmdb_data.get("original_language")

    if source_status:
        summary["source_data_status"] = source_status

    return summary


def _build_reason_text(c, breakdown: dict) -> str:
    """Build multi-source reason text for a candidate."""
    from movietrace.pipeline.multi_source_merge import MergedCandidate
    parts = []

    if c.fp_items:
        best = min((i for i in c.fp_items if i.get("ranking") is not None),
                   key=lambda x: x["ranking"], default=None)
        if best:
            parts.append(
                f"FlixPatrol {best['platform'].title()} #{best['ranking']}, "
                f"在榜 {best.get('days_total', 0)} 天"
            )

    if c.tmdb_data and c.tmdb_data.get("popularity"):
        pop = c.tmdb_data["popularity"]
        parts.append(f"TMDb popularity {pop:.1f}")
        va = c.tmdb_data.get("vote_average")
        vc = c.tmdb_data.get("vote_count")
        if va and vc:
            parts.append(f"TV vote_average {va}, votes {vc}")

    if c.trakt_data and c.trakt_data.get("watchers"):
        w = c.trakt_data["watchers"]
        parts.append(f"Trakt 实时观看 {w} 人")
        tr = c.trakt_data.get("rating")
        tv = c.trakt_data.get("votes")
        if tr and tv:
            parts.append(f"累计评分 {tr}, {tv} votes")

    imdb_r = getattr(c, "imdb_rating", None)
    imdb_v = getattr(c, "imdb_votes", None)
    if imdb_r:
        parts.append(f"IMDb {imdb_r}/{imdb_v or '?'} votes")

    if not parts:
        parts.append("FlixPatrol 在榜（多源评分数据待补充）")

    hot_score = getattr(c, "hot_score", None)
    if hot_score:
        parts.insert(0, f"综合 hot_score: {hot_score:.0f}")
        priority = map_priority(hot_score)
        parts.insert(1, f"priority: {priority}")

    return " — ".join(parts) + "。"


# ── Canonical item auto-registration ─────────────────────────────────────


def _ensure_canonical_item(
    conn: sqlite3.Connection, candidate: dict
) -> int | None:
    """Auto-register a canonical_item + external_ids for a P2+ candidate.

    Used when daily-discover finds hot content that isn't already in A库.
    Returns canonical_item_id, or None on failure.
    """
    tmdb_id = candidate.get("tmdb_id")
    if not tmdb_id:
        return None

    media_type = candidate.get("media_type", "movie")
    title = candidate.get("title", "Unknown")

    # Build canonical_item_key following entity_matching.py convention
    if media_type in ("tv", "show"):
        key = f"tmdb:tv:{tmdb_id}:season:1"
        content_type = "tv"
        granularity = "season"
        season_number = 1
    else:
        key = f"tmdb:movie:{tmdb_id}"
        content_type = "movie"
        granularity = "movie"
        season_number = None

    # Idempotent: skip if key already exists
    existing = conn.execute(
        "select id from canonical_items where canonical_item_key = ?", (key,)
    ).fetchone()
    if existing:
        canonical_id = existing[0]
    else:
        cursor = conn.execute(
            """insert into canonical_items
               (canonical_item_key, title, content_type, content_granularity,
                season_number, year)
               values (?, ?, ?, ?, ?, ?)""",
            (
                key, title, content_type, granularity,
                season_number,
                candidate.get("year"),
            ),
        )
        canonical_id = cursor.lastrowid

    # Register tmdb → canonical mapping in external_ids (P1.9-hotfix-E: prefixed)
    ext_id = f"{content_type}:{tmdb_id}" if content_type in ("tv", "movie") else str(tmdb_id)
    conn.execute(
        """insert or ignore into external_ids
           (canonical_item_id, source, external_id) values (?, ?, ?)""",
        (canonical_id, "tmdb", ext_id),
    )

    logger.info(
        "Auto-registered canonical_item: %s (id=%s) for tmdb_id=%s",
        key, canonical_id, tmdb_id,
    )
    return canonical_id


# ── Content updates write ───────────────────────────────────────────────


def _write_content_updates(
    conn: sqlite3.Connection,
    candidates: list[dict],
    snapshot_date: str,
    source_status: dict | None = None,
) -> int:
    """Write scored candidates to content_updates table. Returns count."""
    count = 0
    for c in candidates:
        tmdb_id = c.get("tmdb_id")
        if not tmdb_id:
            continue
        content_update_id = f"discovery:{tmdb_id}:{snapshot_date}"

        canonical_id = _lookup_canonical_id(conn, tmdb_id, c.get("media_type", "movie"))
        if not canonical_id:
            continue

        source_summary = _build_source_summary(c, source_status)

        try:
            conn.execute(
                """insert or ignore into content_updates
                   (content_update_id, canonical_item_id, update_type, priority,
                    hot_score, source_summary_json, review_status, match_confidence_low)
                   values (?, ?, ?, ?, ?, ?, 'pending', 0)""",
                (
                    content_update_id,
                    canonical_id,
                    "new_discovery",
                    c.get("priority", "P3"),
                    c.get("hot_score", 0),
                    json.dumps(source_summary, ensure_ascii=False),
                ),
            )
            count += 1
        except Exception as exc:
            logger.warning("Failed to write content_update for %s: %s", content_update_id, exc)

    conn.commit()
    logger.info("Wrote %d content_updates for %s", count, snapshot_date)
    return count


def _lookup_canonical_id(
    conn: sqlite3.Connection, tmdb_id: int, media_type: str = "movie"
) -> int | None:
    """Look up canonical_item_id by tmdb_id. media_type disambiguates movie vs tv."""
    # P1.9-hotfix-E: TMDb IDs are prefixed with tv:/movie: for namespace isolation
    candidates = [f"{media_type}:{tmdb_id}", f"tv:{tmdb_id}", f"movie:{tmdb_id}", str(tmdb_id)]
    for ext_id in candidates:
        row = conn.execute(
            "select canonical_item_id from external_ids where source = 'tmdb' and external_id = ?",
            (ext_id,),
        ).fetchone()
        if row:
            return row[0]
    return None


# ── Stats ────────────────────────────────────────────────────────────────


def _compute_discovery_stats(
    all_scored: list[dict],
    passed: list[dict],
    enrich_stats: dict,
    fp_stats: dict | None = None,
) -> dict[str, Any]:
    p0 = sum(1 for c in passed if c.get("priority") == "P0")
    p1 = sum(1 for c in passed if c.get("priority") == "P1")
    p2 = sum(1 for c in passed if c.get("priority") == "P2")
    return {
        "total_merged": len(all_scored),
        "total_passed": len(passed),
        "P0": p0, "P1": p1, "P2": p2,
        "enrich_omdb": enrich_stats.get("omdb", {}),
        "enrich_tmdb_detail": enrich_stats.get("tmdb_detail", {}),
        "enrich_imdb_backfill": enrich_stats.get("imdb_backfill", {}),
        "fp_planned": (fp_stats or {}).get("planned_calls", 0),
        "fp_actual": (fp_stats or {}).get("actual_calls", 0),
    }


def _load_secrets(path: str = "/tmp/movietrace_phase0_secrets.json") -> dict:
    try:
        return json.loads(open(path).read())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
