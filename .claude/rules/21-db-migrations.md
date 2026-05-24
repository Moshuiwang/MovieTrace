---
name: db-migrations
description: SQLite schema 变更规则、migration 编号、SCHEMA_VERSION 同步、唯一索引清单、备份策略。
paths:
  - "src/movietrace/db/**"
include: ["src/movietrace/db/**"]
---

# 数据库与 Migration 规则

## schema 变更前置条件

- 必须有任务包**明确授权 schema 变更**（CLAUDE.md 第 4 条铁律）
- 必须写 migration plan：变更点、回滚方法、备份策略
- 必须在执行 migration **前**做 DB 备份：`data/movietrace_backup_<YYYYMMDD>_<HHMM>[_<note>].db`

## Migration 文件规则

- 命名：`{NNN}_{snake_case_description}.sql`（NNN 三位数）
- 编号递增、不可跳号、不可复用（当前最大 016）
- SQL 必须用 `DROP TABLE IF EXISTS` / `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` 兼容已运行环境
- 一次 migration 一个原子变更（建表 / DROP / 加列 / 加索引），不混合
- 不可逆变更（如 DROP TABLE）必须在 ADR 记录决策（参考 [ADR-0014](../../docs/decisions/0014-legacy-schema-cleanup.md)）

## SCHEMA_VERSION 同步

`src/movietrace/db/schema.py` 中：
- `SCHEMA_SQL` 字典必须与 migrations 累积结果一致（新实例直接初始化等价）
- `SCHEMA_VERSION` 常量必须 = 最大 migration 编号
- 删除表时：DROP migration + `SCHEMA_SQL` 同步删除 CREATE 语句，防止新实例误建

## 关键唯一索引（不可丢）

| 索引 | 表 | 防什么重复 |
|---|---|---|
| `ux_canonical_items_key` | canonical_items | 业务键去重 |
| `ux_external_ids_source_id` | external_ids | (source, external_id) 唯一 |
| `ux_content_updates_update_id` | content_updates | 同一事件 ID 不重复 |
| `ux_virtual_series_tmdb_tv_id` | virtual_series | 每个 TMDb TV 一行 |
| `ux_api_cache_source_key` | api_cache | (source, cache_key) 唯一 |

## 数据流参考

完整 schema、表关系、数据流：[`24-db-schema-map.md`](24-db-schema-map.md)。
