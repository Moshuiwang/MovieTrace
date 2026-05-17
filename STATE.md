# 项目状态快照

> AI 冷启动 3 秒回答：现在停在哪儿、有没有阻塞、下一步做什么。
> **更新策略：** 每次 commit 前更新；"近期变更"段只滚动保留 3 条，旧条目随 commit 移交 `journal/` + `git log`。
> **不在此处：** 历史 Phase → [`docs/history/phase1_state_archive.md`](docs/history/phase1_state_archive.md)（先 `rg`）· 技术地图 → [`docs/context_map.md`](docs/context_map.md) · 日常运行 → [`docs/operations/runbook.md`](docs/operations/runbook.md)。

---

**最后更新：** 2026-05-17 16:45 +08 · Claude Code CLI（Opus 4.7 + 5 个 Haiku 4.5 subagent） · 分支 `worktree-feishu-card-notify`
**测试：** 534 passed（`--ignore=tests/test_flixpatrol_parsing.py`；~70s）
**Schema：** version 16（migrations 001-016 全部落盘，P1.24 不动 schema）

---

## 现在停在哪儿

Phase 0 → 1.24 全部完成代码层；**P1.24 真实 E2E smoke 待用户许可执行**（写飞书 + 调 TMDb）。P1.17 跳过（前置未满足）；P1.22 编号预留给 V2 episode 级缺口检测。

**近 7 天关键变更：**
- 2026-05-17 **P1.24 飞书发现运行日志字段增强**（8 新字段 + 季号 rename + Soap 降权 + 历史回填脚本）— 任务包 [`docs/tasks/p1.24-feishu-fields-enhancement.md`](docs/tasks/p1.24-feishu-fields-enhancement.md)；7 个原子子任务 A→B→(C/D/E)→G→F 全部完成；测试 441→534（+93）
- 2026-05-16 P1.21.9 `sync_doc` → `drive/v1/import_task`（[ADR-0015](docs/decisions/0015-feishu-doc-import-via-import-tasks.md)）
- 2026-05-16 P1.23 飞书运营反馈回流（只读）+ V1 观察期周报 A-E 节生成

## 进行中 / 阻塞 / 待决策

- **进行中：** 无（P1.24 代码就绪，待真实 E2E smoke）
- **阻塞：** FlixPatrol API 订阅 402 Payment Required（脚本走 fallback）
- **待用户决策：** 是否触发真实 `setup-feishu-fields` + 首次跑 `backfill_in_play_season.py`（都已 dry-run 验证；真实跑会写飞书表 + 改 ~138 行 content_updates）

## P1.24 后续真实执行步骤（待用户许可）

```bash
# 主目录（非 worktree）
cd /home/ubuntu/MovieTrace
source .venv/bin/activate

# 1) 真实建飞书字段（幂等）
PYTHONPATH=src python -m movietrace.cli setup-feishu-fields

# 2) 真实回填历史"在播最新季"（零 TMDb 调用）
PYTHONPATH=src python scripts/p1_24_backfill_in_play_season.py --days 30

# 3) 真实 sync 把回填后的 source_summary 写到飞书
PYTHONPATH=src python -m movietrace.cli sync-feishu-table

# 4) 下次 daily-discover 自然带新 8 字段进飞书
```

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
