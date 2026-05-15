# MovieTrace 项目状态快照

> 项目当前状态。**任何 Agent 启动新会话时必读**（启动顺序第 1 步）。
> 每次 git commit 前应更新本文件。
> **历史详情已迁移至 [docs/history/phase1_state_archive.md](docs/history/phase1_state_archive.md)**——默认不整篇读取，先 `rg` 搜索。

---

**最后更新：** 2026-05-15 13:20 +08
**更新人：** Claude Opus 4.7（DeepSeek V4 Pro；API / bash workspace）+ moshuiwang
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

**测试：** 499 passed（全量）

## 最近完成

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
| `content_updates` | ~227 | 事件历史表（schema 14）；new_discovery 76 · new_season 151 |

- TV 链接率：790/790 = 100%
- `imdb_id` 全空 · 85% 节目名含 `S\d\d` 季号

---

## 进行中任务

（无。P1.20-A/B 已完成，项目继续处于 V1 运行观察期。）

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

- **飞书运营同步需求继续打磨**：飞书表使用事件池还是每日快照、通知对象、同步字段范围、是否锁定 `lark-cli` 版本

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
- **测试：** 495 passed, 1 warning, ~68s, 无 API 消耗
- **CI：** `.github/workflows/ci.yml`（PR + main push）
- **Phase 1 全部 43 个任务包执行完毕**
- **P1.17 跳过**（不满足真实运行 3-7 天前置条件）
- **飞书运营同步**：需求草案已落在 `docs/notes/feishu_ops_sync_requirements.md`；尚未建任务包、尚未实现代码；明天优先继续产品打磨
