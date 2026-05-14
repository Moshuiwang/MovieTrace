# Phase 1 历史状态归档

> 从 `STATE.md` 迁移而来。**默认不整篇读取，先 `rg` 搜索关键词再打开命中片段。**
> 迁移时间：2026-05-14（P1.16）

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

**已砍掉：**
- ~~飞书写入~~ — daily-discover 已移除飞书写入步骤
- ~~`feishu/recommendation_writer.py`~~ — 已删除（含测试）
- ~~`tests/test_recommendation_writer.py`~~ — 已删除

**任务包文档：**
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
| 最终 virtual_series | 300（urgent 84 / low 181 / skip 35） |
| 已链接 canonical_items | 763/798 (95.6%) |
| API 调用 | 192（去重后，节省 185 次） |

### P1.5-D：基线追踪
| 指标 | 数值 |
|------|------|
| 轮询计划 | 7（urgent 优先） |
| 检测到新季 | 8 |
| 写入 content_updates | 6（2 条去重） |

### P1.5-E 修复（第二次）
- **根因**：`/search/tv` 和 `/search/movie` 返回结果不含 `media_type` 字段
- **修复**：`parse_tmdb_search_results` 加 `default_media_type` 参数；类型专用搜索 + detail 端点验证
- **结果**：35 条错误匹配全部修复，TV 链接率 100%

### 匹配质量增强（第三次）
- low/medium 置信度记入 `baseline_quality_issues`
- 新增 `_check_close_alternatives`（最多 5 个备选项）

---

## 关键决策记录（2026-05-12）

### 决策 1：A 库数据接入 ✅
- 从生产 DB 导出 CSV → `upstream_programs` / `upstream_episodes`（migration 005）
- A 库取代飞书"线上内容基线表"成为 MovieTrace 的内容目录来源

### 决策 2：飞书从系统链路移除 ✅
- 飞书不再是内容目录来源（被 A 库取代）
- 飞书不再是输出渠道（被日报 MD + JSON 导出取代）

### 决策 3：Q5-Q8 全部解定 ✅
- Q5：正则从 name 提取季号，同名多季幂等合并
- Q6：季级写入，tmdb_number_of_seasons > local_max → 新季
- Q7：last_polled_at + modify_instant 双信号
- Q8：独立 CLI + 嵌入 daily-discover 最后一步

### 决策 4：Migration 编号调整
- 005 → upstream 表 · 006 → virtual_series

---

## 生产数据画像

```
canonical_items:  905 (TV season 509 · TV series 289 · Movie 107)
virtual_series:   300
content_updates:  6 (new_season)
external_ids:     upstream 597 · tmdb 424
TV 链接率:        790/790 = 100%
```

### A 库数据画像
| 表 | 行数 | 说明 |
|----|------|------|
| `upstream_programs` | 735 | `online_flag`=597 |
| `upstream_episodes` | 6,562 | `direct_weight`, `duration_*` |

---

## Phase 1.7 执行结果（2026-05-13）

```
P1.7-A（migration 007 schema 扩展）                ✅
P1.7-B（TMDb 热门源采集）∥ P1.7-C（Trakt 热门源采集）   ✅ ∥ ✅
P1.7-D（多源并集 + 富化 + 评分）                    ✅
P1.7-E（inspect CLI + 端到端验收）                   ✅
```

**新增模块：** tmdb_trending · trakt_trending · multi_source_merge · omdb_enrichment · inspect_renderer
**新增 CLI：** fetch-tmdb-trending · fetch-trakt-trending · inspect-updates
**新增 DB：** tmdb_trending · trakt_trending（migration 007）

### 生产运行结果
```
daily-discover 2026-05-13:
  FP: 0 · TMDb: 180 · Trakt: 601 · Merged: 649 · OMDb: 583 · P2+: 4
```

### P1.7 验收后修复：FlixPatrol 当日数据为 0
- **任务包：** P1.8-A
- **根因：** `snapshot_date >= ?` 误判 + `date[from][lte]` 未强制设置
- **修复：** 精确匹配 + 强制日期范围

---

## Phase 1.8 执行结果（2026-05-14）

按 D → H → C → F/G → E 顺序完成。

**P1.8-D：** API usage logging（migration 008 + api_usage.py + 4 sources + inspect-api-usage CLI）
**P1.8-H：** FP 覆盖范围（4国×6平台 + TV每日/Movie每周 + config.yaml）
**P1.8-C：** TMDb 结构化字段 + TV freshness（migration 009 + last_air_date优先）
**P1.8-F/G：** external_ids + IMDb backfill + TMDb fallback
**P1.8-E：** 多源结构化字段（migration 010）

---

## Phase 1.9 执行结果（2026-05-14）

```
P1.9（auto-register canonical_item）                 ✅
P1.9-hotfix-A~F                                     ✅（全部完成）
```

405 测试。hotfix 涵盖：inspect-api-usage SQL · TV freshness 链路 · baseline local_max 回写 · API logging 脱敏 · TMDb namespace 隔离 · Hulu→Paramount+

---

## Phase 1.10 执行结果（2026-05-14）

```
P1.10-A（TMDb 每接口 20 条）      ✅  180→60
P1.10-B（Trakt 20 条）            ✅  ~625→~40
P1.10-C（source_fetch_runs 表）   ✅  migration 012
P1.10-D（fallback 运行机制）       ✅  单源失败不中断
P1.10-E（报告可感知）               ✅  source_data_status
```

437 测试。

---

## Phase 1.11 执行结果（2026-05-14）

### P1.11-A：API 致命错误熔断
- `http.py` 新增 `FatalApiError`（401/402/403）
- `get_json()` 拦截 → 致命抛 `FatalApiError`，非致命（429/5xx）保留原异常
- FP 首次 `FatalApiError` 立即熔断（原来 24 次请求 → 1 次）

### P1.11-B：OMDb 多 Key 轮转
- secrets: `api_key` → `api_keys: ["key1", "key2"]`，向后兼容
- 401/403 → 标记失效 → 下一个 key → 全部耗尽 → 熔断
- 修复 cache source 参数（OMDb 缓存命中率从 0% 恢复）

458 测试。

---

## Phase 1.12 执行结果（2026-05-14）

```
P1.12-A（TMDb namespace 闭环）        ✅ migration 013
P1.12-B（dry-run 不写业务结果）        ✅
P1.12-C（OMDb key 日志脱敏）           ✅
P1.12-D（PyYAML 依赖声明）             ✅
P1.12-E（多新季汇总修复）              ✅
P1.12-F（Secrets 路径迁移）            ✅ config.py
```

478 测试。

### P1.12-A：TMDb namespace 闭环
- `_lookup_canonical_id()` 严格按 media_type 查询
- external_id 写入带 `tv:`/`movie:`/`unknown:` 前缀
- Migration 013 清理裸 TMDb ID（先删冲突，再 update）

### P1.12-F：Secrets 路径迁移
- 新路径 `~/.config/movietrace/secrets.json`
- fallback `/tmp/movietrace_phase0_secrets.json` + deprecation warning
- 新增 `config.py` 统一入口

---

## Phase 1.13 执行结果（2026-05-14）

- Migration 014：`content_updates` 事件历史化
- `ux_content_updates_item_type` → `ux_content_updates_update_id`
- `content_update_id` 格式：`discovery:{movie|tv}:{tmdb_id}:{snapshot_date}`
- 跨天同内容 → 不同 ID → 多条事件
- 同天同 ID → insert or ignore 幂等
- 测试：495 passed
