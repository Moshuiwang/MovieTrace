# 项目状态快照

> AI 冷启动只回答：停在哪儿、是否阻塞、下一步。历史见 [`docs/history/phase1_state_archive.md`](docs/history/phase1_state_archive.md)，技术地图见 [`docs/context_map.md`](docs/context_map.md)，日常运行见 [`docs/operations/runbook.md`](docs/operations/runbook.md)。
> **更新策略：** 每次 commit 前更新；近期变更只保留影响当前判断的 3 条以内。

**最后更新：** 2026-05-17 22:30 +08 · 分支 `main`
**测试：** 535 passed（`--ignore=tests/test_flixpatrol_parsing.py`；~70s）
**Schema：** version 16（migrations 001-016 已落盘）

## 当前状态

Phase 0 → 1.24 全部完成并上线；V1 运行观察期。P1.24 飞书新字段从 2026-05-18 起随 `daily-discover` 自然写入。P1.17 跳过；P1.22 预留给 V2 episode 级缺口检测。

**近期关键变更：**
- 2026-05-17 row_duration 未播集修复 + SQL join 路径修正；测试 534→535
- 2026-05-17 P1.24 飞书发现运行日志字段增强（任务包 [`docs/tasks/p1.24-feishu-fields-enhancement.md`](docs/tasks/p1.24-feishu-fields-enhancement.md)）；测试 441→534
- 2026-05-16 P1.21.9 `sync_doc` → `drive/v1/import_task`（[ADR-0015](docs/decisions/0015-feishu-doc-import-via-import-tasks.md)）

## 进行中 / 阻塞 / 待决策

- **进行中：** 无
- **阻塞：** FlixPatrol API 订阅 402 Payment Required（脚本走 fallback）
- **待补覆盖：** `sync_gap_table` step 6 仍无自动化覆盖（需飞书）

## 数据画像

`upstream_programs` 735 · `upstream_episodes` 6,562 · `canonical_items` ~905 · `virtual_series` 307 · `content_updates` ~298。TV 链接率 790/790 = 100%，`imdb_id` 全空，85% 节目名含 `S\d\d` 季号。
