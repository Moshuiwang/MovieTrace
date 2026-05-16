# ADR-0014: 翻转后遗留 Schema 清理（Migration 016）

**状态**: 已接受  
**日期**: 2026-05-16  
**任务包**: P1.21.7

---

## 背景

ADR-0007（系统重定位）将系统从"推荐+审核"翻转为"更新追踪+中间表"。翻转后，
以下六张表的写路径在任何活跃 CLI 或调度脚本中均已无调用：

| 表名 | 用途（翻转前）| 状态 |
|------|------------|------|
| `feishu_import_runs` | 飞书导入批次记录 | 死表 |
| `source_records` | 原始导入行 | 死表 |
| `baseline_items` | 飞书基线条目 | 死表 |
| `candidates` | 发现候选 | 死表 |
| `candidate_matches` | 候选匹配结果 | 死表 |
| `match_candidates` | 实体匹配候选 | 死表（FK 依赖 baseline_items）|

相关死代码模块（在 P1.21.7 之前已有部分删除，本任务补全）：

- `baseline_import.py` — 无 CLI 调用  
- `baseline_matching.py` — 无 CLI 调用  
- `canonical_promotion.py` — 无 CLI 调用  
- `daily_writer.py` — 无 CLI 调用  

---

## 决策

1. **Migration 016** (`016_drop_legacy_tables.sql`) 以 `DROP TABLE IF EXISTS` 删除上述六张死表。
2. 同步从 `SCHEMA_SQL` 中删除这些表的 `CREATE TABLE` 语句，防止新实例误创建。
3. 删除对应死代码模块（`baseline_import.py`、`baseline_matching.py`、`canonical_promotion.py`、`daily_writer.py`）。
4. 删除引用死表的测试文件及测试方法（`test_baseline_import.py` 等五个文件，`test_entity_matching.py` 中三个方法）。
5. 修复 `cli.py` 的 `inspect-baseline` 命令，移除对 `baseline_items` 的查询。

**保留**：
- `entity_matching.py`（`baseline_quality_issues` 仍由此模块写入，独立无 FK 依赖）
- `baseline_quality_issues` 表（由 `entity_matching.py` 在运行时按需创建，不纳入 `initialize_database`）

---

## 后果

- `initialize_database()` 在新实例上不再创建死表，schema 干净。
- 现有生产数据库通过 migration 016 自动迁移（`DROP IF EXISTS` 幂等安全）。
- 测试套件通过数量从 519 降至 400（删除了覆盖死代码的测试），无虚假测试覆盖。
- `inspect-baseline` 命令不再显示 `baseline_items` 统计行。
- `baseline_quality_issues` 不在 `initialize_database` 的断言范围内（由 entity_matching 按需建表）。

---

## 风险

低。`DROP IF EXISTS` 在表不存在时幂等；生产数据库在这些表上无活跃写路径，
删除不影响任何运行中功能。
