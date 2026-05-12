# 任务包：SUP-C FlixPatrol × TMDb 匹配率验证

**任务包版本：** v1  
**创建日期：** 2026-05-10  
**完成日期：** 2026-05-10

---

## 任务名称

SUP-C：FlixPatrol 内容与 TMDb 匹配率验证

## 任务类型

`verify` — 验证任务（含匹配脚本实现）

## 当前阶段

Phase 0+（FlixPatrol 接入验证）

## 来源任务

- `docs/phase0_supplement.md` § 任务 SUP-C
- SUP-B 已完成：`data/flixpatrol_parsed_items.json` 就绪（130 条，118 个去重条目）

## 目标

回答一个问题：FlixPatrol Top-10 内容能否以 ≥ 80% 的比例匹配到 TMDb ID？

## 非目标

- ❌ 不写入数据库
- ❌ 不实现完整匹配 pipeline
- ❌ 不做跨源（OMDb/Trakt）联合匹配
- ❌ 不评估合规性（SUP-D）

## 允许修改范围

- 新增 `scripts/sup_c_flixpatrol_matching.py`
- 新增 `tests/test_sup_c_matching.py`
- 新增 `data/sup_c_match_results.json`（运行时写入，data/ 在 .gitignore 中）
- 新增 `reports/flixpatrol_matching_report.md`
- 新增 `docs/tasks/sup_c_flixpatrol_matching.md`（本文件）

## 禁止修改范围

- 🚫 `src/movietrace/pipeline/`
- 🚫 `src/movietrace/sources/`
- 🚫 `data/movietrace.db`
- 🚫 `tests/fixtures/`
- 🚫 `AGENTS.md`、`CLAUDE.md`

## 验收标准

1. ✅ `pytest tests/test_sup_c_matching.py -v` 全部通过（14 passed）
2. ✅ 脚本读取 `/tmp/movietrace_phase0_secrets.json` 获取 TMDb token
3. ✅ 高/中置信度匹配率 ≥ 80%（实际：118/118 = 100%）
4. ✅ `reports/flixpatrol_matching_report.md` 包含全部6节

## 验证命令

```bash
PYTHONPATH=src python -m pytest tests/test_sup_c_matching.py -v
PYTHONPATH=src python scripts/sup_c_flixpatrol_matching.py
```

## 实际验证结果

- pytest：14 passed / 0 failed
- 匹配率：**118/118 = 100%**（全部 high 置信度，similarity = 1.0）
- 结论：✅ 强烈建议进入 P1-B
