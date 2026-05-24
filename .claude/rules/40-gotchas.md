---
name: gotchas
description: MovieTrace 项目最易踩的坑速查（PYTHONPATH）。
paths:
  - "src/**"
  - "scripts/**"
  - "tests/**"
---

# 易踩坑速查

## `PYTHONPATH=src` 必带

src layout 项目。运行测试 / 脚本 / CLI 必须带：

```bash
PYTHONPATH=src python -m movietrace.cli daily-discover --dry-run
PYTHONPATH=src python -m pytest tests/ -v
```

缺少会报 `ModuleNotFoundError: No module named 'movietrace'`。

## 写跨表 SQL 前必读 schema 地图

涉及 `canonical_items` / `external_ids` / `virtual_series` / `current_discovery_items` / `discovery_observations` / `content_updates` 等核心业务表的查询、JOIN、唯一约束、级联前，**必读** [`24-db-schema-map.md`](24-db-schema-map.md)。

schema 不在 boot order 自动加载；凭记忆写易：拼错字段名 / 漏 UNIQUE 索引 / 误引用 migration 016 已 DROP 的 5 张遗留表（`feishu_import_runs` · `source_records` · `baseline_items` · `candidates` · `candidate_matches` · `match_candidates`）。
