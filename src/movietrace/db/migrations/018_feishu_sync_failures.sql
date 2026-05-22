-- Migration 018: feishu_sync_failures 表
-- 用于持久化 batch_create / batch_update 失败的 record，支持次日 replay

create table if not exists feishu_sync_failures (
    id integer primary key autoincrement,
    synced_at text not null default current_timestamp,
    table_id text not null,
    record_id text,                   -- batch_update 场景有，batch_create 失败时为 null
    operation text not null,          -- 'create' | 'update'
    payload_json text not null,       -- 失败 record 的 fields，便于重试
    error_code text,
    error_message text,
    retry_count integer not null default 0,
    resolved_at text                  -- 重做成功后写入，便于历史审计
);

create index if not exists ix_feishu_sync_failures_unresolved
on feishu_sync_failures(table_id, resolved_at);
