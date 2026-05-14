# 会话结束检查清单

> 触发条件：用户说"收尾"，或 Agent 判断主线工作已完成。
> 即使用户没说"收尾"，只要会话中有**阶段推进、重大决策或产出物**，也必须执行。

---

## 必做项（按顺序）

- [ ] **STATE.md** — 更新当前阶段、进行中任务、阻塞项、待用户决策、最近重大决策。时间戳精确到分钟（如 `2026-05-14 10:34 +08`）
- [ ] **任务包同步** — 如本次新增/修改任务包或任务依赖，确认 `STATE.md` 已列出任务包链接、执行顺序和待用户决策
- [ ] **日报** — 写 `journal/YYYY-MM-DD_HHMM_<tool>_<model>.md`（格式见 [journal-spec.md](journal-spec.md)，2026-05-12 起命名加入 HHMM。**所有时间字段精确到分钟**，不可只写日期）
- [ ] **ADR** — 如有新决策或状态变更（Proposed→Accepted 等），更新对应 ADR 和 [docs/decisions/README.md](../decisions/README.md) 索引表
- [ ] **CLAUDE.md / AGENTS.md** — 如有阶段变化、新模块、新约定，同步更新

- [ ] **git commit** — 上述变更统一提交，message 前缀使用：
  - `docs(meta):` — CLAUDE.md / AGENTS.md / STATE.md
  - `docs(state):` — 仅 STATE.md
  - `docs(journal):` — 仅日报
  - `docs(decision):` — ADR 新增或状态变更

---

## 跳过场景

只读问答、纯探索性对话、无产出物的咨询——这些不需要走清单。判断标准：会话结束后，仓库是否有任何文件被修改或新增。如果没有，跳过。

---

## 与完成汇报的关系

完成汇报（[report-format.md](report-format.md)）是任务级别的"做了什么"。
会话结束清单是会话级别的"留下什么记录"。两者互补，不重复。
