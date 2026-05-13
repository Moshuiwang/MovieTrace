# ADR-0008: 多热门源独立采集与并集发现架构


**状态:** Accepted
**日期:** 2026-05-13
**决策者:** 用户 + Claude Code (Sonnet 4.6 / Opus 4.7 / deepseek-v4-pro)
**相关 Commit:** `38247cc`
**影响:** ADR-0003(FlixPatrol 仍为核心真实平台热度源,但不再是唯一候选入口)、ADR-0007(功能 1 的发现架构细化)

---

## 上下文

ADR-0007 将 MovieTrace 定位为"全网内容更新追踪系统",其中功能 1 是"全网热门追踪"。但 Phase 1 V1 MVP 的实际实现仍以 FlixPatrol 为单一候选入口,TMDb / Trakt / OMDb 没有形成可用的外部信号富化链路。

2026-05-13 的功能核查发现:

- `run_discovery` 能从 FlixPatrol 生成候选,但 `ext_data` 始终为空。
- hot_score 中 TMDb 社区热度、Trakt 社区热度、TMDb 评分、IMDb 评分和新鲜度合计 55% 权重长期为 0。
- 即使 FlixPatrol 信号满分,候选最高也只能到 P3,功能 1 无法真实产出 P2+ 内容。

随后对 TMDb / Trakt / OMDb 做了可行性调研:

- TMDb 的 `trending/all/day`、`tv/popular`、`movie/popular` 可批量分页拉取,适合每日独立采集。
- Trakt 的 `shows/trending` 和 `movies/trending` 可拉取社区热度,但需要 Mozilla/Firefox 风格 User-Agent 才能绕过 Cloudflare 1010。
- OMDb 没有列表端点,只能按 IMDb ID 逐条查询,适合作为富化源而不是候选源。
- TMDb/Trakt 与 FlixPatrol 的重叠度有限,不能把它们只当作 FlixPatrol 的补字段索引。

因此需要明确:功能 1 的发现入口应继续是 FlixPatrol 单入口,还是升级为多热门源独立采集后的并集发现。

---

## 决策

**功能 1 采用 FlixPatrol + TMDb + Trakt 三源独立采集、并集发现、统一富化评分的架构。**

具体规则:

1. **三源都是候选来源**,而不是"FlixPatrol 候选 + TMDb/Trakt 补字段"。
2. 三源原始热门数据独立保存:
   - `flixpatrol_top10`
   - `tmdb_trending`
   - `trakt_trending`
3. 合并发生在 pipeline 内存层,当前实现为 `multi_source_merge.py`。
4. 多源去重优先级为:
   - `tmdb_id`
   - `imdb_id`
   - `title_norm`
5. OMDb 作为逐条富化源,用于补 IMDb 评分和投票数,配合 `api_cache` 做 24h 缓存。
6. TMDb 详情可用于补齐 release date、overview、vote 等字段。
7. FlixPatrol 当日无数据时不阻塞 pipeline,系统可用 TMDb + Trakt 二源降级评分并继续写入可确认结果。

Phase 1.7 已按该决策落地:

- migration 007 新增 `tmdb_trending` / `trakt_trending`
- 新增 `fetch-tmdb-trending` / `fetch-trakt-trending` / `inspect-updates`
- `daily-discover` 改为多源采集、合并、富化、评分的 6 步流程

---

## 后果

**正面:**

- 功能 1 不再被 FlixPatrol 单源可用性卡死。
- TMDb / Trakt 中大量未上 FP 的高分内容可进入候选池,符合"全网热门追踪"定位。
- 三源独立存表后,每个源的健康度、数量、字段质量可以单独验收和排查。
- 合并层与采集层分离,未来增删热门源时不需要改动单源原始表结构。
- OMDb 缓存降低重复查询成本,二次运行可大量命中缓存。
- FP 0 数据日仍可产出低量但可追溯的候选,系统具备降级能力。

**负面 / 待解决:**

- 日运行 API 调用数显著增加。2026-05-13 验收约 600 次调用,其中 OMDb 约 583 次。
- OMDb 逐条查询受 1 秒间隔影响,首次全量运行约 10 分钟。
- 多源合并带来更多 identity 边界问题,低质量 `tmdb_id` / `imdb_id` 或标题归一化错误会影响去重。
- FP 为 0 时评分分布偏低。2026-05-13 仅 4 条达到 P2+,需等 FP 数据恢复后再做 Phase 1.8 权重调优。
- `content_updates.canonical_item_id` 当前有 NOT NULL 约束,新发现内容若无法匹配到 existing canonical item 会被跳过。是否自动创建 canonical_items 留给后续任务决策。
- `candidates` 表在新流程中不再写入,但旧 `baseline_matching` 仍依赖它。是否废弃或迁移留给 Phase 1.8 决策。

---

## 备选方案

### 备选 A: 维持 FlixPatrol 单入口,TMDb/Trakt 只做富化

- 优点:
  - 改动范围最小。
  - 候选规模较小,运行成本更低。
  - 与 Phase 1 初版代码结构接近。
- 缺点:
  - TMDb/Trakt 与 FP 重叠度有限,大量社区高热内容无法进入候选池。
  - FP 无当日数据时功能 1 几乎失效。
  - 无法兑现 ADR-0007 中"全网热门追踪"的多源语义。
- 拒绝原因:
  - 2026-05-13 实测证明该路径无法稳定产出 P2+ 内容,核心功能 1 实际不可用。

### 备选 B: 用一张统一大宽表保存所有热门源

- 优点:
  - 查询入口单一。
  - schema 数量较少。
- 缺点:
  - FlixPatrol、TMDb、Trakt 字段结构差异大,大宽表会产生大量空字段和源特定字段。
  - 单源健康检查和重跑不清晰。
  - 后续增加或删除源时容易牵动共享表结构。
- 拒绝原因:
  - 用户已明确要求"热门源数据每日更新,独立保存,互相不干扰";独立表更符合排障和演进需要。

### 备选 C: 下载 IMDb/外部数据集替代 OMDb 逐条查询

- 优点:
  - 可减少 OMDb API 调用。
  - 本地查询速度更快。
- 缺点:
  - 引入新的数据下载、更新、授权和存储复杂度。
  - 超出 V1 当前"低复杂度、可快速验证"边界。
  - 需要额外的数据清洗和同步任务。
- 拒绝原因:
  - OMDb 免费配额在当前候选规模下可承受,配合缓存即可满足 Phase 1.7;引入 IMDb 数据集不符合当前阶段的复杂度约束。

### 备选 D: 本次决策(三源独立采集 + 并集发现 + OMDb 缓存富化)

- 优点:
  - 数据覆盖和系统韧性明显优于 FP 单入口。
  - 与 PRD/ADR-0007 的多源发现方向一致。
  - 保留单源可观测性和未来扩展空间。
- 缺点:
  - 实现复杂度、运行时间和 API 调用数增加。

---

## 引用

- 调研日报: [`journal/2026-05-13_1100_claude-code_sonnet-4.6+opus-4.7.md`](../../journal/2026-05-13_1100_claude-code_sonnet-4.6+opus-4.7.md)
- 执行日报: [`journal/2026-05-13_1100_claude-code_deepseek-v4-pro.md`](../../journal/2026-05-13_1100_claude-code_deepseek-v4-pro.md)
- 验收报告: [`reports/session_2026-05-13_p1.7_acceptance.md`](../../reports/session_2026-05-13_p1.7_acceptance.md)
- 相关任务: [`docs/tasks/p1.7_a_multi_source_schema.md`](../tasks/p1.7_a_multi_source_schema.md)
- 相关任务: [`docs/tasks/p1.7_b_tmdb_trending_source.md`](../tasks/p1.7_b_tmdb_trending_source.md)
- 相关任务: [`docs/tasks/p1.7_c_trakt_trending_source.md`](../tasks/p1.7_c_trakt_trending_source.md)
- 相关任务: [`docs/tasks/p1.7_d_multi_source_merge_and_score.md`](../tasks/p1.7_d_multi_source_merge_and_score.md)
- 相关任务: [`docs/tasks/p1.7_e_inspect_updates_cli.md`](../tasks/p1.7_e_inspect_updates_cli.md)
- 相关代码: commit `38247cc`
