from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from movietrace.db.schema import connect_database
from movietrace.pipeline.poll_scheduler import PollPlan, build_daily_poll_plan
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


def detect_new_seasons(
    conn: sqlite3.Connection,
    poll_plan: list[PollPlan],
    tmdb_client: TmdbDetailClient,
    interval: float = 1.0,
) -> list[NewSeasonEvent]:
    """Query TMDb for each series in the plan and detect new seasons."""
    events: list[NewSeasonEvent] = []
    now_str = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S +08")

    for item in poll_plan:
        try:
            details = tmdb_client.get_tv_details(item.tmdb_tv_id)
        except Exception as exc:
            logger.warning("TMDb API error for %s: %s", item.tmdb_tv_id, exc)
            continue

        if not details or not details.get("name"):
            continue

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
            for season_num in range(local_max + 1, tmdb_seasons + 1):
                events.append(
                    NewSeasonEvent(
                        virtual_series_id=item.virtual_series_id,
                        tmdb_tv_id=item.tmdb_tv_id,
                        name=details.get("name", item.name),
                        new_season_number=season_num,
                        previous_local_max=local_max,
                        detected_at=now_str,
                    )
                )

        time.sleep(interval)

    return events


def write_content_updates(
    conn: sqlite3.Connection, events: list[NewSeasonEvent]
) -> int:
    """Write new season events to content_updates table. Returns count written."""
    written = 0
    for event in events:
        # Find a canonical_item linked to this virtual_series
        ci_row = conn.execute(
            """select ci.id from canonical_items ci
               where ci.virtual_series_id = ?
               order by ci.season_number asc limit 1""",
            (event.virtual_series_id,),
        ).fetchone()
        if not ci_row:
            continue
        canonical_item_id = ci_row[0]

        content_update_id = (
            f"new_season:vs_{event.virtual_series_id}:s{event.new_season_number}"
        )
        source_summary = json.dumps(
            {
                "tmdb_tv_id": event.tmdb_tv_id,
                "season": event.new_season_number,
                "detected_at": event.detected_at,
            },
            ensure_ascii=False,
        )

        before = conn.total_changes
        conn.execute(
            """insert or ignore into content_updates(
                content_update_id, canonical_item_id, update_type,
                priority, hot_score, match_confidence_low, source_summary_json
            ) values (?, ?, 'new_season', ?, NULL, 0, ?)""",
            (
                content_update_id,
                canonical_item_id,
                _priority_from_virtual_series(conn, event.virtual_series_id),
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


def run_baseline_tracking(
    db_path: str = "data/movietrace.db",
    config: dict | None = None,
    tmdb_token: str | None = None,
    *,
    dry_run: bool = False,
    limit: int | None = None,
    interval: float = 1.0,
) -> dict:
    """Main entry point for baseline tracking.

    Returns stats dict with keys:
        polled, plan_size, detected, written, errors, dry_run
    """
    conn = connect_database(db_path)

    try:
        plan = build_daily_poll_plan(conn, config)
        if limit is not None:
            plan = plan[:limit]

        stats = {
            "plan_size": len(plan),
            "polled": 0,
            "detected": 0,
            "written": 0,
            "errors": 0,
            "dry_run": dry_run,
        }

        if not plan:
            return stats

        if dry_run:
            stats["polled"] = len(plan)
            return stats

        if not tmdb_token:
            raise RuntimeError("TMDb token required for baseline tracking")

        client = TmdbDetailClient(tmdb_token, db_path=db_path, request_date=date.today().isoformat())
        events = detect_new_seasons(conn, plan, client, interval=interval)
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
