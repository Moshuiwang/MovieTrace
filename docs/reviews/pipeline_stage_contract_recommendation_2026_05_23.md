# Pipeline Stage Contract Recommendation

> 日期：2026-05-23
> 背景：围绕 FlixPatrol / TMDb / Trakt / canonical enrichment 的先后顺序、fallback 语义和跳过条件，近期已经出现多次修复。本文记录一次轻量方案建议，目标是减少同类 bug，而不是立刻做大规模 orchestrator 重构。

## 问题判断

当前问题不像单点 bug，更像“阶段契约不清”：

- `fallback` 一词被多处复用，但语义不同。
- source 抓取结果、source effective date、source status、stats 分散在多个 dict 中。
- merge 后的候选只携带 `source_flags`，没有清晰表达每个来源是否 fresh。
- “是否可以跳过 TMDb detail”同时受 canonical_items、api_cache、候选内存字段影响，判断散在 enrichment 逻辑里。
- 写入 `content_updates` 前缺少最终 invariant，导致旧快照数据曾被当作今日新发现。

这些问题的共同后果是：每次改一个分支条件，都容易影响另一个阶段的语义。

## 建议一：拆分 fallback 命名

不要继续裸用 `fallback` 表达所有回退行为。建议至少拆成三类：

| 名称 | 含义 | 典型位置 |
|---|---|---|
| `source_date_fallback` | 今天抓取失败或 0 rows，改用历史 source snapshot | source decision / source_fetch_runs |
| `id_match_fallback` | 没有 tmdb_id 时，用 imdb_id 或 title 合并 | multi_source_merge |
| `rating_fallback` | OMDb 评分缺失时，用 TMDb rating 参与评分 | scoring |

收益：读代码时先知道是哪一种 fallback，避免把“旧数据可参与上下文”误读成“旧数据可制造今日事件”。

## 建议二：引入 SourceSnapshotDecision

把每个 source 的抓取和使用决策收敛成一个对象，而不是在 `fp_result` / `tmdb_result` / `source_dates` / `source_status` 之间推断。

示例结构：

```python
SourceSnapshotDecision(
    source="tmdb",
    target_date="2026-05-23",
    effective_date="2026-05-22",
    status="source_date_fallback",
    rows_fetched_today=0,
    rows_used=120,
    is_fresh=False,
    error="..."
)
```

建议约定：

- `target_date`：本次批次日。
- `effective_date`：实际读取的 source snapshot 日期；没有可用数据则为 `None`。
- `is_fresh`：只在 `effective_date == target_date` 时为 true。
- `rows_used`：merge 实际读取的行数，fresh 和 fallback 都有可能大于 0。
- 下游 merge / stats / notify 只读取这个决策对象。

收益：`source_status` 和 `source_dates` 不再各自维护一半事实。

## 建议三：候选携带 source contribution

`MergedCandidate.source_flags` 可以保留，但建议增加更明确的来源贡献信息：

```python
candidate.source_contributions = {
    "flixpatrol": {"effective_date": "2026-05-23", "is_fresh": True},
    "tmdb": {"effective_date": "2026-05-22", "is_fresh": False},
}
```

这样 `has_fresh_signal` 不再是后面临时从 `source_flags` 和 `source_dates` 交叉推断，而是 merge 产物自带事实。

建议规则：

- candidate 是否来自某 source，由 merge 阶段记录。
- candidate 是否拥有 fresh signal，由 source contribution 判断。
- pure fallback candidate 可以参与评分统计和 debug，但不能单独写入今日事件。

## 建议四：集中 TMDb detail skip 判断

P1.52 / P1.55 的问题本质是：canonical enrichment 命中不等于 TMDb detail 字段完整。

建议只允许一个函数决定是否可以跳过 detail API：

```python
has_required_tmdb_detail(candidate, purpose="score")
```

最低规则：

- movie 至少需要 `release_date` 和 `original_language`。
- tv 至少需要 `release_date`、`original_language`、`last_air_date`。
- 计算缺集或时长时，还需要 `last_episode_to_air` / `seasons`。
- canonical_items 可以预填 `genres_json`、`title_zh`、`overview_zh`、`networks_json`，但不能单独触发 detail skip。

建议保留 `canonical_hits`，但口径必须明确：

- 只统计“canonical 命中且真的跳过 API”的次数。
- canonical 仅预填、随后仍走 detail API，不计入 `canonical_hits`。

## 建议五：写 content_updates 前加 invariant

在最终写入前加硬规则，比飞书层补救更可靠。

建议 invariant：

- 非豁免项必须 `has_fresh_signal == True`。
- `source_date_fallback` 只能作为上下文或评分补充，不能单独制造 `new_discovery`。
- 没有 `tmdb_id` 的候选不能写事件。
- `content_update_id` 的日期仍表示批次日，不表示 source snapshot 日期。

如果后续保留 Soap 豁免，需要显式写进规则：

- Soap bypass 是业务豁免；是否允许 pure fallback Soap 写入，应独立决策，不要隐含在 fallback 逻辑里。

## 建议六：补矩阵测试

不建议先做大重构。更现实的下一步是补一组矩阵测试，把阶段契约固定下来。

建议覆盖：

| 测试矩阵 | 关键断言 |
|---|---|
| source decision | fresh / error / 0 rows / fallback / no fallback 的 status、effective_date、rows_used 正确 |
| merge contribution | 不同 source effective date 下，candidate source contribution 正确 |
| write gate | pure fallback 被 suppress；fresh + fallback 正常通过 |
| TMDb detail skip | canonical 有 genres 但缺 detail 字段时仍调用 detail API |
| stats / notify | source_date_fallback 的 cached_count / rows_used 显示一致 |

## 建议任务包

可以后续立一个小任务包，例如：

`P1.56 pipeline-stage-contracts`

建议目标：

1. 写明 pipeline 阶段契约。
2. 拆分 fallback 命名。
3. 引入轻量 `SourceSnapshotDecision` 或等价结构。
4. 让 merge 产物携带 source contribution。
5. 集中 TMDb detail skip 判断。
6. 在写入 `content_updates` 前加 invariant。
7. 补齐上述矩阵测试。

非目标：

- 不做大规模 CLI orchestrator 重构。
- 不改数据库 schema。
- 不引入新依赖。
- 不修改飞书同步层作为主要修复点。

## 优先级

推荐顺序：

1. 先做命名澄清和文档契约。
2. 再做 `SourceSnapshotDecision` / source contribution。
3. 然后集中 TMDb detail skip 判断。
4. 最后加写入前 invariant 和矩阵测试。

这个顺序的好处是：每一步都能独立验证，也不会把 V1 运行观察期变成一次高风险重构。
