from __future__ import annotations

import re
import sqlite3


def derive_poll_priority(tmdb_status: str | None) -> str:
    """Map TMDb tv status to poll_priority value."""
    if not tmdb_status:
        return "normal"
    mapping = {
        "Returning Series": "urgent",
        "In Production": "normal",
        "Ended": "low",
        "Canceled": "skip",
        "Pilot": "skip",
        "Planned": "skip",
    }
    return mapping.get(tmdb_status, "normal")


def extract_season_number(name: str) -> int | None:
    """Extract season number from a name like 'Better Call Saul S01' → 1."""
    m = re.search(
        r"(?<![A-Za-z0-9])S(\d{1,2})(?![A-Za-z0-9])", name, flags=re.IGNORECASE
    )
    return int(m.group(1)) if m else None


def upsert_virtual_series(
    conn: sqlite3.Connection, tmdb_tv_id: str, tmdb_details: dict
) -> int:
    """Insert or update a virtual_series row, return its id."""
    name = tmdb_details.get("name", "")
    status = tmdb_details.get("status")
    num_seasons = tmdb_details.get("number_of_seasons")

    existing = conn.execute(
        "select id, local_max_season from virtual_series where tmdb_tv_id = ?",
        (tmdb_tv_id,),
    ).fetchone()

    if existing:
        vs_id = int(existing[0])
        conn.execute(
            """update virtual_series
               set name = ?, tmdb_status = ?, tmdb_number_of_seasons = ?,
                   updated_at = datetime('now')
               where id = ?""",
            (name, status, num_seasons, vs_id),
        )
        return vs_id

    conn.execute(
        """insert into virtual_series(
            tmdb_tv_id, name, tmdb_status, tmdb_number_of_seasons, poll_priority
        ) values (?, ?, ?, ?, ?)""",
        (
            tmdb_tv_id,
            name,
            status,
            num_seasons,
            derive_poll_priority(status),
        ),
    )
    return int(conn.execute("select last_insert_rowid()").fetchone()[0])


def link_to_virtual_series(
    conn: sqlite3.Connection, canonical_item_id: int, virtual_series_id: int
) -> None:
    """Set canonical_items.virtual_series_id."""
    conn.execute(
        "update canonical_items set virtual_series_id = ? where id = ?",
        (virtual_series_id, canonical_item_id),
    )


def update_local_max_season(
    conn: sqlite3.Connection, virtual_series_id: int, season_number: int
) -> None:
    """Update local_max_season if season_number exceeds current value."""
    row = conn.execute(
        "select local_max_season from virtual_series where id = ?",
        (virtual_series_id,),
    ).fetchone()
    if row and (row[0] is None or season_number > row[0]):
        conn.execute(
            "update virtual_series set local_max_season = ?, updated_at = datetime('now') where id = ?",
            (season_number, virtual_series_id),
        )


def _extract_tmdb_tv_id_from_key(canonical_item_key: str) -> str | None:
    """Extract tmdb_tv_id from canonical_item_key like 'tmdb:tv:1399:season:1'."""
    parts = canonical_item_key.split(":")
    if len(parts) >= 3 and parts[0] == "tmdb" and parts[1] == "tv":
        return parts[2]
    return None


def find_or_create_virtual_series_for_canonical_item(
    conn: sqlite3.Connection,
    canonical_item_id: int,
    tmdb_client: object,
) -> int | None:
    """Look up the tmdb external_id for a canonical_item, fetch TV details,
    upsert virtual_series, and return the virtual_series id.

    Falls back to extracting tmdb_tv_id from canonical_item_key if no
    direct external_id row exists (handles multi-season shows sharing one tmdb_id).

    Returns None on failure.
    """
    row = conn.execute(
        """select external_id from external_ids
           where canonical_item_id = ? and source = 'tmdb'
           order by id limit 1""",
        (canonical_item_id,),
    ).fetchone()

    if row:
        raw_id = row[0]
        # Strip tv:/movie: namespace prefix before passing to TMDb API (P1.9-hotfix-E)
        if raw_id.startswith("tv:") or raw_id.startswith("movie:"):
            tmdb_tv_id = raw_id.split(":", 1)[1]
        else:
            tmdb_tv_id = raw_id
    else:
        # Fallback: extract from canonical_item_key
        key_row = conn.execute(
            "select canonical_item_key from canonical_items where id = ?",
            (canonical_item_id,),
        ).fetchone()
        if not key_row:
            return None
        tmdb_tv_id = _extract_tmdb_tv_id_from_key(key_row[0])
        if not tmdb_tv_id:
            return None

    try:
        details = tmdb_client.get_tv_details(tmdb_tv_id)
    except Exception:
        return None

    if not details or not details.get("name"):
        return None

    vs_id = upsert_virtual_series(conn, tmdb_tv_id, details)
    return vs_id
