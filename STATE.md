# MovieTrace 项目状态快照

> 项目当前状态。**任何 Agent 启动新会话时必读**（CLAUDE.md / AGENTS.md 启动顺序的第 1 步）。
> 每次 git commit 前应更新本文件。

---

**最后更新：** 2026-05-12  +08
**更新人：** Claude Code (DeepSeek V4 Pro) + moshuiwang
**所在分支：** `main`

---

## 当前阶段

| 阶段 | 状态 |
|------|------|
| Phase 0：开发前验证 | ✅ 已完成（Go 决策） |
| Phase 0+：FlixPatrol 接入验证 | ✅ 已完成（SUP-A~G 全部通过） |
| Phase 1：V1 MVP 开发 | ✅ 全部完成（284 测试） |
| **Phase 1.5：V1 定位翻转** | 🟡 进行中（A ✅ / B-D 任务包 v2 已发布 / E 砍掉 / F 合并原 F+G） |
| Phase 1.6：首次真实运行 + 验收 | ⏳ 待 1.5 完成 |
| Phase 1.7：条件性调优 | ⏳ 待 1.6 数据反馈 |

---

## Phase 1.5 待办（B→C→D→F，全部串行）

```
P1.5-A（文档翻转）                                ✅ 已完成
    ↓
P1.5-B（schema v6 migration）                     📝 任务包 v2 已发布，待执行
    ↓
P1.5-E（A 库全量实体匹配 → canonical_items）      📝 任务包 v1 已发布，待 B 完成
    ↓
P1.5-C（virtual_series 一次性回填）                📝 任务包 v2 已发布，待 E 完成
    ↓
P1.5-D（基线主动追踪模块）                         📝 任务包 v2 已发布，待 C 完成
    ↓
P1.5-F（日报模板 + CLI 语义 + 导出，合并原 F/G）   📝 任务包 v1 已发布，待 D 完成
```

**P1.5-E 是新增任务包** — A 库 735 条节目作为输入源后，必须先全量匹配 TMDb 创建 canonical_items，P1.5-C 才有输入。

**已砍掉：**
- ~~P1.5-E（飞书写入翻新）~~ → 飞书已从系统链路移除

**任务包文档：**
- [P1.5-A](docs/tasks/p1.5_a_documentation_repositioning.md) ✅
- [P1.5-B](docs/tasks/p1.5_b_schema_v6_migration.md) 📝
- [P1.5-E](docs/tasks/p1.5_e_entity_matching_full.md) 📝
- [P1.5-C](docs/tasks/p1.5_c_virtual_series_backfill.md) 📝
- [P1.5-D](docs/tasks/p1.5_d_baseline_active_tracking.md) 📝
- [P1.5-F](docs/tasks/p1.5_f_report_cli_export.md) 📝

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

*无*（P1.5-B 任务包 v2 已发布，待其他 Agent 领取执行）

---

## 阻塞项

*无*（之前的阻塞项"生产环境 DB schema 未确认"已解决）

---

## 待用户决策

*无*

---

## Housekeeping 待办（不阻塞主线）

- **任务包文档归档治理**：当前 `docs/tasks/` 顶层散放任务包，含 v1 旧版（P1.5-B/C/D 旧版文件名含 `_b_` `_c_` `_d_` 但不含 `v6`/`active` 等新关键词）与新 v2 版。建议 P1.5 全部完成后统一归档旧版到 `docs/tasks/archive/`。
- **日报归档**：`journal/` 下日报文件命名规范已统一（含 HHMM），但旧文件可能不符合新规。
