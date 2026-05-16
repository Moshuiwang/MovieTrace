from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_VERSION = 16


SCHEMA_SQL = """
pragma foreign_keys = on;

create table if not exists schema_migrations (
    version integer primary key,
    applied_at text not null default current_timestamp
);


create table if not exists canonical_items (
    id integer primary key autoincrement,
    canonical_item_key text not null,
    title text not null,
    original_title text,
    content_type text,
    content_granularity text not null,
    parent_canonical_item_id integer references canonical_items(id),
    season_number integer,
    episode_number integer,
    year integer,
    release_date text,
    language text,
    country text,
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp
);

create unique index if not exists ux_canonical_items_key
on canonical_items(canonical_item_key);

create table if not exists external_ids (
    id integer primary key autoincrement,
    canonical_item_id integer not null references canonical_items(id) on delete cascade,
    source text not null,
    external_id text not null,
    external_granularity text,
    created_at text not null default current_timestamp
);

create unique index if not exists ux_external_ids_source_id
on external_ids(source, external_id);

create table if not exists content_updates (
    id integer primary key autoincrement,
    content_update_id text not null,
    canonical_item_id integer not null references canonical_items(id),
    update_type text not null,
    priority text,
    hot_score integer,
    baseline_match_status text,
    review_status text not null default 'pending',
    source_summary_json text,
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp
);

create table if not exists api_cache (
    id integer primary key autoincrement,
    source text not null,
    cache_key text not null,
    response_json text not null,
    fetched_at text not null default current_timestamp,
    expires_at text
);

create unique index if not exists ux_api_cache_source_key
on api_cache(source, cache_key);

insert or ignore into schema_migrations(version) values (1);
"""


def connect_database(path: str | Path) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("pragma foreign_keys = on")
    return conn


def _apply_migration(conn: sqlite3.Connection, version: int, sql: str) -> None:
    """Apply a migration if not already recorded."""
    applied = conn.execute(
        "select 1 from schema_migrations where version = ?", (version,)
    ).fetchone()
    if not applied:
        conn.executescript(sql)
        conn.execute(
            "insert or ignore into schema_migrations(version) values (?)", (version,)
        )


def _load_migration_sql(filename: str) -> str:
    migrations_dir = Path(__file__).parent / "migrations"
    return (migrations_dir / filename).read_text()


def initialize_database(path: str | Path) -> None:
    with connect_database(path) as conn:
        conn.executescript(SCHEMA_SQL)
        _apply_migration(conn, 2, _load_migration_sql("002_flixpatrol_top10.sql"))
        _apply_migration(conn, 3, _load_migration_sql("003_candidates.sql"))
        _apply_migration(conn, 4, _load_migration_sql("004_candidate_matches.sql"))
        _apply_migration(conn, 5, _load_migration_sql("005_upstream_tables.sql"))
        _apply_migration(conn, 6, _load_migration_sql("006_virtual_series.sql"))
        _apply_migration(conn, 7, _load_migration_sql("007_multi_source_trending.sql"))
        _apply_migration(conn, 8, _load_migration_sql("008_api_usage_log.sql"))
        _apply_migration(conn, 9, _load_migration_sql("009_tmdb_structured_fields.sql"))
        _apply_migration(conn, 10, _load_migration_sql("010_multi_source_structured_fields.sql"))
        _apply_migration(conn, 11, _load_migration_sql("011_external_id_namespace.sql"))
        _apply_migration(conn, 12, _load_migration_sql("012_source_fetch_runs.sql"))
        _apply_migration(conn, 13, _load_migration_sql("013_tmdb_namespace_cleanup.sql"))
        _apply_migration(conn, 14, _load_migration_sql("014_content_updates_event_history.sql"))
        _apply_migration(conn, 15, _load_migration_sql("015_api_cache_unique_key.sql"))
        _apply_migration(conn, 16, _load_migration_sql("016_drop_legacy_tables.sql"))
        conn.commit()
