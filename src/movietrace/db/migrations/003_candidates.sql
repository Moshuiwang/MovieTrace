create table if not exists candidates (
    id integer primary key autoincrement,
    canonical_item_id integer,
    tmdb_id integer,
    imdb_id text,
    title text not null,
    content_type text not null check (content_type in ('movie', 'tv_show')),
    hot_score real not null check (hot_score between 0 and 100),
    priority text not null check (priority in ('P0', 'P1', 'P2', 'P3')),
    discovery_source text not null check (discovery_source in ('new_release', 'global_hot', 'both')),
    score_breakdown_json text not null,
    reason_text text,
    snapshot_date text not null,
    computed_at text not null default current_timestamp,
    unique (canonical_item_id, snapshot_date)
);

create index if not exists idx_candidates_priority on candidates(priority);
create index if not exists idx_candidates_score on candidates(hot_score desc);
create index if not exists idx_candidates_snapshot on candidates(snapshot_date);
