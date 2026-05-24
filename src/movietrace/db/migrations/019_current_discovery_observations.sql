-- Migration 019: current discovery items + observation history
-- ADR-0016: discovery output becomes one current workbench row per stable title,
-- while daily heat snapshots are preserved as observations.

create table if not exists current_discovery_items (
    id integer primary key autoincrement,
    discovery_key text not null,
    canonical_item_id integer references canonical_items(id),
    content_type text not null check (content_type in ('movie', 'tv')),
    tmdb_id integer not null,
    title text,
    original_title text,
    title_zh text,
    first_discovered_date text not null,
    last_discovered_date text not null,
    discovery_count integer not null default 1 check (discovery_count >= 0),
    latest_hot_score real,
    latest_priority text,
    latest_baseline_match_status text,
    latest_match_confidence_low integer not null default 0,
    latest_source_summary_json text,
    stable_metadata_json text,
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp,
    check (discovery_key = 'discovery:' || content_type || ':' || tmdb_id)
);

create unique index if not exists ux_current_discovery_items_key
on current_discovery_items(discovery_key);

create unique index if not exists ux_current_discovery_items_type_tmdb
on current_discovery_items(content_type, tmdb_id);

create index if not exists ix_current_discovery_items_last_discovered_date
on current_discovery_items(last_discovered_date);

create index if not exists ix_current_discovery_items_priority_score
on current_discovery_items(latest_priority, latest_hot_score);

create table if not exists discovery_observations (
    id integer primary key autoincrement,
    discovery_key text not null references current_discovery_items(discovery_key) on delete cascade,
    observed_date text not null,
    hot_score real,
    priority text,
    source_summary_json text,
    raw_inputs_json text,
    score_breakdown_json text,
    source_status_json text,
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp
);

create unique index if not exists ux_discovery_observations_key_date
on discovery_observations(discovery_key, observed_date);

create index if not exists ix_discovery_observations_observed_date
on discovery_observations(observed_date);
