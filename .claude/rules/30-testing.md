---
name: testing
description: 测试命名规则、PYTHONPATH=src 要求、测试失败处置、回归测试要求、可选依赖处理。
include: ["tests/**"]
---

# 测试规则

## 运行命令

```bash
PYTHONPATH=src python -m pytest tests/ -v          # 全量
PYTHONPATH=src python -m pytest tests/test_X.py -v # 单文件
PYTHONPATH=src python -m pytest -k "<pattern>"     # 关键词
```

**`PYTHONPATH=src` 必带**——src layout，缺少会报 `ModuleNotFoundError: No module named 'movietrace'`。

## 测试命名

- 按行为命名：`test_scoring.py` / `test_deduplication.py` / `test_baseline_tracking.py`
- 不按"实现"命名（如 `test_database_helper.py`）
- 单测函数 `test_<行为>_<期望结果>`（如 `test_compute_gaps_excludes_a_lib_zero`）

## 失败处置（与 [`10-validation.md`](10-validation.md) 联动）

- ❌ 不允许：删测试以"修复"问题
- ❌ 不允许：测试失败状态下继续开发新功能
- ✅ 必须：先报现象 → 已排除 → 下一步定位
- ✅ 必须：修复仅限当前任务范围

## 回归测试要求

- Bug 修复必须补充或更新测试，证明回归被覆盖
- 核心功能必须有测试**或**明确的人工验证步骤
- 新功能 PR 必须列出"测试用例数变化"（journal-spec 要求）

## bs4 / 可选依赖处理

- `test_flixpatrol_parsing.py` 依赖 `bs4`，若未装则用 `--ignore=tests/test_flixpatrol_parsing.py` 跳过
- 不要在 `conftest.py` 里硬装 bs4，保持可选

## Mock 与真实库

- 单元测试用 in-memory SQLite 或临时 `data/test_*.db`
- 严禁直接读写真实库 `data/movietrace.db`
- 飞书 / TMDb / Trakt / OMDb 等外部调用必须 mock；真实 smoke 仅由 `scripts/*` 调度
