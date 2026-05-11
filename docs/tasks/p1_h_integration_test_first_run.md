# 任务包：P1-H 集成测试 + 首次实际运行

**任务包版本：** v1
**创建日期：** 2026-05-11
**预计完成：** TBD（依赖 P1-G 完成）

---

## 任务名称

P1-H：编写端到端集成测试，模拟完整日发现流水线，执行首次实际运行（dry-run），生成 Phase 1 整体验收报告

## 任务类型

`test` — 测试和验收

## 当前阶段

Phase 1（V1 MVP 开发）

## 执行环境

- **分支：** `main`（当前 working tree，不开 git worktree）
- **工作目录：** `/home/ubuntu/MovieTrace`
- **commit 策略：** 完成后准备 commit，不要 push
- **测试数据：** 使用真实的 Phase 0 数据（FlixPatrol API 响应、TMDb 数据、飞书基线）或允许生成合成数据（任务包中说明策略）

## 来源任务

- [`docs/next_steps_plan.md`](../next_steps_plan.md) § 5.3 Phase 1 验收
- **前置：** P1-B 到 P1-G 全部完成
- **9 项整体验收清单：** 见 next_steps_plan.md

## 目标

构建端到端集成测试（模拟从 FlixPatrol 数据到飞书推荐的完整流程），执行 dry-run，验证 Phase 1 实现的 9 项功能完整性，生成整体验收报告（含通过率、风险记录、迭代建议）。

## 非目标

- ❌ 不修改 P1-B ~ P1-G 的实现代码（只测试）
- ❌ 不写新的单元测试（P1-B ~ P1-G 已有）
- ❌ 不做性能优化（仅验收，不优化）
- ❌ 不修改 schema 或数据结构
- ❌ 不引入新依赖

## 允许修改范围

**新增文件：**

- `tests/integration/test_daily_discover_pipeline.py`
- `reports/phase1_completion_report.md`

**修改文件：**

- （无需修改源代码或 schema）

## 禁止修改范围

- 🚫 `src/movietrace/pipeline/`（P1-B ~ P1-F，只调用）
- 🚫 `src/movietrace/feishu/`
- 🚫 `src/movietrace/cli.py`（只调用）
- 🚫 所有 schema 和表定义
- 🚫 `STATE.md`、`SCOPE.md`、`AGENTS.md`、`CLAUDE.md`、`docs/decisions/`

## 相关上下文

### Phase 1 整体 9 项验收清单（来自 [`docs/next_steps_plan.md`](../next_steps_plan.md) § 5.3）

| # | 功能 | 验收标准 | 来源 |
|---|------|--------|------|
| 1 | P1-B FlixPatrol API 数据接入 | flixpatrol_top10 表有 ≥ 60 条 6 平台热度数据 | P1-B |
| 2 | P1-C hot_score 评分公式 | 9 因素加权，候选 hot_score 分布合理（P0:P1:P2:P3 ≈ 10:25:40:25） | P1-C |
| 3 | P1-D 基线匹配 | ≥ 90% 候选被正确分类（新/已有/待确认） | P1-D |
| 4 | P1-E 日报生成 | 日报包含 4 类分组、统计汇总、推荐理由、超链接 | P1-E |
| 5 | P1-F 飞书写入 + 去重 | 重复运行不重复写入（按 content_update_id），人工字段保护 ✓ | P1-F |
| 6 | P1-G CLI 命令 | 4 条命令可执行，`--help` 清晰，dry-run 模式可用 | P1-G |
| 7 | 端到端流水线 | daily-discover 从 FlixPatrol 到飞书，无错误 | P1-B~P1-F |
| 8 | 人工审核认可率 | 抽查 50 条候选，认可率 ≥ 60%（可接纳） | 产品 |
| 9 | 文档完整性 | 每个任务包字段完备，验收命令可运行 | P1-B~P1-G |

### 测试数据策略

**选项 A：真实数据**
- 使用 Phase 0 验证时的真实 FlixPatrol API 响应（data/sup_g_api_responses/*.json）
- 从飞书实际导出基线数据（baseline_items 表）
- 优点：高保真，发现真实问题
- 缺点：依赖外部服务，测试不稳定，可能受 API 配额限制

**选项 B：合成数据**
- FlixPatrol 数据：生成 60 条合成热度记录（6 平台 × 10 标题）
- baseline_items：生成 1000 条合成基线（随机标题、年份）
- canonical_items：生成 100 条合成电影/剧集
- 优点：快速、稳定、无网络依赖
- 缺点：可能遗漏真实数据的边界情况

**建议：** 集成测试用合成数据（快速迭代），首次实际运行（验收）用真实数据。

### 集成测试流程

```
Setup Phase:
  1. 初始化临时 SQLite DB
  2. 插入测试数据（FlixPatrol、canonical、baseline）
  
P1-B 验证：
  3. 检查 flixpatrol_top10 表存在，≥ 60 行
  
P1-C 验证：
  4. 调用 scoring.py，生成 candidates 表
  5. 检查 hot_score 分布（P0:P1:P2:P3 比例）
  
P1-D 验证：
  6. 调用 baseline_matching.py，生成 match_candidates 表
  7. 人工抽查 10 行（验证 is_in_baseline 和 match_confidence 正确）
  
P1-E 验证：
  8. 调用 daily_writer.py，生成日报 Markdown
  9. 检查日报格式（4 分类、统计表、字段完整）
  
P1-F 验证 (dry-run)：
  10. 调用 recommendation_writer.py（dry_run=True）
  11. 检查审计日志生成（source_records/YYYY-MM-DD.jsonl）
  
P1-G 验证：
  12. 调用 CLI 命令 daily-discover --dry-run
  13. 检查输出和退出码
  
Teardown Phase:
  14. 清理临时 DB 和日志
  15. 生成集成测试报告
```

### 首次实际运行（验收步骤）

```
1. 使用真实 FlixPatrol API 数据或 Phase 0 缓存数据（据可用性）
2. 运行 movietrace daily-discover --dry-run（不写飞书）
3. 审查生成的日报（reports/daily/YYYY-MM-DD.md）
4. 人工抽查 50 条候选，评估"可接纳"（hot_score 高、排名合理、无重复）
5. 记录认可率、不认可的候选及改进建议
6. 生成 Phase 1 完成报告（reports/phase1_completion_report.md）
```

## 具体要求

### 集成测试（`tests/integration/test_daily_discover_pipeline.py`）

1. **测试类结构**
   - `TestDailyDiscoverPipeline`：端到端流水线测试
   - `setUp()` / `tearDown()` 管理临时 DB 和数据
   - 每个 P1-X 模块一个 test_* 方法

2. **P1-B 数据验证**
   - 插入合成 FlixPatrol 数据到 `flixpatrol_top10` 表
   - 检查：行数 ≥ 60，字段完整（title, release_year, platforms, rank, source 等）

3. **P1-C 评分验证**
   ```python
   # 伪代码
   candidates = scoring.generate_candidates(flixpatrol_data, canonical_items, external_ids)
   assert len(candidates) >= 50, "At least 50 candidates"
   scores = candidates['hot_score'].values
   assert all(0 <= s <= 100 for s in scores), "Scores in [0, 100]"
   
   # 检查 priority 分布
   p0_ratio = (candidates['priority'] == 'P0').sum() / len(candidates)
   p1_ratio = (candidates['priority'] == 'P1').sum() / len(candidates)
   # 预期：P0 ~10%，P1 ~25%，P2 ~40%，P3 ~25%
   assert 0.05 < p0_ratio < 0.15, f"P0 ratio {p0_ratio} out of range"
   ```

4. **P1-D 匹配验证**
   ```python
   matches = baseline_matching.match_candidates(candidates, baseline_items)
   assert len(matches) == len(candidates), "All candidates matched"
   
   # 抽查 high-confidence 匹配
   high_conf = matches[matches['match_confidence'] == 'high']
   for idx in high_conf.sample(min(10, len(high_conf))).index:
       # 人工确认（或自动验证，如已标注）
       pass
   ```

5. **P1-E 日报验证**
   ```python
   report = daily_writer.generate_report(matches)
   assert '# MovieTrace' in report, "Title present"
   assert '📊 统计汇总' in report, "Summary section"
   assert '🆕 新发现' in report or '♻️ 已有' in report, "Categorization"
   
   # 检查表格格式
   assert '|' in report, "Tables present"
   lines = report.split('\n')
   assert len(lines) > 50, "Report has substantial content"
   ```

6. **P1-F 写入验证（dry-run）**
   ```python
   result = recommendation_writer.write_recommendations(
       matches, feishu_api=mock_feishu, dry_run=True
   )
   assert result['dry_run'] == True, "Dry-run mode"
   assert len(result['audit_log']) == len(matches), "All candidates logged"
   assert result['http_calls'] == 0, "No actual API calls"
   ```

7. **P1-G CLI 验证**
   ```python
   # 模拟 CLI 命令
   from src.movietrace.cli import main
   exit_code = main(['daily-discover', '--dry-run'])
   assert exit_code == 0, "Exit code OK"
   
   # 检查输出文件
   assert Path('reports/daily/2026-05-11.md').exists(), "Report generated"
   assert Path('source_records/2026-05-11.jsonl').exists(), "Audit log generated"
   ```

### 首次实际运行验收（手动步骤，文档化在报告中）

1. **数据准备**
   - 确认 FlixPatrol API 数据已导入（P1-B）
   - 确认基线数据已导出（Phase 0）
   - 确认飞书表 schema 完整

2. **运行 dry-run**
   ```bash
   movietrace daily-discover --dry-run --date 2026-05-11
   ```

3. **审查日报**
   - 打开 reports/daily/2026-05-11.md
   - 检查 4 分类内容数（新/已有/待确认/总计）
   - 抽查推荐理由的合理性

4. **人工认可率评估**
   - 从日报中随机抽取 50 条候选
   - 逐条评估：title 是否真实、hot_score 是否合理、平台组合是否合理
   - 记录：认可数 / 50，不认可原因（如虚假标题、排名异常等）
   - 预期：≥ 30 条认可（60%）

5. **生成完成报告**
   - 输出到 reports/phase1_completion_report.md
   - 包含：9 项验收结果、抽查数据、改进建议、后续行动

## 验收标准

1. ✅ 集成测试可执行：`pytest tests/integration/test_daily_discover_pipeline.py -v` 全部通过
2. ✅ P1-B 数据验证：flixpatrol_top10 ≥ 60 行，字段完整
3. ✅ P1-C 评分：candidates 表 ≥ 50 行，hot_score ∈ [0,100]，priority 分布合理
4. ✅ P1-D 匹配：match_candidates 行数 = candidates 行数，≥ 90% 分类正确
5. ✅ P1-E 日报：格式合法，4 分类完整，统计数字准确（新 + 已有 + 待确认 = 总计）
6. ✅ P1-F 写入：dry-run 模式无 API 调用，审计日志格式正确
7. ✅ P1-G CLI：4 条命令可执行，--help 清晰，daily-discover --dry-run 成功
8. ✅ 端到端运行：`movietrace daily-discover --dry-run` 完成，无错误
9. ✅ 人工认可率 ≥ 60%：50 条候选抽查，≥ 30 条认可
10. ✅ Phase 1 完成报告生成，9 项验收结果清晰，改进建议可行

## 测试要求

### 集成测试

- `tests/integration/test_daily_discover_pipeline.py`
  - 7 个 test_* 方法（P1-B 到 P1-G 各一个）
  - 每个测试 < 5 秒完成
  - 使用合成数据（无网络依赖）
  - 覆盖主路径和至少 1 个错误路径（如缺失数据）

### 回归测试

- 全部 P1-B ~ P1-G 单元测试仍通过
- 命令：`pytest tests/ -v` (包括 integration/)

## 验证命令

```bash
# 集成测试
PYTHONPATH=src python -m pytest tests/integration/test_daily_discover_pipeline.py -v

# 全量测试（包含单元和集成）
PYTHONPATH=src python -m pytest tests/ -v

# 首次实际运行（dry-run）
PYTHONPATH=src python -m movietrace daily-discover --dry-run --date 2026-05-11

# 验证生成的文件
ls -lh reports/daily/2026-05-11.md
ls -lh source_records/2026-05-11.jsonl
head reports/daily/2026-05-11.md

# 检查日报内容
PYTHONPATH=src python -c "
with open('reports/daily/2026-05-11.md', 'r') as f:
    content = f.read()
    assert '📊 统计汇总' in content
    assert '🆕 新发现' in content or '♻️ 已有' in content
    print('✓ Report format valid')
"

# 生成 Phase 1 完成报告
PYTHONPATH=src python -c "
from movietrace.reports.phase1_completion import generate_completion_report
report = generate_completion_report(
    integration_test_pass=True,
    manual_review_pass=True,
    acceptance_rate=0.75
)
with open('reports/phase1_completion_report.md', 'w') as f:
    f.write(report)
print('✓ Completion report generated')
"
```

## 风险点

1. **集成测试数据与真实数据差异**
   - 预期：合成数据能代表真实分布（热度、基线匹配率等）
   - 风险：合成数据过于理想化，真实运行时可能出现边界情况
   - 缓解：首次实际运行时用真实数据，记录差异并迭代评分权重

2. **人工认可率可能达不到 60%**
   - 预期：产品认可至少 60% 的候选
   - 风险：hot_score 公式权重不当，导致质量不足
   - 缓解：任务包允许"认可率未达 60% 时，记录原因并迭代权重"，后续在 P1-I 跟进

3. **飞书表 schema 变化**
   - 预期：飞书推荐表与文档一致
   - 风险：人工修改了飞书表结构，导致 P1-F 写入失败
   - 缓解：P1-H 前先运行 `movietrace check-feishu-schema`，确保 schema 匹配

4. **测试数据库冲突**
   - 预期：集成测试用临时 DB，不影响生产
   - 风险：测试代码误删或误改生产数据
   - 缓解：集成测试独占 DB 文件路径（如 `/tmp/test_movietrace.db`），test teardown 中清理

5. **首次实际运行时间过长**
   - 预期：dry-run 完成耗时 < 1 分钟
   - 风险：如 FlixPatrol 数据很大（100+），匹配和评分可能变慢
   - 缓解：记录实际耗时，如超 1 分钟则标注为性能优化 TODO

## 完成后输出要求

按 [`docs/workflow/report-format.md`](../workflow/report-format.md) 格式汇报。

**汇报要点：**
- 集成测试覆盖的场景和通过状态
- 9 项验收清单逐项验证结果（✓ 或 ✗）
- 首次实际运行的日期、候选总数、各分类数量
- 人工抽查 50 条：认可数、不认可原因（按频率排序）
- Phase 1 完成报告（生成路径和主要结论）
- 已知风险和迭代建议（如权重调优、新增候选源等）
- 后续 P1-I（可选迭代）的优先级和预期收益

---

## 附录：Phase 1 MVP 定义（来自 [`docs/next_steps_plan.md`](../next_steps_plan.md)）

Phase 1 目标：完整的日发现流水线原型，支持人工决策前的自动化处理。

**入口：** FlixPatrol 付费 API（6 平台，日更 12 调用）
**出口：** 飞书推荐表（筛选后的候选，待人工审核）
**验证：** 端到端运行，dry-run 模式无误

**不在 Phase 1 范围：**
- ❌ 多轮迭代和权重优化（P1-I 后续）
- ❌ 历史追踪和趋势分析（V2）
- ❌ 推荐表的人工审核 UI（飞书原生 UI）
- ❌ 其他数据源集成（V2）

**预计完成时间：** 5-7 个 Agent 迭代（每个 2-4 小时）
