# MovieTrace 项目状态快照

> 项目当前状态。**任何 Agent 启动新会话时必读**（CLAUDE.md / AGENTS.md 启动顺序的第 1 步）。
> 每次 git commit 前应更新本文件。

---

**最后更新：** 2026-05-13 23:55 +08
**更新人：** Codex (GPT-5) + moshuiwang
**所在分支：** `main`

---

## 当前阶段

| 阶段 | 状态 |
|------|------|
| Phase 0：开发前验证 | ✅ 已完成（Go 决策） |
| Phase 0+：FlixPatrol 接入验证 | ✅ 已完成（SUP-A~G 全部通过） |
| Phase 1：V1 MVP 开发 | ✅ 全部完成（284 测试） |
| **Phase 1.5：V1 定位翻转** | ✅ 全部完成（326 测试） |
| **Phase 1.6：首次真实运行 + 验收** | ✅ 已完成（2026-05-12） |
| **Phase 1.7：多热门源扩充** | ✅ 全部完成（366 测试, 2026-05-13） |
| **Phase 1.8：条件性调优前置数据治理** | 📋 任务包规划中（待用户安排执行） |

---

## Phase 1.5 执行结果（2026-05-12）

```
P1.5-A（文档翻转）                                ✅
    ↓
P1.5-B（schema v6 migration）                     ✅ migration 006 已执行
    ↓
P1.5-E（A 库全量实体匹配 → canonical_items）      ✅ match_upstream_program + 全量脚本
    ↓
P1.5-C（virtual_series 一次性回填）                ✅ virtual_series 模块 + 回填脚本
    ↓
P1.5-D（基线主动追踪模块）                         ✅ poll_scheduler + baseline_tracking + CLI
    ↓
P1.5-F（日报模板 + CLI 语义 + 导出）               ✅ export_writer + CLI 更新 + 飞书写入移除
```

**新增模块：**
- `src/movietrace/pipeline/virtual_series.py`
- `src/movietrace/pipeline/poll_scheduler.py`
- `src/movietrace/pipeline/baseline_tracking.py`
- `src/movietrace/reports/export_writer.py`
- `src/movietrace/sources/tmdb.py` — TmdbDetailClient

**新增 CLI 命令：**
- `baseline-track` — 基线新季检测
- `export-recommendations` — MD+JSON 导出

**新增配置文件：**
- `config.yaml` — baseline_tracking 配置

**已砍掉：**
- ~~飞书写入~~ — daily-discover 已移除飞书写入步骤
- ~~`feishu/recommendation_writer.py`~~ — 已删除（含测试）
- ~~`tests/test_recommendation_writer.py`~~ — 已删除

**任务包文档（全部已执行）：**
- [P1.5-A](docs/tasks/p1.5_a_documentation_repositioning.md) ✅
- [P1.5-B](docs/tasks/p1.5_b_schema_v6_migration.md) ✅
- [P1.5-E](docs/tasks/p1.5_e_entity_matching_full.md) ✅
- [P1.5-C](docs/tasks/p1.5_c_virtual_series_backfill.md) ✅
- [P1.5-D](docs/tasks/p1.5_d_baseline_active_tracking.md) ✅
- [P1.5-F](docs/tasks/p1.5_f_report_cli_export.md) ✅

---

## Phase 1.6 执行结果（2026-05-12）

生产环境真实运行，按 B→E→C→D→F 顺序执行。

### P1.5-E：A库全量实体匹配
| 指标 | 数值 |
|------|------|
| 处理数 | 594（online_flag=1 且未匹配） |
| 匹配成功 | 594/594 (100%) |
| 置信度 | high 587 · medium 7 · low 0 |
| 新建 canonical_items | 513 |
| 复用已有 | 81 |
| API 调用 | 594 · 耗时 15 分钟 |

### P1.5-C：virtual_series 回填
| 指标 | 数值 |
|------|------|
| 最终 virtual_series | **300**（urgent 84 / low 181 / skip 35） |
| 已链接 canonical_items | 763/798 (95.6%) |
| API 调用 | 192（去重后，节省 185 次） |
| 发现并修复 | 旧版 baseline_quality_issues 表冲突 · 多季同 ID fallback · 两阶段去重优化 |

### P1.5-D：基线追踪
| 指标 | 数值 |
|------|------|
| 轮询计划 | 7（urgent 优先） |
| 检测到新季 | 8 |
| 写入 content_updates | 6（2 条去重） |
| 示例 | FROM S4 · Silo S2 · American Horror Story S11 |

### P1.5-F：报告导出
- 导出 6 条 content_updates → `reports/recommendations_*.md` + `.json`

### P1.5-E 修复（第二次）
- **根因**：`/search/tv` 和 `/search/movie` 返回结果不含 `media_type` 字段，被 `parse_tmdb_search_results` 过滤掉
- **修复**：`parse_tmdb_search_results` 加 `default_media_type` 参数；`match_upstream_program` 改用类型专用搜索 + detail 端点验证 ID 有效性；TV 搜索为空时回退 movie 搜索（处理 A 库错标 S01 的电影）
- **结果**：35 条错误匹配全部修复，TV 链接率 100%

### 匹配质量增强（第三次）
- low/medium 置信度均记入 `baseline_quality_issues`
- 新增 `_check_close_alternatives`：当选中有多候选接近时记录备选项（最多 5 个）
- 测试验证：Dream（2 个同名电影）、Sly（4 个低 sim 候选无正确答案）正确识别

---

## 生产数据画像（最终）

```
canonical_items:  903 (TV season 502 · TV series 288 · Movie 113)
virtual_series:   307 (urgent 84 · low 181 · skip 35 · normal 7)
content_updates:  6 (new_season)
external_ids:     upstream 631 · tmdb 458
TV 链接率:        790/790 = 100%
测试:             317 passed
```

### 生产数据画像
```
canonical_items: 905 (TV season 509 · TV series 289 · Movie 107)
virtual_series:  300
content_updates: 6 (new_season)
external_ids:    upstream 597 · tmdb 424
```

---

## 2026-05-12 关键决策记录

### 决策 1：A 库数据接入 ✅

- 用户从生产 DB 导出两张 CSV：`source_records/节目数据.csv`（735 行）+ `source_records/子节目数据.csv`（6,562 行）
- 导入到 `data/movietrace.db` 的 `upstream_programs` / `upstream_episodes` 表（migration 005）
- Schema 参考文档：[reports/upstream_db_schema_reference.md](reports/upstream_db_schema_reference.md)
- **A 库取代飞书"线上内容基线表"成为 MovieTrace 的内容目录来源**

### 决策 2：飞书从系统链路移除 ✅

- 飞书不再是内容目录来源（被 A 库取代）
- 飞书不再是输出渠道（被日报 MD + JSON 导出取代）
- P1.5-E（飞书写入翻新）整包砍掉
- P1.5-F/G 合并为一个任务包（日报 + CLI + 导出）
- `feishu_import_runs` / `source_records` / `baseline_items` 表**保留不动**（历史数据）

### 决策 3：Q5-Q8 全部解定 ✅

| 问题 | 决策 |
|------|------|
| Q5（多季合并 + season_number） | 正则从 name 提取，同名 tv_id 多季幂等合并到同一条 virtual_series |
| Q6（写入粒度） | 季级；tmdb_number_of_seasons > local_max_season → 新季 |
| Q7（增量检测） | last_polled_at（轮询频率）+ modify_instant（定位变更节目）双信号 |
| Q8（集成方式） | 独立 CLI `baseline-track` + 嵌入 `daily-discover` 最后一步，两者都做 |

### 决策 4：Migration 编号调整

- 005 → `upstream_programs` / `upstream_episodes`（A 库备份表，已执行）
- 006 → `virtual_series` 表 + `canonical_items.virtual_series_id` + `content_updates.match_confidence_low`（P1.5-B）

---

## 当前 A 库数据画像

| 表 | 行数 | 关键字段 |
|----|------|---------|
| `upstream_programs` | 735 | `id`, `name`, `online_flag`(597=上架), `modify_instant` |
| `upstream_episodes` | 6,562 | `id`, `fk_program_content_id`, `direct_weight`, `modify_instant`, `duration_*` |

- 85% 节目名含 `S\d\d` 季号（可正则提取）
- `imdb_id` 全空（匹配只能走 TMDb 名称搜索）
- 无 Series 实体（需 `virtual_series` 聚合）

---

## Phase 1.7 执行结果（2026-05-13）

```
P1.7-A（migration 007 schema 扩展）                ✅
    ↓
P1.7-B（TMDb 热门源采集）∥ P1.7-C（Trakt 热门源采集）   ✅ ∥ ✅
    ↓
P1.7-D（多源并集 + 富化 + 评分）                    ✅
    ↓
P1.7-E（inspect CLI + 端到端验收）                   ✅
```

**新增模块：**
- `src/movietrace/pipeline/tmdb_trending.py` — TMDb 热门采集
- `src/movietrace/pipeline/trakt_trending.py` — Trakt 热门采集
- `src/movietrace/pipeline/multi_source_merge.py` — 三源并集
- `src/movietrace/pipeline/omdb_enrichment.py` — OMDb 富化 + TMDb 详情补充
- `src/movietrace/reports/inspect_renderer.py` — 终端表格 / JSON / MD 渲染

**新增 CLI 命令：**
- `fetch-tmdb-trending` — TMDb 热门源采集
- `fetch-trakt-trending` — Trakt 热门源采集
- `inspect-updates` — 本地查阅 content_updates

**新增 DB 表（migration 007）：**
- `tmdb_trending` — TMDb 热度榜单
- `trakt_trending` — Trakt 热度榜单

**任务包文档（全部已执行）：**
- [P1.7-A](docs/tasks/p1.7_a_multi_source_schema.md) ✅
- [P1.7-B](docs/tasks/p1.7_b_tmdb_trending_source.md) ✅
- [P1.7-C](docs/tasks/p1.7_c_trakt_trending_source.md) ✅
- [P1.7-D](docs/tasks/p1.7_d_multi_source_merge_and_score.md) ✅
- [P1.7-E](docs/tasks/p1.7_e_inspect_updates_cli.md) ✅

---

## Phase 1.7 生产运行结果

```
daily-discover 2026-05-13:
  FP:        0 items (无当日快照)
  TMDb:      180 items (trending/day=60, tv/popular=60, movie/popular=60)
  Trakt:     601 items (shows=500, movies=101)
  Merged:    649 candidates
  OMDb enriched: 583
  P2+ passed:    4 (P0=0 P1=0 P2=4)
  Written:   1 new_discovery + 5 new_seasons
  api_cache: 1079 OMDb entries
```

**注意：** FP 0 数据导致仅 4 条 P2+，正常日预计 30-80 条。

---

### P1.7 验收后修复：FlixPatrol 当日数据为 0

- **任务包：** [P1.8-A](docs/tasks/p1.8_a_flixpatrol_zero_data_bugfix.md)
- **根因：** FP 当日数据检测使用 `snapshot_date >= ?`，未来日期数据会误判目标日期已有数据；同时 FP API 单日请求未强制设置 `date[from][lte]`。
- **修复：** FP 当日检测改为 `snapshot_date = ?`；单日请求补上 `date[from][lte] = date_from`；入库时跳过非目标日期。
- **验证：**
  - `tests/test_discovery.py tests/test_flixpatrol_api.py -v` → 54 passed
  - `tests/ -v` → 368 passed
  - `daily-discover --date 2026-05-13 --dry-run` → FP 120 items，P2+ 62（P0=1, P1=6, P2=55）
- **报告：**
  - [修复报告](reports/p1.8_a_flixpatrol_zero_data_bugfix_report.md)
  - [端到端验证报告](reports/session_2026-05-13_p1.8_fp_e2e_validation.md)

---

## Phase 1.8 当前规划（2026-05-13 23:55）

### 已创建任务包（待用户审阅 / 安排执行）

- [P1.8-B OMDb key 授权与配额排查](docs/tasks/p1.8_b_omdb_key_authorization_diagnosis.md)
- [P1.8-C TMDb 字段结构化与 TV freshness](docs/tasks/p1.8_c_tmdb_structured_fields_and_tv_freshness.md)
- [P1.8-D API usage logging](docs/tasks/p1.8_d_api_usage_logging.md)
- [P1.8-E 多源字段结构化与 IMDb ID 补全](docs/tasks/p1.8_e_multi_source_structured_fields_and_imdb_id_backfill.md)
- [P1.8-F 每日主线 TMDb external_ids 入库](docs/tasks/p1.8_f_daily_external_ids_backfill.md) — v2，已标注与 G 合并执行
- [P1.8-G 评分前补 IMDb ID 与 TMDb 评分兜底](docs/tasks/p1.8_g_imdb_id_pre_score_backfill_and_tmdb_rating_fallback.md) — v2，已记录降低 OMDb 依赖
- [P1.8-H FlixPatrol 覆盖范围与 API 预算策略调整](docs/tasks/p1.8_h_flixpatrol_coverage_and_budget_strategy.md)
- [P1.8 执行顺序与依赖调整](docs/tasks/p1.8_execution_order.md)

### 已确认产品决策

- **OMDb 依赖：** 降低 OMDb 对当天评分链路的阻塞性；OMDb 有结果时优先使用真实 IMDb 分，失败时不阻断评分。
- **TMDb fallback：** 接受用 TMDb `vote_average` / `vote_count` 作为 IMDb 评分维度兜底，但必须在 `score_breakdown` 中标记 `tmdb_fallback`。
- **P1.8-F / P1.8-G：** 合并执行，避免重复实现 TMDb external_ids client、缓存和统计。
- **FP 覆盖策略：** World / United States / Nigeria / Kenya；Netflix / Prime Video / Disney+ / Apple TV+ / HBO Max / Paramount+；TV 每日抓取，Movie 每周抓取；预计约 824-864 FP API calls/month。
- **ADR：** [ADR-0009 P1.8 API 预算与评分兜底策略](docs/decisions/0009-p1-8-api-budget-and-rating-fallback.md)

### 建议执行顺序

`P1.8-D → P1.8-H → P1.8-C → P1.8-F/G → P1.8-E`

原因见：[P1.8 执行顺序与依赖调整](docs/tasks/p1.8_execution_order.md)。

---

## 进行中任务

- Phase 1.8 任务包已拆分，等待用户安排执行；当前不应主动进入实现。

---

## 阻塞项

- **OMDb 免费配额**：2026-05-13 已出现 `Request limit reached!`，当天真实 IMDb 评分补全不可依赖 OMDb 全量成功。
- **API usage log 尚未实现**：后续 FP 扩围和 TMDb external_ids 增加请求量前，建议先执行 P1.8-D。

---

## 待用户决策

- **pyyaml 是否纳入 requirements.txt**（当前已 `pip install`，scoring.py 有 fallback 到 DEFAULT_WEIGHTS）
- **P1.8 任务执行安排**：当前建议顺序为 D → H → C → F/G → E；等待用户指定启动哪个任务包。

---

## 给下一个 Agent 的交接

- **Phase 1.7 全部完成**，366 测试全过
- **新增 CLI 命令：** `fetch-tmdb-trending`、`fetch-trakt-trending`、`inspect-updates`（共 3 个）
- **daily-discover 流程已改为 6 步多源版本**，不再写 candidates 表（改写 content_updates）
- **OMDb 缓存已在生产 DB**，第二次运行同日会全量命中缓存（≈0 API 调用）
- **`candidates` 表不再写入**，但 `baseline_matching` 仍依赖。Phase 1.8 需决定是否废弃
- **TMDb Bearer Token 路径：** `/tmp/movietrace_phase0_secrets.json`
- **Trakt 需要 Mozilla UA**（已在 http.py 设默认值）
- **Session 报告：** `reports/session_2026-05-13_p1.7_acceptance.md`

---

## Housekeeping 待办（不阻塞主线）

- ~~**任务包文档归档治理**~~ ✅ 已完成（2026-05-12）
- ~~**日报归档**~~ ✅ 已完成
- **参考文档分类**：`docs/` 根目录文件可考虑按主题分目录
- **pyyaml 纳入依赖**：确认后更新 `requirements.txt`
