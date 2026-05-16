# MovieTrace 项目状态快照

> 项目当前状态。**任何 Agent 启动新会话时必读**（启动顺序第 1 步）。
> 每次 git commit 前应更新本文件。
> **历史详情已迁移至 [docs/history/phase1_state_archive.md](docs/history/phase1_state_archive.md)**——默认不整篇读取，先 `rg` 搜索。

---

**最后更新：** 2026-05-16 20:45 +08
**更新人：** Claude Code CLI（Sonnet 4.6）
**所在分支：** `main`

---

## 当前阶段

| 阶段 | 状态 |
|------|------|
| Phase 0：开发前验证 | ✅ 已完成 |
| Phase 0+：FlixPatrol 接入验证 | ✅ 已完成 |
| Phase 1：V1 MVP 开发 | ✅ 全部完成 |
| Phase 1.5：V1 定位翻转 | ✅ 全部完成 |
| Phase 1.6：首次真实运行 + 验收 | ✅ 已完成 |
| Phase 1.7：多热门源扩充 | ✅ 全部完成 |
| Phase 1.8：条件性调优前置数据治理 | ✅ 全部完成 |
| Phase 1.9：code review hotfix + 候选自动注册 | ✅ 全部完成 |
| Phase 1.10：源数据预算与抓取兜底 | ✅ 全部完成 |
| Phase 1.11：API 调用韧性增强 | ✅ 全部完成 |
| Phase 1.12：review hotfix | ✅ 全部完成 |
| Phase 1.13：content_updates 数据模型修正 | ✅ 全部完成 |
| Phase 1.14：真实库 schema 14 升级与 smoke 验收 | ✅ 全部完成 |
| Phase 1.15：V1 收口复盘与运行手册 | ✅ 全部完成 |
| **Phase 1.16：上下文加载规则与文档瘦身** | ✅ 全部完成 |
| **Phase 1.18：热点发现与基线追踪节奏拆分** | ✅ 已完成 |
| **Phase 1.19：baseline 报告可观测性修正** | ✅ 已完成 |
| **Phase 1.20：code review 跟进修正** | ✅ 全部完成 |
| **Phase 1.21：A库缺口快照子表（状态快照）** | ✅ 全部完成 |
| **Phase 1.21.5：维护批次（review fixes + lark-cli 替换 + migration 015）** | ✅ 全部完成 |
| **Phase 1.21.6：A 库缺口表数据质量修正** | ✅ 全部完成 |
| **Phase 1.21.7：ADR-0007 翻转前遗留 schema 清理** | ✅ 全部完成 |
| **Phase 1.21.8：飞书集成代码清理批次（review Tier 1）** | ✅ 全部完成 |
| **Phase 1.23：飞书运营反馈回流（只读）+ V1 观察期周报** | ✅ 全部完成 |
| **Phase 1.21.9：sync_doc 改用 drive/v1/import_task** | ✅ 全部完成 |

**测试：** 441 passed（全量，含 flixpatrol_parsing 因缺 bs4 跳过；P1.21.7 删除 119 个死代码测试，P1.23 新增 17，P1.21.9 新增 12）

## 最近完成

### P1.21.9：sync_doc 改用 drive/v1/import_task（2026-05-16 20:45 +08）
- **_http.py**：新增 `build_multipart_body`（stdlib RFC 7578）和 `upload_media_file` 两个 helper
- **sync.py**：`sync_doc` 三步改造：upload .md → create import task → poll until done；删除 `_DOCX_BLOCK_MAX_CHARS` 和旧 docx blocks 写入逻辑
- **权限**：所需 scope 从 `docx:document:create` 改为 `drive:drive`（与 gap_sync 一致）；权限错误码 99991661/99991663/1061045 显式提示控制台申请路径
- **测试**：12 个新 case（6 build_multipart_body + 6 sync_doc）；test_sync.py 合并 P1.21.8（11 个）+ P1.21.9（12 个）= 23 个
- **ADR-0015**：`docs/decisions/0015-feishu-doc-import-via-import-tasks.md`
- 全量 441 passed（--ignore=test_flixpatrol_parsing.py）

### P1.23：飞书运营反馈回流（只读）+ V1 观察期周报（2026-05-16 19:10 +08）
- **feedback/pull.py**：`pull_hot_table`（近 N 天，客户端日期过滤）+ `pull_gap_table`（全量快照）；分页 500/页；3 次重试指数退避
- **feedback/weekly_report.py**：A-E 五节周报（基本信息/热点统计/缺口统计/关键案例/V2 触发检查）；回填率/采纳率分母为 0 时显示 N/A；ISO 周文件名
- **CLI**：`pull-feishu-feedback` + `export-feedback-report` 两个子命令
- **scripts/weekly_feedback.sh**：一键 pull+export；非零退出触发飞书告警；不接 cron
- **feishu_feedback_spec.md**：运营字段填写规范（选项口径/何时填/不填影响）
- **feedback_log_template.md**：改写为 AI 自动生成说明
- **测试**：17 个用例（8 pull + 9 weekly_report）；476 passed 在 worktree
- **真实 smoke**：拉取 150 hot records + 68 gap records，生成 reports/feedback/feedback_log_2026-W20.md

### P1.21.7：ADR-0007 翻转前遗留 schema 清理（2026-05-16 18:30 +08）
- **Migration 016**：新增 `016_drop_legacy_tables.sql`，DROP IF EXISTS 删除 6 张死表（feishu_import_runs / source_records / baseline_items / candidates / candidate_matches / match_candidates）
- **SCHEMA_SQL 清理**：schema.py 删除 4 张表的 CREATE TABLE，防止新实例误建；SCHEMA_VERSION 15 → 16
- **死代码删除**：移除 baseline_import.py / baseline_matching.py / canonical_promotion.py / daily_writer.py（均无活跃 CLI 调用）
- **测试清理**：删除 test_baseline_import.py 等 5 个死代码测试文件、test_entity_matching.py 中 3 个引用死表的方法；519 → 400 passed
- **cli.py inspect-baseline**：移除对 baseline_items 的查询（表已不存在）
- **ADR-0014**：新增 `docs/decisions/0014-legacy-schema-cleanup.md` 记录清理决策
- Smoke：`baseline-track --dry-run` 85 条计划 0 error

### P1.21.6：A库缺口表数据质量修正（2026-05-16 14:45 +08）
- **SQL 虚假缺口剔除**：`_GAP_SQL` WHERE 加 `AND COALESCE(alm.a_lib_max_season, 0) > 0`；飞书缺口表行数 142 → 68（真实缺口）
- **追上行删除**：`_http.py` 新增 `batch_delete_records`；`sync_gap_table` step 6 自动删除缺口消失的行（stats.deleted）
- **字段说明子表**：`tblPXLrWEEf4bhtM` 新增 6 条说明（A库当前最大季/TMDb已播季/缺口数/缺口季/运营状态/数据源状态）
- **热点发现类型字段选项**：删除 `TV`/`Movie` 大写选项，仅保留 `tv`/`movie`
- **A库缺口视图**：创建"待补 - 在播中"视图（ID: `vewLMxK9s8`）；filter/sort 需用户在飞书 UI 手工配置（API 不支持 PATCH）
- 测试：`test_compute_gaps_no_upstream_link_counts_as_zero` 更新（期望改为排除）+ `test_compute_gaps_excludes_a_lib_zero` 新增；518 → 519 passed

### P1.21.8：飞书集成代码清理批次（2026-05-16 14:14 +08）
- **sync.py 删 F dict 死代码**：删除 `F = {...}` 字典（50 行）及上方注释块；`F` 无任何外部引用，`sync_table` 直接用中文 field name
- **sync.py import 顺序修正**：`UTC = timezone.utc` 移至 import 块之后，符合 Python 惯例
- **export_writer.py need_cache 重构**：列表推导改 for-loop，保留原有 `parts[1] == "tv"` 约束，行为完全等价
- **export_writer.py 重命名**：`_extract_tmdb_id` → `_extract_tmdb_id_from_discovery_id`，调用方同步更新
- **notify.py docstring 修正**：`send_email` 从 "Stub — not yet configured" 改为准确描述现有实现
- **新增 tests/test_sync.py**：11 个 case（`_to_epoch_ms` × 6 + `_derive_content_type` × 5），全量 507 → 518 passed
- 改动仅限允许范围；无运行时行为变更

### P1.21.5：维护批次（2026-05-16 凌晨/上午）
- **lark-cli 全面替换为 Feishu REST**：
  - `sync_doc` → `/docx/v1/documents` + `/docx/v1/documents/{id}/blocks/{block_id}/children`
  - `notify` 系列（`send_text`/`send_summary`/`send_alert`）→ `/im/v1/messages?receive_id_type=open_id`
  - 移除 `subprocess`+lark-cli 依赖；cron 环境下不再因 PATH 问题崩溃
- **Token 文件缓存**：`~/.cache/movietrace/feishu_token.json`（0600 权限，5 min 过期 skew），`baseline.py` 中 fetch_tenant_access_token 改造完毕，跨 CLI 进程共享，避免一次 baseline_run 里 4 次重复获取
- **Migration 015**：`api_cache` 加 `UNIQUE INDEX ON cache_key`，去重 40 条重复缓存（pre-fix 由 cartesian product 产生过 gap 表 dupes）
- **Review 5 个 Should-have**：错误体截短 + access_token mask、batch_size 100→500 对齐、冗余 tmdb_status guard 删除、SQL `ORDER BY fetched_at DESC, id DESC`、test_gap_sync 增加 2 个 None 边界用例
- 端到端验证：`sync-feishu-doc` 创建文档 OK；`notify-feishu` 发送 OK
- 测试 505 → 507 passed（+2 个新边界 case）

### P1.21：A库缺口快照子表（2026-05-16）
- 任务包：[`docs/tasks/p1.21_a_lib_gap_snapshot_table.md`](docs/tasks/p1.21_a_lib_gap_snapshot_table.md)，决策：[ADR-0013](docs/decisions/0013-baseline-gap-snapshot-table.md)
- **问题**：2026-05-15 morning "清扫 151 条 new_season" 后，local_max_season 未回滚，导致 baseline catch-up 第二次跑 detected=0；事件日志驱动的飞书表展现层不可靠
- **解决**：飞书新增子表 "A库缺口"（`tbl1NNU8kmlLKpLm`），直接从 `virtual_series + canonical_items + api_cache` 实时算缺口，**不依赖 content_updates 事件历史**
- 行粒度：1 行 = 1 series；upsert by TMDb ID
- 范围：season-level；表结构预留 episode-level 字段（缺口类型 / 缺口集）
- 状态机：人工标"待补/部分补充/已补/跳过"，系统提示"建议已补"（缺口数=0 时）
- 新代码：`src/movietrace/feishu/_http.py`（共享 REST helpers）、`src/movietrace/feishu/gap_sync.py`、CLI `sync-feishu-gap-table`、`tests/test_gap_sync.py`
- 重构：`sync.py` 抽取重复 HTTP 函数到 `_http.py`，per-record PUT 改为 `batch_update_records`
- `baseline_run.sh` 集成新同步步骤，GAP_EXIT 纳入退出码 + 错误告警
- 重置 local_max_season（用 A 库 max 为起点）+ catch-up 冒烟：plan 272、polled 272、detected 258、写入 147 条 new_season
- 飞书两张子表全部清空重填：A库缺口 142 行（仅有缺口的），热点发现 150 行（最近 7 天 hot 候选）
- 测试 505 passed
- DB 备份：`data/movietrace_backup_20260516_0326_pre_p121.db`

### 飞书新 App 迁移 + 多维表格重建（2026-05-16）
- 飞书凭据切换至新 App `cli_aa8d80407af89bdf`，用户 `ou_15b9e43c2f80fadbe998791b4246a86f`
- 新建多维表格"发现运行日志"（base `P6y3bMbAXazlL5sui4Mc6B5znMb`，table `tbl84xx4WNv54An9`）：18 字段，类型/单选/日期/人员字段全部正确配置
- `sync.py` 重构：移除表/字段自建逻辑，改用 `field_id` 字典定位（`F` 映射，sync.py:50-68）；表名改字段名改均不断链
- `cli.py` 移除 `--table-name` 参数，直接读 `discovery_table_id`
- 用户已授予 `full_access` 管理权限
- 测试 451 passed；dry-run 80 条正常

### P1.20 code review 跟进（全量）
- 任务包：[`docs/tasks/p1.20_a_baseline_report_trust_signals.md`](docs/tasks/p1.20_a_baseline_report_trust_signals.md)、[`docs/tasks/p1.20_b_cache_null_handling_and_vs_name.md`](docs/tasks/p1.20_b_cache_null_handling_and_vs_name.md)
- `tmdb_detail_cache` 空响应返回 `(None, False)` 而非 `({}, False)`
- `_update_virtual_series_from_details` name 直接覆盖，null 时 warning
- `_baseline_local_max` 返回 `(value, is_fallback)` 元组，fallback 显示 `~N`
- routine 空 plan 三种原因诊断：全 null / 部分 null / status 不匹配
- 测试 499 passed

### Poll scheduler 配额简化
- 移除 tier / quota / coverage_days 三段分配逻辑，routine 简化为单 SQL 全量轮询 Returning Series + In Production
- `daily_max_calls` 默认 0（无限制），config 设为 2000 兜底
- 测试 499 passed

### Hot 报告质量分析（2026-05-15）
- 75 条 `new_discovery` 中 88%（66 条）`virtual_series_id = NULL`——A 库未收录的 trending 热门候选
- 9 条已追踪剧集同时出现在 hot 和 baseline 报告里（如 INVINCIBLE、9-1-1）
- 结论：hot 报告应只保留 A 库未收录候选，去掉已追踪条目的重复信息；当前暂不落地，等下次需要时改一行 SQL

---

## 最近完成

### P1.14（schema 14 升级）
- 真实库 `data/movietrace.db` schema 12 → 14，备份 `data/movietrace_backup_20260514_2028.db`
- Migration 013：裸 TMDb external_id → 0 · Migration 014：legacy discovery ID → 0
- Smoke：495 tests · dry-run 720 merged 75 P2+ · inspect 12 updates · export OK

### P1.15（收口文档）
- 新建 `docs/reviews/v1_closeout_review.md`、`docs/operations/runbook.md`、`docs/operations/feedback_log_template.md`
- `SCOPE.md` 飞书描述修正为当前 MD/JSON 导出

### 运行观察期需求沉淀（飞书运营同步）
- 新增 `docs/notes/feishu_ops_sync_requirements.md`，沉淀飞书运营同步需求草案
- 明确定位：读取 `reports/latest.json` / `latest.md` 后同步飞书多维表格并发送总结/告警，不改变发现、评分、匹配或 B 库事实源
- 调研并记录 `lark-cli` 方案：本机 `node v20.20.2`、`npm 10.8.2`、`lark-cli 1.0.23`；第一阶段优先使用 `--as bot`

### 运行配置调整（2026-05-15）
- Secrets 已从旧路径 `/tmp/movietrace_phase0_secrets.json` 迁移到正式路径 `~/.config/movietrace/secrets.json`，权限 `0600`
- Cron 每日运行已从 dry-run 切换为 commit 模式：`scripts/daily_run.sh` 调用 `daily-discover` 不再带 `--dry-run`
- FlixPatrol 402 订阅问题暂不处理，继续依赖 fallback 机制

### P1.18（热点发现与基线追踪节奏拆分）
- 任务包：[`docs/tasks/p1.18_split_baseline_tracking.md`](docs/tasks/p1.18_split_baseline_tracking.md)
- 用户决策：`daily-discover` 每日只做热点发现；`baseline-track` 独立运行，当前上层调度暂定每周；baseline 报告独立导出
- baseline 新季写入需复用现有 `hot_score` 评分，并优先复用 24 小时内 TMDb detail cache
- 已完成：新增 `export-baseline-updates`、`scripts/baseline_run.sh`、`baseline-track --mode routine|catch-up`；全量测试 499 passed
- 真实库 catch-up：2026-05-15 10:27 +08 完成，轮询 272、检测 236、写入 135；导出 `reports/baseline_updates_2026-05-15_1027.md/json`
- 运行观察：`baseline-track` 已增加进度输出，非 dry-run 每 10 条显示当前序号、cache/API 来源、累计 detected

### P1.19（baseline 报告可观测性修正）
- 任务包：[`docs/tasks/p1.19_baseline_report_observability.md`](docs/tasks/p1.19_baseline_report_observability.md)
- 用户判断确认：baseline 检测时间应与 `content_updates.created_at` 事件写入时间区分；报告不再把写入时间单独标为检测时间
- baseline 新写入 `source_summary_json` 增加 `baseline_detected_at`、`baseline_local_max_season`、`tmdb_number_of_seasons`
- `export-baseline-updates` 顶部增加 A 库 → B 库 → virtual_series → 可追踪剧集 → 当前报告结果的漏斗数据
- baseline 报告表格增加 A 库当前季数、TMDb 当前季数、baseline 检测时间、事件写入时间；事件写入时间从 DB UTC 转为 +08 展示，JSON 同时保留 `event_written_at_utc`
- 已重新导出 `reports/baseline_updates_2026-05-15_1043.md/json`，`reports/baseline_latest.md/json` 同步更新
- 验证：针对性 17 passed；全量 499 passed, 1 warning

> Phase 1.5-1.13 完整历史见 [docs/history/phase1_state_archive.md](docs/history/phase1_state_archive.md)

---

## 关键决策摘要

1. **A 库数据接入** — 取代飞书成为内容目录来源，导入 `upstream_programs`/`upstream_episodes`（migration 005）
2. **飞书从系统链路移除** — 不再是输入（被 A 库取代）和输出（被 MD + JSON 导出取代）
3. **Q5-Q8 解定** — 季号正则提取、季级写入粒度、增量双信号检测、CLI + daily-discover 集成
4. **系统定位翻转** — 从"推荐+人工审核"翻转为"更新追踪+中间表"（ADR-0007）
5. **content_updates 事件历史化** — 从全局去重池改为事件表（ADR-0012）

完整决策记录见 [docs/decisions/](docs/decisions/README.md)。

---

## 当前数据画像

| 表 | 行数 | 说明 |
|----|------|------|
| `upstream_programs` | 735 | `online_flag`=597 |
| `upstream_episodes` | 6,562 | A 库子节目 |
| `canonical_items` | ~905 | TV season 509 · TV series 289 · Movie 107 |
| `virtual_series` | 307 | urgent 85 · low 187 · skip 35 |
| `content_updates` | ~298 | 事件历史表（schema 14）；new_discovery 151 · new_season 147 |

- TV 链接率：790/790 = 100%
- `imdb_id` 全空 · 85% 节目名含 `S\d\d` 季号

---

## 进行中任务

- **P1.21.6 A 库缺口表数据质量修正**：任务包 [`docs/tasks/p1.21.6_a_lib_gap_quality_fixes.md`](docs/tasks/p1.21.6_a_lib_gap_quality_fixes.md) 草案就绪，待执行。
- **P1.21.7 遗留 schema 清理**：任务包 [`docs/tasks/p1.21.7_legacy_schema_cleanup.md`](docs/tasks/p1.21.7_legacy_schema_cleanup.md) 草案就绪，待执行（refactor，drop ADR-0007 翻转前 7 张遗留表 ~2400 行）。
- **P1.23 飞书运营反馈回流 + 周报**：任务包 [`docs/tasks/p1.23_feedback_loop_pull_feishu.md`](docs/tasks/p1.23_feedback_loop_pull_feishu.md) 草案完成（2026-05-16 09:05 +08）。
  - 用户已对 4 个产品决策拍板：只读不回写 B 库 / 每周手动跑 / 漏报暂不结构化 / 两张表都拉
  - 待用户确认任务包后开工
  - P1.22 编号保留给 episode 级缺口检测（详见 P1.21.6 任务包非目标 § episode）

## V1 收口任务包（P1.14-P1.17）：全部完成

PR #1 已合入，分支已删除。

---

## 阻塞项

- **FP API 订阅**：402 Payment Required，US/World/Nigeria/Kenya 全部不可用

---

## 日常监控

- **Cron：** 每天 08:00 北京时间自动执行 `scripts/daily_run.sh`（commit 模式，仅写入热点发现 `content_updates`）
- **Baseline 脚本：** `scripts/baseline_run.sh` 可由上层 crontab 每周调用；执行 `baseline-track --mode routine` + `export-baseline-updates --days 7`
- **日志：** `reports/logs/daily_YYYYMMDD.log`
- **检查方式：** 看日志尾部 `=== 运行摘要 ===`，`状态: ✅` 正常，`状态: ❌` 需排查
- **关键信号：** 退出码非零 · Source data 全部 fallback · P2+ 为 0 · circuit breaker 触发
- **详细操作：** 见 [runbook](docs/operations/runbook.md)

---

## 待用户决策

（无。飞书运营同步代码已通过 field_id 重构，等待 commit。）

## V2 backlog

- **新集更新追踪（new_episode）**：V2 backlog，详见 [ADR-0007](docs/decisions/0007-repositioning-to-update-tracking.md) 2026-05-14 修正

---

## 给下一个 Agent 的交接

- **真实库 schema version = 14**（migrations 001-014 全部落盘）
- **备份：** `data/movietrace_backup_20260514_2028.db`
- **P1.18 catch-up 前备份：** `data/movietrace_backup_20260515_1002_before_baseline_catchup.db`
- **分支：** `main`（PR #1 已合入）
- **Secrets：** `~/.config/movietrace/secrets.json`（fallback `/tmp/movietrace_phase0_secrets.json` + warning）
- **config 模块：** `src/movietrace/config.py` 统一 secrets 入口
- **content_updates 语义：** 事件历史表，`content_update_id` 唯一，discovery ID 格式 `discovery:{movie|tv}:{tmdb_id}:{date}`
- **上下文加载：** 按 `docs/context_map.md` 四层地图加载，历史查 `rg` 不整篇读
- **FP API 402** 不可用 · **OMDb** 正常
- **测试：** 451 passed, ~65s, 无 API 消耗
- **CI：** `.github/workflows/ci.yml`（PR + main push）
- **Phase 1 全部 43 个任务包执行完毕**
- **P1.17 跳过**（不满足真实运行 3-7 天前置条件）
- **飞书运营同步**：`src/movietrace/feishu/notify.py`、`src/movietrace/feishu/sync.py`、`gap_sync.py` 已实现；CLI `sync-feishu-table`、`sync-feishu-doc`、`notify-feishu`、`sync-feishu-gap-table`；shell 脚本集成；505 tests passed
	- **飞书多维表格**：base `P6y3bMbAXazlL5sui4Mc6B5znMb`，三个子表：
		- `tbl84xx4WNv54An9`（"热点发现"）：每日 hot discoveries，append-by-date，150 行
		- `tbl1NNU8kmlLKpLm`（"A库缺口"）：实时状态快照，upsert by series，142 行
		- `tblPXLrWEEf4bhtM`（"字段说明"）：字段释义
	- **共享 HTTP 模块**：`src/movietrace/feishu/_http.py`（`request_json` / `batch_create_records` / `batch_update_records` / `unwrap_text_field`）
