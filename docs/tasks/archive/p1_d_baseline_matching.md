# 任务包：P1-D 飞书基线匹配标记

**任务包版本：** v1
**创建日期：** 2026-05-11
**预计完成：** TBD（依赖 P1-C 完成）

---

## 任务名称

P1-D：将 P1-C 候选与飞书基线内容库做实体匹配，标记每个候选是否已在基线、匹配置信度和对应基线 item_id

## 任务类型

`feat` — 新增功能

## 当前阶段

Phase 1（V1 MVP 开发）

## 执行环境

- **分支：** `main`（当前 working tree，不开 git worktree）
- **工作目录：** `/home/ubuntu/MovieTrace`
- **commit 策略：** 完成后准备 commit，不要 push

## 来源任务

- [`docs/next_steps_plan.md`](../next_steps_plan.md) § 5.2 P1-D
- [`docs/requirements.md`](../requirements.md) § 11.2（R6 业务状态去重）
- **前置：** P1-C 必须完成（`candidates` 表存在并有数据）
- **复用：** P1-A 已修复的 [`src/movietrace/pipeline/entity_matching.py`](../../src/movietrace/pipeline/entity_matching.py)（4 case 修复，12/12 通过）

## 目标

读取 P1-C 输出的 `candidates` 表，调用 P1-A entity_matching 算法与飞书基线 `baseline_items` 表做 title + year 匹配，标记每个候选的 `is_in_baseline`、`baseline_item_id` 和 `match_confidence`，写入新表 `match_candidates`，供 P1-E 日报生成使用。

## 非目标

- ❌ 不修改飞书推荐表或读写飞书 API（那是 P1-F）
- ❌ 不生成日报（P1-E）
- ❌ 不自动决策"待人工确认"的候选是否接纳（只标记，不写飞书）
- ❌ 不修改 P1-A 的 `entity_matching.py` 算法本身
- ❌ 不修改 `baseline_items` 表 schema
- ❌ 不引入新依赖

## 允许修改范围

**新增文件：**

- `src/movietrace/pipeline/baseline_matching.py`
- `src/movietrace/db/migrations/004_match_candidates.sql`
- `tests/test_baseline_matching.py`

**修改文件：**

- `src/movietrace/db/schema.py`（注册 migration 004，`SCHEMA_VERSION` → 4）

## 禁止修改范围

- 🚫 `src/movietrace/pipeline/entity_matching.py`（P1-A 已修复，不再动）
- 🚫 `src/movietrace/sources/`
- 🚫 `src/movietrace/feishu/`（P1-F 负责飞书交互）
- 🚫 `baseline_items`、`canonical_items`、`external_ids` 表 schema
- 🚫 `STATE.md`、`SCOPE.md`、`AGENTS.md`、`CLAUDE.md`、`docs/decisions/`

## 相关上下文

### 基线匹配规则（来自 [`docs/requirements.md`](../requirements.md) § 11.2 R6）

**目的：** 对候选按飞书基线去重，标记是否已收录，以支持"发现/新增/已有"的分类统计。

**算法：** 直接复用 P1-A entity_matching 已修复的匹配算法（现场 12/12 测试通过）。

**输入：**
- 候选列表：`candidates` 表中的 `title`、`release_year`、`content_type`（movie/tv_show）、`canonical_item_id`
- 基线列表：`baseline_items` 表中的 `title`、`release_year`、`content_type`、`baseline_item_id`

**输出：**
- `match_confidence`：`high` / `medium` / `low` / `no_match` 四级
  - `high`：完全匹配（title 同库存、year ± 0）
  - `medium`：宽松匹配（title 部分交集、year ± 1）
  - `low`：模糊匹配（title 编辑距离 ≤ 2、year ± 2），标记"待人工确认"
  - `no_match`：无匹配
- `is_in_baseline`：bool，`match_confidence` ∈ {high, medium} 时为 True；low 标记为可选人工确认；no_match 为 False

### P1-A entity_matching 修复概览

| Case | Title | Release Year | Fix |
|------|-------|--------------|-----|
| Jack Ryan | 2018 | ✅ TV show vs movie 正确分类 |
| La casa de papel | 2017 | ✅ 西班牙語标题正确处理 |
| O Rio do DESEJO | 2024 | ✅ 葡萄牙語特殊字符匹配 |
| Wedding Plan | 2016 | ✅ 同名异制区分（year 权重提升）|

在 P1-D 中复用这个已修复的算法，无需再修改。

### 数据输入范围

P1-C 输出的候选表字段（来自 [`docs/tasks/p1_c_hot_score_scoring.md`](p1_c_hot_score_scoring.md)）:

```
candidates 表：
- canonical_item_id          (FK → canonical_items)
- external_id, external_type (tmdb_id / imdb_id / ...)
- title
- release_year
- content_type               (movie / tv_show)
- hot_score                  (0-100)
- priority                   (P0/P1/P2/P3)
- discovery_source           (new_release / global_hot / both)
- score_breakdown_json       (JSON: {flixpatrol_factor: 0.3, ...})
- reason_text
- created_at
```

基线表字段：

```
baseline_items 表：
- baseline_item_id (PK)
- title
- release_year
- content_type
- custom_fields... (不需要读取)
```

## 具体要求

1. **单次导入，幂等性处理**
   - 调用 `baseline_matching.match_candidates_to_baseline(candidates_df)` 返回 `match_candidates` DataFrame
   - DataFrame 包含：`candidate_id`, `is_in_baseline`, `baseline_item_id`, `match_confidence`, `match_method`, `match_score_detail`
   - 如果 `match_candidates` 表已存在，migration 时选择替换（DELETE + INSERT）或更新（UPDATE 只改 match 字段），**任务中说明策略选择**

2. **低置信度标记机制**
   - `match_confidence = 'low'` 时，在 migration 里新增字段 `requires_human_review` = True
   - `reason_text` 追加 "⚠️ Low confidence match, please review"
   - P1-E 日报生成时，将 low confidence 单列一个分组标示"待人工确认"

3. **匹配方法记录**
   - `match_method` 字段记录用了 entity_matching 算法的哪个策略（如 `exact_title_year`, `fuzzy_title`, `edit_distance`, `no_match`）
   - 便于后续调试和权重优化

4. **完整性检查**
   - P1-C 输出 N 个 candidates，本任务必须为每个都产出一条 match_candidates 记录
   - No-match 候选也要有记录（`is_in_baseline = False`, `baseline_item_id = NULL`）
   - 不丢弃任何候选

5. **算法复用约束**
   - 从 `src/movietrace/pipeline/entity_matching.py` 引入 `EntityMatcher` 类（P1-A 已提供）
   - **不修改 entity_matching.py**；如发现 bug，在 P1-D 测试中记录并汇报，由后续任务跟进
   - 调用时传入 `baseline_items` 表作为 reference corpus，逐个 candidate 查询

6. **性能**
   - N = 300 候选 × M = 5000 基线 items，时间预期 O(N × M × string_ops) ～ 1-3 秒
   - 如超过 10 秒，检查是否有全表扫描；考虑加索引或预先过滤（title 前缀字典等）

7. **数据库 migration**
   - 新建表 `match_candidates`：
     ```sql
     CREATE TABLE match_candidates (
       match_candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
       candidate_id INTEGER NOT NULL,
       is_in_baseline BOOLEAN NOT NULL,
       baseline_item_id INTEGER,
       match_confidence TEXT NOT NULL,  -- high/medium/low/no_match
       match_method TEXT NOT NULL,      -- exact_title_year / fuzzy_title / ...
       match_score_detail REAL,         -- 0.0-1.0，匹配分数细节
       requires_human_review BOOLEAN DEFAULT FALSE,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY(candidate_id) REFERENCES candidates(candidate_id),
       FOREIGN KEY(baseline_item_id) REFERENCES baseline_items(baseline_item_id)
     );
     ```

## 验收标准

1. ✅ 能从 `candidates` 表读取所有候选（如 P1-C dry-run 输出 50 条，本任务也产出 50 条）
2. ✅ 每个候选都有明确的 `match_confidence` 和 `is_in_baseline` 标记
3. ✅ `match_confidence = 'high'` 的候选中，**人工抽查 10 条**，核实 `baseline_item_id` 对应的 item 确实与候选同名、同年、同类型
4. ✅ `match_confidence = 'low'` 的候选中，**人工抽查 5 条**，说明低置信度的原因（title 模糊或 year 偏差多少）
5. ✅ `match_confidence = 'no_match'` 的候选数量合理（不应全是 no_match，也不应都是 high；预期分布 high:medium:low:no_match ≈ 60:20:15:5）
6. ✅ 重复运行本任务**不产生重复行**（migration 处理已存在 match_candidates 表的情况）
7. ✅ P1-A entity_matching 算法调用无错误日志
8. ✅ 全部单元测试通过

## 测试要求

### 单元测试（`tests/test_baseline_matching.py`）

1. **match_candidates_to_baseline() 函数测试**
   - 入参：candidates DataFrame（5 条记录）+ baseline_items DataFrame（10 条）
   - 出参：match_candidates DataFrame，5 行，每行都有 `is_in_baseline`, `baseline_item_id`, `match_confidence`
   - Case：精确匹配、模糊匹配、无匹配混合

2. **low_confidence 标记测试**
   - 输入候选标题 "Forrest Grum"（typo），基线有 "Forrest Gump"
   - 预期：`match_confidence = 'low'`, `requires_human_review = True`

3. **高置信度验证**
   - 输入候选 "The Crown", year=2016，基线有完全相同的 item
   - 预期：`match_confidence = 'high'`, `is_in_baseline = True`, `baseline_item_id` 正确指向

4. **无匹配处理**
   - 输入候选标题 "UnknownMovieXYZ"，基线无相关记录
   - 预期：`match_confidence = 'no_match'`, `is_in_baseline = False`, `baseline_item_id = NULL`

5. **类型一致性**
   - TV show 候选不应匹配 movie 基线
   - movie 候选不应匹配 TV show 基线

6. **幂等性**
   - 调用两次 match_candidates_to_baseline()，第二次输出与第一次相同

### 回归测试

- P1-A entity_matching 全部 12/12 测试仍通过（不能破坏既有匹配逻辑）

## 验证命令

```bash
# 运行 P1-D 单元测试
PYTHONPATH=src python -m pytest tests/test_baseline_matching.py -v

# 数据完整性检查
PYTHONPATH=src python -c "
import sqlite3
db = sqlite3.connect('data/movietrace.db')
c = db.cursor()
c.execute('SELECT COUNT(*) FROM candidates')
candidate_count = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM match_candidates')
match_count = c.fetchone()[0]
assert candidate_count == match_count, f'Mismatch: {candidate_count} candidates, {match_count} matches'
print(f'✓ All {candidate_count} candidates matched')
db.close()
"

# 匹配分布统计
PYTHONPATH=src python -c "
import sqlite3
db = sqlite3.connect('data/movietrace.db')
c = db.cursor()
c.execute('''
  SELECT match_confidence, COUNT(*) 
  FROM match_candidates 
  GROUP BY match_confidence 
  ORDER BY match_confidence
''')
print('Match confidence distribution:')
for conf, cnt in c.fetchall():
    print(f'  {conf}: {cnt}')
db.close()
"

# 回归：P1-A entity_matching
PYTHONPATH=src python -m pytest tests/test_entity_matching.py -v

# 完整单元测试套
PYTHONPATH=src python -m pytest tests/test_baseline_matching.py tests/test_entity_matching.py -v
```

## 风险点

1. **baseline_items 表可能为空**
   - 预期：Phase 0 初始化时从飞书导出的基线数据应该已在 `baseline_items` 表
   - 风险：如果飞书同步还没做，本任务无法验证
   - 缓解：任务包执行前，确认 `SELECT COUNT(*) FROM baseline_items` ≥ 1000

2. **P1-C 输出字段名变化**
   - 预期：P1-C 生成 `candidates` 表，字段名如 `title`, `release_year`, `canonical_item_id`
   - 风险：P1-B schema 可能导致 P1-C 微调字段名（如 `release_year` → `release_date`）
   - 缓解：任务中添加字段名映射或验证步骤，失败时记录实际字段名

3. **低置信度匹配的人工审核流程不明**
   - 预期：P1-D 只标记，P1-E 日报展示，人工在飞书或日报中决定是否接纳
   - 风险：如果无人工审核机制，低置信度候选可能被自动接纳或永久丢弃
   - 缓解：任务汇报中说明"低置信度候选已标记为 `requires_human_review = True`，流程见 P1-E/P1-F"

4. **entity_matching 算法性能**
   - 预期：50 个候选 vs 5000 个基线，<10 秒完成
   - 风险：如超时，可能需要 bulk query 或缓存优化
   - 缓解：验证命令中有性能 check；如超过 10 秒，汇报性能数据和优化建议

## 完成后输出要求

按 [`docs/workflow/report-format.md`](../workflow/report-format.md) 格式汇报。

**汇报要点：**
- 匹配结果分布（high/medium/low/no_match 各多少）
- 人工抽查 10 条 high-confidence 的核实结果
- 人工抽查 5 条 low-confidence 的说明
- 重复运行验证（数据一致性）
- P1-A 回归测试通过状态
- 任何 baseline_items / candidates 字段名不一致导致的调整
