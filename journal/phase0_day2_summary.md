# MovieTrace Phase 0 Day 2 日报

记录时间：2026-05-10 13:22:39 Asia/Shanghai
阶段：Phase 0 开发前验证 / 实体匹配规则验证

## 1. 今日完成

### 1.1 全量实体匹配规则升级

完成内容：

- 基于 `reports/full_entity_matching_report.md` 对低置信度样本做人工复核。
- 修正标题匹配逻辑，支持 TMDB `original_name` / `original_title`。
- 增加核心标题命中判断，例如 `Jack Ryan` 可匹配 `Tom Clancy's Jack Ryan`。
- 增加少量可解释标题清洗：
  - URL 编码解码，例如 `%26`、`%2C`。
  - `interview`
  - `無英文字幕` / `无英文字幕`
  - `百度网盘`
- 增加新近版本优先规则：
  - 当标题和类型足够接近，且本地没有显式年份时，较新的影视实体优先。
  - 当本地标题含显式年份时，显式年份优先。

关键复核案例：

| 案例 | 结果 |
| --- | --- |
| `Jack Ryan S01-S04` | 匹配 TMDB `73375 / Tom Clancy's Jack Ryan` |
| `La casa de papel S01-S05` | 匹配 TMDB `71446 / Money Heist`，通过 `original_name` |
| `O Rio do DESEJO` | 匹配 TMDB `764541 / River of Desire`，通过 `original_title` |
| `Wedding Plan S01 interview` | 清洗 `interview` 后匹配 TMDB `229242 / Wedding Plan` |
| `Lost in Space S01-S03` | 新近版本规则选择 TMDB `75758 / 2018` |
| `All Creatures Great and Small S04` | 新近版本规则选择 TMDB `108255 / 2020` |
| `Julia S02` | 新近版本规则选择 TMDB `116761 / 2022` |

### 1.2 OMDb 纳入验证和匹配建议

完成内容：

- 临时验证 OMDb API 可用。
- 将 OMDb API key 保存到本地密钥文件 `/tmp/movietrace_phase0_secrets.json`，未写入仓库。
- 新增 OMDb 响应解析模块。
- OMDb 加入实体匹配搜索链路。
- 每条 baseline 同时输出 TMDB 建议和 OMDb 建议。
- 报告中分开展示 `TMDB ID` 与 `IMDb ID`。

重要规则：

- TMDB ID 与 IMDb ID 是不同编号体系，不参与冲突判断。
- 差异只基于标题、类型、年份和来源置信度。
- TMDB / OMDb 都确认且兼容时，可直接过关。
- 单一来源强确认时，可直接过关。
- 两家都不确定或两家建议冲突时，交给人工审核。

### 1.3 本地 canonical 写入

完成内容：

- 新增 canonical promotion pipeline。
- 将 `confidence=high` 的匹配写入本地 SQLite：
  - `canonical_items`
  - `external_ids`
  - 回写 `baseline_items.canonical_item_id`
  - 回写 `baseline_items.match_status`
  - 回写 `baseline_items.match_confidence`
- 未写飞书正式表。
- 未提升 `medium`、`low`、`no_match`。

当前本地数据库状态：

| 指标 | 数量 |
| --- | ---: |
| `baseline_items` | 855 |
| `match_candidates high` | 779 |
| `match_candidates medium` | 73 |
| `match_candidates low` | 1 |
| `match_candidates no_match` | 2 |
| `canonical_items` | 389 |
| `external_ids` | 389 |
| `baseline_items matched high` | 779 |
| `baseline_items unmatched` | 76 |

## 2. 今日新增或更新的主要文件

代码：

- `src/movietrace/pipeline/entity_matching.py`
- `src/movietrace/pipeline/canonical_promotion.py`
- `src/movietrace/sources/tmdb.py`
- `src/movietrace/sources/omdb.py`
- `src/movietrace/sources/trakt.py`
- `src/movietrace/sources/http.py`

测试：

- `tests/test_entity_matching.py`
- `tests/test_source_clients.py`
- `tests/test_canonical_promotion.py`

文档和报告：

- `docs/requirements.md`
- `docs/feasibility.md`
- `docs/operating_cost_estimate.md`
- `docs/next_steps_plan.md`
- `reports/full_entity_matching_report.md`
- `reports/manual_entity_matching_review.md`
- `reports/omdb_api_validation_report.md`
- `reports/phase0_day2_summary.md`

本地运行产物：

- `data/movietrace.db`

说明：

- `data/movietrace.db` 是本地运行产物，不提交 Git。
- 真实密钥仍保存在 `/tmp/movietrace_phase0_secrets.json`，不提交 Git。

## 3. 验证结果

最终验证命令：

```bash
python3 -m unittest discover -s tests
```

结果：

```text
Ran 21 tests
OK
```

全量匹配重跑结果：

```text
matched 853/855; errors=2; confidence={'high': 779, 'medium': 73, 'no_match': 2, 'low': 1}
```

本地 canonical promotion 结果：

```text
eligible=779; promoted=779; canonical_created=389; external_ids_created=389
```

敏感信息检查：

- 未在 `docs/`、`reports/`、`src/`、`tests/`、`config/` 中发现真实 OMDb key、verify key、`apikey=` 等明文泄露。
- `api_read_access_token`、`client_secret`、`app_secret` 仅作为代码字段名出现，不是密钥值。

## 4. 今日复盘

### 做得有效的地方

1. 先通过人工复核发现真实错误类型，再改规则，避免盲目扩大匹配逻辑。
2. TMDB `original_name/original_title` 解决了外语原名和英文发行名不一致的问题。
3. OMDb 作为交叉验证源有价值，尤其能发现同名多版本和 movie / TV 类型冲突。
4. 报告中分离 TMDB ID 和 IMDb ID 后，人工复核更清晰。
5. 新近版本优先规则符合业务场景，使同名老剧/新剧的选择更贴近当前热点更新逻辑。

### 暴露的问题

1. 只依赖 TMDB `/search/multi` 默认排序不可靠，短标题和同名多版本容易选错。
2. OMDb 默认排序也不稳定，不能作为唯一真相。
3. 标题中存在明显人工录入或文件名污染，如 `interview`、`無英文字幕`、`百度网盘`。
4. 当前没有 API cache，全量重跑会重复请求 TMDB / OMDb / Trakt，耗时且容易遇到临时错误。
5. `canonical_items` 当前只写入 source 主 ID，IMDb ID 与 TMDB ID 的交叉映射还没有补齐到同一个 canonical 上。

## 5. 剩余风险

1. 73 条 `medium` 未提升，需要人工复核或补充规则。
2. 1 条 `low`：`Special Ops Lioness S01 -> Lioness`。
3. 2 条 `no_match`：外部 API 错误或无可靠结果。
4. 当前 canonical 写入仍是本地 SQLite，不代表可写飞书正式表。
5. OMDb 授权边界仍需在商业生产前确认。
6. `data/movietrace.db` 是本地状态，其他人接手时如重新导入/重跑，需要按报告命令复现。

## 6. 明日建议任务

建议明天按以下顺序继续：

1. 生成 76 条 unmatched 人工审核报告。
   - 范围：73 条 medium、1 条 low、2 条 no_match。
   - 输出建议：确认可提升、补年份、改为 movie、改为 TV、手工填外部 ID、放弃匹配。
   - 建议报告路径：`reports/unmatched_entity_review_report.md`。

2. 为 API 请求增加本地 cache。
   - 使用现有 `api_cache` 表。
   - 覆盖 TMDB、OMDb、Trakt。
   - 目标：全量匹配重复运行时不重复请求已缓存结果。

3. 补齐 canonical 的跨源外部 ID。
   - 当前 `external_ids` 主要写入最终来源 ID。
   - 后续应把同一 canonical 下的 TMDB ID、IMDb ID、Trakt ID 尽量都写入 `external_ids`。
   - 需要先设计冲突处理规则。

4. 进入最近 30 天 TV dry run。
   - 前提：实体基线基本可用。
   - 输出建议报告：`reports/source_coverage_report.md`。
   - 目标：验证 Trakt + TMDB + OMDb 能否发现近期新剧、新季、新集。

## 7. 明日第一个推荐任务包

```text
任务名称：生成 unmatched 实体人工审核报告
任务类型：Phase 0 验证收尾 / 人工审核辅助
当前阶段：验证交付
来源任务：Phase 0 Day 2 实体匹配结果
目标：读取本地 SQLite 中未提升的 76 条 baseline_items，输出人工审核报告。
非目标：不改实体匹配算法；不写 canonical_items；不写飞书正式表。
允许修改范围：
- src/movietrace/pipeline/
- tests/
- reports/
禁止修改范围：
- 飞书正式表
- API 密钥、.env、secrets 文件
输入：
- data/movietrace.db
- match_candidates
- baseline_items
输出：
- reports/unmatched_entity_review_report.md
具体要求：
- 列出本地标题、搜索标题、TMDB 建议、OMDb 建议、差异、当前置信度。
- 给出建议动作：可提升 / 补年份 / 类型修正 / 手工补外部 ID / 暂不处理。
- 不自动写入 canonical_items。
验收标准：
- 报告覆盖 76 条 unmatched。
- 每条都有建议动作。
- 测试通过。
测试要求：
- 增加报告生成单元测试。
验证命令：
- python3 -m unittest discover -s tests
风险点：
- 建议动作只是辅助，不替代人工判断。
完成后输出要求：
- 汇报报告路径、覆盖数量、建议动作分布、验证结果。
```
