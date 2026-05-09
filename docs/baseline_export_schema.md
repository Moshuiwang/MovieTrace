# MovieTrace 节目库导出 Schema

状态：v0.1 草案  
日期：2026-05-09  
适用阶段：Phase 0 基线验证、节目库导出、实体匹配准备  
对应飞书子表：`MovieTrace节目库导出Schema`

## 1. 设计目标

这份 schema 用于指导当前节目库导出，让 MovieTrace 后续能稳定读取现有库内容，并用于冷启动、实体匹配和业务去重。

当前 `节目` 表不是为程序读取设计的，字段简略但业务价值高。因此本 schema 不要求一次性补齐所有字段，而是分清：

1. 必须导出的本地字段。
2. 强烈建议补齐的识别字段。
3. 后续可由程序从 TMDb / Trakt 补齐的字段。
4. 需要原样保留的备注和特殊情况。

## 2. 总体原则

- 不要为了凑字段手工编造不确定信息。
- 不确定的内容类型、季号、集号、外部 ID 可以留空。
- `source_note` 必须尽量原样保留，因为备注中可能有特殊业务情况。
- 外部 ID 字段可以先空着，后续由 `match-baseline` 补齐。
- 缺少外部 ID 和季集信息时，程序不得自动高置信度过滤候选。
- 一行最好表达一个可判断的业务对象：电影、剧集、季或集。

## 3. 字段清单 v0.1

| 排序 | 字段 key | 中文名 | 类型 | 必填级别 | 来源 | 说明 | 示例 | 空值规则 |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | `local_content_id` | 本地内容ID | text | 建议必填 | 本地库 | 当前节目库中的稳定唯一标识。没有时可先留空，但后续建议补齐。 | `show_000123` | 没有稳定 ID 时留空，不要用行号代替长期 ID。 |
| 20 | `title` | 节目名 | text | 必填 | 本地库 | 当前库中用于展示和人工识别的节目名。 | `Silo S01` | 不能为空。 |
| 30 | `original_title` | 原始标题 | text | 可选 | 本地库/外部源 | 影视作品原始标题，用于和 TMDb / Trakt 匹配。 | `Silo` | 没有时留空。 |
| 40 | `content_type` | 内容类型 | enum | 强烈建议必填 | 人工导出/程序补齐 | 内容大类。用于防止同名电影和剧集误匹配。 | `series` | 允许值：`movie`、`series`、`season`、`episode`；不确定时留空并进入人工确认。 |
| 50 | `content_granularity` | 内容粒度 | enum | 强烈建议必填 | 人工导出/程序补齐 | 当前行表达的是电影、整部剧、某一季还是某一集。 | `season` | 允许值：`movie`、`series`、`season`、`episode`。 |
| 60 | `season_number` | 季号 | integer | 条件必填 | 本地库/程序解析 | 当内容粒度为 season 或 episode 时填写。 | `1` | 电影和整部剧为空；未知季号留空。 |
| 70 | `episode_number` | 集号 | integer | 条件必填 | 本地库/程序解析 | 当内容粒度为 episode 时填写。 | `3` | `movie`、`series`、`season` 为空；未知集号留空。 |
| 80 | `episode_title` | 单集标题 | text | 可选 | 外部源/人工补充 | 单集标题，用于 episode 级人工核对。 | `Machines` | 没有时留空。 |
| 90 | `year` | 年份 | integer | 建议必填 | 本地库/外部源 | 电影上映年或剧集首播年，用于标题匹配消歧。 | `2023` | 未知时留空。 |
| 100 | `release_date` | 上映/首播日期 | date | 可选 | 本地库/外部源 | 电影上映日期、剧集首播日期或该季/集发布日期。 | `2023-05-05` | 未知时留空，格式建议 `YYYY-MM-DD`。 |
| 110 | `language` | 主要语言 | text | 建议必填 | 本地库/外部源 | 内容主要语言，用于英文内容优先级判断。 | `en` | 建议用 ISO 639-1，例如 `en`、`ko`、`es`；未知时留空。 |
| 120 | `country` | 国家/地区 | text | 可选 | 本地库/外部源 | 制片国家或地区。 | `US` | 多个值可用逗号分隔或 JSON 数组。 |
| 130 | `genres` | 类型 | text/list | 可选 | 外部源/人工补充 | 影视类型标签，用于运营判断和推荐理由。 | `Drama,Sci-Fi` | 多个值可用逗号分隔或 JSON 数组。 |
| 140 | `aka_titles` | 别名 | text/list | 可选 | 本地库/外部源 | 其他标题、译名或历史命名，用于匹配。 | `Silo Season 1` | 多个值可用逗号分隔或 JSON 数组。 |
| 150 | `tmdb_id` | TMDb ID | text | 强烈建议补齐 | 外部源/程序匹配 | TMDb 内容 ID。电影、剧集、季、集可能对应不同接口粒度。 | `125988` | 未知时留空；程序匹配后补齐。 |
| 160 | `imdb_id` | IMDb ID | text | 建议补齐 | 外部源/程序匹配 | IMDb 标识，用于跨源映射。 | `tt14688458` | 未知时留空；不要抓 IMDb 页面补齐。 |
| 170 | `trakt_id` | Trakt ID | text | 建议补齐 | 外部源/程序匹配 | Trakt 标识，用于剧集更新和热度映射。 | `12345` | 未知时留空。 |
| 180 | `parent_series_tmdb_id` | 父剧 TMDb ID | text | 条件建议 | 外部源/程序匹配 | season / episode 行所属剧集的 TMDb ID。 | `125988` | `movie` 和 `series` 行可为空。 |
| 190 | `parent_series_imdb_id` | 父剧 IMDb ID | text | 条件建议 | 外部源/程序匹配 | season / episode 行所属剧集的 IMDb ID。 | `tt14688458` | `movie` 和 `series` 行可为空。 |
| 200 | `parent_series_trakt_id` | 父剧 Trakt ID | text | 条件建议 | 外部源/程序匹配 | season / episode 行所属剧集的 Trakt ID。 | `12345` | `movie` 和 `series` 行可为空。 |
| 210 | `online_status` | 当前库状态 | enum/text | 建议必填 | 本地库 | 当前库中的业务状态。 | `已上架` | 建议值：`已下载`、`已上传FTP`、`已转码`、`已上架`、`暂无资源`、`未知`。 |
| 220 | `downloaded_at` | 下载时间 | date | 可选 | 本地库 | 内容下载完成时间。 | `2024-03-01` | 未知时留空。 |
| 230 | `uploaded_ftp_at` | 上传FTP时间 | date | 可选 | 本地库 | 上传 FTP 完成时间。 | `2024-03-02` | 未知时留空。 |
| 240 | `transcoded_at` | 转码时间 | date | 可选 | 本地库 | 转码完成时间。 | `2024-03-03` | 未知时留空。 |
| 250 | `published_at` | 上架时间 | date | 可选 | 本地库 | 内容在当前库中上架的时间。 | `2024-03-04` | 未知时留空。 |
| 260 | `provider_or_platform` | 来源平台/供应商 | text/list | 可选 | 本地库/人工补充 | 已知来源平台、供应商或业务来源。 | `Netflix` | 多个值可用逗号分隔或 JSON 数组。 |
| 270 | `source_note` | 原始备注 | text | 建议保留 | 本地库 | 当前节目表中的备注原文，保留特殊情况。 | `缺第 3 集；片源待确认` | 原样导出，不要清洗覆盖。 |
| 280 | `match_status` | 匹配状态 | enum | 程序生成 | 程序生成 | 后续实体匹配阶段写入。 | `需人工确认` | 允许值：`未匹配`、`已匹配`、`需人工确认`、`匹配失败`。 |
| 290 | `match_confidence` | 匹配置信度 | enum | 程序生成 | 程序生成 | 外部实体匹配置信度。 | `high` | 允许值：`high`、`medium`、`low`。 |
| 300 | `match_reason` | 匹配依据 | text | 程序生成 | 程序生成 | 记录为什么匹配到某个外部实体。 | `title + year + content_type matched` | 由程序生成，人工可复核。 |

## 4. 最小可导出字段

如果完整节目库暂时无法一次性导出全部字段，建议至少提供：

```text
title
content_type
content_granularity
season_number
episode_number
year
online_status
source_note
```

如果 `content_type` 和 `content_granularity` 暂时无法提供，也可以先导出 `title` 和 `source_note`，但这只能支持标题级弱基线，不能支持强自动去重。

## 5. 推荐导出格式

推荐 CSV 或 XLSX，字段名使用 `字段 key`，例如：

```text
title,content_type,content_granularity,season_number,episode_number,year,online_status,source_note
```

日期字段建议统一为：

```text
YYYY-MM-DD
```

多值字段建议二选一：

```text
Drama,Sci-Fi
["Drama","Sci-Fi"]
```

同一份导出中应保持一种格式，不要混用。

## 6. 与当前 `节目` 表的映射

| 当前字段 | 建议映射字段 | 说明 |
| --- | --- | --- |
| `节目名` | `title` | 当前最有价值字段，可作为标题级弱基线。 |
| `上传日期（目录名）` | `uploaded_ftp_at` 或 `source_note` | 当前值像毫秒时间戳，后续需确认真实含义。 |
| `已下载` | `online_status` / `downloaded_at` | 复选框只能表达状态，不能表达时间。 |
| `已上传FTP` | `online_status` / `uploaded_ftp_at` | 复选框只能表达状态，不能表达时间。 |
| `已转码` | `online_status` / `transcoded_at` | 当前读取到全为空。 |
| `已上架` | `online_status` / `published_at` | 当前读取到全为空。 |
| `备注` | `source_note` | 必须原样保留。 |

## 7. 后续校准计划

这份 schema 是 v0.1，不是最终数据库结构。后续需要用 TMDb / Trakt 样本校准：

1. 检查 TMDb / Trakt 对 movie、series、season、episode 的 ID 和父子关系表达。
2. 校准 `content_type` 与 `content_granularity` 是否需要拆分或合并。
3. 校准日期字段是保留单一日期，还是需要区分 movie release、series premiere、season air date、episode air date。
4. 校准外部 ID 字段是否需要增加 provider-specific ID。
5. 根据实体匹配报告调整必填字段和空值规则。

