-- Migration 007: multi-source trending tables (P1.7-A)
-- Adds tmdb_trending and trakt_trending as independent hot-source stores,
-- parallel to flixpatrol_top10.

create table if not exists tmdb_trending (
    id integer primary key autoincrement,
    tmdb_id integer not null,
    media_type text not null,
    title text not null,
    original_title text,
    release_date text,
    original_language text,
    popularity real not null,
    vote_average real,
    vote_count integer,
    source_endpoint text not null,
    source_page integer not null,
    snapshot_date text not null,
    raw_payload_json text not null,
    collected_at text not null default current_timestamp
);

create unique index if not exists ux_tmdb_trending_dedup
on tmdb_trending(tmdb_id, media_type, source_endpoint, snapshot_date);

create index if not exists idx_tmdb_trending_snapshot_date
on tmdb_trending(snapshot_date);

create index if not exists idx_tmdb_trending_tmdb_id
on tmdb_trending(tmdb_id);

create table if not exists trakt_trending (
    id integer primary key autoincrement,
    trakt_id integer not null,
    tmdb_id integer,
    imdb_id text,
    media_type text not null,
    title text not null,
    year integer,
    watchers integer not null,
    rating real,
    votes integer,
    source_endpoint text not null,
    snapshot_date text not null,
    raw_payload_json text not null,
    collected_at text not null default current_timestamp
);

create unique index if not exists ux_trakt_trending_dedup
on trakt_trending(trakt_id, media_type, snapshot_date);

create index if not exists idx_trakt_trending_snapshot_date
on trakt_trending(snapshot_date);

create index if not exists idx_trakt_trending_tmdb_id
on trakt_trending(tmdb_id);

insert or ignore into schema_migrations(version) values (7);
