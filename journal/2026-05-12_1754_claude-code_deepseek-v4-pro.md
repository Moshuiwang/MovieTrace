# Agent 身份卡

- **工具：** Claude Code（VSCode 插件）
- **模型：** DeepSeek V4 Pro
- **会话时间：** 2026-05-12 16:40 +08 ~ 17:54 +08
- **起止 commit：** `f48d095` →（待本次 commit）
- **运行环境：** Python 3.12 + `.venv/` + Linux

---

# 今日工作主线

## 1. A 库（生产环境 DB）数据接入

**触发：** 用户从生产 DB 导出两张 CSV（节目数据 735 行 + 子节目数据 6,562 行），放到项目根目录
**完成：**
- CSV 归位 → `source_records/`（.gitignore 已排除）
- 写验证脚本 `scripts/verify_source_db.py`，完整分析两张表的结构和关联
- Migration 005 建 `upstream_programs` / `upstream_episodes` 表
- 写导入脚本 `scripts/import_upstream_data.py`，735 + 6,562 行全部入库
- Schema 参考文档 `reports/upstream_db_schema_reference.md`（含字段含义 + 对本项目的意义分级 🔴/🟡/⚪）
**关键发现：**
- `imdb_id` 全空（匹配只能走名称搜索）
- `program_status` 不可靠（剧集季也标 MOVIE）
- `delete_flag` 全为 1，无意义
- `modify_instant` 是增量更新的核心信号
- A 库扁平两层（节目季级 → 子节目集级），无 Series 概念

## 2. 架构决策：飞书从系统链路移除

**触发：** A 库接入后，飞书"内容目录来源"和"输出渠道"两个角色都被取代
**决策：**
- 飞书不再是内容目录来源（被 A 库取代）
- 飞书不再是输出渠道（被日报 MD + JSON 导出取代）
- P1.5-E（飞书写入翻新）整包砍掉
- P1.5-F/G 合并为一个任务包
- `feishu_import_runs` / `source_records` / `baseline_items` 表保留不动（历史记录）

## 3. P1.5 全部任务包重写/新建

**触发：** A 库数据 + 飞书移除改变了整个 P1.5 的任务依赖链
**完成：** 5 个可执行任务包全部就绪：

| 任务包 | 文件 | 状态 |
|--------|------|------|
| P1.5-B | `p1.5_b_schema_v6_migration.md` | 新建（v2 重写） |
| P1.5-E | `p1.5_e_entity_matching_full.md` | 新建 v1 |
| P1.5-C | `p1.5_c_virtual_series_backfill.md` | 更新（v2 重写，Q5 已定） |
| P1.5-D | `p1.5_d_baseline_active_tracking.md` | 更新（v2 重写，Q6-Q8 已定） |
| P1.5-F | `p1.5_f_report_cli_export.md` | 新建 v1（合并原 F+G） |

执行顺序：B → E → C → D → F

## 4. STATE.md 全量刷新

反映上述所有变更：Phase 1.5 新任务链、A 库数据画像、4 个关键决策记录、清除阻塞项。

---

# 关键决策记录

1. **A 库 = 新基线** — upstream_programs/episodes 是 MovieTrace 的内容目录权威来源
2. **飞书全链路移除** — 内容目录（入）+ 输出渠道（出）都不再用飞书
3. **Q5-Q8 全部解定** — A 库 schema 明确后，P1.5-C/D 的 4 个暂停问题都有了答案
4. **新增 P1.5-E（实体全量匹配）** — canonical_items 基于 A 库全量重建，填补原 P1.5 链路缺口
5. **Migration 编号调整** — 005=A库表（已执行），006=virtual_series（P1.5-B）

---

# 当前项目状态快照

- **Phase 1.5 进度：** A ✅ / B 📝 / E 📝 / C 📝 / D 📝 / F 📝
- **阻塞项：** 无
- **待用户决策：** 无
- **无活跃编码任务**（全量任务包已发布，待其他 Agent 领取执行）

---

# 给下一个 AI Agent 的交接

- **可接任务：** P1.5-B（schema v6 migration），按 STATE.md 中的执行顺序 B→E→C→D→F
- **不要重做的事：** 不要再从飞书读基线数据；不要再写飞书输出
- **容易被忽略的知识：**
  - Migration 005 已被 A 库占用；P1.5-B 用 006
  - A 库 schema 参考在 `reports/upstream_db_schema_reference.md`
  - `upstream_programs.online_flag` 过滤 + `modify_instant` 增量更新 是核心操作模式
  - `program_status` / `delete_flag` 不可靠，不要依赖
  - 旧 P1.5-B 文件（`p1.5_b_schema_extension_and_migration.md`）是 v1 版，任务执行应使用新 v2 版（`p1.5_b_schema_v6_migration.md`）

---

# 数字总结

- **commit 数：** 待提交（本次改动 ~15 个文件）
- **修改文件数：** ~6 修改 + ~9 新增
- **DB 表新增：** 2（upstream_programs + upstream_episodes，migration 005 已执行）
- **测试用例数变化：** 不变（284，本次无代码改动，仅文档/脚本/迁移）
- **任务包：** 5 个可执行（B/E/C/D/F），1 个砍掉（原 E）
- **成本统计：** ~1 小时 15 分钟 | Token 消耗：未记录（会话进行中）
