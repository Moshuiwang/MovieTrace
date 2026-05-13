from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass, field

logger = logging.getLogger("movietrace.pipeline.multi_source_merge")


@dataclass
class MergedCandidate:
    tmdb_id: int | None
    imdb_id: str | None
    title: str
    media_type: str  # 'tv' | 'movie'
    fp_items: list[dict] = field(default_factory=list)
    tmdb_data: dict | None = None
    trakt_data: dict | None = None
    source_flags: set[str] = field(default_factory=set)


def merge_three_sources(
    conn: sqlite3.Connection,
    snapshot_date: str,
) -> list[MergedCandidate]:
    """Merge FP / TMDb / Trakt data for snapshot_date into deduplicated candidates."""
    fp_rows = _read_fp(conn, snapshot_date)
    tmdb_rows = _read_tmdb(conn, snapshot_date)
    trakt_rows = _read_trakt(conn, snapshot_date)

    merged: dict[str, MergedCandidate] = {}

    # Pass 1: tmdb_id-based merge
    _merge_by_tmdb_id(fp_rows, merged, "fp")
    _merge_by_tmdb_id(tmdb_rows, merged, "tmdb")
    _merge_by_tmdb_id(trakt_rows, merged, "trakt")

    # Pass 2: imdb_id fallback for rows without tmdb_id
    _merge_by_imdb_id(fp_rows, merged, "fp")
    _merge_by_imdb_id(tmdb_rows, merged, "tmdb")
    _merge_by_imdb_id(trakt_rows, merged, "trakt")

    # Pass 3: title_norm + media_type fallback
    _merge_by_title(fp_rows, merged, "fp")
    _merge_by_title(tmdb_rows, merged, "tmdb")
    _merge_by_title(trakt_rows, merged, "trakt")

    # Fill in best title from TMDb if available
    candidates = list(merged.values())
    for c in candidates:
        if c.source_flags and "tmdb" in c.source_flags and c.tmdb_data:
            c.title = c.tmdb_data.get("title", c.title)

    logger.info(
        "Multi-source merge: fp=%d tmdb=%d trakt=%d → merged=%d",
        len(fp_rows), len(tmdb_rows), len(trakt_rows), len(candidates),
    )
    return candidates


def _read_fp(conn: sqlite3.Connection, snapshot_date: str) -> list[dict]:
    rows = conn.execute(
        """select fp_id, title, content_type, platform, country,
                  snapshot_date, ranking, ranking_last, value, days_total,
                  tmdb_id, imdb_id
           from flixpatrol_top10
           where snapshot_date = ?""",
        (snapshot_date,),
    ).fetchall()
    out: list[dict] = []
    for r in rows:
        ct = r[2]  # content_type
        mt = "movie"
        if ct in ("tv_show", "tv", "show"):
            mt = "tv"
        item = {
            "fp_id": r[0], "title": r[1], "content_type": ct,
            "media_type": mt,
            "platform": r[3], "country": r[4], "snapshot_date": r[5],
            "ranking": r[6], "ranking_last": r[7], "value": r[8],
            "days_total": r[9], "tmdb_id": r[10], "imdb_id": str(r[11]) if r[11] else None,
        }
        out.append(item)
    return out


def _read_tmdb(conn: sqlite3.Connection, snapshot_date: str) -> list[dict]:
    rows = conn.execute(
        """select tmdb_id, media_type, title, original_title, release_date,
                  original_language, popularity, vote_average, vote_count,
                  source_endpoint, source_page, snapshot_date
           from tmdb_trending
           where snapshot_date = ?""",
        (snapshot_date,),
    ).fetchall()
    out: list[dict] = []
    for r in rows:
        out.append({
            "tmdb_id": r[0], "media_type": r[1], "title": r[2],
            "original_title": r[3], "release_date": r[4],
            "original_language": r[5], "popularity": r[6],
            "vote_average": r[7], "vote_count": r[8],
            "source_endpoint": r[9], "source_page": r[10],
            "snapshot_date": r[11],
        })
    return out


def _read_trakt(conn: sqlite3.Connection, snapshot_date: str) -> list[dict]:
    rows = conn.execute(
        """select trakt_id, tmdb_id, imdb_id, media_type, title, year,
                  watchers, rating, votes, source_endpoint, snapshot_date
           from trakt_trending
           where snapshot_date = ?""",
        (snapshot_date,),
    ).fetchall()
    out: list[dict] = []
    for r in rows:
        mt = r[3]  # media_type
        if mt == "show":
            mt = "tv"
        out.append({
            "trakt_id": r[0], "tmdb_id": r[1], "imdb_id": r[2],
            "media_type": mt, "title": r[4], "year": r[5],
            "watchers": r[6], "rating": r[7], "votes": r[8],
            "source_endpoint": r[9], "snapshot_date": r[10],
        })
    return out


def _make_key_tmdb(tmdb_id: int, media_type: str) -> str:
    return f"tmdb:{tmdb_id}:{media_type}"


def _make_key_imdb(imdb_id: str, media_type: str) -> str:
    return f"imdb:{imdb_id}:{media_type}"


def _make_key_title(title: str, media_type: str) -> str:
    norm = _normalize_title(title)
    return f"title:{norm}:{media_type}"


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", title.lower())


def _merge_by_tmdb_id(rows: list[dict], merged: dict, source: str) -> None:
    for row in rows:
        tmdb_id = row.get("tmdb_id")
        media_type = row.get("media_type", "movie")
        if not tmdb_id:
            continue
        key = _make_key_tmdb(tmdb_id, media_type)
        _upsert_candidate(merged, key, row, source)


def _merge_by_imdb_id(rows: list[dict], merged: dict, source: str) -> None:
    for row in rows:
        if row.get("tmdb_id"):
            continue  # already merged via tmdb_id
        imdb_id = row.get("imdb_id")
        media_type = row.get("media_type", "movie")
        if not imdb_id:
            continue
        key = _make_key_imdb(imdb_id, media_type)
        _upsert_candidate(merged, key, row, source)


def _merge_by_title(rows: list[dict], merged: dict, source: str) -> None:
    for row in rows:
        if row.get("tmdb_id") or row.get("imdb_id"):
            continue
        title = row.get("title", "")
        media_type = row.get("media_type", "movie")
        if not title:
            continue
        key = _make_key_title(title, media_type)
        _upsert_candidate(merged, key, row, source)


def _upsert_candidate(merged: dict, key: str, row: dict, source: str) -> None:
    tmdb_id = row.get("tmdb_id")
    imdb_id = row.get("imdb_id")
    media_type = row.get("media_type", "movie")

    if key not in merged:
        merged[key] = MergedCandidate(
            tmdb_id=tmdb_id,
            imdb_id=str(imdb_id) if imdb_id else None,
            title=row.get("title", ""),
            media_type=media_type,
        )

    c = merged[key]
    if tmdb_id and not c.tmdb_id:
        c.tmdb_id = tmdb_id
    if imdb_id and not c.imdb_id:
        c.imdb_id = str(imdb_id)

    if source == "fp":
        c.fp_items.append(row)
    elif source == "tmdb":
        # Prefer trending/day results
        if c.tmdb_data is None or row.get("source_endpoint") == "trending/day":
            c.tmdb_data = {
                "title": row.get("title"),
                "popularity": row.get("popularity"),
                "vote_average": row.get("vote_average"),
                "vote_count": row.get("vote_count"),
                "release_date": row.get("release_date"),
                "original_language": row.get("original_language"),
            }
    elif source == "trakt":
        if c.trakt_data is None:
            c.trakt_data = {
                "watchers": row.get("watchers"),
                "rating": row.get("rating"),
                "votes": row.get("votes"),
                "tmdb_id": row.get("tmdb_id"),
            }

    c.source_flags.add(source)
