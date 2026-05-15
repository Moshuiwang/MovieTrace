# 工作日报 2026-05-16（凌晨延续会话）

## Agent 身份卡

| 字段 | 值 |
|------|----|
| 工具 | Claude Code（CLI） |
| 模型 | Claude Opus 4.7（编排）+ Sonnet 4.6（5 个子代理） |
| 模型 ID | claude-opus-4-7（主）+ claude-sonnet-4-6（subagent） |
| 运行环境 | Linux CLI（bash workspace） |
| 会话起止 | 2026-05-16 01:15 +08 ～ 04:00 +08 |
| 起始 commit | d2352ae |
| 结束 commit | 待提交（本日报后） |

---

## 今日主线

### 一、Feishu 同步质量修正（早会话 sonnet 段）

- **修复 UTC 时区 bug**：`sync.py:_to_epoch_ms` 加 `tz` 参数；`detected_at` 用 `event_written_at_utc` + `tz=_UTC` 解析（修了 8 小时偏差）
- **新增 `_extract_tmdb_id` fallback**：从 `discovery:{tv|movie}:{id}:date` 格式 ID 中提取，弥补 movie 类 virtual_series JOIN 缺失
- 提交 `51f033d`

### 二、TMDb ID 统一 + new_discovery 季号 + A 库最新季字段（早会话 sonnet 段）

- 飞书字段重命名 `TMDb TV ID → TMDb ID`（fldP8KPqVk）
- 新建飞书字段 `A库最新季`（fld1f3gP2r）
- new_discovery 的 `season=0` 改为从 `tmdb_number_of_seasons`（virtual_series 或 api_cache）填充
- export_writer.py 新增 SQL 聚合 upstream_max_season
- 提交 `3af1a15`

### 三、冒烟测试两次（用户验证）

- `bash scripts/daily_run.sh`：433s 运行，75 条 new_discovery 写入，飞书 doc 同步失败（lark-cli v1 API deprecated + field validation；非阻塞）；其他全部成功
- `bash scripts/baseline_run.sh`：271s 运行，detected=0（local_max_season 已追平），暴露 baseline 数据丢失问题

### 四、数据丢失溯源（用户驱动调查）

- 现象：current DB 里 `new_season` 表 = 0 条，但 STATE.md 写着 151 条
- 溯源：journal/2026-05-15_1045 记录"清扫 151 条旧 new_season 记录，重新 catch-up 全量 272 条" → 第二次 catch-up 跑出 detected=0（因为 `local_max_season` 早被第一次 catch-up 推到 TMDb 最新值，没有回滚）
- **本质**：`virtual_series.local_max_season` 是 baseline-track 的水位线状态字段，独立于 content_updates 事件日志；清扫日志不会回滚水位线
- **结论**：当前 DB 状态本身正确（local_max_season 是真相），但事件历史空了一段；今天 baseline 表里 0 条是数学正确

### 五、关键性架构决策：状态快照子表（P1.21）

用户判断：飞书多维表格的核心价值是"现在 A 库缺哪些季"，不是"事件历史回看"。事件日志驱动的展现层昨日已证不可靠。

决策（最终）：
- 新增子表 "**A 库缺口**"（`tbl1NNU8kmlLKpLm`）
- 行粒度：1 行 = 1 virtual_series；upsert by TMDb ID
- 数据源：**`virtual_series + canonical_items + api_cache` 直接算，不读 content_updates**
- 范围：season-level；表结构预留 episode（"缺口类型"/"缺口集"字段）
- 状态字段：人工标 `待补/部分补充/已补/跳过`，系统提示 `建议已补`（缺口数=0 时）
- 筛选：`poll_priority != 'skip'` AND `A 库 max < TMDb last_episode_to_air.season_number`

用户其他决策：
- 重置一次 local_max_season + catch-up 冒烟（验证管道完整性）
- 清空"热点发现"子表当前 80 条（有 bug 残留），重填
- 全自动运行（用户睡前），review 后修复，最后留报告

### 六、自主运行（深夜段）：实施 + Review + Fix

**Phase A — 实施（sonnet agent）**
1. 备份 DB → `data/movietrace_backup_20260516_0326_pre_p121.db`
2. 写 ADR-0013 `docs/decisions/0013-baseline-gap-snapshot-table.md`
3. 写任务包 P1.21 `docs/tasks/p1.21_a_lib_gap_snapshot_table.md`
4. Feishu API 建子表"A 库缺口"（14 字段，含状态选项）→ `gap_table_id = tbl1NNU8kmlLKpLm`，写回 secrets.json
5. 实现 `src/movietrace/feishu/gap_sync.py` + CLI `sync-feishu-gap-table` + `tests/test_gap_sync.py`（5 个测试）
6. 集成到 `baseline_run.sh`
7. 测试 504 passed（+5）
8. 重置 local_max_season：307 行更新，85 条无 upstream link 的 vs 重置为 0
9. baseline-track catch-up：plan 272、polled 272、detected 258、写入 **147 条 new_season**
10. sync-feishu-gap-table：首次因 api_cache 重复 key 写出 182 行（含 40 行 cartesian product 重复）

**Phase B — Review（3 个并行 sonnet agent）**
- 效率 review：1 HIGH（per-record PUT 应改 batch_update）+ 1 MEDIUM（相关子查询 → CTE+ROW_NUMBER）
- 质量 review：1 HIGH（GAP_EXIT 未触发飞书告警）+ 多个 MEDIUM（stats bug、重复 print、测试资源泄漏等）
- 复用 review：3 HIGH（`_request_json` / `_create_records` / `_update_record` 与 sync.py 完全重复）+ 多个 MEDIUM 共享候选

**Phase C — Cleanup（并行 sonnet agent）**
- 清空 A 库缺口 182 条 → 重新同步 142 条干净行
- 清空热点发现 156 条 → 用 `reports/latest.json` 重填 150 条

**Phase D — Fix（sonnet agent）**
- 新建 `src/movietrace/feishu/_http.py`：共享 `request_json` / `batch_create_records` / `batch_update_records` / `unwrap_text_field`
- 重构 `sync.py` 和 `gap_sync.py` 导入 `_http`，删除重复函数定义
- `gap_sync.py` SQL：相关子查询 → CTE+ROW_NUMBER，单次扫描
- `gap_sync.py` 更新循环：per-record PUT → `batch_update_records`（500 条/批，预期 30s → <1s）
- `gap_sync.py` stats bug：only increment after success（不再预扣回退）
- `gap_sync.py` 移除冗余 print
- `cli.py` 抽取 `_load_feishu_creds` 共享给两个命令
- `tests/test_gap_sync.py` 改用 `unittest.TestCase` + `setUp/tearDown` + `TemporaryDirectory` context manager；新增 `test_compute_gaps_ordering`
- `baseline_run.sh` GAP_EXIT 触发独立错误告警
- 删除一次性脚本 `scripts/feishu_cleanup.py`
- 测试 **505 passed**

---

## 关键决策

1. **飞书展现层和事件历史解耦**（ADR-0013）——状态快照子表不读 content_updates；事件日志保留作审计但不参与展现
2. **任务包先 season、ADR 完整覆盖 season + episode**——避免一次做太多，但表结构预留 episode 字段
3. **行粒度 = 1 行/series 而非 1 行/(series, season)**——简化运营视图；缺口字段以列表形式存储
4. **状态字段半自动机制**——系统提示 `建议已补`，运营人工归档
5. **筛选范围 = 任何 poll_priority != skip 的有缺口剧（含 Ended）**——A 库 历史缺口也要补
6. **绕过 local_max_season 回滚问题**——新表不依赖事件历史，所以不需要修复 P1.20 的历史空洞

---

## 当前项目状态快照

- Phase 1 通过 P1.21，全部完成
- 飞书三个子表：热点发现 150 行（hot）/ A 库缺口 142 行（gap）/ 字段说明（doc）
- 测试 505 passed
- 真实 DB schema 14；新增数据：147 条 new_season（catch-up 写入），15 条 new_discovery（今日 daily_run 写入）
- 文件未提交，待 commit

---

## 给下一个 Agent 的交接

- **新 sub-table "A 库缺口"** `tbl1NNU8kmlLKpLm`：14 字段，详见 `gap_sync.py` field map
- **共享 HTTP 模块** `_http.py`：所有飞书 REST 调用应通过它（sync.py 已迁移；baseline.py 保留独立，因为 `fetch_tenant_access_token` 签名不同）
- **`baseline_run.sh` 现有 4 步**：track → export → sync-feishu-table → sync-feishu-gap-table → doc → notify
- **episode 检测**是 P1.21 ADR 中明确的下一步，字段已预留，实现工作量约：新 TMDb season detail API + upstream_episodes 季-集解析 + 字段刷新逻辑，预估 1-1.5 天
- **P1.20 历史 new_season 事件丢失**已认知，不予修复（绕过）
- **lark-cli docs +create** v1 API deprecated + 大 markdown 触发 field validation，daily doc 同步会失败。独立问题，待后续任务包处理（baseline doc 同步因数据量小未触发）

---

## 数字总结

| 项目 | 值 |
|------|----|
| 本次会话新增 commit | 2（在前段，已提交）+ 1（即将提交） |
| 修改文件 | 6（sync.py、cli.py、baseline_run.sh、reports/baseline_latest.md、reports/latest.json、reports/latest.md） |
| 新建文件 | 5（gap_sync.py、_http.py、test_gap_sync.py、ADR-0013、P1.21 任务包） |
| 删除文件 | 1（scripts/feishu_cleanup.py） |
| 测试 | 499 → 505 passed（+6） |
| 子代理调用 | 5（1 实施 + 1 清理 + 3 review + 1 修复） |

---

## 成本统计

| 项目 | 值 |
|------|-----|
| 会话墙钟时长 | ~165 分钟（含 ~70 分钟自主运行） |
| 子代理累计 token | ~265K（impl 89K + 3 review 共 90K + cleanup 28K + fix 58K） |
| 子代理累计耗时 | ~30 分钟（implementation 20 分钟 + review/cleanup/fix 共 ~10 分钟） |
| 主会话 token | 未记录 |
