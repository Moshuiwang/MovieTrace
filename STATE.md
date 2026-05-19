# 项目状态快照

> AI 冷启动 3 秒回答：现在停在哪儿、有没有阻塞、下一步做什么。
> **更新策略：** 每次 commit 前更新；"近期变更"段只滚动保留 3 条，旧条目随 commit 移交 `journal/` + `git log`。
> **不在此处：** 历史 Phase → [`docs/history/phase1_state_archive.md`](docs/history/phase1_state_archive.md)（先 `rg`）· 技术地图 → [`docs/context_map.md`](docs/context_map.md) · 日常运行 → [`docs/operations/runbook.md`](docs/operations/runbook.md)。

---

**最后更新：** 2026-05-19 +08 · Claude Code CLI（Opus 4.7） · 分支 `feat/p1.31-db-migrate-on-deploy`
**测试：** 613 passed（~74s · +4 migrate CLI 测试）
**Schema：** version 17（P1.28 新增 migration 017 canonical_items zh-CN 字段；P1.31 SCHEMA_VERSION 常量同步到 17）
**在线事故：** 2026-05-19 08:00 cron 触发 export 失败 — Migration 017 未应用到生产库（`schema_migrations.max=16`），`canonical_items.title_zh` 列缺失。诊断 `incident-reports/20260519_run_failure.md`；修复方案 P1.31（本分支）+ P1.32（后续分支）

---

## 现在停在哪儿

Phase 0 → 1.30 全部完成并上线。P1.24 飞书字段已建好；P1.25–P1.29 一批合并修复多个 issue（IMDb URL/在播最新季/原始评分/zh-CN 字段/日报章节）；P1.30 sync_table 增加 IM 通知层 + 工作流配套。P1.17 跳过（前置未满足）；P1.22 编号预留给 V2 episode 级缺口检测。

**最近完成任务包：**

| 编号 | 文件 | 来源 | 状态 |
|---|---|---|---|
| P1.25 | [p1.25-fix-imdb-url.md](docs/tasks/p1.25-fix-imdb-url.md) | issue #7 | ✅ 已合并 (PR #10) |
| P1.26 | [p1.26-fix-last-episode-to-air.md](docs/tasks/p1.26-fix-last-episode-to-air.md) | issue #5 | ✅ 已合并 (commit eaa8297) |
| P1.27 | [p1.27-feishu-raw-ratings.md](docs/tasks/p1.27-feishu-raw-ratings.md) | issue #6 | ✅ 已合并 (commit eaa8297) |
| P1.28 | [p1.28-zh-locale-fields.md](docs/tasks/p1.28-zh-locale-fields.md) | issue #8 | ✅ 已合并 (commit eaa8297，含 schema migration 017，回填 622 条 canonical_items) |
| P1.29 | [p1.29-doc-sections.md](docs/tasks/p1.29-doc-sections.md) | issue #4a | ✅ 已合并 (commit eaa8297) |
| P1.30 | [p1.30-feishu-auto-ensure.md](docs/tasks/p1.30-feishu-auto-ensure.md) | session 设计 | ✅ 已合并 (PR #13) |

**Issues 状态：** #4 / #5 / #6 / #7 / #8 已关闭。#9（IMDB 编辑推荐源头）保持 OPEN（V2 backlog，合规原因跳过）。

**暂缓：** issue #4b（daily log 回填，单独 issue 后续做）

**近 7 天关键变更：**
- 2026-05-19 **P1.30 sync_table IM 通知 + 工作流配套**（auto-ensure 触发 send_text / send_alert；GitHub 分支保护 main；feature branch + PR 工作流；auto-merge 大小写修复；pre-push hook）；测试 609 passed
- 2026-05-18~19 **P1.25-P1.29 批量合并**（IMDb URL tt 前缀 / 在播最新季 / 原始评分 / zh-CN 字段 + migration 017 / 日报章节扩充）；4 个 issue 已关闭
- 2026-05-18 **仓库公开 + CI/CD**（GitHub Actions：push main 自动跑测试 + SSH 部署服务器 + 同步 secrets.json；密钥统一存 GitHub Secrets）

## 进行中 / 阻塞 / 待决策

- **进行中：**
  - [P1.31 部署自动应用 DB Migration](docs/tasks/p1.31-db-migrate-on-deploy.md) — 代码 + 测试已就绪（本分支 `feat/p1.31-db-migrate-on-deploy`），待 PR 评审合并；事故系统性修复（schema + ci.yml + CLI migrate + 4 个测试）
  - [P1.32 Manual Pipeline Workflow](docs/tasks/p1.32-manual-pipeline-workflow.md) — 任务包就绪、代码未启动；P1.31 下游，提供 workflow_dispatch 手动重跑入口，闭环今天事故的数据补救
- **执行顺序：** P1.31 PR 合并 → auto-deploy 应用 017 → 开 P1.32 PR → 合并后 `gh workflow run manual-pipeline -f stage=export -f days=1` 补今天产出
- **阻塞：** FlixPatrol API 订阅 402 Payment Required（脚本走 fallback）
- **已知限制：** auto-merge.yml 用默认 `GITHUB_TOKEN` 合并的 PR 不触发 `push` 事件，导致 auto-merged PR 不会自动 deploy。PR #14 提了 workflow_dispatch 补救方案；长期更优是换 PAT secret。

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
