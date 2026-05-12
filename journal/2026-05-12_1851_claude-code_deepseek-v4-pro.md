# Agent 身份卡

- **工具：** Claude Code（VSCode 插件）
- **模型：** DeepSeek V4 Pro
- **会话时间：** 2026-05-12 16:50 +08 ~ 18:51 +08
- **起止 commit：** `4290624` →（待本次 commit）
- **运行环境：** Python 3.12 + `.venv/` + Linux

---

# 今日工作主线

## P1.5 全量任务包串行执行（B → E → C → D → F）

本次会话按 STATE.md 中的执行顺序，完成了 Phase 1.5 全部 5 个已发布任务包。

### P1.5-B: Schema v6 Migration ✅
- Migration 006 新建 `virtual_series` 表 + `canonical_items.virtual_series_id` + `content_updates.match_confidence_low`
- `SCHEMA_VERSION` 5→6，生产 DB 已执行
- 测试：+6 用例 → 290 total

### P1.5-E: A库全量实体匹配 ✅
- `match_upstream_program()` 新增到 entity_matching.py
- 全量匹配脚本 `scripts/p1.5_e_match_all.py`（--dry-run / --limit / --db）
- `baseline_quality_issues` 表动态创建
- 测试：+5 用例 → 295 total

### P1.5-C: virtual_series 一次性回填 ✅
- 新建 `virtual_series.py` 模块（derive_poll_priority / upsert / link / extract_season_number）
- `TmdbDetailClient` 新增到 tmdb.py
- 回填脚本 `scripts/p1_5_c_backfill_virtual_series.py`
- 修复：`find_or_create_virtual_series_for_canonical_item` 增加从 canonical_item_key 提取 tmdb_id 的回退路径（解决 external_ids 唯一索引导致的同剧多季 ID 丢失）
- 测试：+13 用例 → 308 total

### P1.5-D: 基线主动追踪模块 ✅
- 新建 `poll_scheduler.py`（分层 quota + daily_max_calls 硬上限）
- 新建 `baseline_tracking.py`（detect → write → update 全流程）
- CLI 新增 `baseline-track` 子命令
- `daily-discover` 增加 step 5（基线追踪）
- `config.yaml` 新建（baseline_tracking 配置）
- 修复：content_updates 去重逻辑使用 `INSERT OR IGNORE` + `total_changes`
- 测试：+14 用例 → 322 total

### P1.5-F: 日报模板 + CLI 语义 + 导出 ✅
- daily_writer.py 新增 `_section_new_seasons`（基线新季）
- 新建 `export_writer.py`（MD + JSON 导出）
- CLI 新增 `export-recommendations` 子命令
- `daily-discover` 移除飞书写入步骤
- 测试：+4 用例 → 326 total

---

# 关键决策记录

1. **external_ids 多季同 ID 冲突** — 同剧多季共享 tmdb_tv_id，`external_ids(source, external_id)` 唯一索引导致第二个以后季的 tmdb external_id 行被 `INSERT OR IGNORE` 丢弃。P1.5-C 解决方式：fallback 从 `canonical_item_key`（格式 `tmdb:tv:{id}:season:{n}`）提取 tmdb_id。

2. **content_updates 去重** — 利用已有 `ux_content_updates_item_type(canonical_item_id, update_type)` 复合唯一索引，写入使用 `INSERT OR IGNORE`，配合 `conn.total_changes` 计数。

3. **基线追踪与 discovery 解耦** — `run_baseline_tracking` 不嵌入 `run_discovery`，由 CLI `daily-discover` 作为独立 step 5 调用，确保无 FP 数据时追踪仍可运行。

---

# 当前项目状态快照

- **Phase 1.5 进度：** A ✅ / B ✅ / E ✅ / C ✅ / D ✅ / F ✅（全部完成）
- **阻塞项：** 无
- **待用户决策：** 无
- **下一阶段：** Phase 1.6（首次真实运行 + 验收）

---

# 数字总结

- **commit 数：** 待提交（本次改动 ~20 个文件）
- **新增文件：** 16（3 migration + 6 模块/脚本 + 7 测试）
- **修改文件：** 5（schema.py, entity_matching.py, tmdb.py, discovery.py, cli.py, daily_writer.py）
- **测试用例数：** 284 → 326（+42）
- **全部测试：** 326 passed
- **任务包执行：** 5/5 完成
- **成本统计：** ~2 小时 10 分钟 | Token：未记录（会话进行中）
