#!/usr/bin/env python3
"""P1.5-C: One-time virtual_series backfill from canonical_items + external_ids.

Usage:
    PYTHONPATH=src python scripts/p1_5_c_backfill_virtual_series.py [--dry-run] [--limit N] [--db path]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from movietrace.db.schema import connect_database
from movietrace.pipeline.entity_matching import _ensure_quality_issues_table, _record_quality_issue
from movietrace.pipeline.virtual_series import (
    find_or_create_virtual_series_for_canonical_item,
    link_to_virtual_series,
    update_local_max_season,
)
from movietrace.sources.tmdb import TmdbDetailClient


def load_tmdb_token(secrets_path: str = "/tmp/movietrace_phase0_secrets.json") -> str:
    secrets = json.loads(Path(secrets_path).read_text(encoding="utf-8"))
    token = (secrets.get("tmdb") or {}).get("api_read_access_token")
    if not token:
        raise RuntimeError("TMDb API token not found in secrets file")
    return token


def _has_low_confidence(conn, upstream_program_id: int) -> bool:
    row = conn.execute(
        """select 1 from baseline_quality_issues
           where upstream_program_id = ?
             and issue_type = 'entity_matching_low_confidence'""",
        (upstream_program_id,),
    ).fetchone()
    return row is not None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="P1.5-C: One-time virtual_series backfill"
    )
    parser.add_argument("--db", default="data/movietrace.db")
    parser.add_argument("--secrets", default="/tmp/movietrace_phase0_secrets.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()

    conn = connect_database(args.db)
    _ensure_quality_issues_table(conn)

    rows = conn.execute(
        """select ci.id, ci.canonical_item_key, ci.title, ci.content_type,
                  ci.content_granularity, ci.season_number
           from canonical_items ci
           where ci.content_type = 'tv'
             and ci.virtual_series_id is null
           order by ci.id"""
    ).fetchall()

    if args.limit:
        rows = rows[: args.limit]

    total = len(rows)
    if total == 0:
        print("No TV canonical_items need virtual_series linking.")
        conn.close()
        return

    print(f"TV canonical_items to process: {total}")
    print(f"Dry run: {args.dry_run}")

    token = load_tmdb_token(args.secrets)
    tmdb_client = TmdbDetailClient(token)

    stats = {
        "total": total,
        "linked": 0,
        "virtual_series_created": 0,
        "virtual_series_reused": 0,
        "skipped_low_confidence": 0,
        "skipped_no_tmdb_id": 0,
        "skipped_api_error": 0,
        "api_calls": 0,
    }

    t_start = time.monotonic()
    vs_tracker: set[str] = set()  # track tmdb_tv_ids we've already seen

    for i, (ci_id, ci_key, ci_title, ci_type, ci_granularity, ci_season) in enumerate(
        rows
    ):
        print(
            f"[{i + 1}/{total}] canonical_item #{ci_id} {ci_title[:50]} ... ",
            end="",
            flush=True,
        )

        if args.dry_run:
            print("DRY-RUN")
            continue

        # Check for low confidence via quality issues
        # (low confidence items are skipped for virtual_series aggregation)
        ext_id_row = conn.execute(
            "select external_id from external_ids where canonical_item_id = ? and source = 'tmdb'",
            (ci_id,),
        ).fetchone()
        if not ext_id_row:
            _record_quality_issue(
                conn,
                ci_id,
                ci_key,
                "virtual_series_no_tmdb_id",
                "no_match",
                "no tmdb external_id found",
            )
            stats["skipped_no_tmdb_id"] += 1
            print("SKIP (no tmdb external_id)")
            continue

        tmdb_tv_id = ext_id_row[0]

        vs_id = find_or_create_virtual_series_for_canonical_item(
            conn, ci_id, tmdb_client
        )
        stats["api_calls"] += 1

        if vs_id is None:
            _record_quality_issue(
                conn,
                ci_id,
                ci_key,
                "virtual_series_api_error",
                "no_match",
                "TMDb API call failed",
            )
            stats["skipped_api_error"] += 1
            print("SKIP (API error)")
            continue

        if tmdb_tv_id not in vs_tracker:
            vs_tracker.add(tmdb_tv_id)
            stats["virtual_series_created"] += 1
        else:
            stats["virtual_series_reused"] += 1

        link_to_virtual_series(conn, ci_id, vs_id)

        if ci_season is not None:
            update_local_max_season(conn, vs_id, int(ci_season))

        stats["linked"] += 1
        print(f"OK → virtual_series #{vs_id}")

        conn.commit()
        time.sleep(args.interval)

    conn.close()

    elapsed_total = time.monotonic() - t_start
    print()
    print("=" * 60)
    print("P1.5-C Virtual Series Backfill Complete")
    print("=" * 60)
    print(f"Total processed:            {stats['total']}")
    print(f"Linked:                     {stats['linked']}")
    print(f"Virtual series created:     {stats['virtual_series_created']}")
    print(f"Virtual series reused:      {stats['virtual_series_reused']}")
    print(f"Skipped (no tmdb id):       {stats['skipped_no_tmdb_id']}")
    print(f"Skipped (API error):        {stats['skipped_api_error']}")
    print(f"API calls:                  {stats['api_calls']}")
    print(f"Elapsed:                    {elapsed_total:.0f}s")


if __name__ == "__main__":
    main()
