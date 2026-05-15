from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable
from zoneinfo import ZoneInfo

from movietrace.db.schema import connect_database
from movietrace.pipeline.poll_scheduler import PollPlan, build_daily_poll_plan
from movietrace.pipeline.scoring import compute_hot_score, load_weights_config, map_priority
from movietrace.pipeline.tmdb_detail_cache import get_tmdb_detail_with_cache
from movietrace.pipeline.virtual_series import derive_poll_priority
from movietrace.sources.tmdb import TmdbDetailClient

logger = logging.getLogger("movietrace.pipeline.baseline_tracking")

TZ = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class NewSeasonEvent:
    virtual_series_id: int
    tmdb_tv_id: str
    name: str
    new_season_number: int
    previous_local_max: int
    detected_at: str
    tmdb_details: dict | None = None
    hot_score: float = 0.0
    priority: str = "P3"
    score_breakdown: dict | None = None


def detect_new_seasons(
    conn: sqlite3.Connection,
    poll_plan: list[PollPlan],
    tmdb_client: TmdbDetailClient,
    interval: float = 1.0,
    *,
    weights_config: dict | None = None,
    progress_callback: Callable[[int, int, PollPlan, bool, int], None] | None = None,
) -> list[NewSeasonEvent]:
    """Query TMDb for each series in the plan and detect new seasons."""
    events: list[NewSeasonEvent] = []
    now_str = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S +08")
    scoring_cfg = weights_config or load_weights_config()

    total = len(poll_plan)
    for index, item in enumerate(poll_plan, start=1):
        cache_hit = False
        try:
            details, cache_hit = get_tmdb_detail_with_cache(
                conn,
                tmdb_client,
                item.tmdb_tv_id,
                "tv",
                required_keys=("number_of_seasons",),
            )
        except Exception as exc:
            logger.warning("TMDb API error for %s: %s", item.tmdb_tv_id, exc)
            continue

        if not details or not details.get("name"):
            if progress_callback:
                progress_callback(index, total, item, cache_hit, len(events))
            continue

        _update_virtual_series_from_details(conn, item.virtual_series_id, details)

        tmdb_seasons = details.get("number_of_seasons")
        if tmdb_seasons is None:
            continue

        # Get current local_max_season
        row = conn.execute(
            "select local_max_season from virtual_series where id = ?",
            (item.virtual_series_id,),
        ).fetchone()
        local_max = row[0] if row and row[0] is not None else 0

        if tmdb_seasons > local_max:
            # New seasons detected
            hot_score, priority, breakdown = _score_baseline_series(details, scoring_cfg)
            for season_num in range(local_max + 1, tmdb_seasons + 1):
                events.append(
                    NewSeasonEvent(
                        virtual_series_id=item.virtual_series_id,
                        tmdb_tv_id=item.tmdb_tv_id,
                        name=details.get("name", item.name),
                        new_season_number=season_num,
                        previous_local_max=local_max,
                        detected_at=now_str,
                        tmdb_details=details,
                        hot_score=hot_score,
                        priority=priority,
                        score_breakdown=breakdown,
                    )
                )

        if progress_callback:
            progress_callback(index, total, item, cache_hit, len(events))

        time.sleep(interval)

    return events


def write_content_updates(
    conn: sqlite3.Connection, events: list[NewSeasonEvent]
) -> int:
    """Write new season events to content_updates, merging multi-season into one row.

    Groups events by virtual_series_id so that detecting S2+S3 for the same series
    produces one content_update with full season range in source_summary_json,
    avoiding silent data loss from the (canonical_item_id, update_type) unique index.
    """
    from collections import defaultdict

    by_vs: dict[int, list[NewSeasonEvent]] = defaultdict(list)
    for event in events:
        by_vs[event.virtual_series_id].append(event)

    written = 0
    for vs_id, vs_events in by_vs.items():
        # Find a canonical_item linked to this virtual_series
        ci_row = conn.execute(
            """select ci.id from canonical_items ci
               where ci.virtual_series_id = ?
               order by ci.season_number asc limit 1""",
            (vs_id,),
        ).fetchone()
        if not ci_row:
            continue
        canonical_item_id = ci_row[0]

        seasons = sorted(e.new_season_number for e in vs_events)
        season_min = seasons[0]
        season_max = seasons[-1]

        # Idempotent content_update_id: single season "s2", range "s2-s3"
        if len(seasons) == 1:
            cu_id = f"new_season:vs_{vs_id}:s{season_min}"
        else:
            cu_id = f"new_season:vs_{vs_id}:s{season_min}-s{season_max}"

        sample_event = vs_events[0]
        source_summary = json.dumps(
            {
                "tmdb_tv_id": sample_event.tmdb_tv_id,
                "season": season_max,  # backward-compat: max season
                "seasons": seasons,
                "season_min": season_min,
                "season_max": season_max,
                "detected_at": sample_event.detected_at,
                "baseline_detected_at": sample_event.detected_at,
                "baseline_local_max_season": sample_event.previous_local_max,
                "tmdb_number_of_seasons": (sample_event.tmdb_details or {}).get("number_of_seasons"),
                "tmdb_status": (sample_event.tmdb_details or {}).get("status"),
                "in_production": (sample_event.tmdb_details or {}).get("in_production"),
                "last_episode_to_air": (sample_event.tmdb_details or {}).get("last_episode_to_air"),
                "next_episode_to_air": (sample_event.tmdb_details or {}).get("next_episode_to_air"),
                "hot_score_breakdown": sample_event.score_breakdown or {},
            },
            ensure_ascii=False,
        )

        before = conn.total_changes
        conn.execute(
            """insert or ignore into content_updates(
                content_update_id, canonical_item_id, update_type,
                priority, hot_score, match_confidence_low, source_summary_json
            ) values (?, ?, 'new_season', ?, ?, 0, ?)""",
            (
                cu_id,
                canonical_item_id,
                sample_event.priority,
                sample_event.hot_score,
                source_summary,
            ),
        )
        if conn.total_changes > before:
            written += 1

    return written


def update_local_max_season(
    conn: sqlite3.Connection, virtual_series_id: int, new_max: int
) -> None:
    """Update virtual_series.local_max_season and last_polled_at."""
    now_str = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S +08")
    conn.execute(
        """update virtual_series
           set local_max_season = ?, last_polled_at = ?, updated_at = datetime('now')
           where id = ?""",
        (new_max, now_str, virtual_series_id),
    )


def update_last_polled_at(
    conn: sqlite3.Connection, virtual_series_id: int
) -> None:
    """Update last_polled_at without changing local_max_season."""
    now_str = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S +08")
    conn.execute(
        """update virtual_series
           set last_polled_at = ?, updated_at = datetime('now')
           where id = ?""",
        (now_str, virtual_series_id),
    )


def _priority_from_virtual_series(
    conn: sqlite3.Connection, virtual_series_id: int
) -> str:
    row = conn.execute(
        "select poll_priority from virtual_series where id = ?",
        (virtual_series_id,),
    ).fetchone()
    if row and row[0] == "urgent":
        return "P1"
    return "P2"


def _update_virtual_series_from_details(
    conn: sqlite3.Connection, virtual_series_id: int, details: dict
) -> None:
    status = details.get("status")
    name = details.get("name")
    if not name:
        logger.warning("TMDb returned null/empty name for VS %d (tmdb_tv_id not in context)", virtual_series_id)
    conn.execute(
        """update virtual_series
           set name = ?,
               tmdb_status = ?,
               tmdb_number_of_seasons = ?,
               poll_priority = ?,
               updated_at = datetime('now')
           where id = ?""",
        (
            name,
            status,
            details.get("number_of_seasons"),
            derive_poll_priority(status),
            virtual_series_id,
        ),
    )


def _score_baseline_series(details: dict, cfg: dict) -> tuple[float, str, dict]:
    last_episode = details.get("last_episode_to_air")
    release_date = None
    if isinstance(last_episode, dict):
        release_date = last_episode.get("air_date")
    release_date = release_date or details.get("last_air_date") or details.get("first_air_date")

    hot_score, breakdown = compute_hot_score(
        {
            "fp_items": [],
            "ext_data": {
                "tmdb_popularity": details.get("popularity"),
                "tmdb_vote_average": details.get("vote_average"),
                "tmdb_vote_count": details.get("vote_count"),
            },
            "platform": "unknown",
            "content_type": "tv_show",
            "release_date": release_date,
            "language": details.get("original_language"),
            "ranking": None,
        },
        cfg,
    )
    return hot_score, map_priority(hot_score, cfg.get("priority_thresholds")), breakdown


def _diagnose_empty_routine_plan(conn: sqlite3.Connection) -> None:
    """Log why routine mode produced an empty plan."""
    total_row = conn.execute(
        "select count(*) from virtual_series where poll_priority != 'skip'"
    ).fetchone()
    total_trackable = int(total_row[0] or 0) if total_row else 0

    if total_trackable == 0:
        logger.info("Plan empty: no trackable series found (all skipped?).")
        return

    null_status_row = conn.execute(
        """select count(*) from virtual_series
           where poll_priority != 'skip'
             and (tmdb_status is null or trim(tmdb_status) = '')"""
    ).fetchone()
    null_status = int(null_status_row[0] or 0) if null_status_row else 0

    if null_status == total_trackable:
        logger.info(
            "Plan empty: all %d trackable series have null tmdb_status. "
            "Run catch-up first to backfill TMDb status.",
            total_trackable,
        )
    elif null_status > 0:
        logger.info(
            "Plan empty: %d of %d trackable series have null tmdb_status, "
            "the rest have non-Returning/non-In Production status.",
            null_status,
            total_trackable,
        )
    else:
        logger.info(
            "Plan empty: 0 of %d trackable series match routine status filter "
            "(Returning Series / In Production).",
            total_trackable,
        )


def run_baseline_tracking(
    db_path: str = "data/movietrace.db",
    config: dict | None = None,
    tmdb_token: str | None = None,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    interval: float = 1.0,
    mode: str = "routine",
    progress_callback: Callable[[int, int, PollPlan, bool, int], None] | None = None,
) -> dict:
    """Main entry point for baseline tracking.

    Returns stats dict with keys:
        polled, plan_size, detected, written, errors, dry_run
    """
    conn = connect_database(db_path)
    stats = {
        "plan_size": 0,
        "polled": 0,
        "detected": 0,
        "written": 0,
        "errors": 0,
        "dry_run": dry_run,
        "mode": mode,
    }

    try:
        plan = build_daily_poll_plan(conn, config, mode=mode)
        if limit is not None:
            plan = plan[:limit]

        stats["plan_size"] = len(plan)

        if not plan:
            if mode == "routine":
                _diagnose_empty_routine_plan(conn)
            return stats

        if dry_run:
            stats["polled"] = len(plan)
            return stats

        if not tmdb_token:
            raise RuntimeError("TMDb token required for baseline tracking")

        client = TmdbDetailClient(tmdb_token, db_path=db_path, request_date=date.today().isoformat())
        events = detect_new_seasons(
            conn,
            plan,
            client,
            interval=interval,
            progress_callback=progress_callback,
        )
        stats["polled"] = len(plan)
        stats["detected"] = len(events)

        if events:
            # P1.9-hotfix-C: aggregate by vs_id, update to max new_season_number
            max_by_vs: dict[int, int] = {}
            for event in events:
                vs_id = event.virtual_series_id
                if vs_id not in max_by_vs or event.new_season_number > max_by_vs[vs_id]:
                    max_by_vs[vs_id] = event.new_season_number
            for vs_id, max_ns in max_by_vs.items():
                update_local_max_season(conn, vs_id, max_ns)

            written = write_content_updates(conn, events)
            stats["written"] = written

        # Update last_polled_at for all polled items
        for item in plan:
            update_last_polled_at(conn, item.virtual_series_id)

        conn.commit()
        return stats
    except Exception as exc:
        logger.error("Baseline tracking failed: %s", exc)
        stats["errors"] = 1
        return stats
    finally:
        conn.close()
