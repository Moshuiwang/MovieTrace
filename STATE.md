# MovieTrace 项目状态快照

> 项目当前状态。**任何 Agent 启动新会话时必读**（CLAUDE.md / AGENTS.md 启动顺序的第 1 步）。
> 每次 git commit 前应更新本文件。

---

**最后更新：** 2026-05-12
**更新人：** Claude Code (Opus 4.7)
**Git Commit：** `01add04`（更新前，含 P1.5-A 文档翻转 + B/C/D 任务包起草）
**所在分支：** `main`

---

## 当前阶段

| 阶段 | 状态 |
|------|------|
| Phase 0：开发前验证 | ✅ 已完成（Go 决策） |
| Phase 0+：FlixPatrol 接入验证 | ✅ 已完成（SUP-A~G 全部通过，API 路径确定） |
| Phase 1：V1 MVP 开发 | ✅ 全部完成（P1-B~P1-H 共 7 任务，284 测试，收尾报告：reports/phase1_completion_report.md） |
| **Phase 1.5：V1 定位翻转** | 🟡 进行中（A ✅ / B-D 任务包已起草 / E-G 待 D 完成后起草） |
| Phase 1.6：首次真实运行 + 验收 | ⏳ 待 1.5 完成 |
| Phase 1.7：条件性调优 | ⏳ 待 1.6 数据反馈（如不需要可跳过） |

历史验证结果详见 [`reports/`](reports/)；已采纳决策详见 [`docs/decisions/`](docs/decisions/)。

---

## Phase 1 待办（按依赖顺序）

```
P1-A（实体匹配回归修复）           ✅ 已完成（归档：docs/tasks/p1_a_entity_matching.md）
SUP-G（FlixPatrol API 验证）       ✅ 已完成（验证报告：reports/sup_g_flixpatrol_api_validation.md，ADR-0006）
    ↓
P1-B（FlixPatrol API 数据接入 + DB）   ✅ 已完成（完成报告：journal/2026-05-11_p1_b.md）
    ↓
P1-C（hot_score 评分 + 多源候选合并）  ✅ 已完成（89 candidates 入库，完成报告：journal/2026-05-11_p1_c.md）
    ↓
P1-D（飞书基线匹配标记）              ✅ 已完成（89/89 匹配，完成报告：journal/2026-05-11_p1_d.md）
    ↓
P1-E（每日 Markdown 日报）            ✅ 已完成（日报 89 候选 4 分组，完成报告：journal/2026-05-11_p1_e.md）
    ↓
P1-F（飞书推荐表写入 + 去重 + 字段保护） ✅ 已完成（dry-run 89 条审计日志，完成报告：journal/2026-05-11_p1_f.md）
    ↓
P1-G（CLI 命令 4 条）                 ✅ 已完成（4 条子命令，完成报告：journal/2026-05-11_p1_g.md）
    ↓
P1-H（集成测试 + 首次实际运行）       ✅ 已完成（284 测试通过，收尾报告：reports/phase1_completion_report.md）
```

**当前状态：** Phase 1.5 进行中。ADR-0007 Accepted；P1.5-A 文档翻转已完成；P1.5-B/C/D 任务包已起草待审定；P1.5-E/F/G 待 D 完成后再起草（依赖真实数据反馈）。

---

## Phase 1.5 待办（全部串行，A→B→C→D→E→F→G）

```
P1.5-A（文档翻转）                                ✅ 已完成
    ↓
P1.5-B（B库 schema 扩展 + 飞书 migration）         📝 任务包已起草，待审定执行
    ↓
P1.5-C（virtual_series 表 + 一次性回填脚本）       📝 任务包已起草，待 B 完成
    ↓
P1.5-D（功能 2：基线主动追踪模块）                 📝 任务包已起草，待 C 完成
    ↓
P1.5-E（飞书写入逻辑翻新）                        ⏳ 待 D 完成后起草任务包
    ↓
P1.5-F（日报模板 + CLI 语义调整）                  ⏳ 待 E 完成后起草任务包
    ↓
P1.5-G（检测与导出解耦，export-recommendations）   ⏳ 待 F 完成后起草任务包
```

**任务包文档：**
- [P1.5-A](docs/tasks/p1.5_a_documentation_repositioning.md) ✅
- [P1.5-B](docs/tasks/p1.5_b_schema_extension_and_migration.md) 📝
- [P1.5-C](docs/tasks/p1.5_c_virtual_series_backfill.md) 📝
- [P1.5-D](docs/tasks/p1.5_d_baseline_active_tracking.md) 📝

---

## 后续阶段（Phase 1.5 完成后）

| 阶段 | 内容 | 触发条件 |
|------|------|---------|
| **Phase 1.6** | 用真实数据首次跑完整流程（daily-discover + baseline-track + export-recommendations），1-2 周观察 | P1.5-G 完成 |
| **Phase 1.7** | 根据 1.6 反馈做权重/频率调优（条件性，可跳过） | 1.6 数据显示需要 |
| **Phase 2 (V2)** | 见 [`docs/product_roadmap.md`](docs/product_roadmap.md) § 3 | ADR-0002 V2 启动条件全部满足 |

---

## 进行中任务

*无*（P1.5-A 已完成，B-D 任务包已起草待用户审定后执行）

---

## 阻塞项

*无*

---

## 待用户决策

1. **P1.5-B/C/D 任务包是否审定通过？** — 三份任务包内含字段集设计、回填策略、轮询调度等关键设计决策，需用户 review 后开始执行
2. **P1.5-B Q1 / Q2 已决策** — Q1=直接删除（飞书表清空重建）；Q2=drop 旧字段或重建表
3. **P1.5-C Q3 / Q4 / Q5 决策** — TMDb tv_id 获取来源；低置信度记录处理；同剧多季合并策略（详见任务包）
4. **P1.5-D Q6 / Q7 / Q8 决策** — 新季写入粒度；轮询调度算法；与 daily-discover 集成方式（详见任务包）

---

## Housekeeping 待办（不阻塞主线）

- **任务包文档归档治理**：当前 `docs/tasks/` 顶层散放 17 个任务包，建议建 `phase0_plus/` / `phase1/` / `phase1.5/` 子目录归档；涉及 ~35 处交叉引用修复。建议 P1.5 全部完成后统一治理。
