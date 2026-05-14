# MovieTrace 项目状态快照

> 项目当前状态。**任何 Agent 启动新会话时必读**（CLAUDE.md / AGENTS.md 启动顺序的第 1 步）。
> 每次 git commit 前应更新本文件。

---

**最后更新：** 2026-05-14 19:57 +08
**更新人：** Codex（GPT-5）+ moshuiwang
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
| **Phase 1.9：code review hotfix + 候选自动注册** | ✅ 全部完成（405 测试, 2026-05-14） |
| **Phase 1.10：源数据预算与抓取兜底** | ✅ 全部完成（437 测试, 2026-05-14） |
| **Phase 1.11：API 调用韧性增强** | ✅ 全部完成（458 测试, 2026-05-14） |
| **Phase 1.12：review hotfix** | ✅ 全部完成（478 测试, 2026-05-14） |
| **Phase 1.13：content_updates 数据模型修正** | ✅ 全部完成（495 测试, 2026-05-14） |

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

| **Phase 1.9：code review hotfix + 候选自动注册** | ✅ 全部完成（405 测试, 2026-05-14） |

---

## Phase 1.12 执行结果（2026-05-14）

按 A → B → C → D → E → F 顺序全部完成。

```
P1.12-A（TMDb namespace 闭环修复）                    ✅
    ↓
P1.12-B（daily-discover dry-run 不写业务结果）        ✅
    ↓
P1.12-C（OMDb key 日志脱敏）                           ✅
    ↓
P1.12-D（PyYAML 依赖声明补齐）                         ✅
    ↓
P1.12-E（多新季 content_update 汇总修复）              ✅
    ↓
P1.12-F（Secrets 路径迁移）                            ✅
```

### P1.12-A：TMDb namespace 闭环修复
- `_lookup_canonical_id()` 严格按 media_type 查询，不再跨类型 fallback
- `match_upstream_program()` TMDb external_id 写入带 `tv:`/`movie:` 前缀
- `find_or_create_virtual_series_for_canonical_item()` 剥离前缀后传 TMDb API
- 回填脚本同步处理前缀；Migration 013 清理残留裸 ID；schema version 12→13

### P1.12-B：daily-discover dry-run 不写业务结果
- `run_discovery(dry_run=True)` 不再调用 `_ensure_canonical_item()`
- dry-run 统计 `would_be_registered` 而非 `auto_registered`

### P1.12-C：OMDb key 日志脱敏
- key 失效日志从 `key[:8]` 改为 `fingerprint_key(key)`

### P1.12-D：PyYAML 依赖声明补齐
- `requirements.txt` 添加 `PyYAML==6.0.3`

### P1.12-E：多新季 content_update 汇总修复
- `write_content_updates()` 按 `virtual_series_id` 分组，同剧多新季合并为一条
- `source_summary_json` 新增 `seasons`/`season_min`/`season_max`，保留 `season` 向后兼容

### P1.12-F：Secrets 路径迁移
- 新建 `src/movietrace/config.py`：`load_secrets()` / `get_secrets_path()` / 权限检查
- 新路径 `~/.config/movietrace/secrets.json`，fallback 旧路径 + deprecation warning
- 4 文件 8 处硬编码全部替换；`cli.py`/`discovery.py` 重复 `_load_secrets()` 删除

**新增文件：** `config.py` · migration 013 · `tests/test_config.py` · `tests/db/test_schema_migration_013.py`

**测试：** 478 passed（+20 vs P1.11）

---

## Phase 1.13 执行结果（2026-05-14）

```
P1.13（content_updates 事件历史化）                      ✅
```

- Migration 014：drop `ux_content_updates_item_type` → create `ux_content_updates_update_id`
- Discovery `content_update_id` 加入 TMDb media namespace：`discovery:{movie|tv}:{tmdb_id}:{snapshot_date}`
- Migration 014 会在建唯一索引前把 legacy `discovery:{tmdb_id}:{snapshot_date}` 迁移为带 `movie|tv` 的新格式
- 同内容同类型跨天 → 不同 `content_update_id` → 多条事件（允许重新变热内容重现）
- 同一天同一 `content_update_id` → `insert or ignore` 幂等
- `_write_content_updates()` 统计修正：`conn.total_changes` 替代无条件 `count += 1`
- Schema version：13 → 14
- Review hotfix：migration 013 先删除会与既有 `tv:`/`movie:`/`unknown:` ID 冲突的裸 TMDb ID，再执行 namespace update，避免 `ux_external_ids_source_id` 中断升级
- Review hotfix：`FlixPatrol load_api_key()` 无显式路径时改走统一 `load_secrets()`，保留 `/tmp/movietrace_phase0_secrets.json` legacy fallback
- Review hotfix：`entity_matching --secrets` 未显式传入时走 `load_secrets(None)`，保留 legacy fallback；显式传入路径时继续使用指定文件
- Test hardening：补充 `load_secrets()` 默认新路径坏 JSON 时 fallback legacy 的测试，并修复对应逻辑；显式坏 JSON 仍不 fallback
- Test hardening：补充 schema 12 风格库升级到 14 的 migration 集成测试；发现并修复 `SCHEMA_SQL` 提前创建 `ux_content_updates_update_id` 导致 legacy 重复 ID 在 migration 014 前失败的问题
- 测试：495 passed（新增 discovery namespace、migration 013 duplicate guard、migration 014 legacy namespace、secrets fallback、schema 12→14 升级回归）
- 本地 `data/movietrace.db` 检查：真实库仍为 schema version 12，未落盘升级；仅 1 条 legacy discovery 记录，关联 `content_type=tv`，副本迁移演练通过并转为 `discovery:tv:124364:2026-05-13`

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

无。Phase 1.13 review hotfix 已完成，所有 Phase 1 任务包全部执行完毕。

---

## Phase 1.10 执行结果（2026-05-14）

```
P1.10-A（TMDb 每接口默认 20 条）                       ✅
    ↓
P1.10-B（Trakt shows/movies 各 20 条）                 ✅
    ↓
P1.10-C（migration 012 source_fetch_runs 表 + helper）  ✅
    ↓
P1.10-D（source-level fallback 运行机制）                ✅
    ↓
P1.10-E（fresh/fallback/failed 报告可感知）              ✅
```

### P1.10-A：TMDb 热源抓取精简

- `config.yaml` 新增 `source_fetch_limits.tmdb.pages_per_endpoint: 1`
- `tmdb_trending.py` 默认 `pages_per_endpoint=1`（原 3）
- `cli.py` daily-discover 和 fetch-tmdb-trending 读取配置，`--pages` 可覆盖
- TMDb 每日理论条数：180 → 60（3 endpoint × 1 page × 20）

### P1.10-B：Trakt 热源抓取精简

- `config.yaml` 新增 `source_fetch_limits.trakt.shows_limit: 20` / `movies_limit: 20`
- `trakt.py` client 默认 limit 20（原 500）
- `trakt_trending.py` pipeline 新增 `shows_limit`/`movies_limit` 参数
- `cli.py` daily-discover 和 fetch-trakt-trending 读取配置，`--shows-limit`/`--movies-limit` 可覆盖
- Trakt 每日理论条数：~625 → ~40

### P1.10-C：抓取状态表与状态记录

- Migration 012：`source_fetch_runs` 表（14 字段 + 3 索引 + unique 约束）
- 新增 `src/movietrace/pipeline/source_fetch_status.py`
  - `record_source_fetch_run()` — upsert 状态记录
  - `get_source_fetch_runs()` — 按日期/source 查询
  - `find_latest_source_snapshot()` — 查找最近可用 snapshot
  - `build_effective_source_dates()` — 批量构建有效日期
- 状态枚举：fresh / fallback / failed_no_fallback / skipped
- Schema version：11 → 12

### P1.10-D：每日抓取失败兜底

- `config.yaml` 新增 `source_fallback` 配置节（enabled, max_staleness_days: 30, sources）
- `discovery.py` 新增 `_resolve_source_dates_with_fallback()` + `_find_fallback_snapshot()`
- `multi_source_merge.py::merge_three_sources()` 支持 per-source `source_dates` 参数
- `run_discovery()` 接受 `tmdb_fetch_result`/`trakt_fetch_result`/`fallback_cfg`
- `cli.py` daily-discover：单源失败不中断，fallback 时输出标记
- 控制台显示：`Source data:` 区块列出每个 source 状态

### P1.10-E：兜底来源报告可感知

- `_build_source_summary()` 写入 `source_data_status` 到 `content_updates.source_summary_json`
- `export_writer.py`：Markdown 头部展示"数据源状态"；JSON 包含 `source_data_status`
- `inspect_renderer.py`：detail 视图展示 source 状态；format_json_enhanced 包含 status
- 无 source_status 的旧数据兼容不崩溃

**新增文件：**
- `src/movietrace/db/migrations/012_source_fetch_runs.sql`
- `src/movietrace/pipeline/source_fetch_status.py`
- `tests/db/test_schema_migration_012.py`
- `tests/pipeline/test_source_fetch_status.py`

**修改文件：**
- `config.yaml`、`config/config.example.yaml`
- `src/movietrace/pipeline/tmdb_trending.py`、`trakt_trending.py`
- `src/movietrace/sources/trakt.py`
- `src/movietrace/pipeline/discovery.py`、`multi_source_merge.py`
- `src/movietrace/reports/export_writer.py`、`inspect_renderer.py`
- `src/movietrace/db/schema.py`
- `src/movietrace/cli.py`
- `tests/test_tmdb_trending_pipeline.py`、`tests/test_tmdb_trending_client.py`
- `tests/test_trakt_trending_pipeline.py`、`tests/test_trakt_trending_client.py`
- `tests/test_discovery.py`、`tests/test_multi_source_merge.py`
- `tests/reports/test_export_writer.py`

---

## P1.9 执行结果（2026-05-14）

```
P1.9（auto-register canonical_item）                 ✅ commit b4f6e99
    ↓
P1.9-hotfix-A（inspect-api-usage SQL 修复）          ✅
    ↓
P1.9-hotfix-B（TV freshness last_air_date 数据链路）  ✅ + 修复 TMDb 缓存 source bug
    ↓
P1.9-hotfix-C（baseline 多新季 local_max 回写）      ✅
    ↓
P1.9-hotfix-D（API logging 脱敏加固）                ✅
    ↓
P1.9-hotfix-E（TMDb movie/tv ID 命名空间隔离）       ✅ migration 011
    ↓
P1.9-hotfix-F（Hulu→Paramount+ 默认值同步）          ✅
```

**最终 commit：** `359198c`
**测试：** 405 passed

---

## Phase 1.11 执行结果（2026-05-14）

```
P1.11-A（API 致命错误熔断）                           ✅
    ↓
P1.11-B（OMDb 多 Key 轮转）                           ✅
```

### P1.11-A：API 致命错误熔断

- `http.py` 新增 `FatalApiError` 异常类（401/402/403 时抛出）
- `get_json()` → `HTTPError` 拦截 → 致命状态码抛 `FatalApiError`，非致命状态码（429/5xx）继续原异常
- `FlixPatrolClient.fetch_all_platforms()` → 首次 `FatalApiError` 立即停止遍历，返回部分 stats（含 `circuit_breaker: True`）
- `enrich_with_omdb()` → `FatalApiError` 触发 key 轮转，所有 key 耗尽后熔断停止
- dry-run 验证：FP 402 只报 1 次就熔断（原来 24 次），输出 "flixpatrol circuit breaker: HTTP 402 — stopping all FP requests"

### P1.11-B：OMDb 多 Key 轮转

- secrets 格式变更：`api_key` → `api_keys: ["c9c22b79", "e19de8a0"]`，向后兼容旧格式
- `enrich_with_omdb()` 签名：`omdb_api_key: str` → `omdb_api_keys: list[str]`
- Key 轮转逻辑：401/403 → 标记该 key 失效 → 用下一个 key 重试当前 candidate
- 所有 key 耗尽 → 熔断（停止后续 OMDb 请求）
- 非致命错误（429/5xx）不触发 key 切换
- `_resolve_omdb_keys()` 兼容新旧 secrets 格式
- `_read_cache`/`_write_cache` 修复 source 参数（原硬编码 `'tmdb'` 导致 OMDb 缓存命中率 0%）

**新增文件：**
- `tests/test_http.py` — FatalApiError 8 个测试

**修改文件：**
- `src/movietrace/sources/http.py` — FatalApiError + get_json 拦截
- `src/movietrace/sources/flixpatrol_api.py` — 熔断捕获 + _log_circuit_breaker
- `src/movietrace/pipeline/omdb_enrichment.py` — 熔断 + 多 key 轮转 + cache source 修复
- `src/movietrace/pipeline/discovery.py` — _resolve_omdb_keys + enrich 传参
- `src/movietrace/cli.py` — secrets 读取兼容
- `tests/test_flixpatrol_api.py` — FatalApiError 适配 + circuit breaker 测试
- `tests/test_omdb_enrichment.py` — 多 key/熔断 14 测试
- `/tmp/movietrace_phase0_secrets.json` — api_keys 格式

---

## 阻塞项

- **FP API 订阅**：402 Payment Required，US/World/Nigeria/Kenya 全部不可用

---

## 待用户决策

- ~~P1.8-B（OMDb key 授权排查）~~ → 已完成：新 key `c9c22b79` 验证通过（HTTP 200）
- ~~CR-005（content_updates 唯一键设计）~~ → 已决策，ADR-0012 + P1.13
- ~~CR-007（secrets 路径迁移）~~ → 已决策，ADR-0011 + P1.12-F

## V2 backlog

- **新集更新追踪（new_episode / episode-level update）**：用户于 2026-05-14 确认放入 V2，不进入 P1.12 hotfix；已补充至 [ADR-0007](docs/decisions/0007-repositioning-to-update-tracking.md) 的 2026-05-14 修正。本阶段只修复“多新季信息丢失”，不新增 episode-level 追踪。

---

## 给下一个 Agent 的交接

- **Phase 1.12 + 1.13 全部完成**
- **Schema version = 14**（migrations 001-014）
- **本地真实库 `data/movietrace.db` 当前仍是 schema version 12**；migration 013/014 已在副本演练通过，尚未对真实库落盘执行。
- **Secrets 新路径：** `~/.config/movietrace/secrets.json`（fallback 旧 `/tmp` 路径 + warning）
- **新增 config 模块：** `src/movietrace/config.py` 统一 secrets 加载入口
- **content_updates 语义变更：** 事件历史表，`content_update_id` 唯一，跨天可重复；discovery ID 格式为 `discovery:{movie|tv}:{tmdb_id}:{snapshot_date}`
- **FP API 仍然不可用**（402）；**OMDb 已恢复**
- **测试：** 495 passed，65.16s，无 API 消耗
- **Phase 1 全部任务包（41 个）执行完毕，无待执行任务**
- **新集更新追踪→V2 backlog**

---

## Housekeeping 待办（不阻塞主线）

- ~~**任务包文档归档治理**~~ ✅ 已完成（2026-05-12）
- ~~**日报归档**~~ ✅ 已完成
- **参考文档分类**：`docs/` 根目录文件可考虑按主题分目录
- ~~**pyyaml 纳入依赖**~~ → 已纳入 [P1.12-D](docs/tasks/p1.12_hotfix_d_pyyaml_dependency.md)，任务包授权执行时更新 `requirements.txt`
