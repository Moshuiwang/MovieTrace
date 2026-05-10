# MovieTrace 项目状态快照

> 这是项目当前状态的实时快照。**任何 Agent 启动新会话时必读。**  
> 每次 git commit 前应更新本文件。

---

**最后更新：** 2026-05-10  
**更新人：** Claude Code (Opus 4.7)  
**Git Commit：** `8ada68e`  
**所在分支：** `main`

---

## 当前阶段

| 阶段 | 状态 |
|------|------|
| Phase 0：开发前验证 | ✅ 已完成（Go 决策） |
| Phase 0+：FlixPatrol 接入验证 | 🔄 准备中（任务包就绪，待启动） |
| Phase 1：V1 MVP 开发 | ⏳ 待 Phase 0+ 通过 |

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

## 进行中任务

| 任务 | 状态 | 任务包 |
|------|------|-------|
| SUP-A FlixPatrol 可访问性测试 | Ready（待启动） | [docs/tasks/sup_a_flixpatrol_accessibility.md](docs/tasks/sup_a_flixpatrol_accessibility.md) |

---

## 阻塞项

无。

---

## 待用户决策

1. **SUP-A 启动时间** — 任务包就绪，等用户决定何时启动
2. **多 Agent 协作框架的最终形态** — 已采纳精简版，今日实施中
3. **Phase 1 任务包详细拆分** — Phase 0+ 通过后再写

---

## 最近 5 次重大决策（详见 [docs/decisions/](docs/decisions/)）

1. **ADR-0001** 飞书基线从过滤逻辑改为标记参考（2026-05-10）
2. **ADR-0002** V1/V2 严格划分原则（2026-05-10）
3. **ADR-0003** V1 引入 FlixPatrol 作为真实平台热度源（2026-05-10）
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
