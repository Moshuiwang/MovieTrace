# 项目状态快照

> AI 冷启动 3 秒回答：现在停在哪儿、有没有阻塞、下一步做什么。
> **更新策略：** 每次 commit 前更新；"近期变更"段只滚动保留 3 条，旧条目随 commit 移交 `journal/` + `git log`。
> **不在此处：** 历史 Phase → [`docs/history/phase1_state_archive.md`](docs/history/phase1_state_archive.md)（先 `rg`）· 技术地图 → [`docs/context_map.md`](docs/context_map.md) · 日常运行 → [`docs/operations/runbook.md`](docs/operations/runbook.md)。

---

**最后更新：** 2026-05-18 +08 · Claude Code CLI（Sonnet 4.6） · 分支 `main`
**测试：** 535 passed（`--ignore=tests/test_flixpatrol_parsing.py`；~70s）
**Schema：** version 16（migrations 001-016 全部落盘，P1.24 不动 schema）

---

## 现在停在哪儿

Phase 0 → 1.24 全部完成并上线。P1.24 飞书字段已建好，新字段数据从 2026-05-18 起随 daily-discover 自然写入。P1.17 跳过（前置未满足）；P1.22 编号预留给 V2 episode 级缺口检测。

**活跃任务包（按执行顺序）：**

| 编号 | 文件 | 来源 | 状态 |
|---|---|---|---|
| P1.25 | [p1.25-fix-imdb-url.md](docs/tasks/p1.25-fix-imdb-url.md) | issue #7 | ✅ PR #10 已开（待合并） |
| P1.26 | [p1.26-fix-last-episode-to-air.md](docs/tasks/p1.26-fix-last-episode-to-air.md) | issue #5 | 草案，待执行 |
| P1.27 | [p1.27-feishu-raw-ratings.md](docs/tasks/p1.27-feishu-raw-ratings.md) | issue #6 | 草案，待执行 |
| P1.28 | [p1.28-zh-locale-fields.md](docs/tasks/p1.28-zh-locale-fields.md) | issue #8 | 草案，待执行（独立 PR，含 schema migration 017） |
| P1.29 | [p1.29-doc-sections.md](docs/tasks/p1.29-doc-sections.md) | issue #4a | 草案，待执行 |
| P1.30 | [p1.30-feishu-auto-ensure.md](docs/tasks/p1.30-feishu-auto-ensure.md) | session 设计讨论 | 进行中（sync 入口自动 ensure + 工作流配套） |

**暂缓：** issue #4b（daily log 回填，单独 issue 后续做）；issue #9（V2 backlog，合规原因跳过）

**近 7 天关键变更：**
- 2026-05-18 **P1.25 IMDb 链接 tt 前缀修复**（`_build_imdb_url` 调用 `format_imdb_id`；+4 测试；PR #10 已开）
- 2026-05-18 **仓库公开 + CI/CD**（GitHub Actions：push main 自动跑测试 + SSH 部署服务器 + 同步 secrets.json；密钥统一存 GitHub Secrets；`doc_folder_token` / `notify_chat_id` 迁移到 secrets.json）
- 2026-05-17 **P1.24 飞书发现运行日志字段增强**（8 新字段 + 季号 rename + Soap 降权 + 历史回填脚本）；测试 441→534（+93）

## 进行中 / 阻塞 / 待决策

- **进行中：** P1.30（飞书字段自动 ensure + 工作流配套）
- **阻塞：** FlixPatrol API 订阅 402 Payment Required（脚本走 fallback）

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
