# 任务包：P1-A 实体匹配回归修复（归档）

**任务包版本：** v1（归档）
**创建日期：** 2026-05-11
**任务实际完成日期：** 2026-05-10（commit `896b188` 内打包提交）

---

## 任务名称

P1-A：把 Phase 0 人工复核的 4 个 case 转成回归测试 + 修复算法

## 任务类型

`feat` — 算法修复（已实现）

## 当前阶段

Phase 1（V1 MVP 开发）

## 来源任务

- `docs/next_steps_plan.md` § 5.2 任务 P1-A
- `reports/manual_entity_matching_review.md` CASE-001 ~ CASE-004

## 目标

针对 Phase 0 全量匹配复盘发现的 4 个 case，**在 `entity_matching.py` 中补齐算法逻辑并落地回归测试**，确保后续匹配不再出现同类问题。

## 非目标

- ❌ 不重写整个 `entity_matching.py`
- ❌ 不修改 `canonical_promotion.py`
- ❌ 不引入 LLM、embedding 等 V2 手段
- ❌ 不处理"标题污染"以外的基线数据质量问题（剩 29 条留人工修正）

## 允许修改范围

- `src/movietrace/pipeline/entity_matching.py`
- `tests/test_entity_matching.py`

## 禁止修改范围

- 🚫 `src/movietrace/pipeline/canonical_promotion.py`
- 🚫 `src/movietrace/sources/`
- 🚫 `data/movietrace.db` 的 schema
- 🚫 `AGENTS.md`、`CLAUDE.md`、`STATE.md`、`SCOPE.md`

## 4 个 case（来源：`reports/manual_entity_matching_review.md`）

| Case | 输入 | 根因 | 规则改进 |
|------|------|------|---------|
| CASE-001 Jack Ryan | `Jack Ryan S01-S04` | 品牌前缀 `Tom Clancy's` 拉低相似度 | 核心子串匹配，TV 类型 + 季线索时升级置信度 |
| CASE-002 La casa de papel | `La casa de papel S01-S05` | TMDB 英文主标题是 `Money Heist`，未比较 `original_name` | 标题相似度同时比较主标题与 `original_name`，`reason` 标注 `matched_field=original_name` |
| CASE-003 O Rio do DESEJO | `O Rio do DESEJO` | 电影也应比较 `original_title`，但当前只比较 `title` | 电影候选与 `original_title` 比较，命中时升级置信度 |
| CASE-004 Wedding Plan interview | `Wedding Plan S01 interview` | `interview` 是文件名噪声词，污染搜索词 | `parse_title` 轻量清洗 `interview`、`無英文字幕`、`百度网盘` 等噪声，记录 `removed_noise_terms=...` |

## 验收标准

1. ✅ 4 个 case 各有专门的回归测试，全部通过
2. ✅ 既有实体匹配测试全部不退化
3. ✅ **canonical 入库率 ≥ 95%**（用户 2026-05-11 决策口径：以 `canonical_items / baseline_items` 为准，含人工复核后晋级的 medium；不以"算法直出 high"口径衡量）
4. ✅ `reason` 字段能解释命中字段（`matched_field=original_name|original_title|title` 或 `removed_noise_terms=...`）

## 验证命令

```bash
# 单元 + 回归测试
PYTHONPATH=src python -m pytest tests/test_entity_matching.py -v

# 全量匹配现状参考（不在本任务再次重跑）
cat reports/full_entity_matching_report.md | head -20
```

## 实际验证结果（2026-05-11 归档时核对）

**算法层：**

- `src/movietrace/pipeline/entity_matching.py` 已实现：
  - `original_name` / `original_title` 同步参与相似度比较（line 731 起）
  - 品牌/作者前缀的核心子串匹配（`test_choose_best_match_allows_author_prefix_core_title` 覆盖）
  - 标题噪声词清洗 + 警告记录（`test_parse_title_removes_known_noise_terms_but_records_warning` 覆盖）

**测试层：**

`PYTHONPATH=src python -m pytest tests/test_entity_matching.py -v` → **12 passed in 0.20s**

覆盖 4 个 case 的对应测试：

| Case | 测试函数 | 状态 |
|------|---------|------|
| CASE-001 | `test_choose_best_match_allows_author_prefix_core_title` | ✅ |
| CASE-002 | `test_choose_best_match_uses_tmdb_original_name` | ✅ |
| CASE-003 | `test_choose_best_match_uses_tmdb_original_title_for_movie` | ✅ |
| CASE-004 | `test_parse_title_removes_known_noise_terms_but_records_warning` | ✅ |

**入库层（参考 `reports/full_entity_matching_report.md`，生成于 2026-05-10 13:29，在算法修复之后）：**

- baseline_items：855
- canonical_items：**826（96.6%）** ✅ 达到验收线 ≥ 95%
- 算法直出 high：779（91.1%）
- medium 升级到 canonical：47（人工 + 自动复核晋级路径）
- low：1（CASE-001 已部分缓解，仍有 1 条边缘样本）
- no_match：2（Trakt API HTTPError，与算法无关）

## 风险点

1. **算法直出 high 率 91.1%** 低于"严格 high"口径 95%。本任务以 canonical 入库率为准（用户 2026-05-11 决策），如未来口径调整为"严格 high"，需另起任务包继续提升。
2. **2 条 no_match 是 Trakt API 错误**，属基础设施层，留给 P1 后续任务处理（不在本任务范围）。
3. **29 条 baseline_quality_issues** 是数据层人工待修，不属算法范畴。
4. **CASE-004 噪声词清洗规则在 `entity_matching.py` 中维护**，未来若噪声形式扩散应考虑抽到配置文件（YAGNI 暂不做）。

## 后续追踪

- 算法 high 率提升从 V1 上线后被动观察推进；如运营反馈仍有误匹配，按 case 累积新 review 文档后再决定是否启动 P1-A.2。
- 本任务归档后，Phase 1 主线推进到 **P1-B**（待 SUP-G API 验证决定路径）。

## 完成后输出要求

本任务包**已完成并归档**，无需再次执行。如读到本文件，应按 [`docs/workflow/report-format.md`](../workflow/report-format.md) 报告格式向用户确认归档无误，不应重新实现。
