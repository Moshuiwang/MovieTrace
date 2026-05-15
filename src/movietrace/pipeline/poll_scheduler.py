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
    1. Group virtual_series by poll_priority
    2. Skip 'skip' priority
    3. Within each tier, sort by last_polled_at ASC (NULL first)
    4. Allocate quota per tier based on coverage days
    5. Cap total at daily_max_calls

    Catch-up mode:
    Poll all non-skip series once, sorted by last_polled_at ASC (NULL first).
    """
    cfg = config or {}
    bt = cfg.get("baseline_tracking", {})
    urgent_days = bt.get("urgent_coverage_days", 14)
    normal_days = bt.get("normal_coverage_days", 21)
    low_days = bt.get("low_coverage_days", 180)
    daily_max = bt.get("daily_max_calls", 50)

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

    tiers = [
        ("urgent", urgent_days),
        ("normal", normal_days),
        ("low", low_days),
    ]

    plan: list[PollPlan] = []
    seen: set[int] = set()

    for priority, coverage_days in tiers:
        rows = conn.execute(
            """select id, tmdb_tv_id, name, poll_priority, last_polled_at
               from virtual_series
               where poll_priority = ?
                 and (
                    tmdb_status in ('Returning Series', 'In Production')
                    or tmdb_status is null
                    or trim(tmdb_status) = ''
                 )
               order by last_polled_at asc nulls first""",
            (priority,),
        ).fetchall()

        quota = max(1, len(rows) // coverage_days) if rows else 0
        taken = 0

        for row in rows:
            if len(plan) >= daily_max:
                break
            if taken >= quota:
                break
            vs_id = row[0]
            if vs_id in seen:
                continue
            seen.add(vs_id)
            plan.append(
                PollPlan(
                    virtual_series_id=vs_id,
                    tmdb_tv_id=row[1],
                    name=row[2],
                    poll_priority=row[3],
                    last_polled_at=row[4],
                )
            )
            taken += 1

    return plan
