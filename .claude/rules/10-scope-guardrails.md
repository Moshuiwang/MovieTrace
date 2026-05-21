---
name: scope-guardrails
description: V1 范围硬防线：禁止引入的技术/功能清单，以及越界时的决策规则。任务可做性判断前必读。
include: ["**/*"]
---

# V1 范围硬防线

## 禁止引入（scope creep 防线）

- **付费 API：** Watchmode / IMDb Pro / JustWatch Partner
- **社交信号：** Rotten Tomatoes / Metacritic / Reddit / Twitter / TikTok / YouTube / Letterboxd
- **AI 推理：** LLM 用户契合度 · 多 Agent 推理 · Embedding 语义匹配 · 协同过滤 · 时序预测 · AI 文案
- **业务下游：** 自动提交供应商 · 自动下载/入库/上架 · 国家粒度上线追踪 · 资源版本管理 · 后台管理页
- **V1.5 边界：** 电影主动追踪 · TV episode 级追踪（V2）· 抽象 Writer 多态 · A 库写入或修改（系统对 A 库**只读**）· 系统侧主观判断字段（`review_status` / `audience_relevance` / `ai_reason` 已删除）
- **合规绝对线：** 详见 [`22-sources-compliance.md`](22-sources-compliance.md)

## 越界决策规则

| 判断结果 | 处置 |
|---|---|
| 在 V1 范围内 | 继续读任务包，正常推进 |
| 属于 V2 | 放入 [`PLAN.md`](../../PLAN.md) backlog，不在当前开发 |
| 合规外 | 拒绝并向用户报告原因 |
| 边界模糊 | 向用户澄清，不擅自决策 |

**默认按更窄解释**，争议写入任务包"风险点"。历史范围变更：[`docs/decisions/`](../../docs/decisions/)（ADR-0001/0002/0003/0007/0012）。
