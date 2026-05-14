create table if not exists source_fetch_runs (
    id integer primary key autoincrement,
    target_date text not null,
    source text not null,
    status text not null,
    source_snapshot_date text,
    started_at text not null default current_timestamp,
    finished_at text,
    rows_fetched integer,
    rows_inserted integer,
    rows_used integer,
    error_message text,
    config_json text,
    created_at text not null default current_timestamp,
    updated_at text not null default current_timestamp
);

create unique index if not exists ux_source_fetch_runs_date_source
on source_fetch_runs(target_date, source);

create index if not exists idx_source_fetch_runs_date_source
on source_fetch_runs(target_date, source);

create index if not exists idx_source_fetch_runs_source_status
on source_fetch_runs(source, status);

create index if not exists idx_source_fetch_runs_snapshot_date
on source_fetch_runs(source_snapshot_date);
