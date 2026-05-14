#!/usr/bin/env python3
"""P1.5-C: One-time virtual_series backfill from canonical_items + external_ids.

Two-phase approach to avoid redundant TMDb API calls:
  Phase 1: Collect unique tmdb_tv_ids → one API call per series → upsert virtual_series
  Phase 2: Link each canonical_item to its virtual_series + update local_max_season

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
from movietrace.pipeline.entity_matching import _ensure_quality_issues_table
from movietrace.pipeline.virtual_series import (
    _extract_tmdb_tv_id_from_key,
    link_to_virtual_series,
    update_local_max_season,
    upsert_virtual_series,
)
from movietrace.sources.tmdb import TmdbDetailClient


def load_tmdb_token(secrets_path: str = "/tmp/movietrace_phase0_secrets.json") -> str:
    secrets = json.loads(Path(secrets_path).read_text(encoding="utf-8"))
    token = (secrets.get("tmdb") or {}).get("api_read_access_token")
    if not token:
        raise RuntimeError("TMDb API token not found in secrets file")
    return token


def _collect_unique_tmdb_tv_ids(conn, limit: int | None) -> dict[str, list[tuple]]:
    """Collect all unlinked TV canonical_items, grouped by tmdb_tv_id.

    Returns {tmdb_tv_id: [(ci_id, ci_key, ci_title, season_number), ...]}
    """
    rows = conn.execute(
        """select ci.id, ci.canonical_item_key, ci.title, ci.season_number
           from canonical_items ci
           where ci.content_type = 'tv'
             and ci.virtual_series_id is null
           order by ci.id"""
    ).fetchall()

    if limit:
        rows = rows[:limit]

    grouped: dict[str, list[tuple]] = {}
    no_id_items: list[tuple] = []

    for ci_id, ci_key, ci_title, ci_season in rows:
        # Try external_ids first, then fallback to canonical_item_key
        ext_row = conn.execute(
            "select external_id from external_ids where canonical_item_id = ? and source = 'tmdb'",
            (ci_id,),
        ).fetchone()
        if ext_row:
            raw_id = ext_row[0]
            # Strip tv:/movie: namespace prefix before passing to TMDb API
            if raw_id.startswith("tv:") or raw_id.startswith("movie:"):
                tmdb_tv_id = raw_id.split(":", 1)[1]
            else:
                tmdb_tv_id = raw_id
        else:
            tmdb_tv_id = _extract_tmdb_tv_id_from_key(ci_key)

        if tmdb_tv_id:
            grouped.setdefault(tmdb_tv_id, []).append(
                (ci_id, ci_key, ci_title, ci_season)
            )
        else:
            no_id_items.append((ci_id, ci_key, ci_title, ci_season))

    return grouped, no_id_items


def main() -> None:
    parser = argparse.ArgumentParser(
        description="P1.5-C: One-time virtual_series backfill (deduped)"
    )
    parser.add_argument("--db", default="data/movietrace.db")
    parser.add_argument("--secrets", default="/tmp/movietrace_phase0_secrets.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()

    conn = connect_database(args.db)
    _ensure_quality_issues_table(conn)

    # ── Phase 1: Collect unique tmdb_tv_ids ──
    grouped, no_id_items = _collect_unique_tmdb_tv_ids(conn, args.limit)

    unique_ids = len(grouped)
    total_items = sum(len(v) for v in grouped.values()) + len(no_id_items)
    print(f"TV canonical_items to process: {total_items}")
    print(f"Unique TMDb series IDs:       {unique_ids}")
    print(f"Items with no tmdb_id:        {len(no_id_items)}")
    print(f"Dry run: {args.dry_run}")
    print()

    if args.dry_run:
        print(f"[DRY-RUN] Would make {unique_ids} TMDb API calls "
              f"(instead of {total_items - len(no_id_items)} without dedup)")
        conn.close()
        return

    # ── Phase 2: One API call per unique tmdb_tv_id → upsert virtual_series ──
    token = load_tmdb_token(args.secrets)
    tmdb_client = TmdbDetailClient(token)

    vs_map: dict[str, int] = {}  # tmdb_tv_id → virtual_series_id
    api_calls = 0
    api_errors = 0
    created = 0
    reused = 0

    t_start = time.monotonic()
    for i, (tmdb_tv_id, items) in enumerate(grouped.items()):
        title_preview = items[0][2][:50] if items[0][2] else "?"
        season_count = len(items)
        print(
            f"[{i + 1}/{unique_ids}] {title_preview} "
            f"(tmdb_id={tmdb_tv_id}, {season_count} seasons) ... ",
            end="",
            flush=True,
        )

        try:
            details = tmdb_client.get_tv_details(tmdb_tv_id)
        except Exception as exc:
            print(f"API ERROR: {exc}")
            api_errors += 1
            api_calls += 1
            continue

        api_calls += 1

        if not details or not details.get("name"):
            print("SKIP (empty response)")
            api_errors += 1
            continue

        vs_id = upsert_virtual_series(conn, tmdb_tv_id, details)

        if tmdb_tv_id in vs_map:
            reused += 1
        else:
            created += 1
        vs_map[tmdb_tv_id] = vs_id

        print(f"OK → virtual_series #{vs_id}")

        conn.commit()
        time.sleep(args.interval)

    # ── Phase 3: Link all canonical_items to their virtual_series ──
    linked = 0
    for tmdb_tv_id, items in grouped.items():
        vs_id = vs_map.get(tmdb_tv_id)
        if vs_id is None:
            continue
        for ci_id, ci_key, ci_title, ci_season in items:
            link_to_virtual_series(conn, ci_id, vs_id)
            if ci_season is not None:
                update_local_max_season(conn, vs_id, int(ci_season))
            linked += 1

    # No-ID items get skipped
    for ci_id, ci_key, ci_title, ci_season in no_id_items:
        print(f"  SKIP #{ci_id} {ci_title[:50] if ci_title else '?'} (no tmdb_id)")

    conn.commit()

    # ── Final stats ──
    elapsed_total = time.monotonic() - t_start
    print()
    print("=" * 60)
    print("P1.5-C Virtual Series Backfill Complete")
    print("=" * 60)
    print(f"Total canonical_items:      {total_items}")
    print(f"Unique TMDb series:         {unique_ids}")
    print(f"API calls:                  {api_calls}")
    print(f"  (saved: {total_items - len(no_id_items) - api_calls})")
    print(f"Virtual series created:     {created}")
    print(f"Virtual series reused:      {reused} (already existed)")
    print(f"Linked:                     {linked}")
    print(f"Skipped (no tmdb_id):       {len(no_id_items)}")
    print(f"API errors:                 {api_errors}")
    print(f"Elapsed:                    {elapsed_total:.0f}s")

    # Verify
    remaining = conn.execute(
        "select count(*) from canonical_items where content_type='tv' and virtual_series_id is null"
    ).fetchone()[0]
    print(f"Remaining unlinked:         {remaining}")

    conn.close()


if __name__ == "__main__":
    main()
