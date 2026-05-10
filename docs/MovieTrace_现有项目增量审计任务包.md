# MovieTrace 现有项目增量审计与下一步任务包

## 0. 任务定位

你是 MovieTrace 项目的代码审计助手和增量开发顾问。

当前项目已经在进行中，不是从零开始的新项目。不要重新设计架构，不要创建平行目录，不要把已有项目推倒重来。

项目名：

```text
MovieTrace
```

主包路径：

```text
src/movietrace/
```

本轮任务目标：

1. 理解当前项目状态。
2. 核对已有实现和文档是否一致。
3. 找出当前阶段最小缺口。
4. 给出增量开发计划。
5. 只在现有结构上补强，不另起炉灶。

---

## 1. 当前项目状态摘要

根据当前项目快照，项目状态如下：

```text
Phase 0：开发前验证         已完成，Go 决策
Phase 0+：FlixPatrol 验证   准备中或进行中，需要核对实际代码和报告
Phase 1：V1 MVP 开发         待 Phase 0+ 通过后进入
```

当前数据库状态：

```text
data/movietrace.db
├── baseline_items:           855 条
├── canonical_items:          826 条，约 96.6%
├── external_ids:             826 条
├── match_candidates:         855 条
└── baseline_quality_issues:  29 条，待人工修正基线
```

当前核心产品目标：

```text
每日产出“值得更新”的影视内容列表，供运营人工审核。
```

V1 数据源限定：

```text
TMDb API
Trakt API
OMDb API
FlixPatrol 公开页面，需合规验证通过
飞书 baseline 数据
```

V1 技术边界：

```text
Python 3.12
SQLite
现有依赖
.env + config.yaml
飞书多维表格作为人工协作界面
```

明确不要做：

```text
不要引入 PostgreSQL
不要引入 Redis
不要引入 Celery
不要引入 FastAPI
不要引入 React
不要做复杂后台
不要做 LLM 推荐
不要做多 Agent 推理框架
不要做 IMDb 页面抓取
不要绕过登录、验证码、付费墙、反爬
```

---

## 2. 现有目录结构理解

当前项目已有如下关键结构：

```text
src/movietrace/db/schema.py
src/movietrace/sources/http.py
src/movietrace/sources/flixpatrol.py
src/movietrace/sources/tmdb.py
src/movietrace/sources/omdb.py
src/movietrace/sources/trakt.py
src/movietrace/pipeline/baseline_import.py
src/movietrace/pipeline/entity_matching.py
src/movietrace/pipeline/canonical_promotion.py
src/movietrace/feishu/baseline.py
```

测试已有：

```text
tests/test_baseline_import.py
tests/test_canonical_promotion.py
tests/test_database_schema.py
tests/test_entity_matching.py
tests/test_flixpatrol_parsing.py
tests/test_source_clients.py
```

文档已有：

```text
STATE.md
SCOPE.md
AGENTS.md
CLAUDE.md
docs/requirements.md
docs/product_roadmap.md
docs/local_database_architecture.md
docs/next_steps_plan.md
docs/phase0_supplement.md
docs/decisions/
reports/
journal/
```

重要结论：

这个项目已经有主包、数据库层、数据源层、pipeline 层、测试体系和架构决策记录。

所以后续不能使用从零项目结构：

```text
app/
app/core/
app/infra/
app/clients/
app/jobs/
```

也不能创建：

```text
movie-trend-ops/
```

---

## 3. 旧任务包需要废弃或改写的部分

如果之前存在从零启动任务包，请不要直接执行。

以下旧建议不适合当前项目：

| 旧建议 | 当前项目正确做法 |
|---|---|
| 新建 `app/infra/cached_http_client.py` | 应检查并扩展 `src/movietrace/sources/http.py` |
| 新建 `app/clients/tmdb_client.py` | 应检查并扩展 `src/movietrace/sources/tmdb.py` |
| 新建 `app/clients/flixpatrol_client.py` | 应检查并扩展 `src/movietrace/sources/flixpatrol.py` |
| 新建 `models.py` / SQLAlchemy schema | 应基于 `src/movietrace/db/schema.py` 的 sqlite3 schema |
| 新建 `jobs/` 定时任务目录 | 当前应优先基于 `src/movietrace/pipeline/` 增量扩展 |
| 引入 `requests-cache` / `tenacity` | 当前 ADR-0005 显示 SUP-A 仅 stdlib，不应随意新增依赖 |
| 新建 `trend_snapshots` / `trend_items` | 当前已有 `source_records`、`content_updates`、`match_candidates`、`api_cache`，先评估是否复用 |
| 让 FlixPatrol client 从零实现 | `src/movietrace/sources/flixpatrol.py` 已存在解析逻辑，先审计再补强 |

---

## 4. 必须先阅读的文件

编码前，必须先阅读并总结以下文件。

### 4.1 项目状态与边界

```text
STATE.md
SCOPE.md
AGENTS.md
CLAUDE.md
requirements.txt
config/config.example.yaml
```

重点确认：

1. 当前阶段。
2. 当前禁止事项。
3. 当前依赖边界。
4. Agent 协作规范。
5. 是否允许新增依赖。
6. 是否允许修改数据库 schema。

### 4.2 产品与实施规划

```text
docs/requirements.md
docs/product_roadmap.md
docs/next_steps_plan.md
docs/phase0_supplement.md
docs/local_database_architecture.md
```

重点确认：

1. V1 目标。
2. hot_score 公式。
3. FlixPatrol 在 V1 中的定位。
4. Phase 0+ 是否已经完成。
5. Phase 1 是否可以启动。

### 4.3 架构决策记录

```text
docs/decisions/0001-feishu-baseline-as-marker-not-filter.md
docs/decisions/0002-v1-v2-strict-separation.md
docs/decisions/0003-flixpatrol-as-v1-data-source.md
docs/decisions/0004-phase0-medium-no-auto-promotion.md
docs/decisions/0005-sup-a-stdlib-only.md
```

重点确认：

1. 飞书 baseline 是标记，不是过滤条件。
2. V1 / V2 严格分离。
3. FlixPatrol 是 V1 数据源。
4. Phase 0 medium 不自动 promotion。
5. SUP-A 是否仍限制 stdlib-only。

### 4.4 现有代码

```text
src/movietrace/db/schema.py
src/movietrace/sources/http.py
src/movietrace/sources/flixpatrol.py
src/movietrace/sources/tmdb.py
src/movietrace/sources/omdb.py
src/movietrace/sources/trakt.py
src/movietrace/pipeline/baseline_import.py
src/movietrace/pipeline/entity_matching.py
src/movietrace/pipeline/canonical_promotion.py
```

重点确认：

1. schema 当前有哪些表。
2. api_cache 是否已经可用。
3. source_records 是否已经可保存原始来源记录。
4. http.py 当前是否支持 timeout、headers、错误处理。
5. flixpatrol.py 当前只解析 HTML，还是已经负责访问和缓存。
6. tmdb.py 当前只有 search/multi，还是已有 details/external_ids/watch providers。
7. entity_matching.py 当前的匹配规则和置信度逻辑。
8. canonical_promotion.py 是否会自动 promotion，是否受 ADR-0004 限制。

### 4.5 测试

```text
tests/test_database_schema.py
tests/test_source_clients.py
tests/test_flixpatrol_parsing.py
tests/test_entity_matching.py
tests/test_canonical_promotion.py
tests/test_baseline_import.py
```

重点确认：

1. 当前测试如何运行。
2. 是否使用 unittest 还是 pytest。
3. 是否已经有 FlixPatrol fixtures。
4. 是否已有 source client mock。
5. 新增修改不能破坏现有测试。

---

## 5. 当前代码层面的初步判断

以下判断来自当前项目快照，编码前仍需用实际文件复核。

### 5.1 数据库

当前 `src/movietrace/db/schema.py` 使用 `sqlite3` 和原生 SQL，不是 SQLAlchemy。

已有表包括：

```text
schema_migrations
feishu_import_runs
source_records
canonical_items
external_ids
baseline_items
content_updates
match_candidates
api_cache
```

因此：

- 不要引入 SQLAlchemy。
- 不要新建第二套 schema。
- 不要直接照搬 `titles / trend_snapshots / trend_items` 那套表。
- 如果要存 FlixPatrol 榜单，应优先评估复用 `source_records`、`api_cache`、`content_updates`。
- 如果确实需要新增 `flixpatrol_charts` 表，必须先写 schema 变更说明和测试。

### 5.2 HTTP 层

当前 `src/movietrace/sources/http.py` 使用 stdlib：

```text
urllib.request.Request
urllib.request.urlopen
json.loads
```

已有能力：

```text
GET JSON
query params
headers
timeout
```

明显缺口可能包括：

```text
统一 User-Agent
HTTPError / URLError 分类
429 处理
5xx 重试
响应缓存
非 JSON 响应处理
日志
```

但注意：当前 ADR-0005 显示 SUP-A 任务包仅使用 stdlib，不引入新依赖。所以不要擅自加入 `requests-cache` 或 `tenacity`。

如果要补强，优先使用 stdlib：

```text
urllib.error.HTTPError
urllib.error.URLError
time.sleep
指数退避
sqlite api_cache
```

### 5.3 FlixPatrol

当前 `src/movietrace/sources/flixpatrol.py` 已存在，并且已经实现了 HTML 解析函数：

```text
parse_top10_page(html, platform, region)
```

它支持提取：

```text
rank
title
platform
region
content_type
week_date
days_in_top10
points
```

因此：

- 不要再把 `flixpatrol.py` 当作“新建文件”。
- 下一步应审计它是否只负责解析，还是也包含访问和缓存。
- 如果只负责解析，可以在同文件或相邻模块中补充“受控获取页面”的函数。
- 解析器已有 fixtures 和测试，应优先扩展测试，不要破坏现有格式。

### 5.4 TMDb

当前 `src/movietrace/sources/tmdb.py` 已有：

```text
TmdbSearchClient
search/multi
parse_tmdb_search_results
```

它目前主要服务于 baseline entity matching。

现有返回结构是：

```text
ExternalSearchResult(
    source="tmdb",
    external_id=tmdb_id,
    title=title/name,
    media_type=movie/tv,
    year=release_date/first_air_date,
    score=popularity,
    raw_payload=item
)
```

明显可能缺口：

```text
movie details
tv details
external_ids
watch/providers
images
videos
trending
```

但不要一次性全加。应根据 Phase 0+ / Phase 1 当前目标决定。

### 5.5 Pipeline

当前已有：

```text
baseline_import.py
entity_matching.py
canonical_promotion.py
```

这说明项目已经有：

```text
飞书 baseline 导入
实体匹配
canonical item 晋升
```

下一步若做发现和评分，应放在：

```text
src/movietrace/pipeline/discovery.py
src/movietrace/pipeline/scoring.py
```

但只有在 Phase 0+ 通过后再做 Phase 1 discovery/scoring。

---

## 6. 本轮不要做的事

本轮不要：

1. 不要重构目录。
2. 不要新建 `app/`。
3. 不要新建 `movie-trend-ops/`。
4. 不要迁移到 SQLAlchemy。
5. 不要把 SQLite schema 改成 ORM。
6. 不要加入 Celery、Redis、PostgreSQL。
7. 不要加入 FastAPI、React。
8. 不要加入 LLM 推荐。
9. 不要直接实现 APScheduler。
10. 不要直接实现完整每日自动化。
11. 不要高频抓取 FlixPatrol。
12. 不要绕过 FlixPatrol 合规边界。
13. 不要抓 IMDb 页面。
14. 不要自动 promotion medium/no_match 项。
15. 不要覆盖人工字段。
16. 不要把 baseline 当过滤条件。
17. 不要直接使用旧任务包中的从零架构。

---

## 7. 本轮审计任务

请先完成一次现状审计，不要直接写代码。

输出以下内容：

```md
# MovieTrace 当前项目审计报告

## 1. 当前项目阶段判断

说明项目现在到底处于：
- Phase 0 已完成
- Phase 0+ 准备中
- Phase 0+ 已部分完成
- Phase 1 是否可以启动

需要对比 STATE.md、reports/、docs/tasks/、现有代码实际状态。

## 2. 当前目录结构理解

说明：
- db 层负责什么
- sources 层负责什么
- pipeline 层负责什么
- feishu 层负责什么
- tests 当前覆盖什么

## 3. 当前数据库结构

列出现有表：

- schema_migrations
- feishu_import_runs
- source_records
- canonical_items
- external_ids
- baseline_items
- content_updates
- match_candidates
- api_cache
- 其他实际存在表

说明每张表用途，以及是否足够支持 FlixPatrol 接入。

## 4. 当前数据流

画出当前已实现数据流：

```text
飞书节目表
-> baseline_items
-> TMDb / Trakt / OMDb 搜索匹配
-> match_candidates
-> canonical_items
-> external_ids
```

再说明 FlixPatrol 目前在数据流中处于什么状态。

## 5. 当前 FlixPatrol 实现状态

回答：

1. `src/movietrace/sources/flixpatrol.py` 目前只是解析器，还是已经包含访问逻辑？
2. 当前解析器支持哪些页面格式？
3. 当前 tests/fixtures 覆盖哪些平台？
4. 当前是否已经有 accessibility report / parsing report / matching report？
5. 当前是否还需要 SUP-A？
6. 如果 SUP-A 已实际完成，STATE.md 是否需要更新？

## 6. 当前 HTTP 层状态

回答：

1. `src/movietrace/sources/http.py` 是否有 timeout？
2. 是否有统一 User-Agent？
3. 是否有 HTTPError / URLError 分类？
4. 是否有 429 / 5xx 重试？
5. 是否接入 `api_cache`？
6. 是否符合 ADR-0005 的 stdlib-only 限制？

## 7. 当前 TMDb 层状态

回答：

1. 是否只有 search/multi？
2. 是否支持 details？
3. 是否支持 external_ids？
4. 是否支持 watch providers？
5. 是否支持 trending？
6. 当前是否应该扩展，还是等 Phase 1？

## 8. 当前测试覆盖

列出当前测试文件，每个测试覆盖什么。

说明新增修改应该补哪些测试。

## 9. 当前文档与代码不一致点

重点检查：

1. STATE.md 是否说 SUP-A 待启动，但 reports 里已有 FlixPatrol 报告？
2. next_steps_plan.md 是否说 `flixpatrol.py` 新建，但文件已经存在？
3. docs/tasks 和实际代码是否同步？
4. 数据库文档是否落后于 schema.py？
5. 是否需要更新 STATE.md / next_steps_plan.md / docs/tasks？

## 10. 当前最小缺口

请只列最小缺口，不要展开大重构。

可能包括：

- 更新 STATE.md，使其和实际代码、reports 对齐。
- 补充 FlixPatrol 页面抓取函数。
- 把 FlixPatrol HTML 解析结果写入 SQLite。
- 使用 api_cache 做 24 小时缓存。
- 为 HTTP 层增加 stdlib 重试和错误分类。
- 为 FlixPatrol 接入补测试。
- 明确 Phase 0+ 是否 Go。

## 11. 建议下一步任务拆分

请给出 3 个以内的小任务，每个任务都要包含：

- 目标
- 修改文件
- 不修改文件
- 验收方式
- 测试命令
- 风险点

不要一次性给 10 个任务。

## 12. 不建议改动的部分

列出当前不应改动的文件和原因。
```

---

## 8. 建议的最小增量开发方向

在审计完成前，不要直接执行。以下只是候选方向。

### 任务 A：项目状态同步

目标：

让文档状态和实际代码、reports 对齐。

可能修改：

```text
STATE.md
docs/next_steps_plan.md
docs/tasks/sup_a_flixpatrol_accessibility.md
```

不修改：

```text
src/
schema.py
tests/
```

验收：

```text
文档能准确反映 FlixPatrol 已做到哪一步。
新 Agent 不会误以为 flixpatrol.py 仍需新建。
```

### 任务 B：FlixPatrol 获取 + 缓存最小闭环

目标：

在不引入新依赖的前提下，实现 FlixPatrol 页面获取、24 小时缓存、礼貌访问频率、错误处理。

可能修改：

```text
src/movietrace/sources/http.py
src/movietrace/sources/flixpatrol.py
src/movietrace/db/schema.py
tests/test_source_clients.py
tests/test_flixpatrol_parsing.py
```

注意：

如果 `api_cache` 足够，不新增表。只有当 `api_cache` 无法表达 FlixPatrol 榜单结构时，才考虑新增表。

验收：

```bash
python3 -m unittest discover -s tests
```

或者如果项目已使用 pytest：

```bash
pytest
```

### 任务 C：FlixPatrol 解析结果入库

目标：

把解析后的 Top 10 item 作为 source_records 或 content_updates 的候选输入保存，后续供 discovery/scoring 使用。

可能修改：

```text
src/movietrace/pipeline/
src/movietrace/db/schema.py
tests/
```

注意：

不要自动 promotion。
不要自动写飞书。
不要把未匹配项强行合并到 canonical_items。

验收：

```text
给定 fixtures HTML，能解析并写入本地 SQLite。
重复运行不重复写入。
失败时有日志。
```

---

## 9. 对旧架构建议的吸收方式

可以吸收的思想：

```text
统一 HTTP 出口
缓存
超时
错误分类
重试
ID 映射
榜单快照
原始响应保存
任务幂等
```

但必须按当前项目方式落地：

```text
统一 HTTP 出口 -> src/movietrace/sources/http.py
缓存 -> 现有 api_cache 表，而不是 requests-cache
TMDb client -> src/movietrace/sources/tmdb.py
FlixPatrol client -> src/movietrace/sources/flixpatrol.py
ID 映射 -> external_ids + entity_matching.py
原始响应 -> source_records / api_cache
候选列表 -> content_updates / match_candidates，或经审计后新增最小表
```

---

## 10. 参考项目和链接

以下链接只用于参考设计思路，不能直接复制代码。

### GitHub 参考仓库

```text
leandcesar/themoviedb
https://github.com/leandcesar/themoviedb
```

用途：

- 学 TMDb API client 分层。
- 参考 trending/details/external_ids/watch_providers 的封装边界。

```text
transitive-bullshit/populate-movies
https://github.com/transitive-bullshit/populate-movies
```

用途：

- 学批处理、归一化、外部 ID、upsert、幂等重跑。
- 不复制完整 schema。

```text
cedya77/aiometadata
https://github.com/cedya77/aiometadata
```

用途：

- 只研究缓存策略、ID mapping、图片语言选择、错误分类。
- 注意：GPL-3.0，严禁复制代码。

### 官方文档

```text
TMDb API 文档
https://developer.themoviedb.org/docs
```

```text
TMDb append_to_response
https://developer.themoviedb.org/docs/append-to-response
```

```text
FlixPatrol API v2
https://flixpatrol.com/api2/
```

```text
FlixPatrol rankings endpoint
https://flixpatrol.com/api2/endpoint-rankings/
```

```text
FlixPatrol TOP 10s endpoint
https://flixpatrol.com/api2/endpoint-top10s/
```

说明：

当前 V1 仍以 FlixPatrol 公开页面为验证对象。如果要改用官方 API，必须先由用户确认调用预算和接口价值，不要擅自切换实现路线。

---

## 11. 本轮输出要求

请只输出审计报告，不要直接大规模改代码。

输出格式：

```md
# MovieTrace 当前项目审计报告

## 1. 当前项目阶段判断
## 2. 当前目录结构理解
## 3. 当前数据库结构
## 4. 当前数据流
## 5. 当前 FlixPatrol 实现状态
## 6. 当前 HTTP 层状态
## 7. 当前 TMDb 层状态
## 8. 当前测试覆盖
## 9. 当前文档与代码不一致点
## 10. 当前最小缺口
## 11. 建议下一步任务拆分
## 12. 不建议改动的部分
```

完成审计后，等待用户确认下一步。不要自己直接进入 Phase 1。
