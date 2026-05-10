# MovieTrace 实体匹配人工复核记录

状态：Phase 0 验证复盘
记录时间：2026-05-10 13:22:39 Asia/Shanghai
来源报告：`reports/full_entity_matching_report.md`

本文件用于记录人工复核中发现的实体匹配问题、根因和后续回归用例。正式编码阶段应优先把这里的案例转成自动化测试，避免只修当前样本。

## CASE-001: Jack Ryan S01-S04

### 输入

- `Jack Ryan S01`
- `Jack Ryan S02`
- `Jack Ryan S03`
- `Jack Ryan S04`

### 当前匹配结果

- TMDB 标题：`Tom Clancy's Jack Ryan`
- TMDB 年份：2018
- 当前置信度：`low`
- 当前依据：`title_similarity=0.58; parsed_season=Sxx; season_hint_matches_tv`

### 人工确认

- 该匹配应视为正确实体。
- TMDB 使用标题 `Tom Clancy's Jack Ryan`。
- IMDb 和常见人工搜索场景中可使用 `Jack Ryan`。

### 根因

当前标题相似度对品牌、作者或版权前缀过于敏感。`Tom Clancy's` 是数据源标题的一部分，但不应导致核心标题 `Jack Ryan` 被降为低置信。

### 规则改进

- 增加品牌/作者前缀归一化或核心标题匹配。
- 当本地标题是外部标题的核心子串，且 TV 类型、季数线索成立时，应提高置信度。
- 不应把所有包含关系直接升为 high；仍需检查同名竞争候选、类型和年份。

### 回归用例

- 给定输入 `Jack Ryan S01`，候选包含 `Tom Clancy's Jack Ryan`。
- 期望选择该候选。
- 期望 `confidence` 不为 `low`。
- `reason` 应说明核心标题或前缀归一化命中。

## CASE-002: La casa de papel S01-S05

### 输入

- `La casa de papel S01`
- `La casa de papel S02`
- `La casa de papel S03`
- `La casa de papel S04`
- `La casa de papel S05`

### 当前错误结果

- TMDB ID：`308014`
- TMDB 标题：`Berlin and the Lady with an Ermine`
- TMDB 年份：2026
- 当前置信度：`low`
- 当前依据：`title_similarity=0.28; parsed_season=Sxx; season_hint_matches_tv`

### 人工确认正确结果

- TMDB ID：`71446`
- TMDB 页面标题：`Money Heist`
- TMDB Original Name：`La casa de papel`
- TMDB URL：https://www.themoviedb.org/tv/71446-la-casa-de-papel
- 首播日期：2017-05-02

### 根因

TMDB 搜索接口实际返回了正确候选 `71446`，但英文环境下主标题为 `Money Heist`，原始标题为 `La casa de papel`。当前解析和评分只使用 `name/title` 参与标题相似度，忽略了 `original_name/original_title`，导致正确候选相似度偏低，错误候选反而被选中。

### 规则改进

- TMDB 结果解析应保留 `original_name/original_title`。
- 标题相似度应同时比较本地搜索标题与主标题、原始标题，取可解释的最佳命中。
- `reason` 应记录命中的字段，例如 `matched_field=original_name`。
- TV 季度条目应增加年份合理性检查，避免把 2026 未播衍生内容匹配到历史季。
- 对衍生剧、纪录片、翻拍版和地区改编版应保守处理，不能仅因关键词相关而胜出。

### 回归用例

- 给定输入 `La casa de papel S01`。
- 候选包含：
  - `71446 / Money Heist / original_name=La casa de papel / tv / 2017`
  - `308014 / Berlin and the Lady with an Ermine / original_name=Berlín y la dama del armiño / tv / 2026`
- 期望选择 TMDB `71446`。
- 期望 `confidence` 至少为 `medium`，理想为 `high`。
- `reason` 应包含 `matched_field=original_name`。

## CASE-003: O Rio do DESEJO

### 输入

- `O Rio do DESEJO`

### 当前匹配结果

- TMDB ID：`764541`
- TMDB 标题：`River of Desire`
- TMDB 年份：2023
- 当前置信度：`low`
- 当前依据：`title_similarity=0.53`

### 人工确认

- 该匹配应视为正确实体。
- TMDB 英文页面标题：`River of Desire`
- TMDB Original Title：`O Rio do Desejo`
- TMDB URL：https://www.themoviedb.org/movie/764541-o-rio-do-desejo
- 上映年份：2023

### 根因

当前匹配已经选中了正确 TMDB 实体，但评分只比较英文标题 `River of Desire`，没有比较 `original_title=O Rio do Desejo`。因此该记录不是错选问题，而是置信度被低估。

### 规则改进

- 电影候选也应与 `original_title` 比较，不能只对 TV 使用原始标题。
- 当本地标题与 `original_title` 高相似或完全一致时，应提高置信度。
- `reason` 应记录 `matched_field=original_title`，避免人工复核时误判为弱匹配。

### 回归用例

- 给定输入 `O Rio do DESEJO`。
- 候选包含 `764541 / River of Desire / original_title=O Rio do Desejo / movie / 2023`。
- 期望选择 TMDB `764541`。
- 期望 `confidence` 为 `high`。
- `reason` 应包含 `matched_field=original_title`。

## CASE-004: Wedding Plan S01 interview

### 输入

- `Wedding Plan S01 interview`

### 当前结果

- 当前搜索标题：`Wedding Plan interview`
- 当前置信度：`no_match`
- 当前依据：`api_error=RuntimeError: TraktSearchClient:HTTPError`

### 人工确认

- 正确实体应为 TMDB `229242 / Wedding Plan`。
- TMDB URL：https://www.themoviedb.org/tv/229242
- 该剧为泰国剧，英文标题为 `Wedding Plan`。
- 本地同库中多条 `Wedding Plan S01` 已可正确匹配到 TMDB `229242`。

### 根因

`interview` 是原始文件名或人工录入中遗留的附加描述词，不属于影视实体标题。当前 `parse_title` 只去除了季数 `S01`，没有识别这类非实体描述词，导致搜索词变成 `Wedding Plan interview`。TMDB 搜索 `Wedding Plan interview` 无结果，而搜索 `Wedding Plan` 可正确命中。

### 规则改进

- 这类问题应优先归类为基线数据质量问题，而不是强行通过大量硬编码在匹配器中消化。
- 程序可做少量低风险清洗，例如识别尾部的 `interview`、`無英文字幕`、`百度网盘` 等明显非实体描述。
- 清洗动作必须可解释，`reason` 或质量报告中应记录 `removed_noise_terms=interview`。
- 原始标题必须保留，不能覆盖人工录入值。
- 如果清洗后可命中，应给出匹配候选；如果清洗前后差异明显，应给人类预警和修正建议。

### 回归用例

- 给定输入 `Wedding Plan S01 interview`。
- 搜索前建议清洗为 `Wedding Plan`。
- 期望候选选择 TMDB `229242`。
- 输出应包含数据质量预警，指出原始标题含疑似非实体描述词 `interview`。

## 数据质量类标题污染

以下低置信或未匹配样本可能属于同类问题：

- `Wedding Plan S01 interview`
- `American Horror Story S11 無英文字幕`
- `Bleach Thousand Year Blood War S02無英文字幕`
- `Fear the Walking Dead S02無英文字幕`
- `Love Is Blind S07百度网盘`

处理原则：

1. 不把实体匹配逻辑扩展成复杂文件名解析器。
2. 只对高确定性的噪声词做轻量清洗，并记录清洗依据。
3. 对清洗前后差异明显的记录输出人工预警。
4. 建议人类修正基线数据，而不是让程序长期依赖脆弱规则。
5. 清洗规则应可配置或集中维护，避免分散硬编码。

## 后续处理原则

1. 人工复核发现的问题先写入本文件，再进入编码任务包。
2. 每个问题必须包含输入、当前结果、人工确认、根因、规则改进和回归用例。
3. 正式编码阶段必须先把案例转成测试，再调整算法。
4. 本文件不授权写入 `canonical_items` 或飞书正式表。
