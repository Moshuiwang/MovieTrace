# MovieTrace OMDb API 验证报告

状态：Phase 0 补充验证产物
记录时间：2026-05-10 13:22:39 Asia/Shanghai
写入范围：仅记录验证结果，不保存 API key

## 1. 结论摘要

OMDb API 可作为 MovieTrace 的 IMDb 补充和交叉验证数据源，适合在 Phase 0 / MVP 内部验证中补充：

- IMDb ID
- 英文标题
- 年份
- 类型
- `totalSeasons`
- IMDb rating
- IMDb votes
- runtime、genre、country、language

但 OMDb 不应替代 TMDb / Trakt 作为主实体匹配源，尤其不适合作为原始外语标题匹配的唯一依据。

## 2. 临时连通性验证

### 2.1 IMDb ID 查询

请求类型：按 IMDb ID 查询

样本：

- `tt3896198`

结果：

- `Response=True`
- `Title=Guardians of the Galaxy: Vol. 2`
- `Year=2017`
- `Type=movie`
- `imdbRating=7.6`
- `imdbVotes=828,114`

结论：按 IMDb ID 查询可用。

### 2.2 标题搜索

样本：`Wedding Plan`

结果：

- `Title=Wedding Plan`
- `Year=2023`
- `imdbID=tt28426949`
- `Type=series`

结论：可辅助确认 TMDB `229242 / Wedding Plan`。

### 2.3 精确标题查询

样本：`Money Heist`

结果：

- `Title=Money Heist`
- `Year=2017-2021`
- `imdbID=tt6468322`
- `Type=series`
- `totalSeasons=5`
- `imdbRating=8.2`
- `imdbVotes=604,616`

结论：对英文 IMDb 标题和 series 季数校验有价值。

## 3. 疑难标题样本

| 查询 | 结果 | 结论 |
| --- | --- | --- |
| `Jack Ryan` | 返回 `Tom Clancy's Jack Ryan / tt5057054 / series` | 可辅助品牌/作者前缀别名判断 |
| `Wedding Plan` | 返回 `Wedding Plan / tt28426949 / series` | 可辅助确认正确实体 |
| `Money Heist` | 返回 `Money Heist / tt6468322 / series` | 可辅助确认 IMDb ID、季数和评分 |
| `La casa de papel` | 未直接返回主剧 `Money Heist` | 原始外语标题覆盖不稳定 |
| `O Rio do Desejo` | 未直接命中主实体 | 原始外语标题覆盖不稳定 |
| `River of Desire` | 返回 `River of Desire / tt19855324 / movie` | 英文标题查询可用，但年份可能与 TMDB 不完全一致 |

## 4. 使用定位

建议定位：

1. TMDb 仍作为元数据、original title 和 ID 映射主数据源。
2. Trakt 继续作为 TV 更新、热度和跨源映射补充。
3. OMDb 作为 IMDb ID、英文标题、rating/votes 和 totalSeasons 的补充验证源。
4. OMDb 标题搜索只作为辅助，不作为自动最终裁决。

## 5. 授权和成本注意

官方页面显示：

- 免费 key 有每日 1,000 次请求限制。
- Poster API 仅 patron 可用。
- 内容许可标注为 CC BY-NC 4.0。
- OMDb 不是 IMDb 官方 API。

因此：

1. Phase 0 / MVP 内部验证可以低频使用。
2. 商业生产长期依赖 OMDb rating/votes 前，需要确认授权边界。
3. 不应把 OMDb 视为 IMDb 商业数据授权的替代品。
4. API key 不得提交到 GitHub；应通过 `.env` 或本地 secrets 管理。

## 6. 后续任务建议

1. 增加 `OmdbSearchClient` 或 `OmdbDetailsClient`，优先支持按 IMDb ID 查询。
2. 增加 OMDb 响应解析测试，覆盖 movie、series、no_match、rating/votes。
3. 将 OMDb 响应写入 API cache，避免重复请求。
4. 在实体匹配报告中增加可选的 IMDb 交叉验证字段，但不自动覆盖 TMDb / Trakt 结论。
