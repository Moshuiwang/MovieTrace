# MovieTrace 项目状态快照

> 项目当前状态。**任何 Agent 启动新会话时必读**（CLAUDE.md / AGENTS.md 启动顺序的第 1 步）。
> 每次 git commit 前应更新本文件。

---

**最后更新：** 2026-05-14 +08
**更新人：** Claude Code (deepseek-v4-pro) + moshuiwang
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
| **Phase 1.8：条件性调优前置数据治理** | ✅ 全部完成（402 测试, 2026-05-14） |

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

| **Phase 1.9：code review hotfix** | 📋 任务包已创建，待用户安排执行 |

---

## Phase 1.9 hotfix 任务包（2026-05-14）

Code review（`reports/code_review_2026-05-14.md`）发现 10 个问题。CR-001 已修复，剩余 5 个 bug + 1 个默认值问题拆为 6 个任务包：

```
P1.9-hotfix-A（inspect-api-usage SQL 崩溃）         📋 待执行
    ↓
P1.9-hotfix-B（TV freshness last_air_date 未落地）  📋 待执行
    ↓
P1.9-hotfix-C（baseline 多新季 local_max 回写）     📋 待执行
    ↓
P1.9-hotfix-D（API logging 脱敏加固）               📋 待执行
    ↓
P1.9-hotfix-E（TMDb movie/tv ID 命名空间隔离）      📋 待执行
    ↓
P1.9-hotfix-F（Hulu→Paramount+ 默认值同步）         📋 待执行
```

**任务包文档：**
- [P1.9-hotfix-A](docs/tasks/p1.9_hotfix_a_inspect_api_usage_sql_fix.md)
- [P1.9-hotfix-B](docs/tasks/p1.9_hotfix_b_tv_freshness_last_air_date.md)
- [P1.9-hotfix-C](docs/tasks/p1.9_hotfix_c_baseline_multi_season_fix.md)
- [P1.9-hotfix-D](docs/tasks/p1.9_hotfix_d_api_logging_sanitization.md)
- [P1.9-hotfix-E](docs/tasks/p1.9_hotfix_e_tmdb_id_namespace.md)
- [P1.9-hotfix-F](docs/tasks/p1.9_hotfix_f_hulu_paramount_defaults.md)

**CR-005（content_updates 唯一键）、CR-007（secrets 路径）、CR-009/010、CC-001~004 暂不纳入实现，需产品决策或另排清理周期。**

---

## Phase 1.8 执行结果（2026-05-14）

按 D → H → C → F/G → E 顺序全部完成。

```
P1.8-D（API usage logging）                          ✅  migration 008 + logger + 4 sources + CLI
    ↓
P1.8-H（FP 覆盖范围与 API 预算策略）                   ✅  4国×6平台 + TV每日/Movie每周 + config.yaml
    ↓
P1.8-C（TMDb 结构化字段 + TV freshness）              ✅  migration 009 + last_air_date优先
    ↓
P1.8-F/G（external_ids + IMDb backfill + TMDb fallback） ✅  backfill + external_ids + tmdb_fallback标记
    ↓
P1.8-E（多源结构化字段）                              ✅  migration 010 + FP/Trakt新字段
```

### P1.8-D：API usage logging

**新增模块：**
- `src/movietrace/logging/api_usage.py` — logger helper + key fingerprinting
- `src/movietrace/db/migrations/008_api_usage_log.sql` → `api_usage_log` 表

**改动：**
- `http.py::get_json()` 增加 `log_context` 参数，自动记录成功/失败/耗时
- 4 个 API source（tmdb/trakt/omdb/flixpatrol）全部传入 log_context
- 所有 pipeline client 创建时传入 `db_path` + `request_date`
- 新增 `inspect-api-usage` CLI 命令

**密钥安全：**
- `key_fingerprint` = SHA-256 前 12 位，不可逆
- 测试覆盖"不泄露完整 key"
- metadata 自动过滤 `apikey`/`authorization`/`token` 等敏感字段

### P1.8-H：FlixPatrol 覆盖范围

**国家/范围：** World · United States · Nigeria · Kenya（API 确认 ID）
**平台：** Netflix · Prime Video · Disney+ · Apple TV+ · HBO Max · Paramount+（移除 Hulu）
**调度：** TV 每日 24 calls · Movie 每周一 48 calls · 月估算 824-864 calls
**配置：** `config.yaml` → `flixpatrol` 节
**CLI：** `daily-discover --force-fp-movies`

### P1.8-C：TMDb 字段结构化 + TV freshness

**Migration 009：** `tmdb_trending` 新增 27 个结构化字段
**TV freshness 修正：** 优先使用 `last_air_date`，fallback 链：last_air_date → last_episode_air_date → first_air_date → release_date
**例：** FROM（TMDb 124364）`last_air_date=2026-05-10`，不再被按 `first_air_date=2022-02-20` 扣分

### P1.8-F/G：external_ids + IMDb 回填 + TMDb 评分兜底

- `TmdbDetailClient.fetch_imdb_id()` — 通过 /tv/{id}/external_ids 或 /movie/{id}/external_ids
- `backfill_imdb_ids()` — 评分前补 IMDb ID（P1.8-F/G 合并实现）
- `compute_imdb_rating_score()` → 返回 `(score, source)` 元组，source 为 `omdb` / `tmdb_fallback` / None
- `score_breakdown` 新增 `imdb_rating_source` 字段

### P1.8-E：多源结构化字段

**Migration 010：** `flixpatrol_top10` 新增 `updated_at`/`country_id`/`company_id`；`trakt_trending` 新增 10 个字段（genres_json, trakt_status, country, network, runtime, overview, first_aired, aired_episodes, certification, updated_at）

### 新增 DB migrations

| Migration | 描述 |
|-----------|------|
| 008 | `api_usage_log` 表 |
| 009 | `tmdb_trending` 结构化字段 |
| 010 | `flixpatrol_top10` + `trakt_trending` 结构化字段 |

### 新增 CLI 命令

- `inspect-api-usage` — 查询 API 用量日志（支持 --date/--days/--service/--format table|json）

---

## 进行中任务

- Phase 1.9 hotfix 6 个任务包已创建，等待用户安排执行。建议顺序：A → B → C → D → E → F。

## P1.9 执行结果（2026-05-14）

- **P1.9（auto-register canonical_item）**：✅ 已完成（commit b4f6e99，406 测试）

---

## 阻塞项

- **FP API 订阅**：402 Payment Required，US/World/Nigeria/Kenya 全部不可用
- **OMDb API**：401 Unauthorized，key 过期或配额耗尽

---

## 待用户决策

- **pyyaml 是否纳入 requirements.txt**（延续）
- **P1.8-B（OMDb key 授权排查）**：纯调研任务，未执行
- **P1.9-hotfix 执行**：6 个任务包待安排
- **CR-005（content_updates 唯一键设计）**：需产品决策
- **CR-007（secrets 路径迁移）**：需产品决策

---

## 给下一个 Agent 的交接

- **P1.9 已完成**：P2+ 候选自动注册 canonical_item（commit b4f6e99，406 测试）
- **P1.9-hotfix A-F 待执行**：6 个任务包路径见 `docs/tasks/p1.9_hotfix_*.md`
- **P1.8 全部完成**（commit f264eba，402 测试）
- **FP 和 OMDb API 均不可用**，无法做真实验证，需先解决配额
- **Schema version = 10**（migrations 001-010）
- **TMDb Bearer Token 路径：** `/tmp/movietrace_phase0_secrets.json`

---

## Housekeeping 待办（不阻塞主线）

- ~~**任务包文档归档治理**~~ ✅ 已完成（2026-05-12）
- ~~**日报归档**~~ ✅ 已完成
- **参考文档分类**：`docs/` 根目录文件可考虑按主题分目录
- **pyyaml 纳入依赖**：确认后更新 `requirements.txt`
