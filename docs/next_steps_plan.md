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

### 4.1 任务 A：建立项目骨架

目标：让后续验证脚本有稳定结构。

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
| Watchmode | episode 级 streaming availability | TMDb/Trakt 平台可用性漏报明显 |
| JustWatch Partner API | 平台 offers 和 availability | 能取得商务合作 |
| IMDb 商业数据 | IMDb rating、votes、meters | 业务确认 IMDb 热度不可替代 |
| Google Trends | 外部传播热度 | 需要补充非影视平台热度 |

### 9.2 暂不建议做的事

1. 不抓 IMDb 页面。
2. 不抓需要登录或绕过反爬的流媒体页面。
3. 不把免费 IMDb 非商业数据集用于商业生产。
4. 不一开始购买 Watchmode，除非验证证明必要。
5. 不做非洲各国家逐区 availability，除非后续业务明确需要。

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
5. 实现线上内容基线抽样和字段质量报告。
6. 实现最近 30 天 TV dry run 的本地候选报告。
7. 所有密钥不提交 GitHub。
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
