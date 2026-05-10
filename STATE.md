# MovieTrace 项目状态快照

> 这是项目当前状态的实时快照。**任何 Agent 启动新会话时必读。**  
> 每次 git commit 前应更新本文件。

---

**最后更新：** 2026-05-10  
**更新人：** Claude Code (Sonnet 4.6)  
**Git Commit：** `dd60885`  
**所在分支：** `main`

---

## 当前阶段

| 阶段 | 状态 |
|------|------|
| Phase 0：开发前验证 | ✅ 已完成（Go 决策） |
| Phase 0+：FlixPatrol 接入验证 | ✅ 已完成（SUP-A~F 全部通过，综合结论 GO） |
| Phase 1：V1 MVP 开发 | 🔄 进行中（任务包待拆分，可启动 P1-A / P1-B） |

---

## 数据库状态

```
data/movietrace.db
├── baseline_items:           855 条
├── canonical_items:          826 条 (96.6%)
├── external_ids:             826 条
├── match_candidates:         855 条
└── baseline_quality_issues:  29 条（待人工修正基线）
```

---

## Phase 0+ 验证结果（已完成）

| 任务 | 结论 | 报告 |
|------|------|------|
| SUP-A 可访问性 | ✅ 6/7 URL HTTP 200 | `reports/flixpatrol_accessibility_report.md` |
| SUP-B HTML 解析稳定性 | ✅ 390/390 字段提取率 100% | `reports/flixpatrol_parsing_report.md` |
| SUP-C TMDb 匹配率 | ✅ 118/118 = 100% | `reports/flixpatrol_matching_report.md` |
| SUP-D 合规评估 | ⚠️ 条件接入（robots 允许，条款为空） | `reports/flixpatrol_compliance_report.md` |
| SUP-F 综合结论 | ✅ GO，进入 Phase 1 | `reports/flixpatrol_validation_report.md` |

FlixPatrol 合规访问约束：每 URL 每 24h 最多 1 次 · 间隔 ≥ 2 秒 · `MovieTraceBot/0.1` UA · 仅内部使用。

---

## Phase 1 待办（按依赖顺序）

```
P1-A（实体匹配回归修复）         ← 可立即启动
P1-B（FlixPatrol HTTP 客户端 + DB）← 可立即启动（与 P1-A 并行）
    ↓
P1-C（多源合并 + hot_score 评分）
    ↓
P1-D（飞书基线匹配标记）
    ↓
P1-E（每日 Markdown 日报）
    ↓
P1-F（飞书推荐表写入）
    ↓
P1-G（CLI 命令）
    ↓
P1-H（集成测试 + 首次运行）
```

**当前状态：** 任务包尚未拆分，需先写 P1-A / P1-B 任务包再启动编码。

---

## 进行中任务

无（Phase 1 任务包待创建）。

---

## 阻塞项

无。

---

## 待用户决策

1. **Phase 1 任务包拆分** — 是否现在开始写 P1-A / P1-B 任务包？
2. **SUP-E 长期稳定性观察** — 已延迟到 P1-B 上线后被动观察，无需主动决策

---

## 最近 5 次重大决策（详见 [docs/decisions/](docs/decisions/)）

1. **ADR-0001** 飞书基线从过滤逻辑改为标记参考（2026-05-10）
2. **ADR-0002** V1/V2 严格划分原则（2026-05-10）
3. **ADR-0003** V1 引入 FlixPatrol 作为真实平台热度源（✅ 已 Accepted，Phase 0+ 验证通过）
4. **ADR-0004** Phase 0 不自动升级 26 条电影误标记录（2026-05-10）
5. **ADR-0005** SUP-A 任务包仅使用 stdlib，不引入新依赖（2026-05-10）

---

## Agent 接入快速参考

新 Agent 启动会话，按此顺序读 5 个文件即可进入工作状态：

1. **本文件 STATE.md** — 当前状态
2. [`AGENTS.md`](AGENTS.md) — 项目宪法（约束）
3. [`CLAUDE.md`](CLAUDE.md) — Claude 专用执行规范（如果是 Claude）
4. [`SCOPE.md`](SCOPE.md) — 当前范围（V1 边界）
5. `journal/` 最新 1-2 篇日报 — 上一个 Agent 做了什么

如有任务可拾取，再读对应的 `docs/tasks/<task>.md`。
