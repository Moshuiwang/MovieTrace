# MovieTrace 范围边界（SCOPE）

> **本质：** 给 AI Agent 做"任务可不可做"的**硬边界仲裁**。任务模糊时先对照本文件判断是否越界。
> **配套：** [`docs/product_roadmap.md`](docs/product_roadmap.md) 是详细路线图；本文件只看"可执行边界"。
> **更新策略：** 每次阶段切换或范围调整时更新。

---

**当前阶段：** Phase 1 全部任务包已完成；当前 V1 运行观察期（P1.18 拆分热点发现与基线追踪节奏后）
**最后更新：** 2026-05-17 00:08 +08 by Claude Code CLI（Opus 4.7）

---

## V1 做什么（当前）

**核心目标：** 每日检测全网热门英文影视内容的更新事件；A 库已有 TV 剧集的新季更新由 `baseline-track` 独立按上层调度节奏执行，写入 B 库后导出清单供运营挑选并提交供应商。详见 [ADR-0007](docs/decisions/0007-repositioning-to-update-tracking.md)。

**功能范围：**
- 全网热门追踪（FlixPatrol + TMDb + Trakt + OMDb，按 `hot_score` 阈值过滤）
- 基线 TV 剧集主动追踪（按 TMDb `status` / `in_production` 智能轮询；电影跳过）
- 综合评分 `hot_score`（0-100，可解释，可配置）
- 与 A 库匹配标记（`is_in_baseline` + `match_confidence_low`）
- 三类输出：🆕 新增热门 · ♻️ 已有可补充 · ⚠️ 低置信度待人工确认
- 检测与导出解耦：`daily-discover` + `baseline-track` + `export-recommendations` / `export-baseline-updates`
- `content_updates` 作为事件历史表：跨天重新命中允许再次入库（[ADR-0012](docs/decisions/0012-content-updates-event-history.md)）
- 本地 MD + JSON 报告导出 + 飞书运营同步层（热点发现 / A库缺口 / 周反馈三张子表）
- 手动 dry-run 和 commit 模式；bootstrap（180 天追赶）和 daily 两种运行模式

**数据源（V1 限定）：** TMDb · Trakt · OMDb（免费 1000/日）· FlixPatrol（合规公开页面）

**技术约束：** Python 3.12 + 现有依赖 · SQLite 本地（B 库）· `.env` + `config.yaml`；不引入 PostgreSQL / MySQL

---

## V1 明确不做（防止 scope creep）

**数据源类：**
- ❌ 付费 API（Watchmode、IMDb Pro、JustWatch Partner）
- ❌ Rotten Tomatoes / Metacritic / Reddit / Twitter / TikTok / YouTube / Letterboxd 信号
- ❌ Netflix Tudum 直接爬虫（用 FlixPatrol 聚合代理）

**AI / 算法类：**
- ❌ LLM 用户契合度判断 · 多 Agent 推理框架 · Embedding 语义匹配 · 协同过滤 · 时序预测 · AI 文案

**业务流程类：**
- ❌ 自动提交供应商接口 · 自动下载/入库/上架 · 国家粒度上线追踪 · 资源版本管理 · 后台管理页面

**合规边界（绝对不做）：**
- ❌ 绕过登录、验证码、付费墙、反爬
- ❌ 高频无控制网页抓取
- ❌ IMDb 页面默认抓取（用 OMDb 代理）

**V1.5 定位边界（自 ADR-0007 起）：**
- ❌ 电影的"主动追踪"（电影无"季"概念，续集发现由功能 1 通过热度榜兜底）
- ❌ TV 剧集的"新集" episode-level 追踪（V1 只追新季，episode 进 V2，2026-05-14 用户确认）
- ❌ 抽象 Writer 接口多态（`FeishuWriter` / `NotionWriter`），V1.5 仍硬编码飞书
- ❌ A 库（运营业务库）的写入或修改（系统对 A 库只读，承袭 ADR-0004 精神）
- ❌ 系统侧"内容质量主观判断"（不是推荐系统，V2 LLM 才考虑）
- ❌ 系统侧"人工审核字段"（`review_status` / `audience_relevance` / `ai_reason` 已删除）

---

## V2 触发条件

V2 启动需**全部满足**：
1. V1 已稳定运行至少 1-2 个月
2. 运营反馈了**具体**的需求短板（不是"感觉可以更好"）
3. V2 投入产出比清晰（如 LLM 月成本 vs 推荐质量提升的可量化收益）
4. 业务方明确同意承担 V2 额外成本

**V2 候选方向详表：** 见 [`docs/product_roadmap.md § 3`](docs/product_roadmap.md)。

---

## 边界判断流程

任何 Agent 接到任务时，对照本文件判断：

```
任务在 V1 范围内？
├── 是 → 继续读任务包
└── 否 → 检查：
        ├── 是 V2 范围？      → 拒绝执行，建议放入 V2 backlog
        ├── 是合规边界外？    → 拒绝执行，向用户报告
        └── 边界模糊？        → 向用户澄清，不擅自决定
```

**争议处理：** 不擅自扩大范围（默认按更窄解释）· 写说明放入任务包"风险点"· 向用户提问，不替用户决策。

核心原则：**AI 不能替开发者做最终产品判断**（[CLAUDE.md](CLAUDE.md) 第一原则）。

**历史范围变更：** 见 [`docs/decisions/`](docs/decisions/README.md)（ADR-0001/0002/0003/0007/0012 覆盖）。
