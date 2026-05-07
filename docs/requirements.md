# MovieTrace 项目需求文档

状态：需求确认版  
日期：2026-05-07  
仓库：https://github.com/Moshuiwang/MovieTrace

## 1. 项目背景

MovieTrace 面向视频网站运营场景，用于自动发现英文影视内容的上线、开播、剧集更新和新季发布信息，并结合外部热度、平台权重、内容类型和业务处理状态，生成可审核、可分批、可追踪的更新建议。

项目目标不是直接完成视频资源获取，而是为“应该更新哪些影视内容”提供信息源、排序依据和后续提交供应商的流程记录。

## 2. 业务目标

1. 每日从合规数据源获取影视更新信息。
2. 重点追踪电视剧，其次追踪电影。
3. 重点关注英文内容，允许非英文但在英语用户或目标市场中热度高的内容进入候选。
4. 重点关注 Netflix、Prime Video、Disney+、Apple TV+、HBO/Max、Hulu 的全球或美国上线信息。
5. 为面向英文用户、尤其是非洲用户的视频网站运营提供更新建议。
6. 将推荐结果固化到飞书多维表格，并生成飞书文档日报或多日汇总报告。
7. 支持人工审核、手动分批、提交供应商和上架状态追踪。

## 3. MVP 范围

### 3.1 包含范围

- 新电影上线。
- 新剧上线或开播。
- 连载剧新增单集。
- 新季发布。
- 每日自动运行。
- 手动立即运行。
- 指定日期范围补采。
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

### 5.1 MVP 数据源

| 数据源 | 用途 | 说明 |
| --- | --- | --- |
| TMDb API | 影视元数据、外部 ID、趋势、流媒体 provider 信息 | 优先作为标准化和外部 ID 映射数据源之一 |
| Trakt API | 热门、趋势、剧集日历、观看热度 | 用于补充电视剧更新和热度信号 |
| Netflix Top 10 | Netflix 官方热榜 | 用于 Netflix 内容热度判断 |
| IMDb 数据 | 外部 ID、评分、投票数或授权数据 | 不默认抓取 IMDb 页面 |

### 5.2 平台范围

MVP 覆盖以下流媒体平台：

- Netflix
- Prime Video
- Disney+
- Apple TV+
- HBO/Max
- Hulu

### 5.3 地区范围

MVP 只关注：

- Global
- US

不做非洲各国家/地区的逐区上线追踪。非洲用户相关性仅作为推荐排序因素，主要基于语言、全球热度、美国/国际传播热度和内容类型判断。

## 6. 核心业务流程

```text
每日或手动触发采集
-> 获取候选更新记录
-> 保留原始记录
-> 标准化影视实体
-> 生成内容主键和内容更新主键
-> 内容更新去重
-> 计算 hot_score 和 priority
-> 结合业务状态做推荐过滤
-> 写入飞书多维表格推荐更新表
-> 生成飞书文档日报或多日汇总
-> 人工审核
-> 已采纳内容加入手动批次
-> 提交供应商
-> 更新履约状态
```

## 7. 主键设计

### 7.1 内容主键

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

### 7.2 内容更新主键

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

## 8. 实体标准化策略

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

## 9. 热度与优先级

### 9.1 热度来源

MVP 使用以下热度信号：

| 来源 | 信号 |
| --- | --- |
| TMDb | trending、popular、vote_average、vote_count、watch provider |
| Trakt | trending、popular、watched、collected、calendar/new episode |
| Netflix Top 10 | 全球榜、国家榜，优先使用 Global 和 US |
| IMDb | 评分、投票数或授权可用热度数据 |

### 9.2 hot_score 初版规则

`hot_score` 使用 0-100 分，初版采用透明、可配置的规则，不使用不可解释的黑盒 AI 分数。

| 因素 | 分值 | 说明 |
| --- | ---: | --- |
| 外部热度 | 40 | 榜单、趋势、评分、投票数、观看热度 |
| 更新类型 | 20 | 新季、新剧开播、新增单集优先 |
| 内容类型 | 10 | 电视剧高于电影 |
| 平台来源权重 | 10 | Netflix、Prime Video 等重点平台作为来源或热度证据时更高 |
| 语言和目标用户相关性 | 10 | 英文内容优先，非英文热门内容可进入候选 |
| 新鲜度 | 10 | 最近上线或即将上线内容优先 |

计算公式：

```text
hot_score =
  external_heat_score
+ update_type_score
+ content_type_score
+ platform_source_score
+ audience_relevance_score
+ freshness_score
```

所有权重必须可在配置文件中调整。

### 9.3 priority 映射

| priority | hot_score | 含义 |
| --- | ---: | --- |
| P0 | >= 85 | 强烈建议优先提交 |
| P1 | 70-84 | 建议提交 |
| P2 | 50-69 | 可选提交 |
| P3 | < 50 | 低优先级或仅记录 |

AI 推荐理由必须引用可解释依据，例如：

- 进入 Netflix Global Top 10。
- TMDb trending 排名靠前。
- Trakt 观看热度上升。
- 新季发布且为英文剧集。
- 电视剧优先级高于普通电影上线。

## 10. 去重规则

### 10.1 R4 内容更新去重

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

### 10.2 R6 业务状态去重

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

## 11. 飞书多维表格设计

飞书多维表格作为轻量业务后台，负责结果沉淀、人工审核、批次管理和状态流转。

### 11.1 推荐更新表

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
| review_status | 待审核、已采纳、已忽略、需补充确认 |
| batch_id | 关联批次 ID，可为空 |
| created_at | 记录创建时间 |
| updated_at | 记录更新时间 |

### 11.2 批次表

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

### 11.3 供应商流转表

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

### 11.4 审核状态

`review_status` 可选值：

- 待审核
- 已采纳
- 已忽略
- 需补充确认

只有 `已采纳` 的推荐记录可以进入供应商批次。

### 11.5 履约状态

`fulfillment_status` 可选值：

- 未提交
- 已提交供应商
- 已下载
- 已入库
- 已上架
- 暂无资源

## 12. 飞书文档报告

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

## 13. 原子需求

### R1. 数据源与运行配置

输入：

- 平台范围。
- 内容类型。
- 地区范围。
- 采集频率。
- API Key / Token。
- 热度来源开关。
- 飞书 App ID、App Secret、表格 ID、文档目录 ID。

输出：

- 可保存、可读取的运行配置。

验收标准：

1. 支持配置 Netflix、Prime Video、Disney+、Apple TV+、HBO/Max、Hulu。
2. 支持配置电视剧、电影。
3. 支持配置 Global、US。
4. 支持每日定时运行。
5. 支持手动立即运行。
6. 支持指定日期范围补采。
7. MVP 可使用 `.env` 和 `config.yaml` 管理配置。
8. 配置不等同于虚拟环境配置，虚拟环境只用于依赖隔离。

### R2. 影视更新采集

输入：

- 日期范围。
- 平台范围。
- 内容类型。
- 地区范围。

输出：

- 候选内容更新记录列表。
- 采集错误日志。

验收标准：

1. 能采集新电影上线。
2. 能采集新剧开播。
3. 能采集新季发布。
4. 能采集连载剧新增单集。
5. 只使用合规数据源。
6. 不绕过登录、验证码、付费墙或反爬限制。
7. 数据源失败时记录错误，不影响其他数据源继续运行。

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
6. R6 不替代 R4。R4 是内容更新去重，R6 是业务流程去重。

### R7. 飞书多维表格写入

输入：

- 推荐更新记录。
- 批次记录。
- 供应商流转记录。

输出：

- 飞书多维表格三张表数据。

验收标准：

1. 能写入推荐更新表。
2. 能写入批次表。
3. 能写入供应商流转表。
4. 写入失败时有错误记录。
5. 重复写入时不会破坏已有人工状态。

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

## 14. 非功能需求

### 14.1 可验证性

每日任务必须可立即验证。系统必须提供：

1. `run once`：立即运行一次。
2. `backfill`：按日期范围补采。
3. `dry run`：不写入飞书，仅输出采集和评分结果。

### 14.2 可追溯性

每条推荐必须能追溯：

- 原始数据源。
- 原始记录。
- 标准化过程。
- 热度依据。
- AI 推荐理由。
- 审核状态。
- 批次。
- 履约状态。

### 14.3 稳定性

1. 单一数据源失败不应导致整个任务失败。
2. 写入飞书失败应可重试。
3. 重复运行同一日期范围不应重复创建业务记录。

### 14.4 安全性

1. API Key、Token、飞书密钥不得提交到 GitHub。
2. 配置文件应区分示例配置和本地私密配置。
3. 日志不得输出完整密钥。

## 15. 后续可扩展方向

- 增加 Google Trends 或社交媒体趋势。
- 增加非洲重点国家/地区可看性追踪。
- 增加供应商接口自动提交。
- 增加后台页面。
- 增加 AI 对历史上架效果的反馈学习。
- 增加多供应商管理。

## 16. 参考资料

- IMDb 数据使用说明：https://help.imdb.com/article/imdb/general-information/can-i-use-imdb-data-in-my-software/G5JTRESSHJBBHTGX
- IMDb 非商业数据集：https://developer.imdb.com/non-commercial-datasets/
- TMDb API 文档：https://developer.themoviedb.org/docs
- Trakt API 文档：https://trakt.docs.apiary.io/
- Netflix Top 10：https://www.netflix.com/tudum/top10/
- 飞书开放平台：https://open.feishu.cn/document/
