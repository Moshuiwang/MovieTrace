-- Migration 006: virtual_series aggregation layer (P1.5-B)
-- Enables series-level aggregation for season-level canonical_items

create table if not exists virtual_series (
    id integer primary key autoincrement,
    tmdb_tv_id text not null,
    name text not null,
    tmdb_status text,
    tmdb_number_of_seasons integer,
    local_max_season integer,
    poll_priority text not null default 'normal',
    last_polled_at text,
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp
);

create unique index if not exists ux_virtual_series_tmdb_tv_id
on virtual_series(tmdb_tv_id);

alter table canonical_items add column virtual_series_id integer;

create index if not exists idx_canonical_items_virtual_series
on canonical_items(virtual_series_id);

alter table content_updates add column match_confidence_low integer default 0;

insert or ignore into schema_migrations(version) values (6);
