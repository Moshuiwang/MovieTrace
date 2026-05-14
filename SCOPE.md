# MovieTrace 范围边界（SCOPE）

> **目的：** 让任何 Agent 一眼看到"当前阶段做什么、不做什么"，防止任务越界。  
> **更新策略：** 每次阶段切换或范围调整时更新。  
> **配套文档：** [`docs/product_roadmap.md`](docs/product_roadmap.md) 是更详细的路线图，本文件是"可执行边界"。

---

**当前阶段：** Phase 1 全部任务包已完成；当前为 V1 维护/收尾（P1.15 文档收口进行中）
**最后更新：** 2026-05-14 20:52 +08 by Claude Code (deepseek-v4-pro)

---

## V1 范围（当前）

### ✅ V1 做什么

**核心目标：** 每日检测全网热门英文影视内容的更新事件，以及 A 库（运营业务库）中已有 TV 剧集的新季更新，写入中间表/导出清单供运营从中挑选并提交供应商。详见 [ADR-0007](docs/decisions/0007-repositioning-to-update-tracking.md)。

**功能范围：**
- 功能 1：全网热门追踪（FlixPatrol + TMDb + Trakt + OMDb，按 `hot_score` 阈值过滤）
- 功能 2：基线内容主动追踪（TV 剧集，按 TMDb `status` 智能轮询；电影跳过）
- 综合评分（hot_score 0-100，可解释，可配置）
- 与 A 库匹配标记（`is_in_baseline`，低置信度匹配标记 `match_confidence_low`）
- 输出两类 + 1 低置信度收纳：
  - 🆕 新增：当前库中未有的高热度好评内容
  - ♻️ 已有可补充：当前库中已有但热度/新季可更新
  - ⚠️ 待人工确认：实体匹配低置信度，需运营在中间表中判断对应关系
- 每日 Markdown 日报（运行可观察性）
- 本地 MD + JSON 报告导出（`export-recommendations`）；未来如需中间表协作界面（Notion/Excel），接口抽象等 V2 或后续决策
- 检测与导出解耦：`daily-discover`（检测，写 B 库）+ `export-recommendations`（导出 MD + JSON 到 `reports/`）
- `content_updates` 作为事件历史表：跨天重新命中的内容允许再次进入最近 N 天导出；discovery 事件 ID 必须包含 TMDb 媒体命名空间（ADR-0012）
- 手动 dry-run 和 commit 模式
- bootstrap（180 天追赶）和 daily 两种运行模式

**数据源（V1 限定）：**
- TMDb API（免费）
- Trakt API（免费）
- OMDb API（免费 1000/日）
- FlixPatrol（合规公开页面，待 Phase 0+ 验证通过）

**技术约束（V1 限定）：**
- Python 3.12 + 现有依赖
- SQLite 本地数据库（不引入 PostgreSQL/MySQL）
- 本地 SQLite（B 库）+ MD/JSON 导出作为人工协作输出
- 配置：`.env` + `config.yaml`

---

### ❌ V1 明确不做（防止 scope creep）

#### 数据源类
- ❌ 付费 API（Watchmode、IMDb Pro、JustWatch Partner）
- ❌ Rotten Tomatoes / Metacritic（爬虫或付费）
- ❌ Reddit / Twitter / TikTok 社交信号
- ❌ YouTube 预告片数据
- ❌ Letterboxd 影迷信号
- ❌ Netflix Tudum 直接爬虫（用 FlixPatrol 聚合）

#### AI / 算法类
- ❌ LLM 用户契合度判断
- ❌ 多 Agent 推理框架
- ❌ Embedding 语义匹配
- ❌ 协同过滤推荐
- ❌ 时序预测（即将爆款）
- ❌ AI 推荐文案自动生成

#### 业务流程类
- ❌ 自动提交供应商接口
- ❌ 自动下载、入库、上架
- ❌ 非洲各国家/地区逐区上线追踪
- ❌ 资源清晰度/字幕/配音版本追踪
- ❌ 多供应商管理
- ❌ 后台管理页面

#### 合规边界（绝对不做）
- ❌ 绕过登录、验证码、付费墙、反爬
- ❌ 高频无控制网页抓取
- ❌ IMDb 页面默认抓取（用 OMDb 代理）

#### V1.5 定位边界（自 ADR-0007 起）
- ❌ 电影的"主动追踪"（电影无"季"概念，续集发现由功能 1 通过热度榜兜底）
- ❌ TV 剧集的"新集"主动追踪（episode-level `new_episode`）：2026-05-14 用户确认放入 V2，V1 只追踪新季。
- ❌ 抽象 Writer 接口（`FeishuWriter` / `NotionWriter` 多态），V1.5 仍硬编码飞书，接口抽象等 V2
- ❌ A 库（运营业务库）的写入或修改（系统对 A 库只读，承袭 ADR-0004 精神）
- ❌ 系统侧做"内容质量主观判断"（不是推荐系统，不做 `audience_relevance` 之类评估，V2 LLM 才考虑）
- ❌ 系统侧的"人工审核字段"（`review_status` / `audience_relevance` / `ai_reason` 等已删除）

---

## V2 范围（下阶段，需明确触发条件）

### 触发条件

V2 启动需**全部满足**：
1. V1 已稳定运行至少 1-2 个月
2. 运营反馈了**具体**的需求短板（不是"感觉可以更好"）
3. V2 投入产出比清晰（如 LLM 月成本 vs 推荐质量提升的可量化收益）
4. 业务方明确同意承担 V2 额外成本

### V2 候选方向（按优先级）

详见 [`docs/product_roadmap.md`](docs/product_roadmap.md) § 3。摘要：

| 方向 | 优先级 | 触发问题 |
|------|--------|---------|
| LLM 用户契合度判断 | ⭐⭐⭐ | "推荐内容对非洲英文用户契合度低" |
| 多 Agent 推理框架 | ⭐⭐ | "运营需要更多推荐理由解释" |
| RT + Metacritic 评分聚合 | ⭐⭐ | "单源评分被刷分误导" |
| TV 新集更新追踪 | ⭐⭐ | "运营需要按 episode-level 捕捉已有剧集更新" |
| Watchmode/IMDb Pro 等付费 API | ⭐ | "免费 API 信号不足" |

---

## 当前任务的边界判断

任何 Agent 接到任务时，对照本文件判断：

```
任务在 V1 范围内？
├── 是 → 继续读任务包
└── 否 → 检查：
        ├── 是 V2 范围？→ 拒绝执行，建议放入 V2 backlog
        ├── 是合规边界外？→ 拒绝执行，向用户报告
        └── 边界模糊？→ 向用户澄清，不擅自决定
```

---

## 范围争议的处理

如发现某任务的范围归属不清晰：

1. **不擅自扩大范围**（默认按更窄解释）
2. **写一份说明放入任务包"风险点"**
3. **向用户提问，不替用户决策**

记住 AGENTS.md 第一条：**AI 不能替开发者做最终产品判断**。

---

## 历史范围变更

| 日期 | 变更 | 决策依据 |
|------|------|---------|
| 2026-05-07 | 初始范围（基线对比新更新） | requirements.md 初稿 |
| 2026-05-10 | 调整为"独立全网热门发现 + 基线标记" | ADR-0001（详见 docs/decisions/） |
| 2026-05-10 | 加入 FlixPatrol 作为 V1 数据源 | ADR-0003 |
| 2026-05-10 | 明确 V1/V2 划分原则 | ADR-0002 |
| 2026-05-11 | 系统定位翻转：从"推荐+人工审核"到"更新追踪+中间表"；新增功能 2（基线主动追踪）；确立 A库/B库/中间表三层架构 | ADR-0007 |
| 2026-05-14 | 明确 TV 新集更新追踪放入 V2；V1/P1.12 只修复新季链路，不新增 episode-level update_type | 用户决策；ADR-0007 修正 |
| 2026-05-14 | 明确 `content_updates` 从全局去重建议池改为事件历史表；跨天重复命中可再次写入 | ADR-0012 |
| 2026-05-14 | 明确 discovery `content_update_id` 使用 `discovery:{movie|tv}:{tmdb_id}:{date}`，避免 TMDb movie/tv 数字 ID 撞车 | P1.13 review hotfix |
| 2026-05-14 | SCOPE.md 修正：飞书写入从"当前实现"改为历史，当前输出链路为 B 库 + MD/JSON 导出 | P1.15 V1 收口 |
