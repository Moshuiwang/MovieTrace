---
name: gotchas
description: MovieTrace 项目最易踩的坑速查（PYTHONPATH）。
include: ["**/*"]
---

# 易踩坑速查

## `PYTHONPATH=src` 必带

src layout 项目。运行测试 / 脚本 / CLI 必须带：

```bash
PYTHONPATH=src python -m movietrace.cli daily-discover --dry-run
PYTHONPATH=src python -m pytest tests/ -v
```

缺少会报 `ModuleNotFoundError: No module named 'movietrace'`。
