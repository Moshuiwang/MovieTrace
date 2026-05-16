# MovieTrace 项目状态快照

> **本质：** AI Agent 冷启动的"项目当前指针"——3 秒回答：现在停在哪儿、有没有阻塞、下一步做什么。
> **更新策略：** 每次 git commit 前更新；"近 7 天变更"段只保留 3 条滚动 bullet，旧条目随 commit 移交 `journal/` + `git log`。
> **不在此处：** 历史 Phase 详情 → [`docs/history/phase1_state_archive.md`](docs/history/phase1_state_archive.md)（先 `rg` 关键词再读片段）。

---

**最后更新：** 2026-05-17 00:08 +08
**更新人：** Claude Code CLI（Opus 4.7）
**所在分支：** `main`（worktree: `.claude/worktrees/docs-governance`）
**测试：** 441 passed（`--ignore=tests/test_flixpatrol_parsing.py`，bs4 未装；~73s）

---

## 现在停在哪儿

Phase 0 → 1.23 全部完成；当前 V1 运行观察期；P1.17 跳过（不满足真实运行 3-7 天前置条件）；P1.22 编号预留给 episode 级缺口检测（V2 backlog）。

**近 7 天关键变更：**
- 2026-05-16 P1.21.9：`sync_doc` 改用 `drive/v1/import_task`，所需 scope `docx:document:create` → `drive:drive`（[ADR-0015](docs/decisions/0015-feishu-doc-import-via-import-tasks.md)）
- 2026-05-16 P1.23：飞书运营反馈回流（只读）+ V1 观察期周报 A-E 五节生成器
- 2026-05-16 P1.21.7：legacy schema 清理（migration 016 删 6 张死表，[ADR-0014](docs/decisions/0014-legacy-schema-cleanup.md)）

---

## 进行中任务

无。

## 阻塞项

- **FlixPatrol API 订阅**：402 Payment Required（US/World/Nigeria/Kenya 全部不可用）；脚本依赖 fallback 机制运行

## 待用户决策

无。

---

## Review 跟进项（push 前发现的 minor，非阻塞）

1. **P1.21.6 测试空白** — `feishu/_http.py:batch_delete_records` 和 `gap_sync.py:sync_gap_table` step 6 无单元测试，仅靠真实 smoke 覆盖。建议加 mock 测试覆盖 happy path + chunk 边界。
2. **`weekly_report.py:_lookup_title`** — 每条 pending series 单独 `sqlite3.connect()`，except 分支不关闭依赖 GC。建议用 `with` 复用单连接。
3. **`entity_matching.py` 死代码** — `match_baseline_items` / `_load_baseline_items` / `main()` 仍引用已 drop 的 `baseline_items` / `match_candidates`。ADR-0014 措辞"保留 entity_matching.py"应明确为辅助函数。
4. **`scripts/weekly_feedback.sh` 缺 TZ** — 其他两个脚本已 `export TZ='Asia/Shanghai'`，本脚本漏。
5. **`sync_doc` 入口校验** — `folder_token=""` 时透传 `mount_key=""` 给飞书 API，提示不友好。建议函数开头 `if not folder_token and not dry_run: raise RuntimeError(...)`。

---

## 当前数据画像

| 表 | 行数 | 说明 |
|----|------|------|
| `upstream_programs` | 735 | `online_flag`=597 |
| `upstream_episodes` | 6,562 | A 库子节目 |
| `canonical_items` | ~905 | TV season 509 · TV series 289 · Movie 107 |
| `virtual_series` | 307 | urgent 85 · low 187 · skip 35 |
| `content_updates` | ~298 | 事件历史表（schema 16）；new_discovery 151 · new_season 147 |

TV 链接率 790/790 = 100% · `imdb_id` 全空 · 85% 节目名含 `S\d\d` 季号

---

## 给下一个 Agent 的指针

- **DB schema version**：16（migrations 001-016 全部落盘；016 DROP 了 ADR-0007 翻转前的 6 张遗留表）
- **最近备份**（按需用）：`data/movietrace_backup_20260516_1435_pre_p121.7.db` · `20260516_0326_pre_p121.db` · `20260515_1002_before_baseline_catchup.db`
- **关键约定**（详见 [`docs/context_map.md`](docs/context_map.md)）：Secrets 路径 `~/.config/movietrace/secrets.json`；`content_updates` 为事件历史表（[ADR-0012](docs/decisions/0012-content-updates-event-history.md)）；飞书 `records/search` 读路径用中文 field name、写路径用 field ID；数据源 FP 402、其余正常
- **飞书三张子表**：base `P6y3bMbAXazlL5sui4Mc6B5znMb` → 热点发现 / A库缺口 / 字段说明（详见 [`docs/context_map.md § 3`](docs/context_map.md)）
- **CI**：`.github/workflows/ci.yml`（PR + main push 触发）
- **关键决策摘要**：见 [`docs/decisions/README.md`](docs/decisions/README.md)；近期重点 0007（系统翻转）/ 0012（content_updates 事件化）/ 0014（schema 清理）/ 0015（飞书文档导入）

## 日常运行

详见 [`docs/operations/runbook.md`](docs/operations/runbook.md)。

- **Cron 每日 08:00 +08**：`scripts/daily_run.sh`（commit 模式）
- **每周（上层调度）**：`scripts/baseline_run.sh`
- **每周日手动**：`scripts/weekly_feedback.sh`
