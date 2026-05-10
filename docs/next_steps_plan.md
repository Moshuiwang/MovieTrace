# MovieTrace 下一步实施规划

状态：实施规划版  
日期：2026-05-08  
依据：[requirements.md](requirements.md)、[feasibility.md](feasibility.md)、[operating_cost_estimate.md](operating_cost_estimate.md)

## 1. 总体判断

下一步不建议直接开发完整系统。更稳妥的路线是先做 Phase 0 验证包，用最小代码证明三件事：

1. 飞书线上内容基线能稳定读取，并能形成可用于去重的 movie、season、episode 基线。
2. Trakt + TMDb 能发现最近 30 天足够有价值的英文电视剧更新候选。
3. 实体匹配、去重和优先级排序的误判率在人工可接受范围内。

原因很简单：MovieTrace 的主要不确定性不是能不能写代码，而是数据源覆盖、商业授权、飞书容量、线上内容表质量和 episode 级识别准确性。先验证这些，比先搭完整后台更有价值。

## 2. 推荐路线图

| 阶段 | 时间预估 | 目标 | 主要产物 | 是否进入下一阶段 |
| --- | --- | --- | --- | --- |
| Phase 0：开发前验证 | 1-2 周 | 证明数据、飞书、匹配和候选质量可行 | 验证脚本、验证报告、Go/No-Go 结论 | 达标后进入 Phase 1 |
| Phase 1：MVP 原型 | 1-2 周 | 打通 dry run 到飞书写入的最小闭环 | CLI、SQLite、本地报告、飞书推荐表写入 | 人工确认流程可用后进入 Phase 2 |
| Phase 2：冷启动追赶 | 1-2 周 | 追赶最近 180 天高价值更新 | bootstrap 模式、分批写入、bootstrap 汇总报告 | 候选规模和质量可控后进入 Phase 3 |
| Phase 3：每日自动化 | 1 周 | 每日稳定运行和日报 | daily 模式、定时任务、飞书日报 | 连续运行稳定后进入生产化 |
| Phase 4：生产化加固 | 持续 | 稳定、安全、可恢复 | 监控、备份、限流、错误告警、部署文档 | 达到长期运行条件 |
| Phase 5：数据源增强 | 视验证结果 | 提升平台可用性和热度准确度 | Netflix Top 10、Watchmode/JustWatch 评估 | 只有收益足够时做 |

## 3. 当前最应该做的事

当前应该优先做 Phase 0 验证包。它不是完整产品，而是一组可运行的小脚本和报告，用于回答“这个项目值不值得继续按 MVP 开发”。

### 3.1 Phase 0 的目标

Phase 0 需要回答以下问题：

| 问题 | 为什么重要 | 通过标准 |
| --- | --- | --- |
| 飞书线上内容表能否通过 API 稳定读取 | 它是冷启动和业务去重的基础 | 能分页读取，字段类型能解析 |
| 本地数据库能否作为事实源 | 飞书读写效率不适合作为核心数据库 | SQLite schema 可初始化，能承载基线、实体、外部 ID、候选和缓存 |
| 线上内容表字段质量如何 | 字段不完整会导致误过滤或重复推荐 | 抽样 100-300 条，至少 70% 可形成可用基线 |
| 线上内容能否匹配 TMDb/Trakt/IMDb ID | 没有外部 ID 会影响去重准确性 | 高置信度匹配准确率 >= 95% |
| 最近 30 天 TV 更新能否发现 | 这是核心业务价值 | 热门英文剧集、新季、新集能进入候选 |
| P0/P1 是否真的有用 | 避免每天给运营制造噪音 | 人工认可率 >= 60% |
| bootstrap 半年追赶规模是否可控 | 线上内容半年没更新，不能一次产生几千条 | P0/P1 控制在 200 条左右 |
| 飞书能否承载审核和批次状态 | 用户希望人工审核和批次在多维表格完成 | 推荐表、批次表、流转表能覆盖真实操作 |

### 3.2 Phase 0 应交付的文件

| 文件 | 内容 | 用途 |
| --- | --- | --- |
| `reports/baseline_quality_report.md` | 飞书线上内容表字段、缺失率、可匹配率、问题样本 | 判断基线是否能用于冷启动 |
| `reports/source_coverage_report.md` | 最近 30 天候选发现结果、来源覆盖、漏报和误报 | 判断 Trakt + TMDb 是否够用 |
| `reports/entity_matching_report.md` | 标题匹配、外部 ID 匹配、低置信度样本 | 判断自动去重风险 |
| `reports/bootstrap_dry_run_report.md` | 最近 180 天候选规模、P0/P1/P2 分布 | 判断半年追赶是否可控 |
| `reports/supplier_flow_check.md` | 推荐表、批次表、流转表字段是否覆盖真实流程 | 判断飞书后台是否够用 |
| `reports/go_no_go.md` | 继续、调整或暂停的结论 | 作为是否进入 MVP 开发的决策依据 |

### 3.3 Phase 0 应实现的最小脚本

| 脚本 | 作用 | 写入飞书 |
| --- | --- | --- |
| `movietrace validate-feishu` | 校验飞书 App 权限、表格访问、分页读取、字段类型 | 否，或只写测试表 |
| `movietrace inspect-baseline` | 读取线上内容表，输出字段质量和样本 | 否 |
| `movietrace match-baseline` | 将线上内容样本匹配到 TMDb/Trakt 外部 ID | 否 |
| `movietrace dry-run --days 30 --type tv` | 生成最近 30 天电视剧候选 | 否 |
| `movietrace bootstrap-dry-run --days 180` | 估算半年追赶候选规模 | 否 |
| `movietrace check-feishu-schema` | 检查推荐表、批次表、流转表字段是否存在 | 否 |

Phase 0 默认不向正式推荐表写入业务数据。即使需要测试写入，也应写入专门的测试表或测试视图。

## 4. Phase 0 详细任务拆分

### 4.1 任务 A：建立项目骨架和本地数据库

目标：让后续验证脚本有稳定结构，并建立 SQLite 事实源的初始 schema。

建议技术栈：

| 模块 | 建议 |
| --- | --- |
| 语言 | Python |
| CLI | Typer 或 argparse |
| HTTP | httpx |
| 配置 | `.env` + `config.yaml` |
| 本地存储 | SQLite |
| 日志 | 标准 logging，输出到 `logs/` |
| 报告 | Markdown |
| 测试 | pytest |

目录建议：

```text
movietrace/
  cli.py
  config.py
  db.py
  sources/
    tmdb.py
    trakt.py
  feishu/
    client.py
    bitable.py
  pipeline/
    baseline.py
    matching.py
    discovery.py
    scoring.py
  reports/
    writer.py
config/
  config.example.yaml
docs/
reports/
tests/
```

验收标准：

1. 可以安装依赖。
2. 可以运行 `movietrace --help`。
3. `.env` 不提交 GitHub。
4. `config.example.yaml` 只包含示例配置。
5. SQLite 数据库路径可配置。
6. 能初始化本地数据库，创建基线、实体、外部 ID、候选、缓存和运行记录相关表。

### 4.2 任务 B：飞书权限和基线读取验证

目标：证明现有飞书线上内容表能被系统读取。

需要用户准备：

1. 飞书 App ID。
2. 飞书 App Secret。
3. 线上内容基线表的 app token。
4. 线上内容基线表的 table ID。
5. 字段名对照，至少包括标题、类型、季号、集号、外部 ID、上架状态。

系统要做：

1. 获取 tenant access token。
2. 分页读取线上内容表。
3. 输出字段清单和字段类型。
4. 抽样 100-300 条。
5. 统计字段缺失率。
6. 标记哪些记录可形成 movie、series、season、episode 基线。

验收标准：

1. 能稳定读取全部或指定页数的线上内容。
2. 能识别标题、类型、季号、集号。
3. 能识别已有 IMDb/TMDb/Trakt ID。
4. 能输出 `baseline_quality_report.md`。

### 4.3 任务 C：实体匹配验证

目标：证明线上内容能可靠匹配到外部影视实体。

匹配优先级：

1. 已有 TMDb ID、IMDb ID、Trakt ID。
2. 标题 + 年份 + 内容类型。
3. 标题 + 季号 + 集号。
4. 低置信度标题相似匹配。

输出字段：

| 字段 | 说明 |
| --- | --- |
| local_record_id | 飞书记录 ID |
| local_title | 线上标题 |
| local_type | 线上类型 |
| candidate_title | 外部候选标题 |
| tmdb_id | TMDb ID |
| trakt_id | Trakt ID |
| imdb_id | IMDb ID |
| match_confidence | high、medium、low |
| match_reason | 匹配依据 |
| risk_note | 风险说明 |

验收标准：

1. 高置信度匹配准确率 >= 95%。
2. 同名电影和剧集不会自动误合并。
3. 季集号不一致时进入低置信度或人工确认。
4. 输出 `entity_matching_report.md`。

### 4.4 任务 D：最近 30 天 TV 候选 dry run

目标：证明数据源能发现近期电视剧更新。

采集入口：

1. Trakt TV calendar。
2. Trakt trending/popular shows。
3. TMDb trending TV。
4. TMDb TV details / seasons / episodes。
5. TMDb watch providers 作为平台证据，不作为唯一上线事实。

过滤原则：

1. 电视剧优先。
2. 英文内容优先。
3. 新剧、新季、新集优先。
4. Global/US 优先。
5. P0/P1 默认最多 50 条。

输出：

1. 候选列表。
2. 去重前后数量。
3. P0/P1/P2/P3 分布。
4. 每条候选的热度依据。
5. 需要人工确认的低置信度项。

验收标准：

1. 能生成最近 30 天 TV 候选。
2. 每条候选有 `content_update_id`。
3. 每条候选有 `hot_score` 和 `priority`。
4. 每条候选能追溯数据源。
5. 输出 `source_coverage_report.md`。

### 4.5 任务 E：180 天 bootstrap dry run

目标：估算半年追赶的规模和人工审核压力。

规则：

1. 默认最近 180 天。
2. P0/P1 总量上限 200。
3. P2 可保留在本地报告。
4. P3 不写飞书。
5. 已上架、已提交供应商、已下载、已入库、暂无资源默认过滤。
6. 低置信度基线匹配不直接过滤，标记为需人工确认。

验收标准：

1. 能输出候选规模统计。
2. P0/P1 数量可控。
3. 能区分已上线、疑似已上线、线上缺失、需人工确认。
4. 输出 `bootstrap_dry_run_report.md`。

### 4.6 任务 F：飞书业务表结构验证

目标：证明多维表格能承担人工审核、批次和供应商状态。

建议先创建测试用三张表：

1. 推荐更新表。
2. 批次表。
3. 供应商流转表。

系统验证：

1. 字段是否存在。
2. 单选、多选、日期、文本、数字字段是否可写。
3. 记录是否可更新。
4. 已有人工状态是否不会被覆盖。
5. 是否能根据 `content_update_id` 去重更新。

验收标准：

1. 能写入测试推荐记录。
2. 能更新 `review_status`。
3. 能关联 `batch_id`。
4. 能更新 `fulfillment_status`。
5. 输出 `supplier_flow_check.md`。

## 5. Phase 1 MVP 原型规划

Phase 0 达标后，再进入 Phase 1。

Phase 1 的目标是做一个最小可用闭环：

```text
读取飞书基线
-> 采集 Trakt/TMDb 候选
-> 标准化和去重
-> 计算 hot_score
-> dry run 报告
-> 写入飞书推荐更新表
```

### 5.1 Phase 1 功能范围

| 功能 | 是否包含 |
| --- | --- |
| `daily` 手动运行 | 包含 |
| `dry run` | 包含 |
| 写入推荐更新表 | 包含 |
| 人工审核字段 | 包含 |
| 批次表和流转表 | 只做基础支持 |
| 飞书日报 | 暂缓到 Phase 3 |
| 自动定时 | 暂缓到 Phase 3 |
| Watchmode/JustWatch | 不包含 |
| IMDb 商业数据 | 不包含 |

### 5.2 Phase 1 验收标准

1. 手动运行一次能生成推荐候选。
2. 重复运行不会重复写入同一 `content_update_id`。
3. 不会覆盖人工修改的 `review_status`、`batch_id`、`fulfillment_status`。
4. 所有 API Key 不进入 GitHub。
5. 出错时能看到具体数据源、请求和错误原因。

## 6. Phase 2 冷启动追赶规划

Phase 2 解决“线上内容半年没更新”的问题。

### 6.1 工作内容

1. 实现 `bootstrap` 模式。
2. 默认回看最近 180 天。
3. 从高信号入口获取候选。
4. 用线上内容基线和历史业务状态过滤。
5. P0/P1 控制在 200 条左右。
6. 按周或按优先级分批写入飞书。
7. 生成 bootstrap 汇总报告。

### 6.2 验收标准

1. bootstrap dry run 能先输出统计，不强制写飞书。
2. 用户确认后再写入推荐表。
3. 可按批次逐步追赶，不一次性制造过多人工工作。
4. 已上架内容不会重复推荐。
5. 新季和新集不会被旧季、旧集误过滤。

## 7. Phase 3 每日自动化规划

Phase 3 把系统从手动工具变成每日运营工具。

### 7.1 工作内容

1. 实现 `daily` 模式。
2. 配置服务器 cron 或 systemd timer。
3. 每日读取飞书业务状态。
4. 每日生成 P0/P1 推荐。
5. 写入飞书推荐表。
6. 生成飞书日报或 Markdown 日报。
7. 失败时发送飞书消息或邮件告警。

### 7.2 验收标准

1. 连续运行 7 天无重复写入。
2. 单一数据源失败不影响其他数据源。
3. 每日运行有日志和运行摘要。
4. 用户可以立即手动运行，不必等到第二天。
5. 可按日期范围补采。

## 8. Phase 4 生产化加固规划

Phase 4 不增加太多新功能，重点是稳定和可恢复。

### 8.1 必做项

| 项目 | 说明 |
| --- | --- |
| 配置校验 | 启动前检查 API Key、表 ID、字段映射 |
| 限流队列 | TMDb、Trakt、飞书分别限流 |
| 本地缓存 | 外部 API 响应缓存 7-30 天 |
| 数据库备份 | SQLite 每日压缩备份 |
| 错误重试 | 处理 `429`、网络错误、飞书临时失败 |
| 断点续跑 | bootstrap 中断后可继续 |
| 日志脱敏 | 不输出完整 token 和 secret |
| 部署文档 | 写明服务器、环境变量、定时任务、恢复方法 |

### 8.2 验收标准

1. 服务器重启后任务能恢复。
2. API 临时失败可重试。
3. SQLite 备份可恢复。
4. 日志可定位问题但不泄露密钥。
5. 有一份 `docs/deployment.md`。

## 9. Phase 5 数据源增强规划

只有当 Phase 0-3 证明免费或低成本数据源覆盖不足时，再做 Phase 5。

### 9.1 增强选项

| 数据源 | 解决问题 | 触发条件 |
| --- | --- | --- |
| Netflix Top 10 | Netflix 热度增强 | 需要更强 Netflix 热度证据 |
| OMDb | IMDb ID、英文标题、IMDb rating/votes 交叉验证 | Phase 0 证明对匹配和热度判断有增益，且授权边界可接受 |
| Watchmode | episode 级 streaming availability | TMDb/Trakt 平台可用性漏报明显 |
| JustWatch Partner API | 平台 offers 和 availability | 能取得商务合作 |
| IMDb 商业数据 | IMDb rating、votes、meters | 业务确认 IMDb 热度不可替代 |
| Google Trends | 外部传播热度 | 需要补充非影视平台热度 |

### 9.2 暂不建议做的事

1. 不抓 IMDb 页面。
2. 不抓需要登录或绕过反爬的流媒体页面。
3. 不把免费 IMDb 非商业数据集用于商业生产。
4. 不把 OMDb 当成 IMDb 官方商业授权替代品。
5. 不一开始购买 Watchmode，除非验证证明必要。
6. 不做非洲各国家逐区 availability，除非后续业务明确需要。

## 10. 需要用户准备的信息

进入 Phase 0 前，用户需要准备：

| 信息 | 用途 |
| --- | --- |
| 飞书 App ID / App Secret | 读取和写入多维表格 |
| 线上内容基线表 app token / table ID | 读取已有线上内容 |
| 线上内容表字段说明 | 做字段映射 |
| 测试推荐表 app token / table ID | 验证写入，不污染正式表 |
| TMDb API Key | 元数据和 ID 映射 |
| Trakt Client ID / Client Secret | TV 更新和热度 |
| OMDb API Key | IMDb ID、评分、票数和英文标题交叉验证 |
| 目标平台开关 | Netflix、Prime Video、Disney+ 等 |
| 审核人数和飞书版本 | 判断飞书容量和席位成本 |
| 供应商导出格式样例 | 判断批次表和流转表字段是否够用 |

## 11. 建议的下一次开发任务

下一次开发任务建议直接实现 Phase 0 验证包，不再继续扩写大文档。

建议任务描述：

```text
实现 MovieTrace Phase 0 验证包：
1. 初始化 Python 项目骨架。
2. 支持 .env 和 config.example.yaml。
3. 实现飞书多维表格读取验证。
4. 实现 TMDb/Trakt API 连通性验证。
5. 实现 OMDb API 连通性和字段可用性验证。
6. 实现线上内容基线抽样和字段质量报告。
7. 实现最近 30 天 TV dry run 的本地候选报告。
8. 所有密钥不提交 GitHub。
```

第一版代码不追求完整推荐系统，只追求能跑出验证报告。

## 12. Go / No-Go 决策

Phase 0 完成后，应基于报告做一次明确决策：

| 结论 | 条件 | 下一步 |
| --- | --- | --- |
| Go | 飞书可读写，匹配准确，候选质量可接受 | 进入 Phase 1 MVP 原型 |
| Conditional Go | 部分问题可通过清洗或配置解决 | 先修基线或规则，再进入 Phase 1 |
| No-Go | 数据源覆盖不足、授权不可接受、飞书不可承载 | 暂停开发，改数据源或业务方案 |

## 13. 当前优先级结论

当前最优先级如下：

1. 准备飞书测试应用和测试表。
2. 准备 TMDb、Trakt API Key。
3. 实现 Phase 0 验证包。
4. 先跑 30 天 TV dry run。
5. 人工复核 50-100 条候选。
6. 再决定是否进入完整 MVP 开发。

这条路线能最大限度避免“代码做完了，但数据源或飞书流程不可用”的风险。

## 14. Phase 0 当前进展记录

更新日期：2026-05-09

已完成：

1. 飞书 App 权限、表读取、测试表写入和更新验证。
2. 飞书 `节目` 表全量基线质量报告。
3. 节目库导出 Schema v0.1，并同步到飞书 schema 子表。
4. TMDb / Trakt API 连通性验证。
5. 前 100 条节目名实体匹配样本报告。
6. 架构调整为 SQLite 本地数据库作为事实源，飞书作为输入来源和可选协作视图。
7. SQLite 初始 schema、测试和本地数据库初始化。
8. 飞书 `节目` 表导入本地 `baseline_items`。

已产出：

- `docs/feishu_api_validation_notes.md`
- `docs/baseline_export_schema.md`
- `docs/local_database_architecture.md`
- `reports/baseline_quality_report.md`
- `reports/entity_matching_report.md`
- `reports/baseline_import_report.md`
- `reports/phase0_day1_summary.md`

当前本地数据库状态：

- 数据库路径：`data/movietrace.db`
- `baseline_items`：855 条
- 最近一次飞书导入状态：success

下一步建议：

1. 对 855 条 `baseline_items` 执行全量 TMDb / Trakt 实体匹配 dry run。
2. 将匹配候选写入 `match_candidates`。
3. 生成 `reports/full_entity_matching_report.md`。
4. 人工复核 high 匹配准确率。
5. 准确率达标后，再写入 `canonical_items` 和 `external_ids`。

## 15. Phase 0 实体匹配人工复核发现

更新日期：2026-05-10

来源报告：

- `reports/full_entity_matching_report.md`
- `reports/manual_entity_matching_review.md`

已确认问题：

1. `Jack Ryan S01-S04` 被标为 low，但人工确认应匹配 TMDB `Tom Clancy's Jack Ryan`。根因是当前标题相似度对品牌/作者前缀过于敏感。
2. `La casa de papel S01-S05` 错选 TMDB `Berlin and the Lady with an Ermine`。人工确认正确实体是 TMDB `71446 / Money Heist`，其 `original_name` 为 `La casa de papel`。根因是当前评分忽略 `original_name/original_title`。
3. `O Rio do DESEJO` 已选中正确 TMDB `764541 / River of Desire`，但被标为 low。人工确认其 `original_title` 为 `O Rio do Desejo`。根因同样是当前评分忽略 `original_title`，导致置信度被低估。
4. `Wedding Plan S01 interview` 未匹配，但人工确认应为 TMDB `229242 / Wedding Plan`。根因是原始标题含疑似人工录入或文件名残留词 `interview`，属于基线数据质量问题。

OMDb 临时验证发现：

1. OMDb API key 可用，示例 IMDb ID 查询和标题搜索均成功。
2. `Wedding Plan` 可返回 IMDb `tt28426949`，可辅助确认 TMDB `229242`。
3. `Jack Ryan` 可返回 `Tom Clancy's Jack Ryan / tt5057054`，可辅助标题别名判断。
4. `Money Heist` 可返回 IMDb `tt6468322`、`totalSeasons=5`、IMDb rating/votes。
5. `La casa de papel`、`O Rio do Desejo` 这类原始外语标题不一定能直接命中主实体，因此 OMDb 不能替代 TMDB 的 `original_name/original_title` 匹配。
6. OMDb 官方页面标注免费 key 为每日 1,000 次限制，内容许可为 CC BY-NC 4.0；商业生产使用前需要确认授权边界。

结论：

- 当前问题不是单纯 API 搜索失败，而是候选评分和标题字段使用不足。
- 正式编码阶段应把人工复核案例先转成自动化回归测试，再改匹配算法。
- 在修复前，不应把 low 匹配自动写入 `canonical_items` 或飞书正式表。
- 对 `interview`、`無英文字幕`、`百度网盘` 这类疑似标题污染，应输出人类预警和修正建议；程序只做低风险、可解释、集中维护的轻量清洗。

### 15.1 后续任务包：改进实体匹配标题别名与原始标题评分

```text
任务名称：改进实体匹配标题别名与原始标题评分
任务类型：算法修正 + 回归测试
当前阶段：任务拆解
来源任务：Phase 0 全量实体匹配人工复核 CASE-001 / CASE-002 / CASE-003 / CASE-004
目标：让 Jack Ryan、La casa de papel、O Rio do DESEJO 这类标题别名、品牌前缀、原始标题命中进入正确候选；对 Wedding Plan interview 这类标题污染输出可解释清洗建议和人工预警；评估 OMDb 作为 IMDb 补充与交叉验证源的增益。
非目标：不写入 canonical_items；不写入 external_ids；不写飞书正式表；不做全量人工修正；不引入新第三方依赖。
允许修改范围：
- src/movietrace/pipeline/entity_matching.py
- src/movietrace/sources/tmdb.py
- src/movietrace/sources/omdb.py
- tests/test_entity_matching.py
- tests/test_source_clients.py
- reports/manual_entity_matching_review.md
禁止修改范围：
- docs/local_database_architecture.md 中已确认的数据表边界
- 飞书正式表数据
- API 密钥、.env、secrets 文件
相关上下文：
- reports/full_entity_matching_report.md
- reports/manual_entity_matching_review.md
输入：
- baseline_items 中的标题、季数线索和年份线索
- TMDB / Trakt 搜索候选
- TMDB 候选中的 name/title、original_name/original_title、media_type、first_air_date/release_date
- OMDb 候选中的 imdbID、Title、Year、Type、totalSeasons、imdbRating、imdbVotes
输出：
- 更准确的 match_candidates 候选选择
- 更可解释的 confidence 和 reason
- 针对 CASE-001、CASE-002、CASE-003 和 CASE-004 的自动化回归测试
- 标题污染类记录的人工预警和清洗建议
- OMDb 连通性和字段可用性验证记录
具体要求：
- TMDB 解析保留 original_name/original_title。
- 标题相似度同时比较主标题和原始标题，并记录 matched_field。
- 支持品牌/作者前缀导致的核心标题匹配，例如 Tom Clancy's Jack Ryan -> Jack Ryan。
- TV 季度条目应结合 media_type、season hint 和年份合理性评分。
- 对衍生剧、纪录片、翻拍版和地区改编版保持保守，不能仅因关键词包含就升为 high。
- 对 `interview`、`無英文字幕`、`百度网盘` 等疑似非实体描述词，只做低风险、可解释、集中维护的轻量清洗。
- 清洗后必须保留原始标题，并输出人工预警，不能静默覆盖基线数据。
- OMDb 只作为 IMDb ID、英文标题、rating/votes 和 totalSeasons 的补充验证源，不替代 TMDB / Trakt 主匹配逻辑。
- OMDb API key 不得写入仓库；所有响应应可缓存，避免超过免费额度。
验收标准：
- Jack Ryan S01-S04 不再被判为 low。
- La casa de papel S01-S05 选择 TMDB 71446，而不是 TMDB 308014。
- O Rio do DESEJO 选择 TMDB 764541，且不再被判为 low。
- Wedding Plan S01 interview 能给出 TMDB 229242 候选，并输出标题污染预警。
- OMDb 验证能返回 Wedding Plan、Jack Ryan、Money Heist 的 IMDb ID 和关键字段。
- reason 明确显示 matched_field 或核心标题命中依据。
- 既有实体匹配测试继续通过。
测试要求：
- 增加 TMDB original_name/original_title 解析测试。
- 增加 La casa de papel 多候选选择回归测试。
- 增加 Jack Ryan 品牌/作者前缀回归测试。
- 增加 O Rio do DESEJO 原始电影标题置信度回归测试。
- 增加 Wedding Plan interview 标题污染清洗和人工预警回归测试。
- 增加 OMDb 响应解析测试，覆盖 movie、series、no_match 和 rating/votes 字段。
验证命令：
- python3 -m unittest tests/test_source_clients.py tests/test_entity_matching.py
风险点：
- 不能把所有包含关系都升为 high，否则容易误匹配衍生剧或翻拍版。
- original_name 对非拉丁语标题可能被 ASCII 归一化丢失，需要保留原始字段并谨慎比较。
- 年份规则不能过强，否则可能误伤跨年上线或分季发行的剧集。
- 标题污染清洗不能写成大量分散硬编码，否则维护成本高且容易误删真实标题词。
- OMDb 对原始外语标题覆盖不稳定，不能作为外语标题匹配的唯一依据。
- OMDb 内容许可和商业生产授权边界需要确认，不能默认替代 IMDb 商业数据。
完成后输出要求：
- 汇报修改文件。
- 汇报新增测试覆盖的人工复核案例。
- 汇报验证命令和结果。
- 汇报仍需人工复核的剩余风险。
```

### 15.2 本地 canonical 写入结果

更新日期：2026-05-10

前置条件：

- 已完成人工复核。
- 已修正 CASE-001 至 CASE-004 对应的实体匹配规则。
- 已接入 OMDb 作为 TMDB 的跨源匹配建议来源。
- 已重跑 855 条 `baseline_items` 全量实体匹配 dry run。

执行范围：

- 只提升 `confidence=high` 的 `match_candidates`。
- 只写本地 SQLite `canonical_items`、`external_ids`，并回写 `baseline_items.canonical_item_id`、`match_status`、`match_confidence`。
- 不写飞书正式表。
- 不提升 `medium`、`low`、`no_match`。

跨源匹配规则：

- 每条 baseline 同时输出 TMDB 建议和 OMDb 建议。
- TMDB / OMDb 类型、标题和年份兼容时，标记 `cross_source=tmdb_omdb_consistent`，可直接过关。
- 单一来源强确认时，标记 `cross_source=single_strong_tmdb` 或 `cross_source=single_strong_omdb`，可直接过关。
- TMDB / OMDb 都有结果但类型、年份或标题冲突时，标记 `cross_source=tmdb_omdb_conflict`，保留为 medium，交给人工审核。
- 当同名或近名实体存在多个版本，且标题和类型足够接近、本地没有显式年份时，优先选择较新的影视实体，标记 `version_disambiguation=newer_entity_preferred`。
- 本地标题含显式年份时，显式年份优先，不被新近版本规则覆盖。
- 报告 `reports/full_entity_matching_report.md` 增加 `TMDB / OMDb 全量建议与差异` 表。

执行结果：

| 指标 | 数量 |
| --- | ---: |
| baseline_items | 855 |
| matched candidates | 853 |
| API errors | 2 |
| high candidates | 779 |
| medium candidates | 73 |
| low candidates | 1 |
| no_match candidates | 2 |
| promoted baseline_items | 779 |
| created canonical_items | 389 |
| created external_ids | 389 |
| remaining unmatched baseline_items | 76 |

跨源分布：

| 类型 | 置信度 | 数量 |
| --- | --- | ---: |
| TMDB / OMDb consistent | high | 740 |
| single strong source | high | 39 |
| TMDB / OMDb conflict | medium | 42 |
| no cross-source reason | medium | 31 |
| no cross-source reason | low | 1 |
| no cross-source reason | no_match | 2 |

当前剩余未提升项：

| match_candidates.confidence | baseline_items.match_status | 数量 |
| --- | --- | ---: |
| medium | unmatched | 73 |
| low | unmatched | 1 |
| no_match | unmatched | 2 |

后续建议：

1. 对 73 条 medium 做人工复核，重点看 TV season 被 TMDB movie 候选吸走、标题过短或 OMDb 无可用建议的情况。
2. 单独处理 `Special Ops Lioness S01` 这条 low。
3. 对 2 条 no_match 重试 API 或人工补外部 ID。
4. 在进入候选发现前，补充 canonical 写入报告或 SQL 核对脚本，避免误写。
