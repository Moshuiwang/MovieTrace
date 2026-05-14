# MovieTrace 代码 Review 报告

报告时间：2026-05-14 08:07 +08  
审查人：Codex（system prompt 标识：Codex, a coding agent based on GPT-5）  
审查范围：`src/movietrace/`、关键测试、DB schema/migrations、当前未提交 diff  
当前阶段：Phase 1.8 已完成，当前工作区仍有未提交源码改动

---

## 结论摘要

本次审查发现当前代码存在 **2 个会直接导致 CLI / pipeline 失败的问题**，以及多处会影响推荐准确性、API 成本统计、数据幂等语义和长期可维护性的设计漏洞。

优先修复顺序建议：

1. 修复 `run_discovery()` 的 `fp_stats` 未定义 / `None.get()` 崩溃。
2. 修复 `inspect-api-usage` 无过滤条件时拼出非法 SQL。
3. 修复 TMDb TV freshness 字段未写入，导致 `last_air_date` 方案实际未生效。
4. 修复 `baseline_tracking` 多新季时 `local_max_season` 回写错误。
5. 梳理 `content_updates` / `external_ids` 的唯一键语义，避免丢数据和错链。

---

## 严重问题

### CR-001：`run_discovery()` 当前会在评分统计阶段崩溃

级别：高  
类型：逻辑漏洞 / 回归缺陷  
位置：
- `src/movietrace/pipeline/discovery.py:147`
- `src/movietrace/pipeline/discovery.py:200`
- `src/movietrace/pipeline/discovery.py:442`
- `src/movietrace/pipeline/discovery.py:458`

问题：

`run_discovery()` 调用 `_ensure_fp_data(...)` 后没有接收返回值，但后面调用：

```python
stats = _compute_discovery_stats(scored, passed, enrich_stats, fp_stats)
```

此处 `fp_stats` 未定义，会触发 `NameError`。同时 `_compute_discovery_stats(..., fp_stats=None)` 的默认参数也不安全，函数内部直接调用 `fp_stats.get(...)`，会触发 `AttributeError`。

验证证据：

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/test_discovery.py tests/integration/test_daily_discover_pipeline.py -q

3 failed, 15 passed
- NameError: name 'fp_stats' is not defined
- AttributeError: 'NoneType' object has no attribute 'get'
```

影响：

- `daily-discover` 只要进入评分统计阶段就可能失败。
- 当前工作区无法声明 Phase 1.8 全链路健康。
- 相关回归测试已经能稳定复现。

建议：

- `fp_stats = _ensure_fp_data(...)`。
- `_compute_discovery_stats()` 内部先做 `fp_stats = fp_stats or {}`。
- 加回归测试覆盖 `fp_stats=None` 和 `run_discovery(dry_run=True)`。

---

### CR-002：`inspect-api-usage` 不带过滤条件时 SQL 语法错误

级别：高  
类型：逻辑漏洞 / CLI 可用性  
位置：
- `src/movietrace/cli.py:622`
- `src/movietrace/cli.py:627`
- `src/movietrace/cli.py:628`
- `src/movietrace/cli.py:631`
- `src/movietrace/cli.py:635`
- `src/movietrace/cli.py:638`

问题：

当没有 `--date` / `--days` / `--service` 条件时，`where = ""`，但后续 SQL 仍拼接：

```sql
select count(*) from api_usage_log AND status='success'
```

这是非法 SQL。

验证证据：

```text
PYTHONPATH=src .venv/bin/python -m movietrace.cli inspect-api-usage --format json

sqlite3.OperationalError: near "AND": syntax error
```

带过滤条件时可运行：

```text
PYTHONPATH=src .venv/bin/python -m movietrace.cli inspect-api-usage --date 2026-05-14 --format json

total=264, success=101, errors=163
```

影响：

- 新增 CLI 的默认用法不可用。
- API usage logging 的验收面不完整。

建议：

- 构造 `base_where` 和 `and_clause`，或统一把条件列表扩展为 `where_for_status = conditions + ["status = ?"]`。
- 增加无参数、按日期、按 service 三类 CLI 测试。

---

## 重要逻辑漏洞

### CR-003：TV freshness 号称使用 `last_air_date`，但采集链路没有写入该字段

级别：高  
类型：业务逻辑漏洞 / 推荐准确性  
位置：
- `src/movietrace/db/migrations/009_tmdb_structured_fields.sql:15`
- `src/movietrace/sources/tmdb.py:303`
- `src/movietrace/sources/tmdb.py:322`
- `src/movietrace/pipeline/tmdb_trending.py:55`
- `src/movietrace/pipeline/tmdb_trending.py:56`
- `src/movietrace/pipeline/multi_source_merge.py:88`
- `src/movietrace/pipeline/discovery.py:245`

问题：

schema 增加了 `last_air_date` / `last_episode_air_date`，`discovery` 也按这些字段计算 TV freshness；但 `normalize_tmdb_trending_row()` 和 `fetch_and_store_tmdb_trending()` 插入字段时没有填充 `last_air_date` / `last_episode_air_date`。当前 DB 中也能看到这些列为空：

```text
select count(*), sum(last_air_date is not null), sum(last_episode_air_date is not null) from tmdb_trending;
372|0|0

media_type=tv: count=180, first_air_date=85, last_air_date=0
```

影响：

- P1.8-C 的核心目标“TV freshness 使用 last_air_date”实际未落地。
- 老剧新季仍可能按 `first_air_date` 扣分，影响 hot_score 和 P2+ 筛选。

建议：

- 明确字段来源：trending/popular payload 没有 `last_air_date` 时，应通过 TMDb detail 批量补写，或在评分前对 TV 候选强制 detail enrich。
- `enrich_with_tmdb_details()` 当前在已有 `release_date` 和 `original_language` 时跳过 detail，应针对 TV freshness 调整跳过条件。
- 增加以 FROM / Silo 这类新季剧为样例的回归测试。

---

### CR-004：多新季检测时 `local_max_season` 只会更新到第一条新季

级别：中高  
类型：幂等漏洞 / 重复告警  
位置：
- `src/movietrace/pipeline/baseline_tracking.py:61`
- `src/movietrace/pipeline/baseline_tracking.py:63`
- `src/movietrace/pipeline/baseline_tracking.py:213`
- `src/movietrace/pipeline/baseline_tracking.py:217`

问题：

当本地 `local_max_season=1`，TMDb `number_of_seasons=3` 时，`detect_new_seasons()` 会生成 S2、S3 两个事件；但 `run_baseline_tracking()` 使用 `seen_vs`，只对该 virtual series 的第一条 event 调用：

```python
update_local_max_season(conn, event.virtual_series_id, event.new_season_number)
```

因此 `local_max_season` 会被写成 2，而不是 3。

影响：

- 下一次 baseline tracking 会再次检测到 S3。
- 新季告警可能重复出现。
- `content_updates` 的幂等状态与 `virtual_series.local_max_season` 不一致。

建议：

- 按 `virtual_series_id` 聚合事件后写入该组最大的 `new_season_number`。
- 增加“local=1, tmdb=3”的回归测试。

---

### CR-005：`content_updates` 的唯一键会丢失同一内容的后续发现记录

级别：中高  
类型：数据模型漏洞 / 业务语义不清  
位置：
- `src/movietrace/db/schema.py:96`
- `src/movietrace/db/schema.py:110`
- `src/movietrace/pipeline/discovery.py:398`
- `src/movietrace/pipeline/discovery.py:407`

问题：

`content_update_id` 包含日期：

```python
content_update_id = f"discovery:{tmdb_id}:{snapshot_date}"
```

但唯一索引是：

```sql
unique(canonical_item_id, update_type)
```

这意味着同一个 canonical item 的 `new_discovery` 只能写入一次。后续日期即使热度变化、来源变化、分数变化，也会被 `insert or ignore` 静默忽略。

同时 `_write_content_updates()` 在 `insert or ignore` 后无论是否真正插入都 `count += 1`，会导致 `written` 统计虚高。

影响：

- “热度变化追踪”语义不成立。
- dry-run / CLI 输出的 written 数量不可信。
- 审核清单无法表达同一内容跨日趋势。

建议：

- 明确产品语义：若只保留一条状态记录，应改为 `upsert` 并更新 `hot_score/source_summary_json/updated_at`；若要保留每日发现，应把 `snapshot_date` 或 `content_update_id` 纳入唯一键。
- 统计写入数量时使用 `cursor.rowcount` 或 `conn.total_changes`。

---

### CR-006：TMDb 外部 ID 没有区分 movie / tv 命名空间，存在错链风险

级别：中  
类型：数据一致性漏洞  
位置：
- `src/movietrace/db/schema.py:61`
- `src/movietrace/db/schema.py:70`
- `src/movietrace/pipeline/discovery.py:430`
- `src/movietrace/pipeline/entity_matching.py:1245`

问题：

TMDb movie 和 TV 是不同命名空间，数字 ID 可重复。但 `external_ids` 唯一键只有：

```sql
unique(source, external_id)
```

`_lookup_canonical_id()` 查询也只用：

```sql
where source = 'tmdb' and external_id = ?
```

虽然写入时有 `external_granularity`，但它没有进入唯一键和查询条件。

影响：

- 如果 TMDb movie 和 TV 出现相同 numeric ID，可能复用错误 canonical item。
- `content_updates` 可能写到错误内容上。

建议：

- TMDb external_id 统一存成 `tv:<id>` / `movie:<id>`，或把 `external_granularity` 纳入唯一键和查询条件。
- 为 `_lookup_canonical_id(conn, tmdb_id, media_type)` 增加 media_type 参数。

---

## 安全风险

### CR-007：密钥存储路径固定在 `/tmp`，不适合作为长期 secrets 位置

级别：中  
类型：密钥管理风险  
位置：
- `src/movietrace/cli.py:372`
- `src/movietrace/cli.py:379`
- `src/movietrace/sources/flixpatrol_api.py:15`
- `src/movietrace/pipeline/discovery.py:463`

问题：

项目多处硬编码 `/tmp/movietrace_phase0_secrets.json`。`/tmp` 在多用户系统中语义上不是长期秘密存储目录，且容易被清理或被错误权限创建。

正向观察：

- 本次 `git ls-files` 未发现 `data/`、`source_records/`、真实 DB 或 secrets 被跟踪。
- `.gitignore` 已覆盖 `.env`、`data/`、`*.db`、`source_records/`。

建议：

- 改用环境变量或 `~/.config/movietrace/secrets.json`，启动时检查权限为 `0600`。
- 将 secrets path 收敛到一个配置函数，避免多处硬编码。

---

### CR-008：API usage 日志脱敏不够稳健

级别：中  
类型：日志泄露风险  
位置：
- `src/movietrace/logging/api_usage.py:49`
- `src/movietrace/logging/api_usage.py:90`
- `src/movietrace/logging/api_usage.py:98`
- `src/movietrace/sources/http.py:93`
- `src/movietrace/sources/http.py:118`

问题：

当前只对 `metadata` 的顶层 key 做过滤，且 key 归一化后 `"access_token"` 会变成 `"accesstoken"`，但禁用集合里保留的是 `"access_token"`，存在漏过滤。类似 `client_secret`、嵌套 dict/list、URL query 中的 `apikey` 也没有统一脱敏。

`error_message` 直接保存 `str(exc)`，没有走脱敏函数。当前 urllib 的常见 HTTPError 通常不包含完整 URL，但这是依赖库行为，不应作为安全边界。

建议：

- 对 metadata 和 error_message 统一做递归脱敏。
- 禁用 key 使用同一种 normalize 结果，例如 `apikey`、`authorization`、`accesstoken`、`clientsecret`。
- 增加 `error_message` 包含 `apikey=...` / `Authorization: Bearer ...` 的测试。

---

### CR-009：Feishu 验证命令仍打印 token 前缀，且 Feishu 代码与当前定位不一致

级别：低到中  
类型：信息泄露 / 陈旧代码  
位置：
- `src/movietrace/cli.py:133`
- `src/movietrace/cli.py:158`
- `src/movietrace/cli.py:295`

问题：

`validate-feishu` 打印 `token[:8]`。虽然不是完整 token，但没有实际诊断必要。更重要的是，STATE 中说明飞书已从主链路移除，但 CLI 中仍保留 Feishu 验证和 schema 检查命令。

建议：

- 不打印 token 前缀，只输出“token 获取成功”。
- 若 Feishu 已退出主链路，把相关命令迁到 legacy/debug 区，或在 help 文案中标注历史用途。

---

## 测试与验证风险

### CR-010：部分 dry-run / integration test 会读取真实 secrets 并访问真实 API

级别：中  
类型：测试不隔离 / 成本与稳定性风险  
位置：
- `tests/integration/test_daily_discover_pipeline.py:104`
- `tests/integration/test_daily_discover_pipeline.py:113`
- `src/movietrace/pipeline/discovery.py:159`
- `src/movietrace/pipeline/discovery.py:166`
- `src/movietrace/pipeline/discovery.py:172`
- `src/movietrace/pipeline/discovery.py:176`

问题：

集成测试说明使用 synthetic data，但 `run_discovery()` 内部会读取 `/tmp/movietrace_phase0_secrets.json`，如果存在真实 token，就会在测试中执行 TMDb / OMDb 请求。本次测试日志中出现真实 HTTP 401 / 404，并耗时 143.53 秒。

影响：

- CI 或本地测试结果受网络、配额、密钥状态影响。
- 测试可能消耗生产 API 预算。
- dry-run 语义不等于“不访问外部服务”。

建议：

- `run_discovery()` 支持显式注入 secrets 或 clients。
- integration test 默认禁用外部 enrich，或 mock `_load_secrets()` / clients。
- 区分 `--dry-run`（不写 DB）和 `--offline`（不访问外部 API）。

---

## Clean Code 问题

### CC-001：文件和函数职责过大

位置：
- `src/movietrace/pipeline/entity_matching.py`：1290 行
- `src/movietrace/cli.py`：798 行
- `src/movietrace/pipeline/discovery.py`：467 行

问题：

`entity_matching.py` 同时包含 title parsing、搜索、匹配、质量问题表管理、A 库匹配、CLI 入口等职责。`cli.py` 同时负责配置读取、secrets 读取、真实业务编排、输出格式和多条历史命令。

建议：

- 将 `entity_matching.py` 拆分为 `title_parser.py`、`match_decider.py`、`quality_issues.py`、`upstream_matching.py`。
- 将 CLI handler 保持薄层，把业务编排移到 service/pipeline 模块。

---

### CC-002：重复的配置和 secrets 读取逻辑

位置：
- `src/movietrace/cli.py:362`
- `src/movietrace/cli.py:372`
- `src/movietrace/cli.py:379`
- `src/movietrace/pipeline/discovery.py:463`
- `src/movietrace/sources/flixpatrol_api.py:41`

问题：

同一 secrets path 和 config path 在多个模块重复实现，错误处理行为也不一致：有的返回 `{}`，有的直接抛错。

建议：

- 建立 `movietrace.config` 模块，集中处理 config/secrets 路径、权限检查、错误类型和脱敏输出。

---

### CC-003：陈旧注释和阶段标签降低可信度

位置示例：
- `src/movietrace/cli.py:23`：docstring 仍写 P1.7-D
- `src/movietrace/cli.py:44`：打印 `[1/6]`，后续又变成 `[2/5]`
- `src/movietrace/reports/daily_writer.py:150`：数据版本仍写 Phase 1.5
- `src/movietrace/pipeline/discovery.py:133`：docstring 写 P1.8，但内部步骤注释和真实 CLI 编排不完全一致

问题：

阶段标签散落在代码里，随着项目推进容易过期。当前已经出现 P1.5/P1.7/P1.8 混杂。

建议：

- 代码注释只解释稳定业务语义，阶段信息留在任务包、ADR、STATE。
- CLI step 数字由实际步骤列表生成，避免手工维护。

---

### CC-004：过多 `except Exception` 和静默 `pass`

位置示例：
- `src/movietrace/sources/http.py:79`
- `src/movietrace/sources/http.py:122`
- `src/movietrace/logging/api_usage.py:86`
- `src/movietrace/reports/daily_writer.py:295`
- `src/movietrace/sources/omdb.py:204`

问题：

部分异常被完全吞掉，或降为 debug。对于“API usage logging”这种用于审计预算和故障排查的能力，写入失败只打 debug 会使生产问题难以发现。

建议：

- 明确哪些异常可以吞，哪些要 warning。
- 日志写入失败可不阻断主链路，但应保留 warning 或计数指标。
- JSON 解析失败可以返回空，但建议把字段名和数据来源记入 debug。

---

### CC-005：硬编码业务默认值已经与当前策略不一致

位置：
- `src/movietrace/pipeline/scoring.py:25`
- `src/movietrace/pipeline/scoring.py:31`
- `src/movietrace/pipeline/scoring.py:162`
- `src/movietrace/pipeline/discovery.py:232`

问题：

P1.8-H 已将平台策略从 Hulu 切到 Paramount+，但默认 platform fallback 仍是 `"hulu"`，权重配置里也仍有 Hulu，没有 Paramount+。

影响：

- 非 FP 候选或未知平台候选会吃到 Hulu 权重。
- 配置和业务策略不一致，后续调参容易误判。

建议：

- 将平台权重完全交给 `config/scoring_weights.yaml`。
- unknown platform 使用显式 `"unknown"` 权重，而不是借用 Hulu。

---

## 已运行验证

```text
git status --short --branch
## main...origin/main [ahead 1]
 M src/movietrace/cli.py
 M src/movietrace/logging/api_usage.py
 M src/movietrace/pipeline/discovery.py
 M src/movietrace/sources/http.py
?? reports/session_2026-05-14_p1.8_dryrun_analysis.md
```

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/test_discovery.py tests/integration/test_daily_discover_pipeline.py -q
3 failed, 15 passed in 143.53s
```

```text
PYTHONPATH=src .venv/bin/python -m movietrace.cli inspect-api-usage --format json
sqlite3.OperationalError: near "AND": syntax error
```

```text
PYTHONPATH=src .venv/bin/python -m movietrace.cli inspect-api-usage --date 2026-05-14 --format json
成功输出 API usage JSON，total=264
```

```text
sqlite3 data/movietrace.db "select count(*), sum(case when last_air_date is not null then 1 else 0 end), sum(case when last_episode_air_date is not null then 1 else 0 end) from tmdb_trending;"
372|0|0
```

```text
PYTHONPATH=src .venv/bin/python -m pytest tests/test_api_usage_logging.py tests/test_scoring.py tests/pipeline/test_baseline_tracking.py -q
75 passed in 4.80s
```

```text
.venv/bin/python -m bandit -q -r src/movietrace
未运行成功：当前虚拟环境未安装 bandit
```

---

## 剩余风险

- 本次是静态审查加局部验证，不是完整渗透测试。
- 未对真实外部 API 的所有异常响应做系统性 fuzz。
- 未修改业务代码，因此上述失败仍然存在。
- 当前工作区已有他人未提交改动，本报告没有尝试回滚或修复这些改动。

---

## 建议后续任务拆分

1. P1.8-hotfix-A：修复 `run_discovery()` 和 `inspect-api-usage` 两个直接崩溃问题，并补回归测试。
2. P1.8-hotfix-B：补齐 TMDb TV detail enrichment，使 `last_air_date` 真正进入评分链路。
3. P1.8-hotfix-C：修复 baseline tracking 多新季回写和 content update 写入统计。
4. P1.9-data-model：重新审视 `external_ids` 与 `content_updates` 唯一键，形成 migration plan。
5. P1.9-cleanup：集中 config/secrets、瘦身 CLI、清理 Feishu legacy 命令与阶段注释。
