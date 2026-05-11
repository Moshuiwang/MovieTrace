# MovieTrace 项目状态快照

> 项目当前状态。**任何 Agent 启动新会话时必读**（CLAUDE.md / AGENTS.md 启动顺序的第 1 步）。
> 每次 git commit 前应更新本文件。

---

**最后更新：** 2026-05-11
**更新人：** Claude Code (Opus 4.7)
**Git Commit：** `6261d53`（更新前）
**所在分支：** `main`

---

## 当前阶段

| 阶段 | 状态 |
|------|------|
| Phase 0：开发前验证 | ✅ 已完成（Go 决策） |
| Phase 0+：FlixPatrol 接入验证 | ✅ 已完成（SUP-A~G 全部通过，API 路径确定） |
| Phase 1：V1 MVP 开发 | ✅ 全部完成（P1-B~P1-H 共 7 任务，284 测试，收尾报告：reports/phase1_completion_report.md） |

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

**当前状态：** Phase 1 V1 MVP ✅ 全部完成（P1-B~P1-H 共 7 任务，284 测试通过，收尾报告：reports/phase1_completion_report.md）

---

## 进行中任务

*无（Phase 1 全部完成）*

---

## 阻塞项

- **SUP-G 阻塞 P1-B**：在 SUP-G 给出 API/HTML 路径建议前，不写 P1-B 任务包，避免写完后大幅返工。

---

## 待用户决策

1. **P1-B~P1-H 派发顺序和调度** — 建议按依赖链串行（P1-B → P1-C → ... → P1-H），确认是否需要并行加速某些任务
2. **首次实际运行的数据量** — P1-H 集成测试用合成数据；首次验收运行的真实数据规模和时间点（如今日下午或明日）
3. **认可率不足 60% 时的处理** — 如 P1-H 验收的人工认可率 < 60%，是否容许进行权重调优（P1-I），还是回滚重设计
