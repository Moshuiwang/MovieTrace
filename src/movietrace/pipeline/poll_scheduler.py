from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class PollPlan:
    virtual_series_id: int
    tmdb_tv_id: str
    name: str
    poll_priority: str
    last_polled_at: str | None


def build_daily_poll_plan(
    conn: sqlite3.Connection, config: dict | None = None, *, mode: str = "routine"
) -> list[PollPlan]:
    """Generate a baseline polling plan.

    Routine mode:
    Poll all non-skip series with tmdb_status Returning Series / In Production
    (or null), sorted by last_polled_at ASC (NULL first).
    Optional daily_max_calls cap (0 = no limit).

    Catch-up mode:
    Poll all non-skip series once, sorted by last_polled_at ASC (NULL first).
    """
    cfg = config or {}
    bt = cfg.get("baseline_tracking", {})
    daily_max = bt.get("daily_max_calls", 0)

    if mode not in ("routine", "catch-up"):
        raise ValueError("mode must be 'routine' or 'catch-up'")

    if mode == "catch-up":
        rows = conn.execute(
            """select id, tmdb_tv_id, name, poll_priority, last_polled_at
               from virtual_series
               where poll_priority != 'skip'
               order by last_polled_at asc nulls first, id asc"""
        ).fetchall()
        return [
            PollPlan(
                virtual_series_id=row[0],
                tmdb_tv_id=row[1],
                name=row[2],
                poll_priority=row[3],
                last_polled_at=row[4],
            )
            for row in rows
        ]

    rows = conn.execute(
        """select id, tmdb_tv_id, name, poll_priority, last_polled_at
           from virtual_series
           where poll_priority != 'skip'
             and (
                tmdb_status in ('Returning Series', 'In Production')
                or tmdb_status is null
                or trim(tmdb_status) = ''
             )
           order by last_polled_at asc nulls first""",
    ).fetchall()

    plan: list[PollPlan] = []
    for row in rows:
        if daily_max and len(plan) >= daily_max:
            break
        plan.append(
            PollPlan(
                virtual_series_id=row[0],
                tmdb_tv_id=row[1],
                name=row[2],
                poll_priority=row[3],
                last_polled_at=row[4],
            )
        )

    return plan
