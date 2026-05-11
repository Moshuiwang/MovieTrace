# 任务包：P1-E 每日 Markdown 日报生成

**任务包版本：** v1
**创建日期：** 2026-05-11
**预计完成：** TBD（依赖 P1-D 完成）

---

## 任务名称

P1-E：从 P1-D 匹配结果生成可读的每日 Markdown 日报，按"发现/新增/已有/待确认"四分类汇总统计和列表

## 任务类型

`feat` — 新增功能

## 当前阶段

Phase 1（V1 MVP 开发）

## 执行环境

- **分支：** `main`（当前 working tree，不开 git worktree）
- **工作目录：** `/home/ubuntu/MovieTrace`
- **commit 策略：** 完成后准备 commit，不要 push

## 来源任务

- [`docs/next_steps_plan.md`](../next_steps_plan.md) § 5.2 P1-E
- [`docs/product_roadmap.md`](../product_roadmap.md) § 2.4（3 类分组样板）
- **前置：** P1-D 必须完成（`match_candidates` 表存在）

## 目标

读取 P1-D 输出的 `match_candidates` 表及其关联的 `candidates` / `baseline_items` 数据，按 4 类（🆕 新发现、♻️ 已有内容、⚠️ 待人工确认、📊 统计汇总）生成每日 Markdown 日报，存储到 `reports/daily/YYYY-MM-DD.md`，供人工审核和飞书推荐系统（P1-F）使用。

## 非目标

- ❌ 不写飞书推荐表（P1-F）
- ❌ 不生成周报、月报或其他聚合报告
- ❌ 不自动决策是否接纳候选（只分类展示，人工确认）
- ❌ 不修改 candidates / match_candidates / baseline_items 表
- ❌ 不引入新依赖（Markdown 生成用内置 str format，不用 Jinja2 等模板库）

## 允许修改范围

**新增文件：**

- `src/movietrace/reports/daily_writer.py`
- `tests/test_daily_report.py`
- `reports/daily/` 目录（首次创建）
- `reports/daily/YYYY-MM-DD.md` 每日日报

**修改文件：**

- （无需修改 schema.py，不创建新表）

## 禁止修改范围

- 🚫 `src/movietrace/pipeline/`（P1-C、P1-D 产物，只读）
- 🚫 `src/movietrace/feishu/`（P1-F 负责）
- 🚫 `candidates`, `match_candidates`, `baseline_items` 表 schema 或数据（只读）
- 🚫 `STATE.md`、`SCOPE.md`、`AGENTS.md`、`CLAUDE.md`、`docs/decisions/`

## 相关上下文

### 日报格式样板（来自 [`docs/product_roadmap.md`](../product_roadmap.md) § 2.4）

```markdown
# MovieTrace 每日发现日报

**生成时间：** YYYY-MM-DD HH:MM:SS  
**覆盖周期：** T-1 00:00 ~ T 23:59（UTC）  
**数据版本：** v1（Phase 1 MVP）

---

## 📊 统计汇总

| 指标 | 数值 |
|------|------|
| **新发现候选** | N_new |
| **已有基线内容** | N_existing |
| **待人工确认** | N_review |
| **总计候选** | N_total |
| **覆盖平台** | Netflix, Prime Video, Disney+, Apple TV+, HBO Max, Hulu |
| **内容类型** | 电影 M 部 / 剧集 S 部 |

---

## 🆕 新发现（is_in_baseline = False）

> 未在飞书基线中的候选，推荐人工审核后添加

### 高置信度（可直接审核）

**数量：** N_new_high

| 标题 | 发布年 | 类型 | hot_score | 平台 | 推荐理由 |
|------|--------|------|-----------|------|---------|
| Title 1 | YYYY | movie/tv_show | 85 | Netflix, Prime | FlixPatrol 排名高 + TMDb 热度 |
| ... | ... | ... | ... | ... | ... |

### 低置信度（建议有经验者审核）

**数量：** N_new_medium

| 标题 | 发布年 | 类型 | hot_score | 置信度 | 原因 |
|------|--------|------|-----------|--------|------|
| Title A | YYYY | movie | 72 | medium | title 部分交集，year ± 1 |
| ... | ... | ... | ... | ... | ... |

---

## ♻️ 已有基线内容

> is_in_baseline = True，已在飞书管理系统

**数量：** N_existing

| 标题 | 发布年 | 基线 ID | hot_score | 平台 |
|------|--------|---------|-----------|------|
| Title B | YYYY | baseline_123 | 78 | Netflix, Hulu |
| ... | ... | ... | ... | ... |

---

## ⚠️ 待人工确认

> match_confidence = low，需要经验者核对是否同一内容

**数量：** N_review

| 标题 | 发布年 | hot_score | 建议基线 | 不确定原因 | 操作 |
|------|--------|-----------|---------|-----------|------|
| Title C | YYYY | 65 | baseline_456 | title 模糊，year 偏差 2 | 确认/驳回 |
| ... | ... | ... | ... | ... | ... |

---

## 备注

- 日报基于 [`docs/requirements.md`](../../docs/requirements.md) § 10.2 hot_score 公式和 § 11.2 基线匹配规则生成
- 低置信度候选标记为"待人工确认"，不会自动写入飞书，由人工在本日报或飞书推荐表中决策
- 已有基线内容（♻️）可作为"热度变化追踪"，观察其 hot_score 趋势

```

### 分类逻辑

| 分类 | SQL WHERE | 含义 |
|------|-----------|------|
| 🆕 新发现 | `is_in_baseline = False` | 基线中无此项 |
| ♻️ 已有 | `is_in_baseline = True AND match_confidence IN ('high', 'medium')` | 基线中有，匹配置信 |
| ⚠️ 待确认 | `is_in_baseline = False AND match_confidence = 'low'` | 基线中可能有，但置信度低 |
| 📊 统计 | 上述三类统计+元数据 | 总数、平台覆盖、类型分布 |

### 平台权重和覆盖

从 P1-C hot_score 公式，平台权重：
- Netflix/Prime Video：权重 1.0
- Disney+：权重 0.9
- HBO Max：权重 0.85
- Apple TV+ / Hulu：权重 0.8

日报中统计"候选覆盖的平台列表"，取自 `candidates.platforms` 或 FlixPatrol API 响应。

## 具体要求

1. **日报生成频率与日期处理**
   - 默认生成"今天"的日报（date = today）
   - 支持命令行参数 `--date YYYY-MM-DD` 生成指定日期日报
   - 已生成的日报不覆盖；如需更新，先删除旧文件或追加版本号（YYYY-MM-DD_v2.md）
   - 所有时间使用 UTC 或本地时区，任务中明确说明

2. **内容完整性**
   - 统计汇总表包含：新发现、已有、待确认三个数字 + 总计 + 覆盖平台列表 + 内容类型分布
   - 新发现分"高置信度"和"低置信度"，分别展示
   - 已有内容按 hot_score 降序排列
   - 待确认候选列出"原因"（如 "title 编辑距离 2，year 偏差 1"）和"建议基线 ID"（如有）

3. **排序和去重**
   - 新发现按 hot_score 降序（最热的在上）
   - 已有内容按 hot_score 降序
   - 待确认按 hot_score 降序
   - 同一 canonical_item_id 在同分类中只出现一次（按 hot_score 最高取）

4. **推荐理由生成**
   - 从 P1-C score_breakdown_json 提取，简化为"主要因素"（如 "FlixPatrol 排名高" / "TMDb 热度" / "多平台覆盖"）
   - 理由为 3-5 个单词的短句，不超过 60 字符

5. **可读性格式**
   - Markdown 表格对齐、清晰
   - emoji 使用一致（🆕 新、♻️ 已有、⚠️ 待确认、📊 统计）
   - 标题层级：一级（日报名称）、二级（四个分类）、三级（子分类如"高置信度"）
   - 备注部分说明数据来源和去重规则

6. **错误处理**
   - 如 `match_candidates` 表为空，输出"暂无候选"日报
   - 如数据缺失（如 candidates.platforms = NULL），使用默认值"N/A"或跳过该列
   - 错误日志输出到 stderr，不影响日报生成

## 验收标准

1. ✅ 生成的日报文件存在且为有效 Markdown（无语法错误）
2. ✅ 统计汇总表中，新发现 + 已有 + 待确认 = 总计数
3. ✅ 新发现和已有候选数量 ≥ 10 时，表格能清晰显示（不截断）
4. ✅ 每个候选都包含必要字段：标题、发布年、hot_score、分类原因
5. ✅ 重复生成同一日期日报（非 `--date`），输出结果一致（幂等性）
6. ✅ 日报中"推荐理由"字数 ≤ 60 字符，简洁明了
7. ✅ 待确认候选的"建议基线"和"不确定原因"都有填充
8. ✅ 日报在 1 秒内生成（性能要求）
9. ✅ 全部单元测试通过

## 测试要求

### 单元测试（`tests/test_daily_report.py`）

1. **日报生成主函数**
   - 入参：match_candidates DataFrame（20 条记录）
   - 出参：Markdown 字符串，包含四个分类和统计表
   - Case：新/旧/待确认混合，各占 1/3

2. **分类逻辑**
   - 新发现：`is_in_baseline = False` 的候选都归入 🆕 or ⚠️
   - 已有：`is_in_baseline = True` 的候选都归入 ♻️
   - 待确认：`match_confidence = 'low'` 的都标记 ⚠️（即使 `is_in_baseline = False`）

3. **排序验证**
   - 新发现表中，hot_score 严格降序
   - 已有表中，hot_score 严格降序
   - 待确认表中，hot_score 严格降序

4. **统计正确性**
   - 统计汇总中，新发现数 = (is_in_baseline=False AND match_confidence != 'low') 的行数
   - 已有数 = (is_in_baseline=True) 的行数
   - 待确认数 = (match_confidence='low') 的行数
   - 总数 = 新 + 已有 + 待确认

5. **去重处理**
   - 输入同一 canonical_item_id 的两条记录（score 分别 80 和 75）
   - 预期输出只有 1 条（score 80）

6. **空表处理**
   - 输入空 DataFrame
   - 出参日报包含"暂无候选"或类似提示，不报错

7. **字段缺失**
   - 输入缺少 `platforms` 或 `reason_text` 字段
   - 预期表格中显示 "N/A" 或空值，不报错

### 回归测试

- 所有上游测试仍通过（P1-C, P1-D）

## 验证命令

```bash
# 生成今天的日报
PYTHONPATH=src python -c "
from movietrace.reports.daily_writer import generate_daily_report
from datetime import date
md = generate_daily_report(date.today())
with open(f'reports/daily/{date.today()}.md', 'w') as f:
    f.write(md)
print(f'✓ Generated reports/daily/{date.today()}.md')
"

# 验证 Markdown 格式
PYTHONPATH=src python -c "
import re
with open('reports/daily/2026-05-11.md', 'r') as f:
    content = f.read()
    assert '# MovieTrace' in content, 'Missing title'
    assert '📊 统计汇总' in content, 'Missing summary section'
    assert '|' in content, 'Missing table format'
    print('✓ Markdown format valid')
"

# 统计汇总正确性
PYTHONPATH=src python -c "
import re
with open('reports/daily/2026-05-11.md', 'r') as f:
    content = f.read()
    tables = re.findall(r'\| .*? \| .*? \|', content)
    print(f'✓ Found {len(tables)} tables')
"

# 单元测试
PYTHONPATH=src python -m pytest tests/test_daily_report.py -v

# 集成验证（与上游数据一致）
PYTHONPATH=src python -c "
import sqlite3
db = sqlite3.connect('data/movietrace.db')
c = db.cursor()
c.execute('SELECT COUNT(*) FROM match_candidates')
total = c.fetchone()[0]
print(f'✓ {total} total candidates in match_candidates')
db.close()
"
```

## 风险点

1. **日期和时区处理**
   - 预期：日报日期基于数据库中的 `created_at` 时间戳
   - 风险：如果 P1-C / P1-D 跨越两个时区边界生成，日期可能不对
   - 缓解：明确选择 UTC 或本地时区，并在日报顶部标注

2. **字段名和数据类型变化**
   - 预期：P1-D match_candidates 包含 `is_in_baseline`, `match_confidence`, `baseline_item_id` 等
   - 风险：P1-D 实施时可能调整字段名或添加新字段
   - 缓解：任务中添加字段存在性检查，缺失时报错或使用默认值

3. **候选数量可能很大**
   - 预期：首次运行 50-100 个候选，日报可读
   - 风险：如果候选数 > 500，表格可能超大
   - 缓解：任务包允许"超大日报可按分类生成多个文件"或"分页"，由实施者决策

4. **已生成日报文件覆盖问题**
   - 预期：重复生成同日期日报时，应检查文件是否已存在
   - 风险：如果直接覆盖，已有的人工审核笔记可能丢失
   - 缓解：生成前检查文件，存在时提示（不自动覆盖）；可用版本号如 _v2

5. **no_match 候选处理**
   - 预期：`match_confidence = 'no_match'` 的候选应归入"新发现"
   - 风险：如果误归为"待确认"，会增加人工工作量
   - 缓解：单元测试明确验证 no_match 分类逻辑

## 完成后输出要求

按 [`docs/workflow/report-format.md`](../workflow/report-format.md) 格式汇报。

**汇报要点：**
- 生成的日报样本（YYYY-MM-DD.md 内容截图或摘要）
- 四分类统计分布（新/已有/待确认各多少）
- 日报生成耗时（秒数）
- 单元测试覆盖率
- 任何日期处理或字段映射的调整
