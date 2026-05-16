# 项目状态快照

> AI 冷启动 3 秒回答：现在停在哪儿、有没有阻塞、下一步做什么。
> **更新策略：** 每次 commit 前更新；"近期变更"段只滚动保留 3 条，旧条目随 commit 移交 `journal/` + `git log`。
> **不在此处：** 历史 Phase → [`docs/history/phase1_state_archive.md`](docs/history/phase1_state_archive.md)（先 `rg`）· 技术地图 → [`docs/context_map.md`](docs/context_map.md) · 日常运行 → [`docs/operations/runbook.md`](docs/operations/runbook.md)。

---

**最后更新：** 2026-05-17 00:08 +08 · Claude Code CLI（Opus 4.7） · 分支 `main`（worktree `.claude/worktrees/docs-governance`）
**测试：** 441 passed（`--ignore=tests/test_flixpatrol_parsing.py`；~73s）
**Schema：** version 16（migrations 001-016 全部落盘）

---

## 现在停在哪儿

Phase 0 → 1.23 全部完成；V1 运行观察期。P1.17 跳过（前置未满足）；P1.22 编号预留给 V2 episode 级缺口检测。

**近 7 天关键变更：**
- 2026-05-16 P1.21.9 `sync_doc` → `drive/v1/import_task`（[ADR-0015](docs/decisions/0015-feishu-doc-import-via-import-tasks.md)）
- 2026-05-16 P1.23 飞书运营反馈回流（只读）+ V1 观察期周报 A-E 节生成
- 2026-05-16 P1.21.7 legacy schema 清理（migration 016 删 6 张死表，[ADR-0014](docs/decisions/0014-legacy-schema-cleanup.md)）

## 进行中 / 阻塞 / 待决策

- **进行中：** 无
- **阻塞：** FlixPatrol API 订阅 402 Payment Required（脚本走 fallback）
- **待用户决策：** 无

## Review 跟进项（push 前发现的 minor，非阻塞）

1. **P1.21.6 测试空白** — `feishu/_http.py:batch_delete_records` + `gap_sync.py:sync_gap_table` step 6 仅靠真实 smoke 覆盖
2. **`weekly_report.py:_lookup_title`** — 每条 pending series 单独 `sqlite3.connect()`，建议用 `with` 复用单连接
3. **`entity_matching.py` 死代码** — `match_baseline_items` / `_load_baseline_items` / `main()` 仍引用已 drop 的 `baseline_items` / `match_candidates`
4. **`scripts/weekly_feedback.sh` 缺 TZ** — 漏 `export TZ='Asia/Shanghai'`
5. **`sync_doc` 入口校验** — `folder_token=""` 且非 dry-run 时建议直接 raise

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
