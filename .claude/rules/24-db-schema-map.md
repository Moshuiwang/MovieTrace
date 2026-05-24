---
name: db-schema-map
description: SQLite 数据库地图——核心业务表 / A 库镜像 / 外部源快照 / 运维表 / 关键唯一索引 / 数据流图。涉及任意表查询、JOIN、唯一约束、字段名、cascade、已 DROP 遗留表时必读。
paths:
  - "src/movietrace/db/**"
  - "src/movietrace/pipeline/**"
  - "src/movietrace/feishu/**"
  - "src/movietrace/reports/**"
  - "src/movietrace/feedback/**"
  - "tests/db/**"
  - "tests/pipeline/**"
include:
  - "src/movietrace/db/**"
  - "src/movietrace/pipeline/**"
  - "src/movietrace/feishu/**"
  - "src/movietrace/reports/**"
  - "src/movietrace/feedback/**"
  - "tests/db/**"
  - "tests/pipeline/**"
---

# 数据库地图（`data/movietrace.db`，schema version 19）

SQLite，17 张活跃表。备份命名 `movietrace_backup_<YYYYMMDD>_<HHMM>.db`。

## 核心业务表（B 库主链路）

| 表 | 用途 | 重点字段 |
|----|------|---------|
| `canonical_items` | B 库标准化条目（movie / tv series / tv season）| `id`（PK）· `canonical_item_key`（unique，业务键）· `content_type`（movie/tv）· `content_granularity`（series/season/episode）· `parent_canonical_item_id`（season → series 自引用）· `season_number` · `virtual_series_id`（→ virtual_series.id）|
| `external_ids` | TMDb / IMDb / Trakt → canonical_items 映射 | `canonical_item_id`（FK，cascade）· `source`（tmdb/imdb/trakt）· `external_id` · UNIQUE(source, external_id) |
| `content_updates` | 事件历史表（ADR-0012）。当前只写 `new_season`；`new_discovery` 已迁出到 current_discovery_items + discovery_observations（ADR-0016 / P1.57） | `content_update_id`（unique；`new_season:{tmdb_tv_id}:{season}:{date}`；历史 discovery 行 `discovery:{movie\|tv}:{tmdb_id}:{date}` 保留）· `canonical_item_id` · `update_type` · `priority`（P0/P1/P2）· `hot_score` · `baseline_match_status` · `match_confidence_low`（0/1）· `source_summary_json` |
| `current_discovery_items` | ADR-0016 当前发现项，一稳定内容一行 | `discovery_key`（unique，`discovery:{movie\|tv}:{tmdb_id}`，**不含日期**）· `content_type` · `tmdb_id` · `first_discovered_date` · `last_discovered_date` · `discovery_count` · `latest_hot_score` · `latest_priority` · `latest_source_summary_json` · `stable_metadata_json` |
| `discovery_observations` | ADR-0016 有效观察日留痕，一 `discovery_key + observed_date` 一行 | `discovery_key`（FK → current_discovery_items.discovery_key）· `observed_date` · `source_summary_json` · `raw_inputs_json` · `score_breakdown_json` · `hot_score` · `priority` |
| `virtual_series` | TV 系列聚合层（按 tmdb_tv_id 一行）；用于"新季追踪" | `tmdb_tv_id`（unique）· `tmdb_status`（Returning Series / Ended / ...）· `tmdb_number_of_seasons` · `local_max_season`（B 库已收录最高季）· `poll_priority`（urgent / normal / low / skip，由 tmdb_status 推导）· `last_polled_at` |
| `baseline_quality_issues` | A 库实体匹配的质量问题日志（运行时按需建表）| `upstream_program_id` · `issue_type`（low_confidence / no_match / ...）· `source_name` · `confidence` · `reason` |

## A 库镜像表（上游业务库快照，只读）

| 表 | 用途 |
|----|------|
| `upstream_programs` | A 库节目主表镜像；`online_flag` 过滤"在售"剧集 |
| `upstream_episodes` | A 库子节目（季/集），`fk_program_content_id` 关联到 upstream_programs |

## 外部源快照表（trending 抓取留痕）

| 表 | 用途 |
|----|------|
| `tmdb_trending` | 每日 TMDb trending/popular 快照，按 `snapshot_date` 分区 |
| `trakt_trending` | 每日 Trakt trending 快照 |
| `flixpatrol_top10` | FlixPatrol top10 抓取快照，6 个平台 × 多国家 |

## 运维 / 监控表

| 表 | 用途 | 重点字段 |
|----|------|---------|
| `api_cache` | 外部 API 响应缓存（TMDb detail / OMDb / Trakt 等，TTL 24-72h）| `source` + `cache_key`（unique）· `response_json` · `fetched_at` · `expires_at`（migration 015 加 unique index 防 cartesian 重复）|
| `api_usage_log` | 每次外部 API 调用的配额监控 | `service` · `endpoint` · `request_date` · `status`（ok / error / quota_error / rate_limited / cache_hit）· `key_fingerprint`（多 key 轮换时区分）|
| `source_fetch_runs` | 每日各源抓取运行状态机 | `target_date` · `source` · `status`（fresh / fallback / failed）· `rows_used` |
| `feishu_sync_failures` | P1.45 飞书同步失败持久化与次日 replay | `table_id` · `record_id` · `operation` · `payload_json` · `retry_count` · `resolved_at` |
| `schema_migrations` | migration 版本号 | `version`（当前最大 19）· `applied_at` |

## 已 DROP 的遗留表（migration 016，ADR-0014）

`feishu_import_runs` · `source_records` · `baseline_items` · `candidates` · `candidate_matches` · `match_candidates` — Phase 0 / 翻转前残留，已无活跃写路径。**禁止重新引用**。

## 关键唯一索引

| 索引 | 表 | 防什么重复 |
|------|-----|----------|
| `ux_canonical_items_key` | canonical_items | 业务键去重 |
| `ux_external_ids_source_id` | external_ids | (source, external_id) 唯一 |
| `ux_content_updates_update_id` | content_updates | 同一事件 ID 不重复 |
| `ux_virtual_series_tmdb_tv_id` | virtual_series | 每个 TMDb TV 一行 |
| `ux_api_cache_source_key` | api_cache | (source, cache_key) 唯一（P1.21.5 加）|
| current_discovery_items.discovery_key UNIQUE | current_discovery_items | 一稳定内容一行（ADR-0016）|
| (discovery_observations.discovery_key, observed_date) UNIQUE | discovery_observations | 同一稳定内容同日只一条 observation |

## 数据流（简化）

```
外部源（TMDb/Trakt/OMDb/FlixPatrol）
  → sources/*.py 抓取
  → tmdb_trending / trakt_trending / flixpatrol_top10（源快照表）
  → multi_source_merge.py 合并去重
  → scoring.py 计算 hot_score
  → discovery.py 写 current_discovery_items + discovery_observations（ADR-0016）；new_season 仍走 content_updates 事件路径

A 库快照（upstream_programs/episodes）
  → entity_matching.py 与 TMDb 匹配
  → canonical_items + external_ids
  → virtual_series 聚合
  → baseline_tracking.py 检测 TMDb 新季
  → content_updates（new_season）

current_discovery_items / discovery_observations / content_updates
  → export_writer.py → reports/*.md + .json
  → feishu/sync.py → 飞书"热点发现"子表
  → feishu/gap_sync.py（直接从 virtual_series 实时算缺口）→ 飞书"A库缺口"子表

运营人工操作飞书表
  → feedback/pull.py 拉回 → reports/feedback/*.json
  → feedback/weekly_report.py → reports/feedback/feedback_log_YYYY-Www.md
```

## 配套规则

- 改 `src/movietrace/db/**`（schema / migration）→ [`21-db-migrations.md`](21-db-migrations.md)
- 不可逆变更必须有 ADR（参考 [ADR-0012](../../docs/decisions/0012-content-updates-event-history.md) · [ADR-0014](../../docs/decisions/0014-legacy-schema-cleanup.md) · [ADR-0016](../../docs/decisions/0016-current-discovery-with-observations.md)）
