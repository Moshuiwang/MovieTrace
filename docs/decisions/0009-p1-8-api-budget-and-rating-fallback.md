# ADR-0009: P1.8 API 预算与评分兜底策略


**状态:** Accepted  
**日期:** 2026-05-13  
**决策者:** 用户 + Codex (GPT-5)  
**相关 Commit:** 未提交  
**影响:** ADR-0008（多源并集发现架构的运行成本与评分降级策略细化）

---

## 上下文

ADR-0008 确认 MovieTrace 使用 FlixPatrol + TMDb + Trakt 三源并集发现，并用 OMDb / TMDb 进行富化评分。2026-05-13 的端到端验证暴露出三个问题：

- FlixPatrol 只抓美国区 6 平台 Movie/TV Top10，无法覆盖 FROM 这类在全球榜有热度但不在美国平台榜中的内容。
- OMDb 免费 key 当天触发 `Request limit reached!`，真实 IMDb 评分不能作为当天评分链路的稳定前置条件。
- TMDb `external_ids` 尚未接入，候选缺 IMDb ID 时会跳过 OMDb enrichment，影响评分。

同时，FlixPatrol API 月度调用预算需要控制在 1000 calls/month 以下，不能无限扩国家和平台。

---

## 决策

### 1. 降低 OMDb 对评分链路的阻塞性

OMDb 仍作为优先可信的 IMDb 评分来源，但不再作为当天 hot_score 的硬前置条件。

- 有真实 OMDb IMDb rating/votes：优先使用。
- OMDb 因配额、授权、网络或响应缺失失败：不中断 `daily-discover`。
- 评分阶段用 TMDb `vote_average` / `vote_count` 对 IMDb 评分维度做 fallback。
- fallback 必须写入 `score_breakdown`，例如 `imdb_rating_score_source = "tmdb_fallback"`，不能伪装成真实 IMDb 分。

### 2. P1.8-F / P1.8-G 合并执行

TMDb external_ids 入库、评分前补 IMDb ID、OMDb enrichment 接入和 TMDb fallback 评分合并成一次实现。

- P1.8-F 负责 external_ids client、缓存/入库、统计、限流、可重跑。
- P1.8-G 负责评分前补 IMDb ID、OMDb enrichment 接入、TMDb fallback 评分。
- 报告必须分别覆盖 F/G 的验收标准。

### 3. FlixPatrol 覆盖范围按 API 预算重设

FlixPatrol 抓取策略调整为：

- 国家/范围：World、United States、Nigeria、Kenya。
- 平台：Netflix、Prime Video、Disney+、Apple TV+、HBO Max、Paramount+。
- 移除 Hulu。
- TV Shows TOP10：每日抓取。
- Movies TOP10：每周抓取一次。

预算估算：

- 普通日：`4 × 6 = 24` 次 FP API。
- Movie 抓取日：`4 × 6 × 2 = 48` 次 FP API。
- 30 天月：约 824 次。
- 31 天且 5 个 Movie 抓取周：约 864 次。

### 4. P1.8 执行顺序

建议执行顺序为：

`P1.8-D → P1.8-H → P1.8-C → P1.8-F/G → P1.8-E`

先做 API usage log，再扩 FP 覆盖和 external_ids，避免后续 API 用量继续不可审计。

---

## 后果

**正面:**

- OMDb 配额耗尽时，系统仍能给出可解释的评分结果。
- TMDb fallback 能减少 IMDb 缺失对 P0/P1/P2 判断的干扰。
- FP 覆盖范围能解释 FROM 这类全球榜内容，同时保持月度 API 调用低于 1000。
- F/G 合并执行减少重复代码和重复测试成本。
- 先做 API usage log 能让后续 API 消耗有账可查。

**负面 / 待解决:**

- TMDb fallback 会让 TMDb rating 同时影响 `tmdb_rating` 和 `imdb_rating` 两个评分维度，必须在 breakdown 中透明标记。
- Movie 每周抓取会降低电影榜时效性。
- World / Nigeria / Kenya / Paramount+ 的 FP API ID 仍需在 P1.8-H 执行时用官方接口或最小请求确认。
- OMDb 仍有价值，但免费配额无法支撑无节制全量查询，后续需要 API usage log 和缓存策略约束。

---

## 备选方案

### 备选 A：继续强依赖 OMDb

- 优点：IMDb 分来源纯净。
- 缺点：OMDb 配额耗尽时当天评分缺失严重，P0/P1/P2 容易偏少。
- 拒绝原因：2026-05-13 已实测触发 `Request limit reached!`，不能作为稳定前置。

### 备选 B：只扩 FlixPatrol，不做 TMDb fallback

- 优点：评分语义变化小。
- 缺点：仍不能解决 IMDb ID / OMDb 评分缺失导致的评分偏低。
- 拒绝原因：FP 覆盖和 IMDb 评分缺失是两个独立问题，需要分别治理。

### 备选 C：平台不限、国家扩到更多

- 优点：FP 覆盖最大。
- 缺点：API 调用约 1.8 万次/月，远超 1000 calls/month 预算。
- 拒绝原因：不符合当前成本约束。

### 备选 D：当前决策

- 优点：在预算内提升 FP 覆盖，同时降低 OMDb 对评分的阻塞。
- 缺点：需要更复杂的评分来源标记和 API usage log。

---

## 引用

- 当前状态：[`STATE.md`](../../STATE.md)
- 执行顺序：[`docs/tasks/p1.8_execution_order.md`](../tasks/p1.8_execution_order.md)
- FP 策略任务：[`docs/tasks/p1.8_h_flixpatrol_coverage_and_budget_strategy.md`](../tasks/p1.8_h_flixpatrol_coverage_and_budget_strategy.md)
- external_ids 任务：[`docs/tasks/p1.8_f_daily_external_ids_backfill.md`](../tasks/p1.8_f_daily_external_ids_backfill.md)
- fallback 任务：[`docs/tasks/p1.8_g_imdb_id_pre_score_backfill_and_tmdb_rating_fallback.md`](../tasks/p1.8_g_imdb_id_pre_score_backfill_and_tmdb_rating_fallback.md)
- 日报：[`journal/2026-05-13_2355_codex_gpt-5.md`](../../journal/2026-05-13_2355_codex_gpt-5.md)
