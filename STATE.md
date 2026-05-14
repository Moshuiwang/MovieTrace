# MovieTrace 项目状态快照

> 项目当前状态。**任何 Agent 启动新会话时必读**（启动顺序第 1 步）。
> 每次 git commit 前应更新本文件。
> **历史详情已迁移至 [docs/history/phase1_state_archive.md](docs/history/phase1_state_archive.md)**——默认不整篇读取，先 `rg` 搜索。

---

**最后更新：** 2026-05-14 22:49 +08
**更新人：** Codex（GPT-5；API / bash workspace）+ moshuiwang
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

**测试：** 495 passed（全量）

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
| `virtual_series` | 300 | urgent 84 · low 181 · skip 35 |
| `content_updates` | ~12 | 事件历史表（schema 14） |

- TV 链接率：790/790 = 100%
- `imdb_id` 全空 · 85% 节目名含 `S\d\d` 季号

---

## 进行中任务

（无。V1 收口任务包已全部完成，PR #1 已合入 main。项目进入 V1 运行观察期。）

## V1 收口任务包（P1.14-P1.17）：全部完成

PR #1 已合入，分支已删除。

---

## 阻塞项

- **FP API 订阅**：402 Payment Required，US/World/Nigeria/Kenya 全部不可用

---

## 日常监控

- **Cron：** 每天 08:00 北京时间自动执行 `scripts/daily_run.sh`（dry-run 模式）
- **日志：** `reports/logs/daily_YYYYMMDD.log`
- **检查方式：** 看日志尾部 `=== 运行摘要 ===`，`状态: ✅` 正常，`状态: ❌` 需排查
- **关键信号：** 退出码非零 · Source data 全部 fallback · P2+ 为 0 · circuit breaker 触发
- **详细操作：** 见 [runbook](docs/operations/runbook.md)

---

## 待用户决策

- **飞书运营同步需求继续打磨**：是否从 cron dry-run 切 commit、飞书表使用事件池还是每日快照、通知对象、同步字段范围、是否锁定 `lark-cli` 版本

## V2 backlog

- **新集更新追踪（new_episode）**：V2 backlog，详见 [ADR-0007](docs/decisions/0007-repositioning-to-update-tracking.md) 2026-05-14 修正

---

## 给下一个 Agent 的交接

- **真实库 schema version = 14**（migrations 001-014 全部落盘）
- **备份：** `data/movietrace_backup_20260514_2028.db`
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
