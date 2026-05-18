#!/usr/bin/env python3
"""P1.5-E: A 库全量实体匹配 → canonical_items + external_ids.

Usage:
    PYTHONPATH=src python scripts/p1.5_e_match_all.py [--dry-run] [--limit N] [--db path]
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from movietrace.config import DEFAULT_SECRETS_PATH
from movietrace.db.schema import connect_database
from movietrace.pipeline.entity_matching import (
    _ensure_quality_issues_table,
    match_upstream_program,
)
from movietrace.sources.tmdb import TmdbDetailClient, TmdbSearchClient


def load_tmdb_token(secrets_path: str = str(DEFAULT_SECRETS_PATH)) -> str:
    secrets = json.loads(Path(secrets_path).read_text(encoding="utf-8"))
    token = (secrets.get("tmdb") or {}).get("api_read_access_token")
    if not token:
        raise RuntimeError("TMDb API token not found in secrets file")
    return token


def main() -> None:
    parser = argparse.ArgumentParser(description="P1.5-E: Full upstream program matching")
    parser.add_argument("--db", default="data/movietrace.db")
    parser.add_argument("--secrets", default=str(DEFAULT_SECRETS_PATH))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()

    token = load_tmdb_token(args.secrets)
    client = TmdbSearchClient(token)
    detail_client = TmdbDetailClient(token) if not args.dry_run else None

    db_path = args.db
    conn = connect_database(db_path)

    if not args.dry_run:
        _ensure_quality_issues_table(conn)

    rows = conn.execute(
        """select id, name from upstream_programs
           where online_flag = '1'
           and id not in (
               select external_id from external_ids where source = 'upstream'
           )
           order by id"""
    ).fetchall()

    if args.limit:
        rows = rows[: args.limit]

    total = len(rows)
    if total == 0:
        print("No programs to match (all already matched or empty upstream_programs).")
        conn.close()
        return

    print(f"Programs to match: {total}")
    print(f"Dry run: {args.dry_run}")

    stats = {
        "total": total,
        "matched": 0,
        "created_new": 0,
        "reused_existing": 0,
        "failed": 0,
        "low_confidence": 0,
        "by_confidence": {"high": 0, "medium": 0, "low": 0, "no_match": 0},
        "by_type": {"tv": 0, "movie": 0},
        "api_calls": 0,
    }

    t_start = time.monotonic()

    for i, (upstream_id, name) in enumerate(rows):
        print(f"[{i + 1}/{total}] #{upstream_id} {name[:60]} ... ", end="", flush=True)

        if args.dry_run:
            season = None
            import re

            m = re.search(
                r"(?<![A-Za-z0-9])S(\d{2})(?![A-Za-z0-9])", name, flags=re.IGNORECASE
            )
            if m:
                season = int(m.group(1))
            ctype = "tv" if season else "movie"
            stats["by_type"][ctype] += 1
            print(f"DRY-RUN type={ctype} season={season}")
            continue

        result = match_upstream_program(conn, upstream_id, client, detail_client)
        stats["api_calls"] += 1

        if result is None:
            stats["failed"] += 1
            print("SKIP (not found)")
            continue

        stats["by_confidence"][result.get("confidence", "no_match")] += 1
        if result.get("content_type"):
            stats["by_type"][result["content_type"]] += 1

        if result.get("matched"):
            stats["matched"] += 1
            if result.get("created"):
                stats["created_new"] += 1
            else:
                stats["reused_existing"] += 1
            if result.get("confidence") == "low":
                stats["low_confidence"] += 1
            print(
                f"OK confidence={result.get('confidence')} "
                f"tmdb_id={result.get('tmdb_id')} "
                f"type={result.get('content_type')}"
            )
        else:
            stats["failed"] += 1
            print(f"FAIL confidence={result.get('confidence')}")

        conn.commit()

        elapsed = time.monotonic() - t_start
        rate = (i + 1) / elapsed if elapsed > 0 else 0
        remaining = (total - i - 1) / rate if rate > 0 else 0
        if (i + 1) % 10 == 0 or i == total - 1:
            print(
                f"  --- progress: {i + 1}/{total} | "
                f"rate={rate:.1f}/s | "
                f"ETA={remaining:.0f}s | "
                f"elapsed={elapsed:.0f}s"
            )

        time.sleep(args.interval)

    conn.close()

    elapsed_total = time.monotonic() - t_start
    print()
    print("=" * 60)
    print("P1.5-E Matching Complete")
    print("=" * 60)
    print(f"Total processed:     {stats['total']}")
    print(f"Matched:             {stats['matched']}")
    print(f"  New canonical:     {stats['created_new']}")
    print(f"  Reused existing:   {stats['reused_existing']}")
    print(f"Failed:              {stats['failed']}")
    print(f"Low confidence:      {stats['low_confidence']}")
    print(f"Confidence dist:     {stats['by_confidence']}")
    print(f"Type dist:           {stats['by_type']}")
    print(f"API calls:           {stats['api_calls']}")
    print(f"Elapsed:             {elapsed_total:.0f}s")
    print(f"Rate:                {stats['total'] / elapsed_total:.1f}/s")


if __name__ == "__main__":
    main()
