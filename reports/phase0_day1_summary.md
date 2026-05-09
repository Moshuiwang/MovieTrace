# MovieTrace Phase 0 Day 1 总结

日期：2026-05-09  
阶段：Phase 0 开发前验证  
当前结论：项目可以继续推进 Phase 0；架构已调整为本地 SQLite 作为事实源，飞书作为输入来源和可选协作视图。

## 1. 今日完成

### 1.1 飞书权限与读写验证

完成内容：

- 验证飞书 App 凭证可获取 `tenant_access_token`。
- 发现并解决 API scope 缺失问题。
- 验证可读取目标 base 下的数据表。
- 读取正式 `节目` 表字段和记录样本。
- 新建独立测试子表 `MovieTrace写入测试`。
- 在测试子表完成字段创建、记录写入、记录更新和回读。

沉淀文档：

- `docs/feishu_api_validation_notes.md`

关键经验：

- 多维表格内授权不等于开放平台 API scope 授权。
- App 凭证有效不代表目标表可访问。
- 写入测试必须使用测试表，不能污染正式 `节目` 表。
- 飞书建表和建字段要拆开，创建后应重新列出 tables 确认 `table_id`。

### 1.2 基线质量报告

完成内容：

- 全量读取飞书 `节目` 表。
- 生成 `reports/baseline_quality_report.md`。

关键数据：

| 指标 | 数值 |
| --- | ---: |
| 读取记录数 | 856 |
| `节目名` 非空 | 855 |
| 标题级弱基线比例 | 99.9% |
| 标题 + 状态弱基线比例 | 88.1% |
| 强实体基线比例 | 0.0% |
| 重复标题数量 | 81 |
| 涉及重复标题记录数 | 170 |

结论：

- 当前 `节目` 表业务价值高，但字段不是为程序读取设计。
- 当前只能形成标题级弱基线，不能直接用于 movie / season / episode 强自动去重。

### 1.3 节目库导出 Schema

完成内容：

- 在飞书 base 中新建 `MovieTrace节目库导出Schema` 子表。
- 写入 30 条字段定义。
- 新增 `docs/baseline_export_schema.md`。

用途：

- 指导后续完整节目库导出。
- 明确字段 key、中文名、类型、必填级别、来源、说明、示例和空值规则。

重要字段：

- `title`
- `content_type`
- `content_granularity`
- `season_number`
- `episode_number`
- `year`
- `tmdb_id`
- `imdb_id`
- `trakt_id`
- `online_status`
- `source_note`

### 1.4 TMDb / Trakt 连通性与实体匹配样本

完成内容：

- 保存并验证 TMDb Bearer Token 和 API Key。
- 保存并验证 Trakt Client ID / Secret。
- 发现 Trakt `extended=full` 在当前环境曾返回 `403 error code: 1010`。
- 改用普通 search / trending 端点验证成功。
- 生成 `reports/entity_matching_report.md`。

关键数据：

| 指标 | 数值 |
| --- | ---: |
| 样本数 | 100 |
| 解析出季号 | 94 |
| high 匹配 | 100 |
| medium | 0 |
| low | 0 |
| no_match | 0 |

注意：

- 100 条样本是前 100 条，标题质量较好，结果偏乐观。
- 不能直接推断全量 856 条都能达到同样质量。
- high 匹配仍需人工抽样复核。

### 1.5 架构调整：本地数据库作为事实源

背景：

- 飞书多维表格读写效率、字段约束和分页模型不适合作为核心数据库。
- 飞书更适合作为输入来源、字段对齐表和可选协作视图。

完成内容：

- 新增 `docs/local_database_architecture.md`。
- 更新以下文档中的架构表述：
  - `docs/requirements.md`
  - `docs/feasibility.md`
  - `docs/next_steps_plan.md`
  - `docs/operating_cost_estimate.md`
- 新增 SQLite schema 初始化代码。
- 新增测试。
- 初始化本地数据库 `data/movietrace.db`。

核心表：

- `baseline_items`
- `canonical_items`
- `external_ids`
- `content_updates`
- `match_candidates`
- `source_records`
- `api_cache`
- `feishu_import_runs`
- `schema_migrations`

### 1.6 飞书基线导入 SQLite

完成内容：

- 实现 `Feishu -> SQLite` 基线导入。
- 将正式 `节目` 表导入本地 `baseline_items`。
- 生成 `reports/baseline_import_report.md`。

关键数据：

| 指标 | 数值 |
| --- | ---: |
| 飞书读取记录数 | 856 |
| 成功导入 baseline_items | 855 |
| 跳过记录数 | 1 |
| 导入运行状态 | success |

状态分布：

| 状态 | 数量 |
| --- | ---: |
| 已下载 | 500 |
| 已上传FTP | 254 |
| 未知 | 101 |

粒度粗判：

| 粒度 | 数量 |
| --- | ---: |
| season | 741 |
| unknown | 114 |

## 2. 今日新增或更新的主要文件

文档：

- `docs/feishu_api_validation_notes.md`
- `docs/baseline_export_schema.md`
- `docs/local_database_architecture.md`
- `docs/requirements.md`
- `docs/feasibility.md`
- `docs/next_steps_plan.md`
- `docs/operating_cost_estimate.md`

报告：

- `reports/baseline_quality_report.md`
- `reports/entity_matching_report.md`
- `reports/baseline_import_report.md`
- `reports/phase0_day1_summary.md`

代码：

- `src/movietrace/db/schema.py`
- `src/movietrace/feishu/baseline.py`
- `src/movietrace/pipeline/baseline_import.py`
- `tests/test_database_schema.py`
- `tests/test_baseline_import.py`
- `config/config.example.yaml`

运行产物：

- `data/movietrace.db`

说明：

- `data/` 已加入 `.gitignore`，本地数据库不应提交。
- 真实密钥保存在 `/tmp/movietrace_phase0_secrets.json`，未进入仓库。

## 3. 验证结果

今日最终验证命令：

```bash
python3 -m unittest discover -s tests
```

结果：

```text
Ran 2 tests
OK
```

敏感信息检查：

- 已扫描 `docs/`、`reports/`、`src/`、`tests/`、`config/` 和 `.gitignore`。
- 未发现真实飞书、TMDb、Trakt 密钥写入仓库文件。

## 4. 剩余风险

1. 当前实体匹配只做了前 100 条样本，结果偏乐观。
2. `baseline_items.content_granularity` 只是基于标题 `Sxx` 的粗判。
3. 还没有把 TMDb / Trakt 全量匹配结果写入 `match_candidates`。
4. 还没有将确认后的实体写入 `canonical_items` 和 `external_ids`。
5. 当前重复导入策略是替换所有飞书来源 baseline 行，适合 Phase 0；后续如需历史快照，需要扩展策略。
6. App Secret、TMDb Token、Trakt Secret 曾在对话中出现，进入长期使用前建议轮换。

## 5. 明日建议顺序

建议明天按以下顺序继续：

1. 全量实体匹配 dry run：对 855 条 `baseline_items` 调用 TMDb / Trakt，写入 `match_candidates`。
2. 生成 `reports/full_entity_matching_report.md`，统计 high / medium / low / no_match。
3. 抽样人工复核 high 匹配准确率，目标 >= 95%。
4. 将通过规则确认的 high 匹配写入 `canonical_items` 和 `external_ids`。
5. 再开始最近 30 天 TV 候选发现 dry run。

推荐明日第一个任务包：

```text
任务名称：全量 baseline_items 实体匹配 dry run
任务类型：Phase 0 验证
目标：读取本地 SQLite 中 855 条 baseline_items，调用 TMDb / Trakt 搜索，写入 match_candidates，并生成 full_entity_matching_report.md
非目标：不自动改 canonical_items；不写飞书正式表；不做候选推荐
允许修改范围：src/、tests/、reports/
验证命令：python3 -m unittest discover -s tests
验收标准：match_candidates 有记录；报告包含置信度分布、API 错误、低置信度样本和人工复核建议
```

