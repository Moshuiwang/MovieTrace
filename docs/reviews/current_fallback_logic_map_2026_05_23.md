# Current Fallback Logic Map

> 日期：2026-05-23
> 范围：当前 `daily-discover` 主链路里，FlixPatrol / TMDb / Trakt 的 source 日期回退、merge fallback、rating fallback、TMDb detail skip 逻辑。本文描述“现在代码长什么样”，不是目标重构方案。

## 一句话产品语义

每日发现允许用历史 source snapshot 保持 pipeline 可运行；但“纯历史快照候选”不应被当成今日新发现写入 `content_updates`。如果一个候选至少有一个今日 fresh source 命中，则可以把其他历史 source 当补充上下文使用。

## 总览图

```mermaid
flowchart TD
    A["CLI daily-discover<br/>target_date"] --> B1["Step 1 拉 FlixPatrol<br/>_ensure_fp_data"]
    A --> B2["Step 2 拉 TMDb trending<br/>fetch_and_store_tmdb_trending"]
    A --> B3["Step 3 拉 Trakt trending<br/>fetch_and_store_trakt_trending"]

    B1 --> C["run_discovery"]
    B2 --> C
    B3 --> C

    C --> D["统计 target_date 当天三源表行数<br/>flixpatrol_top10 / tmdb_trending / trakt_trending"]
    D --> E["_resolve_source_dates_with_fallback<br/>为每个 source 决定 effective_date"]
    E --> F["source_dates<br/>{source: effective_date or None}"]
    E --> G["source_status<br/>fresh / fallback / failed_no_fallback"]

    F --> H["merge_three_sources<br/>按各 source effective_date 读表"]
    H --> I["MergedCandidate<br/>source_flags = fp/tmdb/trakt"]

    I --> J["enrichment<br/>IMDb backfill / OMDb / TMDb detail"]
    J --> K["score + priority"]
    K --> L["has_fresh_signal = source_flags ∩ fresh_sources"]
    L --> M["threshold filter<br/>hot_score >= P2 或 Soap"]
    M --> N{"has_fresh_signal<br/>或 Soap?"}
    N -- "yes" --> O["row_duration_hours<br/>auto-register canonical<br/>write content_updates"]
    N -- "no" --> P["suppressed_fallback_only<br/>不写 content_updates"]
```

注意：当前实现里 `enrichment` 在 `has_fresh_signal` 过滤之前执行。因此 pure fallback 候选最终不会写入，但在被压制前已经可能参与 IMDb / OMDb / TMDb detail enrichment。

## Source 日期回退

当前函数：`src/movietrace/pipeline/discovery.py::_resolve_source_dates_with_fallback`

对 `flixpatrol`、`tmdb`、`trakt` 每个 source 独立跑同一套判断。

```mermaid
flowchart TD
    A["输入：source 今日 rows + fetch error"] --> B{"有 error?"}
    B -- "yes" --> C{"fallback enabled<br/>且该 source 允许 fallback?"}
    B -- "no" --> D{"rows == 0?"}

    D -- "no" --> E["status=fresh<br/>effective_date=target_date<br/>record rows_fetched/inserted=rows"]

    D -- "yes" --> C

    C -- "no" --> F["status=failed_no_fallback<br/>effective_date=None"]
    C -- "yes" --> G["_find_fallback_snapshot"]

    G --> H{"找到 target_date 之前<br/>max_staleness_days 内最近 snapshot?"}
    H -- "yes" --> I["status=fallback<br/>effective_date=fallback_snapshot<br/>rows_fetched=0 rows_inserted=0"]
    H -- "no" --> F
```

`_find_fallback_snapshot` 当前规则：

- 只找 `snapshot_date < target_date` 的历史数据。
- 只找 `snapshot_date >= target_date - max_staleness_days` 的数据。
- 取最近一天。
- source 到表的映射：
  - `flixpatrol` -> `flixpatrol_top10`
  - `tmdb` -> `tmdb_trending`
  - `trakt` -> `trakt_trending`

## Source 状态到产品含义

| status | effective_date | 产品含义 | 后续是否参与 merge |
|---|---|---|---|
| `fresh` | `target_date` | 今天这个 source 有可用数据 | 参与 |
| `fallback` | 历史 snapshot date | 今天不可用，用历史快照补上下文 | 参与 |
| `failed_no_fallback` | `None` | 今天不可用，也没有可用历史快照 | 不参与 |

`source_fallback_used` 当前只要任一 source 的 `effective_date != target_date` 且非空，就为 true。

## Merge fallback

当前函数：`src/movietrace/pipeline/multi_source_merge.py::merge_three_sources`

这里的 fallback 不是 source 日期回退，而是候选去重时的 ID fallback。

```mermaid
flowchart TD
    A["source_dates"] --> B["按 effective_date 读取三张 source 表<br/>None 则该 source 读空列表"]
    B --> C["_reconcile_fp_media_types<br/>优先 TMDb/Trakt/cache 修正 FP media_type"]
    C --> D["Pass 1: tmdb_id + media_type merge"]
    D --> E["Pass 2: 无 tmdb_id 时<br/>imdb_id + media_type merge"]
    E --> F["Pass 3: 无 tmdb_id/imdb_id 时<br/>title_norm + media_type merge"]
    F --> G["MergedCandidate<br/>source_flags 记录 fp/tmdb/trakt"]
```

当前 merge key 顺序：

| 顺序 | key | 语义 |
|---|---|---|
| 1 | `tmdb:{tmdb_id}:{media_type}` | 最可信 |
| 2 | `imdb:{imdb_id}:{media_type}` | ID fallback |
| 3 | `title:{normalized_title}:{media_type}` | title fallback |

当前 candidate 只记录 `source_flags`，不记录每个 source 的 effective_date。后续 `has_fresh_signal` 是用 `source_flags` 和 `fresh_sources` 交叉计算出来的。

## Fresh signal 与写入门禁

当前位置：`src/movietrace/pipeline/discovery.py::run_discovery`

```python
fresh_sources = {s for s, d in source_dates.items() if d == snapshot_date}
has_fresh_signal = bool(candidate.source_flags & fresh_sources)
```

写入前逻辑：

```mermaid
flowchart TD
    A["scored candidates"] --> B["Soap genre 自动降权<br/>is_soap=True priority=P3"]
    B --> C["threshold filter<br/>hot_score >= P2 或 is_soap"]
    C --> D{"has_fresh_signal<br/>或 is_soap?"}
    D -- "yes" --> E["passed<br/>后续可写 content_updates"]
    D -- "no" --> F["suppressed_fallback_only +1<br/>不写 content_updates"]
```

产品上可以这样理解：

| 候选来源组合 | has_fresh_signal | 当前结果 |
|---|---:|---|
| 只来自今日 FP | true | 可作为今日候选 |
| 今日 FP + 昨日 TMDb fallback | true | 可作为今日候选，TMDb 作为补充上下文 |
| 只来自昨日 TMDb fallback | false | 评分后被压制，不写今日事件 |
| 昨日 TMDb fallback + 昨日 Trakt fallback | false | 评分后被压制，不写今日事件 |
| source 全部 failed_no_fallback | false / 无候选 | 无该 source 输入 |

## Rating fallback

当前位置：`src/movietrace/pipeline/scoring.py`

这是评分 fallback，不是 source 日期 fallback。

```mermaid
flowchart TD
    A["评分输入"] --> B{"有 OMDb/IMDb rating?"}
    B -- "yes" --> C["使用 OMDb/IMDb rating score"]
    B -- "no" --> D{"有 TMDb vote_average<br/>和 vote_count?"}
    D -- "yes" --> E["使用 tmdb_fallback rating score"]
    D -- "no" --> F["rating score = 0"]
```

产品含义：没有 IMDb/OMDb 评分时，用 TMDb 评分兜底，避免评分维度完全为 0。它不影响 source 是否 fresh，也不决定能不能写今日事件。

## TMDb detail / canonical skip

当前位置：`src/movietrace/pipeline/omdb_enrichment.py::enrich_with_tmdb_details`

```mermaid
flowchart TD
    A["candidate"] --> B{"有 tmdb_id?"}
    B -- "no" --> Z["跳过"]
    B -- "yes" --> C["_load_canonical_enrichment<br/>读 canonical_items"]

    C --> D{"canonical 有记录?"}
    D -- "yes" --> E["_apply_canonical_enrichment<br/>预填 genres_json/title_zh/overview_zh/networks_json"]
    D -- "no" --> G

    E --> F{"canonical 有 genres_json<br/>且 _has_sufficient_tmdb_detail?"}
    F -- "yes" --> H["canonical_hits +1<br/>enriched +1<br/>跳过 TMDb detail API"]
    F -- "no" --> G{"_has_sufficient_tmdb_detail?"}

    G -- "yes" --> I["跳过 TMDb detail API<br/>不计 canonical_hits"]
    G -- "no" --> J["get_tmdb_detail_with_cache<br/>api_cache 命中或调用 TMDb API"]

    J --> K{"拿到 detail data?"}
    K -- "yes" --> L["_apply_tmdb_detail_data<br/>enriched +1<br/>抓 zh-CN detail 并更新 canonical_items"]
    K -- "no" --> Z
```

`_has_sufficient_tmdb_detail` 当前规则：

| media_type | 必要字段 |
|---|---|
| movie | `release_date` + `original_language` |
| tv | `release_date` + `original_language` + `last_air_date` |

注意：canonical enrichment 只预填中文、类型、平台等持久字段；只有候选已经满足 `_has_sufficient_tmdb_detail` 时，才允许因为 canonical 命中而跳过 detail API。

## 当前最容易误读的点

1. CLI 第 1-3 步说“拉取成功/失败”，但真正决定 source 使用哪天数据的是 `run_discovery` 里的 source fallback resolution。
2. `fallback` 有三种含义：source 日期回退、merge ID fallback、rating fallback。
3. pure fallback candidate 当前不会写 `content_updates`，但会先经过 enrichment 和 scoring。
4. `snapshot_date` 在 candidate / content_update 里是批次日，不等于每个 source 的真实 snapshot date。
5. `source_status` 里 fallback 的 `cached_count` 是 fallback snapshot 的行数；CLI Step 5 里展示的 `fp/tmdb/trakt rows` 仍主要来自 fetch result，和实际 rows used 不是完全同一个口径。

## 代码入口速查

| 逻辑 | 文件 / 函数 |
|---|---|
| CLI 三源抓取顺序 | `src/movietrace/cli.py::cmd_daily_discover` |
| FP 抓取和缓存复用 | `src/movietrace/pipeline/discovery.py::_ensure_fp_data` |
| source 日期回退 | `src/movietrace/pipeline/discovery.py::_resolve_source_dates_with_fallback` |
| 查历史 snapshot | `src/movietrace/pipeline/discovery.py::_find_fallback_snapshot` |
| 三源合并 | `src/movietrace/pipeline/multi_source_merge.py::merge_three_sources` |
| fresh signal / suppress pure fallback | `src/movietrace/pipeline/discovery.py::run_discovery` |
| rating fallback | `src/movietrace/pipeline/scoring.py` |
| TMDb detail skip | `src/movietrace/pipeline/omdb_enrichment.py::enrich_with_tmdb_details` |
