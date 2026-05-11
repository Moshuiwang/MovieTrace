create table if not exists flixpatrol_top10 (
    id integer primary key autoincrement,
    fp_id text not null,
    title text not null,
    content_type text not null,
    platform text not null,
    country text not null,
    snapshot_date text not null,
    ranking integer not null check (ranking between 1 and 10),
    ranking_last integer,
    value integer,
    days_total integer,
    tmdb_id integer,
    imdb_id integer,
    raw_payload_json text not null,
    collected_at text not null default current_timestamp
);

create unique index if not exists ux_fp_top10_dedup
    on flixpatrol_top10(fp_id, snapshot_date);

create index if not exists idx_fp_top10_date
    on flixpatrol_top10(snapshot_date);

create index if not exists idx_fp_top10_tmdb
    on flixpatrol_top10(tmdb_id) where tmdb_id is not null;
