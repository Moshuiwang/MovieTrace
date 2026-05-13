-- Migration 008: API usage logging (P1.8-D)
-- Tracks every external HTTP request across all API services.

create table if not exists api_usage_log (
    id integer primary key autoincrement,
    service text not null,
    endpoint text not null,
    operation text,
    request_date text not null,
    started_at text not null default current_timestamp,
    finished_at text,
    status text not null,
    http_status integer,
    cache_status text,
    quota_error integer not null default 0,
    rate_limited integer not null default 0,
    duration_ms integer,
    item_count integer,
    error_code text,
    error_message text,
    key_fingerprint text,
    metadata_json text
);

create index if not exists idx_api_usage_log_service
on api_usage_log(service, request_date);

create index if not exists idx_api_usage_log_status
on api_usage_log(status);

create index if not exists idx_api_usage_log_endpoint
on api_usage_log(endpoint);

create index if not exists idx_api_usage_log_quota
on api_usage_log(service, quota_error);

insert or ignore into schema_migrations(version) values (8);
