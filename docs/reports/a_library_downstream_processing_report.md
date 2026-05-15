# A 库下游数据处理报告

> 面向 A 库研发团队。
> 2026-05-15 · MovieTrace Phase 1

---

## 一、做了什么

A 库提供两张源表 — `upstream_programs`（735 行）和 `upstream_episodes`（6562 行）。我们没有修改任何原始字段，所有增强都在下游完成，通过外键关联回 A 库数据。

### 1. 内容规范化（969 条 `canonical_items`）

对 A 库命名做统一解析，建立规范化中间表：

```
upstream_programs          upstream_episodes
      \                        /
       → canonical_items (969) ←
         ├── tv/series   (289)   完整剧集
         ├── tv/season   (532)   单季
         └── movie       (107)   电影
```

每个条目有统一标题、类型标记、TMDb ID / IMDB ID 交叉引用。

### 2. 剧集聚合与追踪状态（307 部 `virtual_series`）

将同名剧的不同季聚合为一部"虚拟剧集"，并接入 TMDb 实时状态：

| 增强字段 | 来源 | 说明 |
|---------|------|------|
| `tmdb_status` | TMDb | Returning Series / Ended / Canceled / In Production / Pilot / Planned |
| `tmdb_number_of_seasons` | TMDb | 官方总季数 |
| `local_max_season` | 本地追踪 | 系统记录的最大季号 |
| `poll_priority` | 规则推导 | 决定轮询是否跳过 |
| `last_polled_at` | 本地 | 上次查询时间 |

```
307 部
  ├── Returning Series  85   ← 持续追踪
  ├── Ended            187   ← 数据冻结
  └── Canceled          35   ← 自动跳过
```

### 3. TMDb 富元数据缓存（1213 条 TV + 246 条 Movie）

每次查询 TMDb API，返回的完整 JSON（33 个字段）全部缓存到 `api_cache` 表，275/307 部 VS 已有详情缓存。以 The Last of Us 为例：

| 类别 | 缓存字段 | A 库可直接复用 |
|------|---------|-------------|
| 视觉素材 | `poster_path`、`backdrop_path` | 前端海报/背景，无需再调 TMDb |
| 内容文本 | `overview`、`tagline` | 详情页介绍 |
| 创作者 | `created_by[]`（姓名+头像） | 演职员信息 |
| 类型/国家 | `genres[]`、`origin_country[]`、`languages[]` | 分类筛选 |
| 播出方 | `networks[]`、`production_companies[]` | HBO·Netflix 等出品方 |
| 评分 | `vote_average`、`vote_count`、`popularity` | 热度排序 |
| 季详情 | `seasons[]`（每季含海报+简介+集数+首播日） | 季级页面 |
| 播出进度 | `last_episode_to_air`、`next_episode_to_air` | 排期/回归预警 |
| 制作状态 | `in_production`、`status`、`type` | 上下架决策参考 |

这些字段本身不归属于我们，而是我们对 TMDb 的合规调用结果。A 库如果要在界面展示或运营流程中使用，可以直接读 `api_cache` 的 `response_json` 字段（标准 JSON），按需解析。

### 4. 更新事件检测（`content_updates`）

每天从 **3 个热度源**（TMDb Trending、Trakt Trending、FlixPatrol Top10）抓取榜单，与已入库内容做实体匹配，产出两类事件：

| 事件类型 | 含义 | 触发条件 |
|---------|------|---------|
| `new_discovery` | 热门候选 | trending 榜单上的热门内容 |
| `new_season` | 新季检测 | TMDb 季数 > 本地记录 |

每条事件带有 `hot_score`（综合多信号计算）和 `priority`。

### 5. 辅助数据

- **1083 条 IMDB ↔ TMDb 交叉引用**（`external_ids`）
- **TMDb / Trakt / FlixPatrol 源数据归档**，可追溯每日热度快照

---

## 二、数据量一览

```
A 库源表 (735 programs + 6562 episodes)
        │
        ▼
  canonical_items (969)        ← 规范化
        │
        ▼
  virtual_series (307)         ← 聚合 + TMDb 状态 + 海报/简介/评分
        │
        ├──→ baseline-track    → new_season 事件
        └──→ daily-discover    → new_discovery 事件
                                      │
                                      ▼
                               content_updates (事件历史)
                                      │
                                      ▼
                               reports/latest.md  (可读报告)
```

---

## 三、当前已可用

1. **节目状态面板** — 275 部剧集的 TMDb 详情缓存在本地，含海报、简介、评分、类型、季列表
2. **新季自动发现** — 每周轮询 85 部活跃剧集，季号一涨自动记录
3. **市场热度快照** — 每天 3 个源的热度榜单，知道什么在火
4. **数据漏斗** — 从 A 库到可追踪剧集的每一步转化可量化

---

## 四、未来可协同方向

### 4.1 直接给 A 库前端提供素材

`api_cache` 里 275 部剧集的海报、背景、简介、评分、演职人员都已就绪，A 库前端可以直接读 JSON 渲染节目详情页，不用再单独调用 TMDb。数据结构是标准 TMDb API 返回值，你们的研发可以直接对接。

### 4.2 内容运营工作台

- 飞书多维表格自动同步事件报告
- 按 hot_score 排序的候选推荐单
- Returning / Ended / Canceled 状态筛选

### 4.3 排期与预警

- `next_episode_to_air` 可做回归预告
- `last_episode_to_air` 可追踪播出进度
- `in_production` 标记制作中的剧集

### 4.4 A 库数据治理反馈

规范化过程中发现的可反馈 A 库的数据问题：在线节目数 vs 季级匹配数的 gap、Canceled 节目是否需要调整展示优先级、名称含 Sxx 但缺剧集级条目的情况。

### 4.5 直接对接飞书运营

当前已产出结构化 JSON（`reports/latest.json`、`reports/baseline_latest.json`），可以对接 `lark-cli` 写入飞书多维表格，运营在飞书里直接看候选和更新。

---

## 五、技术概要

| 项目 | 数据 |
|------|------|
| 源表（只读） | `upstream_programs` 735 · `upstream_episodes` 6562 |
| 规范化 | 969 条 `canonical_items` |
| 聚合追踪 | 307 部 `virtual_series`（272 跟踪中） |
| TMDb 详情缓存 | 1213 TV + 246 Movie 完整 JSON |
| IMDB 交叉引用 | 1083 条 |
| 日常输出 | `reports/latest.md` / `reports/latest.json`（每天 08:00） |
| 数据库 | SQLite `data/movietrace.db`，schema version 14 |
