# MovieTrace 基线质量报告

状态：Phase 0 正式验证产物
生成时间：2026-05-09 16:03:26 +0800
数据来源：飞书多维表格正式基线表 `节目`
写入范围：仅读取正式表，未写入或修改正式表

## 1. 结论摘要

- 本次读取记录数：856 条。
- `节目名` 非空记录：855 条，占 99.9%。这些记录可形成标题级弱基线。
- 已上架状态为真的记录：0 条，占 0.0%。
- 可形成 movie / season / episode 强基线的记录：0 条，占 0.0%。
- 当前表缺少内容类型、季号、集号、IMDb ID、TMDb ID、Trakt ID，因此不能直接形成可靠的影视实体强基线。
- Phase 0 后续可以继续做标题级抽样匹配，但低置信度结果不得用于自动过滤候选。

## 2. 表结构

| 字段名 | 飞书字段类型 | 是否为当前已知字段 |
| --- | ---: | --- |
| `节目名` | 1 | 是 |
| `上传日期（目录名）` | 5 | 是 |
| `已下载` | 7 | 是 |
| `已上传FTP` | 7 | 是 |
| `已转码` | 7 | 是 |
| `已上架` | 7 | 是 |
| `备注` | 1 | 是 |

缺失的强基线字段：

- `content_type`
- `season_number`
- `episode_number`
- `imdb_id`
- `tmdb_id`
- `trakt_id`

## 3. 字段完整性

| 字段名 | 非空记录数 | 非空比例 |
| --- | ---: | ---: |
| `节目名` | 855 | 99.9% |
| `上传日期（目录名）` | 833 | 97.3% |
| `已下载` | 754 | 88.1% |
| `已上传FTP` | 254 | 29.7% |
| `已转码` | 0 | 0.0% |
| `已上架` | 0 | 0.0% |
| `备注` | 154 | 18.0% |

## 4. 状态字段分布

说明：飞书复选框字段未出现在记录 fields 中时，按 `missing` 统计；出现且为真按 `true`，出现但为空或假按 `false`。

| 状态字段 | true | false | missing |
| --- | ---: | ---: | ---: |
| `已下载` | 754 | 0 | 102 |
| `已上传FTP` | 254 | 0 | 602 |
| `已转码` | 0 | 0 | 856 |
| `已上架` | 0 | 0 | 856 |

## 5. 可形成基线的比例

| 基线类型 | 判定标准 | 记录数 | 比例 | 当前用途 |
| --- | --- | ---: | ---: | --- |
| 标题级弱基线 | `节目名` 非空 | 855 | 99.9% | 可用于人工抽样、标题搜索、初步去重候选 |
| 标题 + 状态弱基线 | `节目名` 非空，且至少存在一个流程状态字段 | 754 | 88.1% | 可辅助判断是否已下载、上传、转码、上架 |
| 强实体基线 | 有内容类型，并具备外部 ID 或明确季集信息 | 0 | 0.0% | 可用于自动 movie / season / episode 去重 |

## 6. 重复标题情况

- 重复标题数量：81 个。
- 涉及记录数：170 条。

| 标题 | 出现次数 |
| --- | ---: |
| Wedding Plan S01 | 4 |
| Elsbeth S01 | 3 |
| Foundation S02 | 3 |
| NCT 127 The Lost Boys S01 | 3 |
| Outlander S07 | 3 |
| The Gilded Age S02 | 3 |
| The Lincoln Lawyer S02 | 3 |
| 3 Body Problem S01 | 2 |
| 9-1-1 S07 | 2 |
| A Gentleman in Moscow S01 | 2 |
| Abbott Elementary S03 | 2 |
| Agatha All Along S01 | 2 |
| All Creatures Great and Small S04 | 2 |
| American Horror Story S03 | 2 |
| American Horror Story S10 | 2 |
| And Just Like That S02 | 2 |
| Black Mirror S02 | 2 |
| Black Mirror S04 | 2 |
| Black Mirror S05 | 2 |
| Black Mirror S06 | 2 |
| Bleach Thousand Year Blood War 2023 S02 | 2 |
| Bridgerton S01 | 2 |
| Deceitful Love S01 | 2 |
| Disclaimer S01 | 2 |
| Echo S01 | 2 |
| Elite S01 | 2 |
| Elsbeth S02 | 2 |
| Envious S01 | 2 |
| Fatal Seduction S01 | 2 |
| Fear the Walking Dead S08 | 2 |

## 7. 样本记录

以下仅列出前 10 条可读样本，用于确认字段解析是否符合预期。

| 记录 ID | 节目名 | 上传日期（目录名） | 已下载 | 已上传FTP | 已转码 | 已上架 |
| --- | --- | --- | --- | --- | --- | --- |
| `recW2nsUa8` | Avatar The Way of Water | 1687795200000 | true | true | missing | missing |
| `recjExe5qs` | From S02 | 1687795200000 | true | true | missing | missing |
| `reccaixQLB` | Narappa | 1687795200000 | true | true | missing | missing |
| `rec2B82YaG` | Never Have I Ever S01 | 1687795200000 | true | true | missing | missing |
| `recXBYPu8O` | Never Have I Ever S02 | 1687795200000 | true | true | missing | missing |
| `recLrPcCOi` | Never Have I Ever S03 | 1687795200000 | true | true | missing | missing |
| `rec26t75S7` | Never Have I Ever S04 | 1687795200000 | true | true | missing | missing |
| `recs1hSmDd` | Platonic S01 | 1687795200000 | true | true | missing | missing |
| `rec0c6q5hH` | Silo S01 | 1687795200000 | true | true | missing | missing |
| `recMmAWWYb` | The Crowded Room S01 | 1687795200000 | true | true | missing | missing |

## 8. 风险与建议

1. 当前基线表适合作为标题级弱基线，不适合直接作为强自动去重依据。
2. 后续实体匹配需要通过 TMDb / Trakt 搜索补齐外部 ID，并抽样人工复核准确率。
3. 由于缺少内容类型，同名电影和剧集存在误匹配风险，不得自动高置信度合并。
4. 由于缺少 season / episode 字段，新增季和新增集不能仅靠当前表稳定判断是否已上架。
5. 建议后续在基线表或映射表中逐步补充 `content_type`、`season_number`、`episode_number`、`tmdb_id`、`imdb_id`、`trakt_id`。

## 9. 下一步

建议进入 Phase 0 第二个验证动作：抽样 100-300 条 `节目名`，使用 TMDb / Trakt 做外部实体匹配，输出 `entity_matching_report.md`，并人工复核高置信度匹配准确率。
