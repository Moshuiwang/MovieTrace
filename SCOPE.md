# 项目范围边界（SCOPE）

> AI 做"任务可不可做"的硬边界仲裁。任务模糊时先对照本文件判断是否越界。
> **配套：** [`docs/product_roadmap.md`](docs/product_roadmap.md) 是详细路线图。
> **更新策略：** 阶段切换或范围调整时更新。

**当前阶段：** Phase 1 全部任务包已完成；V1 运行观察期。

---

## V1 做什么

每日检测全网热门英文影视更新事件；A 库 TV 剧集新季更新由 `baseline-track` 按上层调度独立执行，输出清单供运营挑选。详见 [ADR-0007](docs/decisions/0007-repositioning-to-update-tracking.md)。

**核心范围：** 全网热门追踪 · 基线 TV 主动追踪（电影跳过）· `hot_score` 综合评分 · A 库匹配标记 · 检测/导出解耦 · 三类输出（🆕 新增 / ♻️ 已有可补充 / ⚠️ 低置信度）· 本地 MD/JSON 报告 + 飞书运营三张子表 · `content_updates` 事件历史表（[ADR-0012](docs/decisions/0012-content-updates-event-history.md)）。
**数据源：** TMDb · Trakt · OMDb（1000/日）· FlixPatrol（合规公开页面）。
**技术栈：** Python 3.12 + SQLite 本地 B 库（不引入 PostgreSQL / MySQL）。

## V1 明确不做（scope creep 防线）

- **付费 API：** Watchmode / IMDb Pro / JustWatch Partner
- **社交信号：** Rotten Tomatoes / Metacritic / Reddit / Twitter / TikTok / YouTube / Letterboxd
- **AI 推理：** LLM 用户契合度 · 多 Agent 推理 · Embedding 语义匹配 · 协同过滤 · 时序预测 · AI 文案
- **业务下游：** 自动提交供应商 · 自动下载/入库/上架 · 国家粒度上线追踪 · 资源版本管理 · 后台管理页
- **V1.5 边界（ADR-0007 起）：** 电影主动追踪 · TV episode 级追踪（V2） · 抽象 Writer 多态（仍硬编码飞书） · A 库写入或修改（系统对 A 库只读） · 系统侧主观判断或人工审核字段（`review_status` / `audience_relevance` / `ai_reason` 已删除）
- **合规绝对线：** 详见 [`.claude/rules/22-sources-compliance.md`](.claude/rules/22-sources-compliance.md)

## V2 触发条件（全部满足）

1. V1 稳定运行 ≥ 1-2 个月
2. 运营反馈**具体**需求短板（不是"感觉可以更好"）
3. 投入产出比清晰（LLM 月成本 vs 推荐质量可量化）
4. 业务方明确同意承担额外成本

V2 候选方向见 [`docs/product_roadmap.md § 3`](docs/product_roadmap.md)。

## 边界判断

任务在 V1 范围 → 继续读任务包；不在 → 是 V2（放入 backlog）/ 合规外（拒绝并报告）/ 边界模糊（向用户澄清，不擅自决策）。**默认按更窄解释**，争议写入任务包"风险点"。历史范围变更：[`docs/decisions/`](docs/decisions/README.md)（ADR-0001/0002/0003/0007/0012）。
