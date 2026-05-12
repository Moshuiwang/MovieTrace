# MovieTrace 项目状态快照

> 项目当前状态。**任何 Agent 启动新会话时必读**（CLAUDE.md / AGENTS.md 启动顺序的第 1 步）。
> 每次 git commit 前应更新本文件。

---

**最后更新：** 2026-05-12 22:58 +08
**更新人：** Claude Code (DeepSeek V4 Pro) + moshuiwang
**所在分支：** `main`

---

## 当前阶段

| 阶段 | 状态 |
|------|------|
| Phase 0：开发前验证 | ✅ 已完成（Go 决策） |
| Phase 0+：FlixPatrol 接入验证 | ✅ 已完成（SUP-A~G 全部通过） |
| Phase 1：V1 MVP 开发 | ✅ 全部完成（284 测试） |
| **Phase 1.5：V1 定位翻转** | ✅ 全部完成（326 测试） |
| **Phase 1.6：首次真实运行 + 验收** | ✅ 已完成（2026-05-12） |
| Phase 1.7：条件性调优 | ⏳ 待 1.6 数据反馈 |

---

## Phase 1.5 执行结果（2026-05-12）

```
P1.5-A（文档翻转）                                ✅
    ↓
P1.5-B（schema v6 migration）                     ✅ migration 006 已执行
    ↓
P1.5-E（A 库全量实体匹配 → canonical_items）      ✅ match_upstream_program + 全量脚本
    ↓
P1.5-C（virtual_series 一次性回填）                ✅ virtual_series 模块 + 回填脚本
    ↓
P1.5-D（基线主动追踪模块）                         ✅ poll_scheduler + baseline_tracking + CLI
    ↓
P1.5-F（日报模板 + CLI 语义 + 导出）               ✅ export_writer + CLI 更新 + 飞书写入移除
```

**新增模块：**
- `src/movietrace/pipeline/virtual_series.py`
- `src/movietrace/pipeline/poll_scheduler.py`
- `src/movietrace/pipeline/baseline_tracking.py`
- `src/movietrace/reports/export_writer.py`
- `src/movietrace/sources/tmdb.py` — TmdbDetailClient

**新增 CLI 命令：**
- `baseline-track` — 基线新季检测
- `export-recommendations` — MD+JSON 导出

**新增配置文件：**
- `config.yaml` — baseline_tracking 配置

**已砍掉：**
- ~~飞书写入~~ — daily-discover 已移除飞书写入步骤
- ~~`feishu/recommendation_writer.py`~~ — 已删除（含测试）
- ~~`tests/test_recommendation_writer.py`~~ — 已删除

**任务包文档（全部已执行）：**
- [P1.5-A](docs/tasks/p1.5_a_documentation_repositioning.md) ✅
- [P1.5-B](docs/tasks/p1.5_b_schema_v6_migration.md) ✅
- [P1.5-E](docs/tasks/p1.5_e_entity_matching_full.md) ✅
- [P1.5-C](docs/tasks/p1.5_c_virtual_series_backfill.md) ✅
- [P1.5-D](docs/tasks/p1.5_d_baseline_active_tracking.md) ✅
- [P1.5-F](docs/tasks/p1.5_f_report_cli_export.md) ✅

---

## Phase 1.6 执行结果（2026-05-12）

生产环境真实运行，按 B→E→C→D→F 顺序执行。

### P1.5-E：A库全量实体匹配
| 指标 | 数值 |
|------|------|
| 处理数 | 594（online_flag=1 且未匹配） |
| 匹配成功 | 594/594 (100%) |
| 置信度 | high 587 · medium 7 · low 0 |
| 新建 canonical_items | 513 |
| 复用已有 | 81 |
| API 调用 | 594 · 耗时 15 分钟 |

### P1.5-C：virtual_series 回填
| 指标 | 数值 |
|------|------|
| 最终 virtual_series | **300**（urgent 84 / low 181 / skip 35） |
| 已链接 canonical_items | 763/798 (95.6%) |
| API 调用 | 192（去重后，节省 185 次） |
| 发现并修复 | 旧版 baseline_quality_issues 表冲突 · 多季同 ID fallback · 两阶段去重优化 |

### P1.5-D：基线追踪
| 指标 | 数值 |
|------|------|
| 轮询计划 | 7（urgent 优先） |
| 检测到新季 | 8 |
| 写入 content_updates | 6（2 条去重） |
| 示例 | FROM S4 · Silo S2 · American Horror Story S11 |

### P1.5-F：报告导出
- 导出 6 条 content_updates → `reports/recommendations_*.md` + `.json`

### 生产数据画像
```
canonical_items: 905 (TV season 509 · TV series 289 · Movie 107)
virtual_series:  300
content_updates: 6 (new_season)
external_ids:    upstream 597 · tmdb 424
```

---

## 2026-05-12 关键决策记录

### 决策 1：A 库数据接入 ✅

- 用户从生产 DB 导出两张 CSV：`source_records/节目数据.csv`（735 行）+ `source_records/子节目数据.csv`（6,562 行）
- 导入到 `data/movietrace.db` 的 `upstream_programs` / `upstream_episodes` 表（migration 005）
- Schema 参考文档：[reports/upstream_db_schema_reference.md](reports/upstream_db_schema_reference.md)
- **A 库取代飞书"线上内容基线表"成为 MovieTrace 的内容目录来源**

### 决策 2：飞书从系统链路移除 ✅

- 飞书不再是内容目录来源（被 A 库取代）
- 飞书不再是输出渠道（被日报 MD + JSON 导出取代）
- P1.5-E（飞书写入翻新）整包砍掉
- P1.5-F/G 合并为一个任务包（日报 + CLI + 导出）
- `feishu_import_runs` / `source_records` / `baseline_items` 表**保留不动**（历史数据）

### 决策 3：Q5-Q8 全部解定 ✅

| 问题 | 决策 |
|------|------|
| Q5（多季合并 + season_number） | 正则从 name 提取，同名 tv_id 多季幂等合并到同一条 virtual_series |
| Q6（写入粒度） | 季级；tmdb_number_of_seasons > local_max_season → 新季 |
| Q7（增量检测） | last_polled_at（轮询频率）+ modify_instant（定位变更节目）双信号 |
| Q8（集成方式） | 独立 CLI `baseline-track` + 嵌入 `daily-discover` 最后一步，两者都做 |

### 决策 4：Migration 编号调整

- 005 → `upstream_programs` / `upstream_episodes`（A 库备份表，已执行）
- 006 → `virtual_series` 表 + `canonical_items.virtual_series_id` + `content_updates.match_confidence_low`（P1.5-B）

---

## 当前 A 库数据画像

| 表 | 行数 | 关键字段 |
|----|------|---------|
| `upstream_programs` | 735 | `id`, `name`, `online_flag`(597=上架), `modify_instant` |
| `upstream_episodes` | 6,562 | `id`, `fk_program_content_id`, `direct_weight`, `modify_instant`, `duration_*` |

- 85% 节目名含 `S\d\d` 季号（可正则提取）
- `imdb_id` 全空（匹配只能走 TMDb 名称搜索）
- 无 Series 实体（需 `virtual_series` 聚合）

---

## 进行中任务

*无*

---

## 阻塞项

*无*

---

## 待用户决策

- **Phase 1.6 启动时机**：P1.5 全部代码已就绪，测试 326 通过。生产环境实际执行（P1.5-E → C → D → F）需用户确认时间和 TMDb API 配额

---

## 给下一个 Agent 的交接

- **P1.5 全部完成**，Phase 1.6 是下一阶段
- **生产执行前请注意：**
  - P1.5-E 匹配脚本需 ~20 分钟（597 条 × 1 次/秒），建议先 `--dry-run --limit 5` 验证 API 连通性
  - TMDb Bearer Token 路径：`/tmp/movietrace_phase0_secrets.json`
  - `baseline_quality_issues` 表由 `_ensure_quality_issues_table()` 动态创建（非正式 migration）
  - `external_ids(source, external_id)` 唯一索引导致同剧多季只存一条 tmdb external_id，P1.5-C 已处理此情况
- **新增 CLI 命令：** `baseline-track`、`export-recommendations`
- **Session 报告：** `reports/session_2026-05-12_p1.5_full_execution.md`

---

## Housekeeping 待办（不阻塞主线）

- **任务包文档归档治理**：当前 `docs/tasks/` 顶层散放任务包，含 v1 旧版（P1.5-B/C/D 旧版文件名含 `_b_` `_c_` `_d_` 但不含 `v6`/`active` 等新关键词）与新 v2 版。建议 P1.5 全部完成后统一归档旧版到 `docs/tasks/archive/`。
- **日报归档**：`journal/` 下日报文件命名规范已统一（含 HHMM），但旧文件可能不符合新规。
