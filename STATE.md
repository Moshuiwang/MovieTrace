# 项目状态快照

> AI 冷启动 3 秒回答：现在停在哪儿、有没有阻塞、下一步做什么。
> **更新策略：** 每次 commit 前更新；"近期变更"段只滚动保留 3 条，旧条目随 commit 移交 `journal/` + `git log`。
> **不在此处：** 历史 Phase → [`docs/history/phase1_state_archive.md`](docs/history/phase1_state_archive.md)（先 `rg`）· 技术地图 → [`docs/context_map.md`](docs/context_map.md) · 日常运行 → [`docs/operations/runbook.md`](docs/operations/runbook.md)。

---

**最后更新：** 2026-05-22 +08 · Claude Code CLI（Opus 4.7） · 分支 `feat/p1.42-fix-fallback-output-pollution`
**测试：** 641 passed（P1.42 合并后，+50 新测试）
**Schema：** version 17（P1.28 新增 migration 017 canonical_items zh-CN 字段；P1.31 SCHEMA_VERSION 常量同步到 17）
**在线事故：** 2026-05-19 08:00 ✅ 完全闭环（P1.31 migration 017 已应用；P1.32 手动补跑 export+sync 均成功）

---

## 现在停在哪儿

Phase 0 → 1.30 全部完成并上线。P1.24 飞书字段已建好；P1.25–P1.29 一批合并修复多个 issue（IMDb URL/在播最新季/原始评分/zh-CN 字段/日报章节）；P1.30 sync_table 增加 IM 通知层 + 工作流配套。P1.17 跳过（前置未满足）；P1.22 编号预留给 V2 episode 级缺口检测。

**最近完成任务包：**

| 编号 | 文件 | 来源 | 状态 |
|---|---|---|---|
| P1.28 | [p1.28-zh-locale-fields.md](docs/tasks/p1.28-zh-locale-fields.md) | issue #8 | ✅ 已合并 (commit eaa8297，含 schema migration 017，回填 622 条 canonical_items) |
| P1.30 | [p1.30-feishu-auto-ensure.md](docs/tasks/p1.30-feishu-auto-ensure.md) | session 设计 | ✅ 已合并 (PR #13) |
| P1.31 | [p1.31-db-migrate-on-deploy.md](docs/tasks/p1.31-db-migrate-on-deploy.md) | 事故修复 | ✅ 已合并 (PR #17 #18)，生产 migration 017 applied |
| P1.32 | [p1.32-manual-pipeline-workflow.md](docs/tasks/p1.32-manual-pipeline-workflow.md) | 事故善后 | ✅ 已合并 (PR #19)，今日 export+sync 补跑成功 |
| P1.33 | — | issue #21 | ✅ 已合并 (PR #24)，飞书 A库最新季整数化 + A库/TMDB总集数字段 |
| P1.34 | [p1.34-ci-resilience.md](docs/tasks/p1.34-ci-resilience.md) | 流程审视 | ✅ 已合并 (PR #31)，CI concurrency 拆分 + deploy 冒烟 + auto-merge dispatch 告警 |
| P1.35 | [p1.35-fix-gzip-http.md](docs/tasks/p1.35-fix-gzip-http.md) | HTTP bug | ✅ 已合并 (PR #33)，HTTP get_json() gzip 解压修复 |
| P1.36 | [p1.36-fp-fetch-lift-out.md](docs/tasks/p1.36-fp-fetch-lift-out.md) | 重构 | ✅ 已合并 (PR #34)，FP fetch 提出到 CLI 层 |
| P1.37 | [p1.37-progress-format-notify.md](docs/tasks/p1.37-progress-format-notify.md) | 进度通知 | ✅ 已合并 (PR #35)，[1/8] 进度格式 + enrichment 细节 + 飞书卡片进度 section |
| P1.40 | [p1.40-fix-json-export-missing-fields.md](docs/tasks/p1.40-fix-json-export-missing-fields.md) | bug fix | ✅ 已合并 (PR #36)，format_json 补充 8 个缺失字段（中文名/平台/集数等）|
| P1.41 | [p1.41-feishu-type-label-field.md](docs/tasks/p1.41-feishu-type-label-field.md) | feat | ✅ 已合并 (PR #37 #38)，热点发现子表新增"类型标签"多选字段（TMDb genre 名称）|
| P1.42 | [p1.42-fix-fallback-output-pollution.md](docs/tasks/p1.42-fix-fallback-output-pollution.md) | 架构审查 § 1.7（P0）| ✅ 本地完成（待 PR），纯 fallback 候选不写 content_updates / 不推飞书；新增 has_fresh_signal 判定 + suppressed_fallback_only stats |

**Issues 状态：** #4 / #5 / #6 / #7 / #8 已关闭。#9（IMDB 编辑推荐源头）保持 OPEN（V2 backlog，合规原因跳过）。

**暂缓：** issue #4b（daily log 回填，单独 issue 后续做）

**近 7 天关键变更：**
- 2026-05-22 **P1.42 fallback 输出污染修复**（has_fresh_signal 判定基于 source_flags & fresh_sources；Step 5 阈值过滤后追加 fallback 过滤，保留 Soap bypass；stats 新增 suppressed_fallback_only；新增 2 条单测 + 1 条 fixture 调整；641 passed）
- 2026-05-22 **架构审查 + 5 个任务包立项**（[`docs/reviews/architecture_audit_2026_05.md`](docs/reviews/architecture_audit_2026_05.md)）：审查 8 大痛点，立项 5 个（P1.42-P1.46），拒绝 3 项（1.1 DB 解耦 / 1.3 异步 / 1.8 CLI 重构——投机性或场景不符）
- 2026-05-21 **P1.40 export_writer 缺字段修复**（format_json 补充 8 个字段：title_zh/overview_zh/genres_json/networks_json/upstream_total_eps/tmdb_total_episodes/content_type/match_confidence_low；464/465 记录有中文名；PR #36）

## 进行中 / 阻塞 / 待决策

- **进行中：** P1.43 → P1.45 → P1.44 → P1.46 + P1.38 由 subagent 队列推进（本地 commit 不开 PR）
- **阻塞：** FlixPatrol API 订阅 402 Payment Required（脚本走 fallback）
- **待决策：** 无
- **P1.39 已完成**：生产日志 SSH 拉取方案已落地（`scripts/fetch-prod-logs.sh`），Logtail 接入决策放弃

## 即将立项的任务包

> 任务包立项后在此登记；合并后移入"最近完成任务包"表并从本节删除。
> **推进顺序：** P1.42（P0）→ P1.43（最便宜）→ P1.45（合规线）→ P1.44 → P1.46；P1.38 可与上述并行。

| 编号 | 名称 | 来源 | 说明 | 阻塞？ |
|---|---|---|---|---|
| P1.38 | fix-notify-bugs | Bug B-01 / B-02 | 修复飞书卡片缓存计数 0 + 重点内容重复（两 bug 共一 PR）| 无 |
| P1.42 | [fix-fallback-output-pollution](docs/tasks/p1.42-fix-fallback-output-pollution.md) | 架构审查 § 1.7（P0）| 纯 fallback 候选不写 content_updates / 不推飞书；混合源照旧 | 无 |
| P1.43 | [omdb-enrichment-batch-commit](docs/tasks/p1.43-omdb-enrichment-batch-commit.md) | 架构审查 § 1.4 | 去掉循环内 micro-commits，改批量事务 | 无 |
| P1.44 | [tmdb-search-cache](docs/tasks/p1.44-tmdb-search-cache.md) | 架构审查 § 1.5 | TMDb /search/tv\|movie 接入 api_cache，TTL 72h | 无 |
| P1.45 | [feishu-sync-retry-and-failures-table](docs/tasks/p1.45-feishu-sync-retry-and-failures-table.md) | 架构审查 § 1.6 + 合规规则 23 | 显式重试（指数退避×3）+ 失败 record 持久化 + replay（含 migration 018）| 无 |
| P1.46 | [http-policy-unification](docs/tasks/p1.46-http-policy-unification.md) | 架构审查 § 1.2 | stdlib 范围统一 HTTP 超时/重试/429 策略，**不引入新依赖** | 建议在 P1.45 之后或同窗口推进 |

**审查未采纳项**（详见 [`docs/reviews/architecture_audit_2026_05.md § 二`](docs/reviews/architecture_audit_2026_05.md)）：
- § 1.1 DB 长连接解耦 — 单进程 cron 无并发写入，锁风险不存在
- § 1.3 异步 + 取消 sleep — OMDb `sleep(1)` 是合规要求，60 秒可接受
- § 1.8 CLI Orchestrator 重构 — 投机性，违反 CLAUDE.md No Speculative Code 铁律

## 待修 Bug（已确认，纳入 P1.38）

| # | 位置 | 现象 | 根因 |
|---|---|---|---|
| B-01 | `notify.py _build_card()` + `discover_stats` | 飞书卡片 [1/8][2/8] 缓存条数显示 0 | stats JSON 只存新抓取数量，fallback 时为 0，未记录缓存快照实际条数 |
| B-02 | `notify.py _build_card()` `top_items` | 重点内容重复出现（The Boys × 2，FROM × 2） | top_items 未按标题去重，同一剧多 content_update_id 导致 |

---

## Review 跟进项（push 前发现的 minor，非阻塞）

1. **P1.21.6 测试空白** — `batch_delete_records` 已补 4 个单测 ✓；`sync_gap_table` step 6 仍无自动化覆盖（需飞书）
2. ~~`weekly_report.py:_lookup_title` per-row sqlite connect~~ **已修复** ✓ (541ef70)
3. ~~`entity_matching.py` 死代码 `__main__` 调用未定义 `main()`~~ **已删除** ✓ (541ef70)
4. ~~`scripts/weekly_feedback.sh` 缺 TZ~~ **已修复** ✓
5. ~~`sync_doc` 入口校验~~ **已修复** ✓


## 当前数据画像

| 表 | 行数 | 备注 |
|----|------|------|
| `upstream_programs` | 735 | `online_flag`=597 |
| `upstream_episodes` | 6,562 | A 库子节目 |
| `canonical_items` | ~905 | TV season 509 · TV series 289 · Movie 107 |
| `virtual_series` | 307 | urgent 85 · low 187 · skip 35 |
| `content_updates` | ~298 | new_discovery 151 · new_season 147 |

TV 链接率 790/790 = 100% · `imdb_id` 全空 · 85% 节目名含 `S\d\d` 季号

## 最近备份

`data/movietrace_backup_20260516_1435_pre_p121.7.db` · `20260516_0326_pre_p121.db` · `20260515_1002_before_baseline_catchup.db`
