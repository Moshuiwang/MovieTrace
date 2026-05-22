# MovieTrace 项目地图

> Agent 启动时按本图**分层加载**，不做全量读取。
> 使用者/开发者也可用本图快速定位代码、表、脚本所在位置。
> 最后更新：2026-05-20（去除易漂移计数；schema version 17）

---

## § 1. 项目状态文档（顶层 4 个 .md）

| 文件 | 用途 | 何时读 |
|------|------|--------|
| [`STATE.md`](../STATE.md) | 当前阶段、最近完成、进行中任务、review 跟进项 | **每次会话启动必读**（第 1 步）|
| [`SCOPE.md`](../SCOPE.md) | V1/V2 范围边界，"做什么不做什么" | 启动必读（防止越界）|
| [`CLAUDE.md`](../CLAUDE.md) | Claude Code 协作宪法（12 条规则 + 4 易踩坑）| AI 入口 |
| [`AGENTS.md`](../AGENTS.md) | 指针入口（→ CLAUDE.md），Codex / Cursor / Cline 等工具读取 | AI 入口 |

**预算：** 启动默认 3 个文件（STATE + SCOPE + 本文件）≈ 600 行。

---

## § 2. 文档地图（docs/ 下）

### 第一层：操作层（运行 / 排障 / 反馈时读取）

| 场景 | 文件 | 为什么 |
|------|------|--------|
| 日常运行 | [`docs/operations/runbook.md`](operations/runbook.md) | CLI 命令、备份、排障 |
| 飞书运营字段规范 | [`docs/operations/feishu_feedback_spec.md`](operations/feishu_feedback_spec.md) | P1.23 新增：运营怎么填、填了之后怎么影响系统 |
| 反馈周报使用指南 | [`docs/operations/feedback_report_guide.md`](operations/feedback_report_guide.md) | P1.23 起改为 `export-feedback-report` 自动生成；说明字段含义 |
| 排查故障 | [`docs/workflow/troubleshooting.md`](workflow/troubleshooting.md) | 排查方法论 |
| 会话收尾 | [`docs/workflow/session-checklist.md`](workflow/session-checklist.md) | 收尾清单 |
| Git / PR 工作流 | [`.claude/rules/50-git-workflow.md`](../.claude/rules/50-git-workflow.md) | 分支、commit、push、PR、CI/CD、合并后同步规则 |
| 完成任务汇报 | [`docs/workflow/report-format.md`](workflow/report-format.md) | 报告格式 |
| 写新任务包 | [`docs/tasks/TEMPLATE.md`](tasks/TEMPLATE.md) | 任务包模板 |
| 写新 ADR | [`docs/decisions/README.md`](decisions/README.md) | ADR 索引和写法 |

### 第二层：决策层（边界争议 / 产品判断 / 架构问题）

| 场景 | 文件 | 为什么 |
|------|------|--------|
| V1/V2 边界 | [`SCOPE.md`](../SCOPE.md) + [`docs/product_roadmap.md`](product_roadmap.md) | 定位和路线图 |
| 当前需求基线 | [`docs/requirements.md`](requirements.md) | V3 版需求（含 V1.5 翻转）|
| 架构决策 | [`docs/decisions/`](decisions/) | 15 篇 ADR，关键看 0007（系统翻转）/ 0012（content_updates 事件化）/ 0014（schema 清理）/ 0015（飞书文档导入）|
| 飞书运营同步背景 | [`docs/notes/feishu_ops_sync_requirements.md`](notes/feishu_ops_sync_requirements.md) | 运行观察期新增需求草案 |
| V1 收口复盘 | [`docs/reviews/v1_closeout_review.md`](reviews/v1_closeout_review.md) | V1 能力和边界总结 |

### 第三层：历史层（默认不整篇读取，先 `rg` 再读片段）

| 内容 | 文件 | 搜索关键词示例 |
|------|------|---------------|
| Phase 1 全历史 | [`docs/history/phase1_state_archive.md`](history/phase1_state_archive.md) | `Phase 1.7` `P1.8-D` `virtual_series` |
| 已完成任务包 | [`docs/tasks/p1.*.md`](tasks/) | `OMDb` `migration 012` `FatalApiError` |
| 历史 journal 存档 | [`journal/`](../journal/) | 仅查历史，不再新增 |
| 旧验证报告 | [`reports/`](../reports/) | `flixpatrol_zero` `e2e_validation` |
| 参考资料 | [`docs/reference/`](reference/) | 外部 API 文档片段、字段映射 |

```bash
# 例：查 Phase 1.8 的详细执行结果
rg -n "P1.8-D|P1.8-E|008_api_usage" docs/history/phase1_state_archive.md docs/tasks/

# 例：查某个功能的实现记录
rg -n "virtual_series|canonical_items|OMDb" docs/history/phase1_state_archive.md
```

---

## § 3. 代码地图（src/movietrace/）

入口 + 6 个子包；所有运行通过 `PYTHONPATH=src python -m movietrace.cli <command>`。

### 入口与公用

| 文件 | 职责 |
|------|------|
| `cli.py` | CLI 入口；主要子命令见下表 |
| `config.py` | 加载 `~/.config/movietrace/secrets.json` 和 `config.yaml` |
| `__init__.py` | 包初始化 |

**主要 CLI 子命令（来源：`cli.py` 中 `sub.add_parser`）：**

| 命令 | 用途 | 调度 |
|------|------|------|
| `daily-discover` | 每日热点发现主流水线（FlixPatrol + TMDb + Trakt + OMDb → 评分 → 写 content_updates） | cron 每日 |
| `baseline-track` | A 库基线 TV 剧集新季追踪（按 TMDb status 决定 routine/catch-up） | 每周 |
| `export-recommendations` | 导出最近 N 天 content_updates 到 `reports/latest.md` + JSON | 跟着 daily-discover |
| `export-baseline-updates` | 导出 baseline 新季更新到 `reports/baseline_latest.md` + JSON | 跟着 baseline-track |
| `inspect-baseline` | 查看 A 库 / B 库 / virtual_series 数量统计 | 手动 |
| `inspect-updates` | 查询 content_updates 表内容（按时间/优先级筛选） | 手动 |
| `inspect-api-usage` | 查询 api_usage_log（配额监控） | 手动 |
| `fetch-tmdb-trending` | 单独抓 TMDb trending（debug 用） | 手动 |
| `fetch-trakt-trending` | 单独抓 Trakt trending（debug 用） | 手动 |
| `sync-feishu-table` | 把 `reports/latest.json` upsert 到飞书"热点发现"子表 | 跟着 daily-discover |
| `sync-feishu-gap-table` | 把 SQL 实时计算的 A 库缺口 upsert 到飞书"A库缺口"子表 | 跟着 baseline-track |
| `sync-feishu-doc` | 把 `reports/latest.md` 导入为飞书文档（P1.21.9 改用 drive/v1/import_task） | 跟着 daily-discover |
| `notify-feishu` | 飞书 IM 消息（success/warn/error） | 各脚本失败时 |
| `validate-feishu` | 验证飞书 API 连通性 | 一次性 |
| `check-feishu-schema` | 验证飞书表字段名/类型 | 一次性 |
| `pull-feishu-feedback` | P1.23：拉飞书"热点发现 + A库缺口"两张表运营回填到本地 JSON（只读）| 每周日手动 |
| `export-feedback-report` | P1.23：把 pull JSON 转为 A-E 五节 ISO 周报 Markdown | 跟着 pull |
| `setup-feishu-fields` | P1.24：幂等创建/重命名飞书发现运行日志表字段（在 sync 主流程中也会自动 ensure） | 首次部署或手动 |

### 子包

| 子包 | 职责 | 关键文件 |
|------|------|---------|
| `db/` | SQLite schema + migrations | `schema.py`（DDL + initialize_database）· `migrations/002…017*.sql` |
| `sources/` | 外部数据源客户端（无业务逻辑）| `tmdb.py`（trending/detail/search）· `trakt.py`（trending/search）· `omdb.py`（评分补充）· `flixpatrol.py`（HTML 解析）· `flixpatrol_api.py`（付费 API，目前 402）· `http.py`（公共 UA / 重试 / 配额）|
| `pipeline/` | 业务流水线 | `discovery.py`（每日热点主链路）· `baseline_tracking.py`（A 库基线新季）· `scoring.py`（hot_score 0-100 加权）· `multi_source_merge.py`（多源候选合并）· `entity_matching.py`（A 库↔TMDb 匹配 + baseline_quality_issues 写入）· `virtual_series.py`（TV 系列聚合 + poll_priority 推导）· `poll_scheduler.py`（A 库 TV 轮询计划生成）· `tmdb_detail_cache.py`（24h api_cache 复用）· `tmdb_trending.py` / `trakt_trending.py`（写各自快照表）· `omdb_enrichment.py`（OMDb 评分补充）· `source_fetch_status.py`（source_fetch_runs 状态机）|
| `reports/` | 报告生成 | `export_writer.py`（MD + JSON 双写）· `inspect_renderer.py`（CLI 查询渲染）|
| `feishu/` | 飞书集成（V1 运营同步层） | `baseline.py`（tenant token + 文件缓存）· `_http.py`（共享 REST helpers：request_json / batch_create / batch_update / batch_delete / multipart / upload_media_file）· `sync.py`（热点发现子表 upsert + sync_doc 导入文档；P1.24 起内嵌 ensure_table_fields + 8 新字段映射）· `gap_sync.py`（A 库缺口子表 upsert + 追上行删除）· `notify.py`（IM 消息）· `schema_setup.py`（P1.24：幂等创建/重命名 bitable 字段，权限不足直接 raise） |
| `feedback/` | P1.23 运营反馈回流 | `pull.py`（飞书两张表 paginated 拉取 + 重试）· `weekly_report.py`（A-E 五节周报生成器）|
| `logging/` | 日志辅助 | （早期 phase 产物，目前最小化使用） |

---

## § 4. 脚本地图（scripts/）

### 日常调度（cron 或人工）

| 脚本 | 何时跑 | 内部链路 |
|------|--------|----------|
| `daily_run.sh` | **cron 每日 08:00 +08** | `daily-discover` → `export-recommendations` → `sync-feishu-table` → `sync-feishu-doc` → `notify-feishu` |
| `baseline_run.sh` | 每周（上层调度） | `baseline-track --mode routine` → `export-baseline-updates` → `sync-feishu-gap-table` → `notify-feishu` |
| `weekly_feedback.sh` | **每周日手动** | `pull-feishu-feedback` → `export-feedback-report` → `notify-feishu` |

三个脚本都 `export TZ='Asia/Shanghai'`（防御 UTC 服务器漂移），日志写入 `reports/logs/`。

### 一次性 / 验证脚本

| 脚本 | 用途 | 状态 |
|------|------|------|
| `import_upstream_data.py` | 从 A 库快照（CSV/JSON）导入 `upstream_programs` + `upstream_episodes` | 在每次 A 库更新时手动跑 |
| `p1.5_e_match_all.py` | P1.5 阶段：A 库全量实体匹配 → canonical_items + external_ids | 历史一次性 |
| `p1_24_backfill_in_play_season.py` | P1.24：扫历史 content_updates 行，从 api_cache 提 `last_episode_to_air` 合入 source_summary（零 TMDb 调用） | 一次性，rename "季号" 后跑 |
| `p1_5_c_backfill_virtual_series.py` | P1.5 阶段：从 canonical_items 回填 virtual_series | 历史一次性 |
| `sup_a_flixpatrol_check.py` / `sup_c_flixpatrol_matching.py` / `sup_g_flixpatrol_api_check.py` | FlixPatrol 接入验证（Phase 0+） | 历史一次性 |
| `verify_source_db.py` | A 库源 DB 字段一致性检查 | 偶尔用 |

---

## § 5. 数据库地图（`data/movietrace.db`，schema version 17）

SQLite，14 张活跃表。备份命名 `movietrace_backup_<YYYYMMDD>_<HHMM>.db`。

### 核心业务表（B 库主链路）

| 表 | 用途 | 重点字段 |
|----|------|---------|
| `canonical_items` | B 库标准化条目（movie / tv series / tv season）| `id`（PK）· `canonical_item_key`（unique，业务键）· `content_type`（movie/tv）· `content_granularity`（series/season/episode）· `parent_canonical_item_id`（season → series 自引用）· `season_number` · `virtual_series_id`（→ virtual_series.id）|
| `external_ids` | TMDb / IMDb / Trakt → canonical_items 映射 | `canonical_item_id`（FK，cascade）· `source`（tmdb/imdb/trakt）· `external_id` · UNIQUE(source, external_id) |
| `content_updates` | **事件历史表**（ADR-0012）；新发现/新季事件 | `content_update_id`（unique，格式：`discovery:{movie\|tv}:{tmdb_id}:{date}` 或 `new_season:{tmdb_tv_id}:{season}:{date}`）· `canonical_item_id` · `update_type`（new_discovery / new_season）· `priority`（P0/P1/P2）· `hot_score` · `baseline_match_status` · `match_confidence_low`（0/1）· `source_summary_json` |
| `virtual_series` | TV 系列聚合层（按 tmdb_tv_id 一行）；用于"新季追踪" | `tmdb_tv_id`（unique）· `tmdb_status`（Returning Series / Ended / ...）· `tmdb_number_of_seasons` · `local_max_season`（B 库已收录最高季）· `poll_priority`（urgent / normal / low / skip，由 tmdb_status 推导）· `last_polled_at` |
| `baseline_quality_issues` | A 库实体匹配的质量问题日志（运行时按需建表）| `upstream_program_id` · `issue_type`（low_confidence / no_match / ...）· `source_name` · `confidence` · `reason` |

### A 库镜像表（上游业务库快照，只读）

| 表 | 用途 |
|----|------|
| `upstream_programs` | A 库节目主表镜像；`online_flag` 过滤"在售"剧集 |
| `upstream_episodes` | A 库子节目（季/集），`fk_program_content_id` 关联到 upstream_programs |

### 外部源快照表（trending 抓取留痕）

| 表 | 用途 |
|----|------|
| `tmdb_trending` | 每日 TMDb trending/popular 快照，按 `snapshot_date` 分区 |
| `trakt_trending` | 每日 Trakt trending 快照 |
| `flixpatrol_top10` | FlixPatrol top10 抓取快照，6 个平台 × 多国家 |

### 运维 / 监控表

| 表 | 用途 | 重点字段 |
|----|------|---------|
| `api_cache` | 外部 API 响应缓存（TMDb detail 24h、OMDb 等）| `source` + `cache_key`（unique）· `response_json` · `fetched_at` · `expires_at`（migration 015 加 unique index 防 cartesian 重复）|
| `api_usage_log` | 每次外部 API 调用的配额监控 | `service` · `endpoint` · `request_date` · `status`（ok / error / quota_error / rate_limited）· `key_fingerprint`（多 key 轮换时区分）|
| `source_fetch_runs` | 每日各源抓取运行状态机 | `target_date` · `source` · `status`（fresh / fallback / failed）· `rows_used` |
| `schema_migrations` | migration 版本号 | `version`（当前最大 17）· `applied_at` |

### 已 DROP 的遗留表（migration 016，ADR-0014）

`feishu_import_runs` · `source_records` · `baseline_items` · `candidates` · `candidate_matches` · `match_candidates` — Phase 0 / 翻转前残留，已无活跃写路径。

### 关键唯一索引

| 索引 | 表 | 防什么重复 |
|------|-----|----------|
| `ux_canonical_items_key` | canonical_items | 业务键去重 |
| `ux_external_ids_source_id` | external_ids | (source, external_id) 唯一 |
| `ux_content_updates_update_id` | content_updates | 同一事件 ID 不重复 |
| `ux_virtual_series_tmdb_tv_id` | virtual_series | 每个 TMDb TV 一行 |
| `ux_api_cache_source_key` | api_cache | (source, cache_key) 唯一（P1.21.5 加） |

### 数据流（简化）

```
外部源（TMDb/Trakt/OMDb/FlixPatrol）
  → sources/*.py 抓取
  → tmdb_trending / trakt_trending / flixpatrol_top10（源快照表）
  → multi_source_merge.py 合并去重
  → scoring.py 计算 hot_score
  → discovery.py 写 content_updates（new_discovery）
  
A 库快照（upstream_programs/episodes）
  → entity_matching.py 与 TMDb 匹配
  → canonical_items + external_ids
  → virtual_series 聚合
  → baseline_tracking.py 检测 TMDb 新季
  → content_updates（new_season）

content_updates
  → export_writer.py → reports/*.md + .json
  → feishu/sync.py → 飞书"热点发现"子表
  → feishu/gap_sync.py（直接从 virtual_series 实时算缺口）→ 飞书"A库缺口"子表

运营人工操作飞书表
  → feedback/pull.py 拉回 → reports/feedback/*.json
  → feedback/weekly_report.py → reports/feedback/feedback_log_YYYY-Www.md
```

---

## 维护本图

发现 stale 时直接改本文件；同步关键来源：

- 表新增/删除/字段大改 → 改 § 5 数据库地图
- 新 CLI 命令 → 改 § 3 CLI 子命令表
- 新脚本或调度变化 → 改 § 4 脚本地图
- 新文档分类 → 改 § 2 文档地图

Migration 后更新 schema version 注记（§ 5 头部）。
