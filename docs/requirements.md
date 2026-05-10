# MovieTrace 项目需求文档

状态：需求确认版 V2（产品方向重新对齐）  
日期：2026-05-10（产品方向重新对齐）  
原始日期：2026-05-07  
仓库：https://github.com/Moshuiwang/MovieTrace

## 1. 项目背景

MovieTrace 面向视频网站运营场景，**每日产出"值得更新"的英文影视内容列表**，给运营做人工审核和提交供应商的决策。

"值得更新"= 同时满足：
- **热度高** — 当前正在流行（基于真实平台热度 + 社区热度）
- **评分好** — 内容质量经过多源验证
- **平台相关** — Netflix、Prime Video、Disney+、Apple TV+、HBO/Max、Hulu
- **目标用户契合** — 非洲英文用户口味（V2 阶段引入 LLM 契合度判断）

项目核心定位：
1. **不是**视频资源获取系统（不下载、不入库）
2. **不是**纯粹的"新内容更新追踪系统"（不只是发现上线消息）
3. **是**"全网值得更新内容的发现 + 排序 + 推荐"系统

### 1.1 关键产品决策（2026-05-10）

**核心逻辑调整：** 从"基线对比"改为"独立发现 + 基线标记"。

- **旧逻辑：** TMDb/Trakt → 与飞书基线去重 → 推荐"基线没有"的
- **问题：** 陷入"先有鸡还是先有蛋"。基线本身不完整 → 永远打不破基线天花板。
- **新逻辑：** 独立发现"全网热门好评" → 与基线匹配（仅标记，不过滤）→ 输出"新增 + 已有可补充"

**详细路线图见 [product_roadmap.md](product_roadmap.md)**。

## 2. 业务目标

### 2.1 主要业务目标

1. **每日产出"值得更新"内容列表** — 包括两类：
   - 🆕 新增推荐：飞书基线未有的高热度好评内容
   - ♻️ 已有可补充：飞书基线已有但热度数据可更新的内容
2. **多维度信号融合** — 真实平台热度 + 社区热度 + 内容质量评分 + 平台权重
3. **重点追踪电视剧，其次追踪电影**
4. **重点关注英文内容**，允许非英文但在英语用户或目标市场中热度高的内容进入候选
5. **重点关注六大平台**：Netflix、Prime Video、Disney+、Apple TV+、HBO/Max、Hulu，覆盖 Global 和 US
6. **服务于非洲英文用户运营** — 推荐结果围绕该群体口味做排序（V2 引入 LLM 判断）
7. **结果沉淀到飞书多维表格** + 生成日报和多日汇总
8. **支持人工审核、手动分批、提交供应商、上架状态追踪**

### 2.2 飞书基线的角色变更

**从"主过滤逻辑"变为"标记参考"：**
- ✅ 飞书基线用于：标记候选内容是否已上架（is_in_baseline = true/false）
- ❌ 飞书基线**不用于**：过滤掉已有内容（已有内容也可能需要补充评分/热度数据）

**业务价值：**
- 不依赖基线完整性也能发现新内容
- 已有内容的元数据（评分、热度变化）可持续更新
- 运营可以决定"已有内容是否值得二次推广"

## 3. MVP 范围

### 3.1 包含范围

- 新电影上线。
- 新剧上线或开播。
- 连载剧新增单集。
- 新季发布。
- 每日自动运行。
- 手动立即运行。
- 指定日期范围补采。
- 基于现有线上内容飞书表的冷启动。
- 半年内新剧、新季、新集、新电影的追赶更新。
- 飞书多维表格结构化沉淀。
- 飞书文档日报和多日汇总。
- 人工审核。
- 手动创建供应商批次。
- 供应商与上架状态追踪。

### 3.2 不包含范围

- 资源清晰度更新。
- 字幕版本更新。
- 配音版本更新。
- 非洲各国家/地区逐平台可看性追踪。
- 自动提交供应商接口。
- 自动下载、入库或上架视频资源。
- 绕过登录、验证码、付费墙或反爬机制的网页采集。

## 4. 合规采集边界

系统必须优先使用官方 API、授权数据源、公开允许访问的数据集或符合目标网站规则的公开页面。

约束如下：

1. 不绕过登录、验证码、付费墙、反爬限制。
2. 不进行高频、无控制的网页抓取。
3. 对每个数据源支持限流、重试和错误记录。
4. IMDb 不作为默认网页抓取目标。若使用 IMDb 数据，应优先使用官方授权数据、公开数据集或通过 TMDb/Trakt 等数据源映射外部 ID。
5. 对无法确认合规性的页面，仅记录为待评估数据源，不进入 MVP 自动采集。

## 5. 数据源

### 5.1 V1 数据源（当前阶段）

V1 只使用免费/低成本数据源，且优先使用官方 API 或合规公开页面。

| 数据源 | 用途 | 类型 | 状态 |
| --- | --- | --- | --- |
| **TMDb API** | 元数据、社区热度、评分、流媒体 provider | 官方API（免费） | ✅ 已接入 |
| **Trakt API** | 用户观看热度、趋势、剧集日历 | 官方API（免费） | ✅ 已接入 |
| **OMDb API** | IMDb 评分、投票数、英文标题 | 官方API（免费 1000/日） | ✅ 已接入 |
| **FlixPatrol** | **真实平台热度（Netflix Top 10、Prime Charts、Disney+ Top、Apple TV+ Top、HBO Max Top、Hulu Top）** | 合规公开页面 | 🆕 V1 待接入 |

**FlixPatrol 的关键价值：**

FlixPatrol（https://flixpatrol.com/）是行业内事实上的"流媒体平台 TOP 10 聚合源"，已经聚合了 Netflix、Prime Video、Disney+、Apple TV+、HBO Max、Hulu 等所有主流平台的官方排行榜。

- ✅ 弥补"TMDb/Trakt 是社区热度，缺真实平台热度"的核心短板
- ✅ 公开页面，合规可访问
- ✅ 按地区（Global/US/各国）和按平台细分
- ⚠️ 需以礼貌频率访问，加入缓存避免高频抓取
- ⚠️ 商业生产前需审视服务条款

### 5.2 V2 候选数据源（下一阶段，详见 product_roadmap.md）

V2 在 V1 上线运营一段时间后启动，根据实际运营反馈再决定具体引入哪些。

| 数据源 | 用途 | 类型 | 优先级 |
| --- | --- | --- | --- |
| **LLM API（Claude/GPT）** | 用户契合度判断、推荐文案、多维评估 | 付费按token | ⭐⭐⭐ |
| Rotten Tomatoes | 专业评分（Tomatometer + Audience Score） | 爬虫/付费API | ⭐⭐ |
| Metacritic | 严格的专业评分 | 爬虫/付费API | ⭐⭐ |
| Watchmode API | episode级流媒体追踪 | $99-499/月 | ⭐ |
| IMDb Pro Datasets | 商业级 popularity meter | $50+/月 | ⭐ |
| JustWatch Partner API | 跨平台可用性 | 需企业合作 | ⭐ |
| Reddit / Twitter | 社交讨论热度 | 爬虫/付费API | ⭐ |
| YouTube API | 预告片观看数据（预热信号） | 免费配额 | ⭐ |
| Letterboxd | 影迷深度评价 | 爬虫 | ⭐ |

### 5.3 平台范围

V1 覆盖以下流媒体平台：

- Netflix
- Prime Video
- Disney+
- Apple TV+
- HBO/Max
- Hulu

### 5.4 地区范围

V1 只关注：

- Global
- US

不做非洲各国家/地区的逐区上线追踪。非洲用户相关性在 V2 引入 LLM 判断后实现。

## 6. 核心业务流程

V2 的产品方向调整后，业务流程分为两条独立路径，最终汇合到推荐表。

### 6.1 流程图

```text
                    ┌─────────────────────────────────┐
                    │    路径A: 全网热门好评发现         │
                    │  (V1 核心，独立于飞书基线运行)     │
                    └─────────────────────────────────┘
                                 ↓
            FlixPatrol(平台热度) + TMDb/Trakt(社区热度) + OMDb(IMDb评分)
                                 ↓
                    多源合并去重(by external_id)
                                 ↓
                    过滤(rating>=7.0, vote_count>=100)
                                 ↓
                    综合评分 hot_score(融合多源信号)
                                 ↓
                    priority 映射(P0/P1/P2/P3)


                    ┌─────────────────────────────────┐
                    │    路径B: 飞书基线匹配标记         │
                    │  (仅用于标记 is_in_baseline)       │
                    └─────────────────────────────────┘
                                 ↓
                    读取飞书线上内容基线表(855条)
                                 ↓
                    本地 SQLite 维护 baseline_items
                                 ↓
                    实体匹配 → external_ids 映射


                    ┌─────────────────────────────────┐
                    │       路径汇合: 候选合并标记       │
                    └─────────────────────────────────┘
                                 ↓
            候选 + 基线匹配 → 标记 is_in_baseline = true / false
                                 ↓
                    输出分类:
                    🆕 新增推荐 (is_in_baseline=false)
                    ♻️ 已有可补充 (is_in_baseline=true)
                    ⚠️ 待人工确认 (低置信度匹配)
                                 ↓
                    每日 Markdown 日报
                                 ↓
                    写入飞书多维表格推荐更新表
                                 ↓
                    人工审核 → 批次 → 供应商 → 上架追踪
```

### 6.2 关键变化（与原版对比）

| 项目 | 旧版 | 新版（V1） |
|------|------|-----------|
| 主发现路径 | 基线对比新更新 | 独立全网热门好评发现 |
| 飞书基线作用 | 主过滤逻辑 | 仅标记 is_in_baseline |
| 数据源主力 | TMDb/Trakt 候选 | FlixPatrol + TMDb + Trakt + OMDb |
| 推荐输出 | 单一"新内容"列表 | 三类（新增/已有可补充/待确认） |
| 解决的核心问题 | 发现新上线 | 突破基线天花板，全网值得更新 |

## 7. 运行模式

系统支持三种运行模式：

| 模式 | 用途 | 时间范围 | 输出控制 |
| --- | --- | --- | --- |
| bootstrap | 初始冷启动和追赶更新 | 默认最近 180 天，可配置 | 分批输出，避免一次性产生过多候选 |
| daily | 每日增量 | 默认最近 1-7 天和近期即将上线内容 | 输出每日高价值候选 |
| backfill | 人工补采 | 人工指定日期范围 | 用于修复漏采或补充历史窗口 |

### 7.1 冷启动基线

用户当前线上已有内容保存在飞书多维表格中。冷启动不应假设平台从零开始，而应先读取该表作为“已上架内容基线”。

基线表至少需要提供以下信息中的一部分：

| 字段 | 说明 |
| --- | --- |
| title | 线上已有内容标题 |
| content_type | 电影或电视剧 |
| season_number | 季编号，可为空 |
| episode_number | 集编号，可为空 |
| imdb_id | IMDb ID，可为空 |
| tmdb_id | TMDb ID，可为空 |
| trakt_id | Trakt ID，可为空 |
| online_status | 线上状态 |
| published_at | 上架时间，可为空 |

系统需要将线上已有内容标准化为内容基线，用于判断哪些内容已经存在，哪些内容是半年内需要补上的新剧、新季、新集或新电影。

### 7.2 半年追赶更新

由于线上内容较久未更新，MVP 冷启动需要覆盖最近半年内的高价值更新，但不做无边界全量抓取。

默认策略：

1. 时间窗口：最近 180 天，可配置。
2. 电视剧优先，电影其次。
3. 优先追赶新剧、新季和新集。
4. 新电影只保留热度较高或平台来源明确的候选。
5. 以现有线上内容基线为参照，过滤已上架内容。
6. 同一剧集中线上已存在旧集时，只推荐半年内新增且线上缺失的 episode。
7. 同一剧集已有上一季时，新 season 应作为追赶候选。
8. bootstrap 结果需要分批进入飞书，避免一次性产生过多人工审核项。

### 7.3 候选数量控制

系统不是全量影视数据库，不追求收集所有上线内容。系统只追求发现与业务更新决策相关的高价值候选内容。

候选规模必须可配置：

| 配置项 | 默认建议 |
| --- | --- |
| bootstrap_date_window_days | 180 |
| bootstrap_max_p0_p1_total | 200 |
| daily_max_p0_p1_total | 50 |
| min_hot_score_for_movie | 70 |
| min_hot_score_for_tv | 50 |
| p2_retention_enabled | true |
| p3_write_to_feishu | false |

P0/P1 是主要人工审核队列。P2 可作为备选保留，P3 默认不写入飞书或只写入调试日志。

## 8. 主键设计

### 8.1 内容主键

内容主键用于标识电影、剧集、季或集。

字段建议：

| 字段 | 说明 |
| --- | --- |
| canonical_item_id | 系统内部统一内容主键 |
| source | 主映射来源，例如 tmdb、imdb、trakt |
| source_item_id | 来源站点内容 ID |
| imdb_id | IMDb ID，可为空 |
| tmdb_id | TMDb ID，可为空 |
| trakt_id | Trakt ID，可为空 |
| content_granularity | movie、series、season、episode |
| parent_series_id | 所属剧集 ID，电影为空 |
| season_number | 季编号 |
| episode_number | 集编号 |

电视剧优先粒度：

```text
episode > season > series
```

如果能识别到具体集，应以 episode 作为最小业务对象。如果数据源没有稳定 episode ID，则退化为：

```text
source + parent_series_id + season_number + episode_number
```

### 8.2 内容更新主键

内容更新主键用于标识一次需要业务处理的影视更新。对当前业务来说，同一电影、同一集或同一季在不同平台上线，不需要生成多条待审核推荐；平台只作为来源证据、热度信号和推荐理由保留。

```text
content_update_id = canonical_item_id + update_type
```

示例：

同一集在 Netflix 和 Prime Video 上线，只生成一条 content_update。  
同一电影同时出现在 Global 和 US 来源中，只生成一条 content_update。  
同一内容在不同平台或地区的上线信息，应合并到 `platform_sources`、`regions`、`release_dates` 和 `heat_signals` 中。

只有当内容本身不同或业务更新类型不同，才生成新的内容更新记录。例如：

- 同一剧集的新一集上线，应按 episode 生成新的 content_update。
- 同一剧集的新季发布，应按 season 生成新的 content_update。
- 同一电影已上架后又被其他平台采集到，不应再次生成待审核推荐。

## 9. 实体标准化策略

实体标准化存在误合并风险，MVP 不要求一次性完美合并所有来源，而是采用分层策略。

每条采集记录必须保留：

| 字段 | 说明 |
| --- | --- |
| raw_source_record | 原始采集记录 |
| normalized_item | 标准化候选实体 |
| source | 数据来源 |
| source_item_id | 来源 ID |
| external_ids | IMDb、TMDb、Trakt 等外部 ID |
| mapping_confidence | high、medium、low |

规则：

1. 高置信度映射可以自动合并。
2. 中置信度映射可以合并，但必须保留来源依据。
3. 低置信度映射不得自动合并，应进入人工确认。
4. 标题相似但季集信息不一致时，不得自动合并。
5. 电影与电视剧不得因同名自动合并。

## 10. 热度与优先级

### 10.1 V1 热度来源

| 来源 | 信号 | 维度 |
| --- | --- | --- |
| **FlixPatrol** | Netflix Top 10、Prime Charts、Disney+ Top、Apple TV+ Top、HBO Max Top、Hulu Top | **真实平台热度** |
| TMDb | trending(day/week)、popular、vote_average、vote_count、watch provider | 社区热度+评分 |
| Trakt | trending、popular、watched、collected、calendar/new episode | 影迷社区热度 |
| OMDb / IMDb | imdb_rating、imdb_votes | 内容质量 |

**信号维度对比（重要洞察）：**
- TMDb / Trakt = 社区热度（影视迷为主）— 经常背离大众
- **FlixPatrol = 真实平台热度（大众用户）— V1 关键补充**
- IMDb 评分 = 长期质量信号（不是热度）
- 多维度交叉验证 > 单一来源排序

### 10.2 V1 hot_score 计算规则

`hot_score` 使用 0-100 分，采用透明可配置的规则，不使用黑盒 AI 分数。

| 因素 | 分值 | 说明 |
| --- | ---: | --- |
| **平台真实热度（FlixPatrol）** | **30** | **V1 核心信号，进入平台 Top 10 大幅加权** |
| TMDb 社区热度 | 15 | trending/popularity 排名 |
| Trakt 社区热度 | 10 | trending/popular 信号 |
| TMDb 评分 | 10 | vote_average × log(vote_count) |
| IMDb 评分 | 10 | imdb_rating × log(imdb_votes) |
| 平台来源权重 | 10 | Netflix、Prime Video 等重点平台加权 |
| 内容类型 | 5 | 电视剧高于电影 |
| 新鲜度 | 5 | 最近 90 天内上线加分 |
| 语言相关性 | 5 | 英文优先，非英文高热度也可进入 |

计算公式：

```text
hot_score = 
    flixpatrol_score * 0.30
  + tmdb_popularity_score * 0.15  
  + trakt_signal_score * 0.10
  + tmdb_rating_score * 0.10
  + imdb_rating_score * 0.10
  + platform_weight_score * 0.10
  + content_type_score * 0.05
  + freshness_score * 0.05
  + language_relevance_score * 0.05
```

所有权重必须可在配置文件中调整。

**V2 新增因素（产品迭代时启用，详见 product_roadmap.md）：**
- LLM 用户契合度评分（替代 language_relevance）
- Rotten Tomatoes 评分聚合
- Metacritic 评分聚合
- 时序预测信号（即将爆款）

### 10.3 priority 映射

| priority | hot_score | 含义 |
| --- | ---: | --- |
| P0 | >= 85 | 强烈建议优先提交 |
| P1 | 70-84 | 建议提交 |
| P2 | 50-69 | 可选提交 |
| P3 | < 50 | 低优先级或仅记录 |

推荐理由必须引用可解释依据，例如：

- 进入 FlixPatrol Netflix Global Top 10（排名 #3）。
- TMDb trending 排名靠前（popularity 95.6）。
- Trakt 观看热度本周上升 30%。
- IMDb 评分 8.2 / 投票数 1.2万。
- 多源交叉验证一致（FlixPatrol + TMDb + IMDb 都 high）。

## 11. 去重规则

### 11.1 R4 内容更新去重

内容更新去重解决同一次或多次采集中重复采到同一个内容更新的问题。不同平台、地区或来源采到同一内容时，不生成多条业务推荐，而是合并来源证据。

规则：

```text
同一 canonical_item_id
+ 同一 update_type
= 同一 content_update
```

合并规则：

1. 不同平台上线不生成新推荐，合并到 `platform_sources`。
2. 不同地区来源不生成新推荐，合并到 `regions`。
3. 不同上线日期不生成新推荐，合并到 `release_dates`，并保留最早采集日期和各平台日期。
4. 不同数据源采到同一内容不生成新推荐，合并到 `source_records` 和 `heat_signals`。
5. 不同内容粒度不得错误合并。例如同一季的不同 episode 不能合并。
6. 不同业务更新类型不得错误合并。例如新季发布和新增单集应分别处理。

### 11.2 R6 业务状态去重

业务状态去重解决已经进入后续业务流程的内容是否继续推荐的问题。

规则：

| 对象 | 去重粒度 |
| --- | --- |
| 电影 | movie |
| 新季 | season |
| 连载剧新增单集 | episode |
| 新剧开播 | series 或 premiere episode |

状态判断：

1. 已上架内容默认不再重复推荐。
2. 暂无资源内容默认不再重复推荐，除非人工改回待处理。
3. 已提交供应商、已下载、已入库内容不再作为新的待提交推荐。
4. 同一季中此前未采集到的新 episode，本次首次采集到时，不算重复，应进入候选。
5. 同一剧集出现新季发布时，即使上一季已上架，也应作为新的内容更新进入候选。

## 12. 飞书多维表格设计

本地数据库作为系统事实源，负责结果沉淀、去重、状态记录、原始响应缓存和运行记录。飞书多维表格作为输入来源和可选人工协作视图，不再承担唯一主数据管理职责。

### 12.1 线上内容基线表

线上内容基线表是用户已有的飞书多维表格，用于记录当前网站已经上线的影视内容。系统需要读取该表，但 MVP 不要求改造用户现有表结构；如果字段不完整，系统应通过标题、类型、季集号和外部 ID 做尽可能可靠的映射。

建议字段：

| 字段 | 说明 |
| --- | --- |
| title | 线上已有内容标题 |
| content_type | 电影或电视剧 |
| season_number | 季编号，可为空 |
| episode_number | 集编号，可为空 |
| imdb_id | IMDb ID，可为空 |
| tmdb_id | TMDb ID，可为空 |
| trakt_id | Trakt ID，可为空 |
| online_status | 线上状态 |
| published_at | 上架时间，可为空 |

该表作为业务状态去重和半年追赶更新的输入来源。

### 12.2 推荐更新表

每一行是一条 content_update，即一个需要人工判断是否提交供应商的业务更新。

| 字段 | 说明 |
| --- | --- |
| content_update_id | 内容更新主键 |
| canonical_item_id | 内容主键 |
| title | 标题 |
| original_title | 原始标题 |
| content_type | tv、movie |
| content_granularity | movie、series、season、episode |
| update_type | 新电影上线、新剧开播、新增单集、新季发布 |
| platform_sources | 采集到该内容的平台集合，例如 Netflix、Prime Video |
| regions | 采集到该内容的地区集合，例如 Global、US |
| release_dates | 不同平台或来源对应的上线日期 |
| language | 语言 |
| country | 制片国家/地区 |
| season_number | 季编号 |
| episode_number | 集编号 |
| imdb_id | IMDb ID |
| tmdb_id | TMDb ID |
| trakt_id | Trakt ID |
| external_links | 外部链接 |
| hot_score | 0-100 分 |
| priority | P0、P1、P2、P3 |
| heat_signals | 热度依据 |
| source_records | 原始来源记录引用 |
| audience_relevance | 非洲英文用户相关性：高、中、低 |
| ai_reason | AI 推荐理由 |
| discovery_run_type | bootstrap、daily、backfill |
| baseline_match_status | 已上线、疑似已上线、线上缺失、需人工确认 |
| review_status | 待审核、已采纳、已忽略、需补充确认 |
| batch_id | 关联批次 ID，可为空 |
| created_at | 记录创建时间 |
| updated_at | 记录更新时间 |

### 12.3 批次表

每一行是一次手动创建的供应商提交批次。

| 字段 | 说明 |
| --- | --- |
| batch_id | 批次 ID |
| batch_name | 批次名称 |
| date_range | 批次覆盖日期范围 |
| supplier_name | 供应商名称，MVP 默认一个供应商 |
| batch_status | 草稿、待提交、已提交、已完成 |
| created_by | 创建人 |
| created_at | 创建时间 |
| note | 备注 |

### 12.4 供应商流转表

每一行是一条进入供应商流程的内容。

| 字段 | 说明 |
| --- | --- |
| flow_id | 流转记录 ID |
| content_update_id | 内容更新 ID |
| batch_id | 批次 ID |
| title | 标题 |
| supplier_name | 供应商名称 |
| fulfillment_status | 履约状态 |
| submitted_at | 提交供应商时间 |
| downloaded_at | 下载完成时间 |
| ingested_at | 入库时间 |
| published_at | 上架时间 |
| no_resource_reason | 暂无资源原因 |
| operator_note | 人工处理备注 |
| last_status_changed_at | 状态最后更新时间 |

### 12.5 审核状态

`review_status` 可选值：

- 待审核
- 已采纳
- 已忽略
- 需补充确认

只有 `已采纳` 的推荐记录可以进入供应商批次。

### 12.6 履约状态

`fulfillment_status` 可选值：

- 未提交
- 已提交供应商
- 已下载
- 已入库
- 已上架
- 暂无资源

## 13. 飞书文档报告

系统需要生成两类飞书文档：

1. 每日日报。
2. 多日汇总报告。

报告必须包含：

- 统计摘要。
- P0/P1 推荐清单。
- 新剧、新季、新增单集、新电影分类汇总。
- AI 推荐理由。
- 热度依据。
- 提交建议。
- 待人工确认项。
- 已采纳、已忽略、暂无资源等状态概览。

多日汇总必须支持按日期范围生成，并可用于整理后提交供应商。

## 14. 原子需求

### R1. 数据源与运行配置

输入：

- 平台范围。
- 内容类型。
- 地区范围。
- 采集频率。
- 运行模式：bootstrap、daily、backfill。
- 冷启动时间窗口。
- 候选数量上限。
- API Key / Token。
- 热度来源开关。
- 飞书 App ID、App Secret、线上内容基线表 ID、推荐结果表 ID、文档目录 ID。

输出：

- 可保存、可读取的运行配置。

验收标准：

1. 支持配置 Netflix、Prime Video、Disney+、Apple TV+、HBO/Max、Hulu。
2. 支持配置电视剧、电影。
3. 支持配置 Global、US。
4. 支持每日定时运行。
5. 支持手动立即运行。
6. 支持指定日期范围补采。
7. 支持配置 bootstrap、daily、backfill 三种运行模式。
8. 支持配置线上内容基线表 ID。
9. 支持配置冷启动时间窗口，默认 180 天。
10. 支持配置候选数量上限和最低 hot_score 阈值。
11. MVP 可使用 `.env` 和 `config.yaml` 管理配置。
12. 配置不等同于虚拟环境配置，虚拟环境只用于依赖隔离。

### R2. 影视更新采集

输入：

- 日期范围。
- 运行模式。
- 平台范围。
- 内容类型。
- 地区范围。
- 线上内容基线。

输出：

- 候选内容更新记录列表。
- 被过滤记录统计。
- 采集错误日志。

验收标准：

1. 能采集新电影上线。
2. 能采集新剧开播。
3. 能采集新季发布。
4. 能采集连载剧新增单集。
5. 只使用合规数据源。
6. 不绕过登录、验证码、付费墙或反爬限制。
7. 数据源失败时记录错误，不影响其他数据源继续运行。
8. bootstrap 模式默认覆盖最近 180 天，并支持配置。
9. bootstrap 模式不做全量影视库抓取，只采集高信号入口和高价值候选。
10. daily 模式默认覆盖最近 1-7 天和近期即将上线内容。
11. 支持按 hot_score、内容类型、更新时间窗口和候选数量上限过滤输出。
12. 每次运行应记录采集总量、过滤数量、写入候选数量。

### R3. 影视实体标准化

输入：

- 各数据源返回的原始影视数据。

输出：

- 原始记录。
- 标准化候选实体。
- 内容主键。
- 映射置信度。

验收标准：

1. 能区分 movie、series、season、episode。
2. 电视剧优先识别到 episode 粒度。
3. 缺少稳定 episode ID 时可使用 source、series_id、season_number、episode_number 生成兜底主键。
4. 每条标准化记录保留 raw_source_record。
5. 低置信度映射不得自动合并。

### R4. 内容更新去重

输入：

- 候选内容更新记录。

输出：

- 去重后的 content_update。

验收标准：

1. 同一内容、同一更新类型只生成一条推荐记录。
2. 同一内容在不同平台上线时，不生成多条推荐，而是合并到 `platform_sources`。
3. 同一内容在 Global 和 US 来源中同时出现时，不生成多条推荐，而是合并到 `regions`。
4. 同一内容不同平台上线日期不一致时，不生成多条推荐，而是合并到 `release_dates`。
5. 同一季的不同 episode 不得错误合并。
6. 不同更新类型不得错误合并。

### R5. 热度与优先级计算

输入：

- TMDb 热度信号。
- Trakt 热度信号。
- Netflix Top 10。
- IMDb 评分、投票数或授权可用数据。
- 内容类型。
- 更新类型。
- 平台来源集合。
- 语言。
- 上线日期集合。

输出：

- hot_score。
- priority。
- heat_signals。
- ai_reason。

验收标准：

1. hot_score 范围为 0-100。
2. priority 映射为 P0、P1、P2、P3。
3. 计算依据可解释。
4. 权重可配置。
5. 电视剧权重高于电影。
6. 新季、新剧开播、新增单集权重高于普通电影上线。
7. Netflix、Prime Video 等重点平台作为来源或热度证据时具有更高平台权重，但不因此拆分多条推荐记录。

### R6. 业务状态去重

输入：

- 历史推荐记录。
- 线上内容基线表。
- 批次记录。
- 供应商流转记录。
- 当前候选内容更新记录。

输出：

- 过滤后的待处理推荐候选。

验收标准：

1. 已上架内容不再重复推荐。
2. 暂无资源内容默认不再重复推荐，除非人工改回待处理。
3. 已提交供应商、已下载、已入库内容不再进入待提交推荐。
4. 新 episode 首次采集到时，即使同一季其他集已处理，也应进入候选。
5. 新 season 发布时，即使上一季已处理，也应进入候选。
6. 冷启动时必须先读取线上内容基线表，识别已有 movie、season、episode。
7. 线上内容基线表中已存在的 movie、season、episode 默认视为已上架。
8. 线上只有旧季或旧集时，半年内新增 season 或 episode 应进入候选。
9. 线上内容基线表字段不完整时，低置信度匹配不得直接过滤，应标记为需人工确认。
10. R6 不替代 R4。R4 是内容更新去重，R6 是业务流程去重。

### R7. 飞书多维表格写入

输入：

- 线上内容基线记录。
- 推荐更新记录。
- 批次记录。
- 供应商流转记录。

输出：

- 飞书线上内容基线读取结果。
- 飞书多维表格三张业务表数据。

验收标准：

1. 能读取用户已有的线上内容基线表。
2. 能写入推荐更新表。
3. 能写入批次表。
4. 能写入供应商流转表。
5. 写入失败时有错误记录。
6. 重复写入时不会破坏已有人工状态。
7. 重复运行 bootstrap 或 backfill 时不会重复写入同一 content_update。

### R8. 飞书日报和汇总报告生成

输入：

- 单日或多日日期范围。
- 推荐更新表。
- 批次表。
- 供应商流转表。

输出：

- 飞书文档日报。
- 飞书文档多日汇总报告。

验收标准：

1. 每日可自动生成日报。
2. 可手动指定日期范围生成多日汇总。
3. 报告包含 AI 推荐理由。
4. 报告包含热度依据。
5. 报告包含提交建议。
6. 报告包含优先级和审核状态摘要。
7. bootstrap 报告必须包含半年追赶更新摘要。
8. bootstrap 报告必须区分线上缺失、疑似已上线、需人工确认的候选。

### R9. 人工审核与批次管理

输入：

- 待审核推荐记录。
- 人工审核结果。
- 人工创建的批次。

输出：

- 审核状态。
- 批次关联关系。

验收标准：

1. 人工审核在飞书多维表格中完成。
2. 批次创建在飞书多维表格中完成。
3. 只有已采纳记录可以进入供应商批次。
4. 每条批次内容必须能追溯到原 content_update。
5. 系统后续推荐时必须读取飞书中的审核和批次状态。

### R10. 供应商提交与上架状态追踪

输入：

- 已采纳内容。
- 批次。
- 人工维护的履约状态。

输出：

- fulfillment_status。
- 状态更新时间。
- 操作备注。

验收标准：

1. 每条已采纳内容必须能关联一个批次。
2. 每条批次内容必须有 fulfillment_status。
3. fulfillment_status 只能为：未提交、已提交供应商、已下载、已入库、已上架、暂无资源。
4. 已上架内容不再重复推荐。
5. 暂无资源内容默认不再重复推荐，除非人工改回待处理。
6. 状态变更必须记录最后更新时间。

### R11. 全网热门好评内容发现（V1 核心新增需求）

输入：

- 当前日期。
- 平台范围（Netflix、Prime Video、Disney+、Apple TV+、HBO Max、Hulu）。
- 地区范围（Global、US）。
- 评分阈值（默认 imdb_rating >= 7.0 或 tmdb_rating >= 7.0）。
- 投票数阈值（默认 vote_count >= 100）。
- TopN 配置（默认 50）。
- 数据源：FlixPatrol、TMDb、Trakt、OMDb。

输出：

- 全网热门好评候选列表（已排序）。
- 每条候选的多源热度依据。
- 每条候选与飞书基线的匹配状态（is_in_baseline）。
- 综合评分 hot_score 和 priority。
- discovery_source 标记（new_release、global_hot、both）。

验收标准：

1. 每日运行一次能输出"全网值得更新"内容列表。
2. 至少使用 4 个数据源（FlixPatrol + TMDb + Trakt + OMDb）。
3. FlixPatrol 数据来自合规公开页面，加缓存避免高频访问。
4. 候选合并按 external_id 去重（tmdb_id 优先，imdb_id 次之）。
5. 每条候选必须能追溯到至少一个数据源的具体证据。
6. 输出分为三类：新增推荐、已有可补充、待人工确认。
7. 不依赖飞书基线完整性也能产出推荐。
8. 飞书基线仅用于标记（is_in_baseline），不参与过滤。
9. hot_score 综合评分必须包含 FlixPatrol 平台热度因素（权重 30%）。
10. 重复运行同一日不重复写入相同 content_update_id。
11. 单一数据源失败不影响其他数据源继续运行。

### R12. FlixPatrol 数据接入（V1 关键依赖）

输入：

- FlixPatrol 公开页面 URL（按平台和地区）。
- 礼貌访问频率配置（默认每页 >= 2 秒间隔）。
- 缓存有效期（默认 24 小时）。

输出：

- 各平台 Top 10 内容榜单（按地区）。
- 每条记录的标题、外部 ID（如有）、上榜日期、排名。
- 缓存到本地 SQLite 的 `flixpatrol_charts` 表。

验收标准：

1. 能稳定获取 Netflix Global Top 10、US Top 10。
2. 能稳定获取 Prime Video、Disney+、Apple TV+、HBO Max、Hulu 的 Top 列表（如可用）。
3. 数据缓存避免高频抓取（默认 24 小时缓存）。
4. 单次失败有重试机制（默认 3 次重试，指数退避）。
5. 失败时记录详细日志，不影响其他数据源。
6. 能与 TMDb/Trakt 候选通过标题+年份做匹配。
7. 不存储 FlixPatrol 原始 HTML，只存解析后的结构化数据。
8. 接入前完成可访问性、解析稳定性、合规性的验证（详见 phase0_supplement.md）。

## 15. 非功能需求

### 15.1 可验证性

各运行模式必须可立即验证。系统必须提供：

1. `run once`：立即运行一次。
2. `bootstrap`：读取线上内容基线，并追赶最近 180 天候选。
3. `backfill`：按日期范围补采。
4. `dry run`：不写入飞书，仅输出采集、过滤和评分结果。

### 15.2 可追溯性

每条推荐必须能追溯：

- 原始数据源。
- 原始记录。
- 标准化过程。
- 热度依据。
- AI 推荐理由。
- 运行模式。
- 线上内容基线匹配状态。
- 审核状态。
- 批次。
- 履约状态。

### 15.3 稳定性

1. 单一数据源失败不应导致整个任务失败。
2. 写入飞书失败应可重试。
3. 重复运行同一日期范围不应重复创建业务记录。

### 15.4 安全性

1. API Key、Token、飞书密钥不得提交到 GitHub。
2. 配置文件应区分示例配置和本地私密配置。
3. 日志不得输出完整密钥。

## 16. V2 扩展方向（产品迭代时启动）

详细的 V2 路线图见 [product_roadmap.md](product_roadmap.md)，以下为概要：

### 16.1 高优先级 V2 方向

| 方向 | 价值 | 备注 |
|------|------|------|
| **LLM 用户契合度判断** | ⭐⭐⭐ | 解决"非洲英文用户喜欢什么"的判断 |
| **多 Agent 推理框架** | ⭐⭐ | 把推荐变成"评审委员会"决策 |
| **Rotten Tomatoes + Metacritic** | ⭐⭐ | 多源评分交叉验证 |

### 16.2 中等优先级 V2 方向

- Watchmode API（episode级流媒体追踪）
- IMDb Pro Datasets（商业级popularity meter）
- 时序预测（即将爆款内容发现）
- Reddit / Twitter 社交信号
- YouTube 预告片数据（预热信号）

### 16.3 长期方向

- 增加非洲重点国家/地区可看性追踪
- 增加供应商接口自动提交
- 增加后台页面
- 增加 AI 对历史上架效果的反馈学习
- 增加多供应商管理

**V2 启动条件：**
- V1 已稳定运行至少 1-2 个月
- 运营反馈了明确的需求短板
- 有具体业务证据支撑 V2 投入

## 17. 参考资料

- **FlixPatrol（V1 关键数据源）**：https://flixpatrol.com/
- IMDb 数据使用说明：https://help.imdb.com/article/imdb/general-information/can-i-use-imdb-data-in-my-software/G5JTRESSHJBBHTGX
- IMDb 非商业数据集：https://developer.imdb.com/non-commercial-datasets/
- TMDb API 文档：https://developer.themoviedb.org/docs
- Trakt API 文档：https://trakt.docs.apiary.io/
- Netflix Top 10：https://www.netflix.com/tudum/top10/
- 飞书开放平台：https://open.feishu.cn/document/
