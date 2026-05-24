from __future__ import annotations

import json
import logging
import sqlite3
import time
from datetime import date, datetime, timedelta
from typing import Any

from movietrace.config import load_secrets as _load_secrets
from movietrace.db.schema import connect_database
from movietrace.pipeline.scoring import (
    DEFAULT_WEIGHTS,
    SOAP_GENRE_ID,
    compute_hot_score,
    load_weights_config,
    map_priority,
)
from movietrace.pipeline.source_fetch_status import (
    record_source_fetch_run,
)
from movietrace.pipeline.tmdb_detail_cache import get_tmdb_season_detail_with_cache

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


def _should_skip_enrichment(candidate, conn: sqlite3.Connection) -> bool:
    """Return True if this is a known repeat hit with sufficient existing metadata.

    Conditions:
    1. current_discovery_items already has this discovery_key (repeat hit)
    2. candidate's tmdb_data already has original_language AND date field
       - Movie: release_date or movie_release_date
       - TV: last_air_date, last_episode_air_date, or last_episode_to_air.air_date

    If either condition fails, return False (run full enrichment).
    Never skips for first-time discoveries.
    """
    tmdb_id = getattr(candidate, 'tmdb_id', None)
    if not tmdb_id:
        return False
    media_type = getattr(candidate, 'media_type', 'movie')
    content_type = "tv" if media_type in ("tv", "show") else "movie"

    # C3: use build_discovery_key instead of f-string interpolation
    from movietrace.pipeline.current_discovery import build_discovery_key
    try:
        dkey = build_discovery_key(content_type, tmdb_id)
    except ValueError:
        return False

    # Check repeat hit
    row = conn.execute(
        "SELECT id, stable_metadata_json FROM current_discovery_items WHERE discovery_key=?",
        (dkey,)
    ).fetchone()
    if not row:
        return False  # First discovery — need full enrichment

    # Check metadata sufficiency — first try candidate.tmdb_data, then stable_metadata fallback
    tmdb_data = getattr(candidate, 'tmdb_data', None) or {}
    has_language = bool(tmdb_data.get('original_language'))

    if content_type == "movie":
        has_date = bool(tmdb_data.get('release_date') or tmdb_data.get('movie_release_date'))
    else:
        has_date = bool(
            tmdb_data.get('last_air_date')
            or tmdb_data.get('last_episode_air_date')
            or (tmdb_data.get('last_episode_to_air') or {}).get('air_date')
        )

    if has_language and has_date:
        return True

    # B2: TMDb trending API may omit last_air_date for TV.
    # Fall back to stable_metadata_json stored from a previous successful enrichment.
    # stable_metadata is only present after at least one completed enrichment cycle.
    # If the row has no stable_metadata (NULL), skip silently — no enrichment skip.
    stable_meta_raw = row[1] if row else None
    if stable_meta_raw:
        import json as _json
        try:
            stable = _json.loads(stable_meta_raw)
        except (ValueError, TypeError):
            stable = {}
        if not has_language:
            has_language = bool(stable.get('original_language'))
        if not has_date:
            if content_type == "movie":
                has_date = bool(
                    stable.get('release_date') or stable.get('movie_release_date')
                )
            else:
                has_date = bool(
                    stable.get('last_air_date')
                    or stable.get('last_episode_air_date')
                )
        if has_language and has_date:
            return True

    return False


def should_write_observation(candidate: dict) -> bool:
    """Return True if a candidate is eligible to be written as a discovery observation.

    P1.57d: Soap threshold exemption applies to hot_score gate only.
    Pure source-date fallback candidates (has_fresh_signal=False) are not eligible,
    even if is_soap=True.  Only candidates with a genuine fresh signal are eligible.
    """
    return bool(candidate.get("has_fresh_signal"))


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
    fp_fetch_result: dict | None = None,
    fallback_cfg: dict | None = None,
) -> dict:
    """End-to-end multi-source discovery pipeline (P1.8/P1.10).

    1. Ensure FP/TMDb/Trakt data for date_from
    2. Resolve source dates with fallback (P1.10-D)
    3. Merge three sources
    4. Enrich with IMDb backfill + OMDb + TMDb detail
    5. Score + threshold filter
    6. Write current_discovery_items + discovery_observations (P1.57i: new_discovery no longer written to content_updates)
    """
    cfg = load_weights_config(weights_path)
    conn = connect_database(db_path)
    snapshot_date = date_from or date.today().isoformat()

    try:
        # Step 1: Ensure FP data
        if fp_fetch_result is not None:
            # FP fetch was performed at CLI layer; use the passed result directly
            fp_stats = fp_fetch_result
        else:
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

        _table_map = {
            "flixpatrol": "flixpatrol_top10",
            "tmdb": "tmdb_trending",
            "trakt": "trakt_trending",
        }
        source_status = {}
        for source, d in source_dates.items():
            if d == snapshot_date:
                status = "fresh"
                cached_count = None
            elif d:
                status = "fallback"
                table = _table_map.get(source, "")
                cached_count = conn.execute(
                    f"select count(*) from {table} where snapshot_date = ?",
                    (d,),
                ).fetchone()[0] if table else 0
            else:
                status = "failed_no_fallback"
                cached_count = None
            entry: dict = {"status": status, "snapshot_date": d}
            if cached_count is not None:
                entry["cached_count"] = cached_count
            source_status[source] = entry

        # Step 2: Multi-source merge
        from movietrace.pipeline.multi_source_merge import merge_three_sources
        logger.info("Discovery merge: reading and merging source rows")
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

        # P1.42-A: Mark fresh signal on each candidate (before enrichment)
        # fresh_sources = set of sources with effective_date == snapshot_date
        # This will be used later to filter out pure-fallback candidates
        fresh_sources = {s for s, d in source_dates.items() if d == snapshot_date}

        # Step 3: Enrichment
        secrets = _load_secrets()
        omdb_keys = _resolve_omdb_keys(secrets)
        tmdb_token = (secrets.get("tmdb") or {}).get("api_read_access_token", "")

        enrich_stats = {}

        # P1.8-F/G: Pre-score IMDb ID backfill via TMDb external_ids
        # backfill runs on full candidates list (lightweight: only fetches external_ids)
        if tmdb_token:
            logger.info("Discovery enrichment: backfilling IMDb IDs for %d candidates", len(candidates))
            from movietrace.pipeline.omdb_enrichment import backfill_imdb_ids
            enrich_stats["imdb_backfill"] = backfill_imdb_ids(
                candidates, tmdb_token, db_path=db_path, request_date=snapshot_date,
            )

        # P1.57j: Skip enrichment for repeat hits with sufficient metadata
        repeat_hit_enrichment_skipped = 0
        candidates_to_enrich = []
        for c in candidates:
            if _should_skip_enrichment(c, conn):
                repeat_hit_enrichment_skipped += 1
            else:
                candidates_to_enrich.append(c)

        if omdb_keys:
            logger.info(
                "Discovery enrichment: fetching OMDb ratings for %d candidates (%d repeat-hits skipped)",
                len(candidates_to_enrich), repeat_hit_enrichment_skipped,
            )
            from movietrace.pipeline.omdb_enrichment import enrich_with_omdb
            enrich_stats["omdb"] = enrich_with_omdb(conn, candidates_to_enrich, omdb_keys, db_path=db_path, request_date=snapshot_date)

        if tmdb_token:
            logger.info(
                "Discovery enrichment: fetching TMDb details for %d candidates (%d repeat-hits skipped)",
                len(candidates_to_enrich), repeat_hit_enrichment_skipped,
            )
            from movietrace.pipeline.omdb_enrichment import enrich_with_tmdb_details
            enrich_stats["tmdb_detail"] = enrich_with_tmdb_details(conn, candidates_to_enrich, tmdb_token, db_path=db_path, request_date=snapshot_date)

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
            # P1.42-A: Add has_fresh_signal based on contributing sources
            contributing = c.source_flags or set()
            c_dict["has_fresh_signal"] = bool(contributing & fresh_sources)
            scored.append(c_dict)

        # Sort by hot_score desc
        scored.sort(key=lambda x: x.get("hot_score", 0), reverse=True)

        # P1.24-C: Soap 自动降权(在阈值过滤前标记,Soap 强制通过)
        for c in scored:
            genres = (c.get("tmdb_data") or {}).get("genres") or []
            genre_ids = [g.get("id") for g in genres if isinstance(g, dict)]
            if SOAP_GENRE_ID in genre_ids:
                c["priority"] = "P3"
                c["is_soap"] = True
                c["ops_note"] = "TMDb 标识为 Soap,自动降权"
            else:
                c["is_soap"] = False

        # Step 5: Threshold filter (with Soap bypass)
        threshold = (cfg.get("priority_thresholds") or {}).get("P2", 50)
        passed = [s for s in scored if s.get("hot_score", 0) >= threshold or s.get("is_soap")]

        # P1.57d: Filter by observation eligibility (replaces P1.42-B Soap bypass)
        # Soap threshold exemption applies only to hot_score gate above; write gate uses fresh signal only.
        soap_pure_fallback_suppressed = sum(
            1 for c in passed if c.get("is_soap") and not c.get("has_fresh_signal")
        )
        before_write_gate = len(passed)
        passed = [c for c in passed if should_write_observation(c)]
        suppressed_fallback_only = before_write_gate - len(passed)
        if suppressed_fallback_only > 0:
            logger.info(
                "P1.57d: Suppressed %d pure-fallback-only candidates (%d Soap)",
                suppressed_fallback_only,
                soap_pure_fallback_suppressed,
            )

        # P1.24-B: 仅对 passed 集合计算 row_duration_hours
        # (避免对被阈值过滤的候选浪费 TMDb season detail 调用)
        tmdb_client_for_seasons = None
        if tmdb_token:
            from movietrace.sources.tmdb import TmdbDetailClient
            tmdb_client_for_seasons = TmdbDetailClient(
                tmdb_token, db_path=db_path, request_date=snapshot_date,
            )

        duration_started = time.monotonic()
        for idx, c in enumerate(passed, start=1):
            if idx == 1 or idx % 25 == 0 or idx == len(passed):
                elapsed = time.monotonic() - duration_started
                logger.info(
                    "Discovery row duration: %d/%d candidates processed (%.1fs)",
                    idx,
                    len(passed),
                    elapsed,
                )
            if tmdb_client_for_seasons:
                try:
                    c["row_duration_hours"] = compute_row_duration_hours(c, conn, tmdb_client_for_seasons)
                except Exception as exc:
                    logger.warning("compute_row_duration_hours failed for %s: %s", c.get("tmdb_id"), exc)
                    c["row_duration_hours"] = 0.0
            else:
                c["row_duration_hours"] = 0.0

        stats = _compute_discovery_stats(scored, passed, enrich_stats, fp_stats)
        stats["source_status"] = source_status
        stats["source_effective_dates"] = source_dates
        stats["source_fallback_used"] = fallback_used
        stats["suppressed_fallback_only"] = suppressed_fallback_only
        stats["soap_pure_fallback_suppressed"] = soap_pure_fallback_suppressed
        stats["repeat_hit_enrichment_skipped"] = repeat_hit_enrichment_skipped

        # P1.9: Auto-register candidates without canonical_item
        auto_registered = 0
        would_be_registered = 0
        for c in passed:
            tmdb_id = c.get("tmdb_id")
            media_type = c.get("media_type", "movie")
            if tmdb_id and not _lookup_canonical_id(conn, tmdb_id, media_type):
                if dry_run:
                    would_be_registered += 1
                else:
                    cid = _ensure_canonical_item(conn, c)
                    if cid:
                        auto_registered += 1
        if auto_registered:
            logger.info("Auto-registered %d new canonical_items", auto_registered)
            conn.commit()

        # Step 6: Write current discovery + observations (new_discovery no longer written to content_updates)
        if not dry_run:
            try:
                cd_stats = _write_current_discovery_batch(conn, passed, snapshot_date, source_status)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            stats["current_discovery_created"] = cd_stats["created"]
            stats["current_discovery_updated"] = cd_stats["updated"]
            stats["observations_written"] = cd_stats["observations_written"]
            # B1: renamed from observations_skipped_source_date_fallback.
            # This counter is non-zero only when _write_current_discovery_batch is called
            # directly bypassing the outer should_write_observation gate (e.g. in tests or
            # future callers).  In the normal run_discovery path the gate runs first, so this
            # value is always 0.  The rename makes the intent explicit.
            stats["observations_skipped_internal_fallback_guard"] = cd_stats["skipped_source_date_fallback"]
            # A2: propagate skipped_no_canonical_id count to top-level stats
            stats["current_discovery_skipped_no_canonical_id"] = cd_stats["skipped_no_canonical_id"]
        else:
            stats["would_be_registered"] = would_be_registered
        stats["auto_registered"] = auto_registered

        return {"candidates": passed, "all_scored": scored, "stats": stats}
    finally:
        conn.close()


# ── Candidate conversion ────────────────────────────────────────────────


def _to_scoring_dict(c) -> dict:
    """Convert MergedCandidate to scoring-compatible dict."""
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

    # P1.24: 字段扩展
    summary["imdb_id"] = c_dict.get("imdb_id") or None
    summary["last_episode_to_air"] = (tmdb_data or {}).get("last_episode_to_air") if tmdb_data else None
    summary["genres"] = [g.get("id") for g in (tmdb_data or {}).get("genres", []) if isinstance(g, dict)] if tmdb_data else []
    summary["score_breakdown"] = c_dict.get("score_breakdown") or {}
    summary["row_duration_hours"] = float(c_dict.get("row_duration_hours") or 0)
    if c_dict.get("ops_note"):
        summary["ops_note"] = c_dict["ops_note"]
    if c_dict.get("is_soap"):
        summary["is_soap"] = True

    return summary


def _build_reason_text(c, breakdown: dict) -> str:
    """Build multi-source reason text for a candidate."""
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
        media_type = "tv" if c.get("media_type") in ("tv", "show") else "movie"
        content_update_id = f"discovery:{media_type}:{tmdb_id}:{snapshot_date}"

        canonical_id = _lookup_canonical_id(conn, tmdb_id, media_type)
        if not canonical_id:
            continue

        source_summary = _build_source_summary(c, source_status)

        before = conn.total_changes
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
            if conn.total_changes > before:
                count += 1
        except Exception as exc:
            logger.warning("Failed to write content_update for %s: %s", content_update_id, exc)

    logger.info("Wrote %d content_updates for %s", count, snapshot_date)
    return count


# ── Current discovery batch write ──────────────────────────────────────


def _write_current_discovery_batch(
    conn: sqlite3.Connection,
    candidates: list[dict],
    snapshot_date: str,
    source_status: dict | None = None,
) -> dict:
    """Write eligible candidates to current_discovery_items + discovery_observations.

    Returns stats dict with keys:
      created, updated, observations_written, skipped_source_date_fallback.
    Caller is responsible for commit/rollback.
    """
    from movietrace.pipeline.current_discovery import (
        build_discovery_key,
        upsert_current_discovery_item,
        upsert_discovery_observation,
    )
    stats = {
        "created": 0,
        "updated": 0,
        "observations_written": 0,
        "skipped_source_date_fallback": 0,
        "skipped_no_canonical_id": 0,
    }
    for c in candidates:
        if not should_write_observation(c):
            stats["skipped_source_date_fallback"] += 1
            continue
        tmdb_id = c.get("tmdb_id")
        if not tmdb_id:
            continue
        media_type = "tv" if c.get("media_type") in ("tv", "show") else "movie"
        try:
            dkey = build_discovery_key(media_type, tmdb_id)
        except ValueError:
            continue
        existing = conn.execute(
            "SELECT id FROM current_discovery_items WHERE discovery_key=?", (dkey,)
        ).fetchone()
        canonical_id = _lookup_canonical_id(conn, tmdb_id, media_type)
        # A2: Do not write current_discovery_items rows with canonical_item_id=NULL.
        # If auto-register ran before this, canonical_id should be populated.
        # Candidates that slipped through without canonical registration are skipped.
        if canonical_id is None:
            stats["skipped_no_canonical_id"] += 1
            logger.debug(
                "Skipping current_discovery write for tmdb_id=%s media_type=%s: no canonical_item_id",
                tmdb_id, media_type,
            )
            continue
        tmdb_data = c.get("tmdb_data") or {}
        stable_meta = {
            "tmdb_id": tmdb_id,
            "media_type": media_type,
            "genres": tmdb_data.get("genres"),
            "original_language": tmdb_data.get("original_language"),
            "networks": tmdb_data.get("networks"),
        }
        source_summary = _build_source_summary(c, source_status)
        upsert_current_discovery_item(
            conn,
            discovery_key=dkey,
            content_type=media_type,
            tmdb_id=tmdb_id,
            observed_date=snapshot_date,
            canonical_item_id=canonical_id,
            hot_score=c.get("hot_score"),
            priority=c.get("priority"),
            source_summary=source_summary,
            stable_metadata=stable_meta,
            title=c.get("title"),
            original_title=(tmdb_data.get("original_name") or tmdb_data.get("original_title")),
            title_zh=(tmdb_data.get("title_zh") or c.get("title_zh")),
        )
        if existing is None:
            stats["created"] += 1
        else:
            stats["updated"] += 1
        score_breakdown = c.get("score_breakdown")
        upsert_discovery_observation(
            conn,
            discovery_key=dkey,
            observed_date=snapshot_date,
            hot_score=c.get("hot_score"),
            priority=c.get("priority"),
            source_summary=source_summary,
            score_breakdown=score_breakdown,
            source_status=source_status,
        )
        stats["observations_written"] += 1
    return stats


def _lookup_canonical_id(
    conn: sqlite3.Connection, tmdb_id: int, media_type: str = "movie"
) -> int | None:
    """Look up canonical_item_id by tmdb_id with strict media_type namespace isolation.

    tv/show → only queries tv:{id}; movie → only queries movie:{id}.
    No cross-type fallback — a movie:100 does not match a tv lookup for 100.
    """
    if media_type in ("tv", "show"):
        ext_id = f"tv:{tmdb_id}"
    else:
        ext_id = f"movie:{tmdb_id}"
    row = conn.execute(
        "select canonical_item_id from external_ids where source = 'tmdb' and external_id = ?",
        (ext_id,),
    ).fetchone()
    return row[0] if row else None


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
    passed_ids = {c.get("content_id") for c in passed}
    filtered = [c for c in all_scored if c.get("content_id") not in passed_ids]
    filtered_out = sorted(filtered, key=lambda c: c.get("hot_score", 0), reverse=True)[:10]

    # Enrichment detail fields — each sub-dict has {enriched/backfilled, api_calls, cache_hits, errors, total}
    enrich_imdb = enrich_stats.get("imdb_backfill", {})
    enrich_omdb = enrich_stats.get("omdb", {})
    enrich_tmdb_detail = enrich_stats.get("tmdb_detail", {})

    return {
        "total_merged": len(all_scored),
        "total_passed": len(passed),
        "P0": p0, "P1": p1, "P2": p2,
        "filtered_out": filtered_out,
        # Enrichment detail — full sub-dicts for CLI/notify formatting
        "enrich_omdb": enrich_omdb,
        "enrich_tmdb_detail": enrich_tmdb_detail,
        "enrich_imdb_backfill": enrich_imdb,
        # FP fetch stats
        "fp_planned": (fp_stats or {}).get("planned_calls", 0),
        "fp_actual": (fp_stats or {}).get("actual_calls", 0),
        "fp_error": (fp_stats or {}).get("error"),
        "fp_inserted": (fp_stats or {}).get("inserted", 0),
    }


def _resolve_omdb_keys(secrets: dict) -> list[str]:
    """Resolve OMDb API keys from secrets, with backward compat for old format.

    New format: {"omdb": {"api_keys": ["key1", "key2"]}}
    Old format: {"omdb": {"api_key": "xxx"}} -> ["xxx"]
    """
    omdb_cfg = secrets.get("omdb") or {}
    api_keys = omdb_cfg.get("api_keys")
    if api_keys:
        return [k for k in api_keys if k]
    # Backward compat: single api_key string
    api_key = omdb_cfg.get("api_key", "")
    return [api_key] if api_key else []


# ── P1.24-B: Row duration & Soap support ────────────────────────────────────


def _query_a_lib_max_season(conn: sqlite3.Connection, tmdb_id: int | str) -> int:
    """Query A 库 (upstream) 已有的最高 season_number for a TMDb TV ID.

    返回 0 表示 A 库无该剧。逻辑:
    - 通过 external_ids (source='tmdb', external_id='tv:{id}') → canonical_items.virtual_series_id
    - → 所有同 virtual_series_id 的 canonical_items 里、source='upstream' 的 max(season_number)
    """
    row = conn.execute(
        """select coalesce(max(ci2.season_number), 0)
           from external_ids ei
           join canonical_items ci on ci.id = ei.canonical_item_id
           join canonical_items ci2 on ci2.virtual_series_id = ci.virtual_series_id
           join external_ids ei2 on ei2.canonical_item_id = ci2.id and ei2.source = 'upstream'
           where ei.source = 'tmdb' and ei.external_id = ?""",
        (f"tv:{tmdb_id}",),
    ).fetchone()
    return int(row[0] if row else 0)


def _query_a_lib_episode_count(conn: sqlite3.Connection, tmdb_id: int | str, season_number: int) -> int:
    """Count upstream_episodes for the specified TMDb TV+season.

    TMDb 与 upstream 的 external_ids 分挂在不同粒度的 canonical_items 上:
    TMDb 挂 series 粒度,upstream 挂 season 粒度。通过 virtual_series_id 关联。
    """
    row = conn.execute(
        """select count(ue.id)
           from external_ids ei
           join canonical_items ci_tmdb on ci_tmdb.id = ei.canonical_item_id
           join canonical_items ci_season on ci_season.virtual_series_id = ci_tmdb.virtual_series_id
                                         and ci_season.season_number = ?
           join external_ids eup on eup.canonical_item_id = ci_season.id and eup.source = 'upstream'
           join upstream_programs up on cast(up.id as text) = eup.external_id
           join upstream_episodes ue on ue.fk_program_content_id = up.id
           where ei.source = 'tmdb' and ei.external_id = ?""",
        (int(season_number), f"tv:{tmdb_id}"),
    ).fetchone()
    return int(row[0] if row else 0)


def compute_row_duration_hours(c_dict: dict, conn: sqlite3.Connection, tmdb_client) -> float:
    """计算单行时长(h) = 缺失集累加 × 1h; Movie 固定 2h。

    Args:
        c_dict: _candidate_to_dict 输出的 dict (含 tmdb_id / media_type / tmdb_data)
        conn: sqlite3 连接
        tmdb_client: TmdbDetailClient 实例 (for get_tv_season_details)

    Returns:
        float: 时长(小时)；无法定位时返回 0.0
    """
    media_type = c_dict.get("media_type", "movie")

    # Movie → 固定 2.0
    if media_type == "movie":
        return 2.0

    tmdb_id = c_dict.get("tmdb_id")
    if not tmdb_id:
        return 0.0

    tmdb_data = c_dict.get("tmdb_data") or {}
    last_aired_season = (tmdb_data.get("last_episode_to_air") or {}).get("season_number")
    if not last_aired_season:
        return 0.0

    a_lib_max = _query_a_lib_max_season(conn, tmdb_id)
    available_seasons = _available_tmdb_seasons(tmdb_data, a_lib_max, last_aired_season)

    # 起算季 = max(a_lib_max, 0) + 1 → 缺失从 a_lib_max+1 开始;a_lib_max=0 表示全季缺失,从 S1 开始
    total = 0
    for s in available_seasons:
        if s <= a_lib_max or s > last_aired_season:
            continue
        season_detail, _ = get_tmdb_season_detail_with_cache(conn, tmdb_client, tmdb_id, s)
        if not season_detail:
            continue
        total += _aired_episode_count(season_detail, last_aired_season, s, tmdb_data)

    # a_lib_max 季内 A 库未补齐的缺集(a_lib_max=0 时跳过,无意义)
    if a_lib_max > 0:
        a_lib_eps_in_max = _query_a_lib_episode_count(conn, tmdb_id, a_lib_max)
        season_detail_max, _ = get_tmdb_season_detail_with_cache(conn, tmdb_client, tmdb_id, a_lib_max)
        if season_detail_max:
            tmdb_eps_in_max = _aired_episode_count(season_detail_max, last_aired_season, a_lib_max, tmdb_data)
            if a_lib_eps_in_max < tmdb_eps_in_max:
                total += (tmdb_eps_in_max - a_lib_eps_in_max)

    return float(total)


def _available_tmdb_seasons(tmdb_data: dict, a_lib_max: int, last_aired_season: int) -> list[int]:
    seasons = tmdb_data.get("seasons")
    if not isinstance(seasons, list):
        return list(range(a_lib_max + 1, last_aired_season + 1))

    out: list[int] = []
    for season in seasons:
        if not isinstance(season, dict):
            continue
        season_number = season.get("season_number")
        try:
            out.append(int(season_number))
        except (TypeError, ValueError):
            continue
    return sorted(set(out))


def _aired_episode_count(
    season_detail: dict, last_aired_season: int, season_number: int, tmdb_data: dict
) -> int:
    """Return aired episodes in a season.

    For the current airing season(season_number == last_aired_season),用
    last_episode_to_air.episode_number(已播);for older seasons,episode_count 即全季已播。
    """
    if season_number == last_aired_season:
        last_aired = (tmdb_data.get("last_episode_to_air") or {}).get("episode_number")
        if last_aired:
            return int(last_aired)
    ep_count = season_detail.get("episode_count")
    if ep_count:
        try:
            return int(ep_count)
        except (ValueError, TypeError):
            pass
    episodes = season_detail.get("episodes", [])
    return len(episodes) if isinstance(episodes, list) else 0
