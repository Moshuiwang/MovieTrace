# MovieTrace 核心代码库架构审查报告

> 审查日期：2026-05-22
> 范围：本地核心代码（pipeline、sources、feishu、cli）
> 性质：架构与性能审计，非任务包，不直接驱动编码

---

## 一、原始审查报告：8 大核心痛点

### 1.1 数据库长连接生命周期内执行网络 I/O 的锁定风险

**定位**：`discovery.py` `run_discovery` 函数

在 `run_discovery` 开始时打开 SQLite 连接，直到 `finally` 块才关闭。期间串行发起大量外部网络请求（TMDb ID 回填、OMDb 评分丰富化、TMDb 详情拉取），整体耗时数十秒至数分钟。

SQLite 采用库级锁/表级锁。当 `discovery.py` 持有连接并等待慢速网络 I/O 时，如果有其他并发进程写入数据库，会触发 `sqlite3.OperationalError: database is locked`。

**建议方案**：先在内存中完成所有外部 API 抓取，汇总完成后再开启短平快的数据库事务批量落库，将连接占用时间缩短到毫秒级。

---

### 1.2 割裂的 HTTP 客户端实现与 Keep-Alive 缺失

**定位**：`sources/http.py` `get_json` · `feishu/_http.py` `request_json`

业务数据抓取与飞书 API 模块各自实现了一套 HTTP 轮子，基于 `urllib.request.urlopen`，无连接池、无 Keep-Alive。每次请求均需重新 TCP + TLS 握手。

**建议方案**：统一网络通信层，引入 `httpx` 或 `requests`，维护单例 HTTP Session 连接池，配置全局限速与自适应退避。

---

### 1.3 串行同步网络 I/O 与硬编码 sleep 导致的性能瓶颈

**定位**：`omdb_enrichment.py` L143 `time.sleep(1.0)`

对 OMDb 的丰富化查询单线程串行执行，每次 API 调用后硬编码等待 1 秒。60 条内容需丰富化时，Pipeline 在此无条件挂起至少 1 分钟。

**建议方案**：改用 `asyncio` + `httpx.AsyncClient` 并发请求，通过异步信号量限制并发数，从分钟级缩短至秒级。

---

### 1.4 循环内 Micro-Commits 造成的磁盘 I/O 瓶颈

**定位**：`omdb_enrichment.py` L189、L218 `conn.commit()`

`enrich_with_tmdb_details` 循环中，每成功写入一条 `api_cache` 或更新一条 `canonical_items` 都执行单独的 `conn.commit()`，触发磁盘 fsync。数十次 Micro-Commits 造成高磁盘负载，在并发时极易引发库锁定。

**建议方案**：消除循环内 `commit()`，改用 `with conn:` 上下文管理器将整个循环包裹在单一事务中，一次性批量提交。

---

### 1.5 实体匹配无缓存与 SequenceMatcher 搜索开销

**定位**：`entity_matching.py` L745–L787 `match_upstream_program`

1. TMDb `search_tv/movie` 接口无本地缓存，同一节目多次运行时重复发起网络请求。
2. 使用 `difflib.SequenceMatcher` 对所有候选计算相似度，无前置快速初筛。

**建议方案**：将 TMDb 搜索结果纳入 `api_cache`（TTL 3–7 天）；在 SequenceMatcher 之前前置字符集重合率粗过滤，剪枝低概率候选。

---

### 1.6 飞书 Bitable 同步的"半同步状态"与 Ledger 账本缺失

**定位**：`feishu/sync.py` L387–L407 `sync_table`

批次同步中途若发生网络中断、鉴权过期或 429 限频，程序静默退出，导致一部分数据写入飞书、另一部分未写入（半同步脏态）。同时，本地无 Sync Ledger 映射表，每次同步前不得不全表扫描飞书重建 lookup。

**建议方案**：引入本地 `feishu_sync_ledger` 映射表；遇 429 自适应等待重试；故障中断后通过 Ledger diff 实现幂等增量重试。

---

### 1.7 数据源失败时"以旧充新"导致的脏数据污染

**定位**：`discovery.py` L123–125 `_ensure_fp_data`

FlixPatrol 抓取失败时，系统回溯 30 天历史快照，以今日 `snapshot_date` 名义写入 `content_updates`，触发丰富化逻辑，并推送至飞书。历史数据被误判为"今日新发现"，制造重复冗余事件，浪费 TMDb/OMDb API 配额，干扰运营决策。

**建议方案**：FlixPatrol 抓取失败应作为 Fatal Error 直接抛出，阻断 Pipeline 并通过飞书发送报警，不得静默 Fallback 历史数据。

---

### 1.8 CLI 模块职责严重过载

**定位**：`cli.py`

`cli.py` 承担了 yaml 配置加载、token 动态加载、Gzip 异常模式解析、数据库连接控制、数百行工作流编排等职责，与命令行入口强绑定。若未来需要 Web API 或调度器集成，无法以纯 Python SDK 形式调用。

**建议方案**：提取独立 `Orchestrator` 编排层，`cli.py` 仅保留参数解析与屏幕输出。

---

## 二、对原始报告的批判性评估

### 2.1 认可的部分（有真实依据，值得推进）

| 痛点 | 评估 |
|---|---|
| **1.4 循环内 Micro-Commits** | 确实是 SQLite anti-pattern，修复成本低，收益明确 |
| **1.7 源失败以旧充新** | 最严重的语义 bug，历史数据以今日名义落库，直接影响数据质量与 API 配额 |
| **1.5 TMDb 搜索无缓存** | 重复 API 调用确实存在，缓存是合理改进 |

---

### 2.2 有保留或不认可的部分

**1.1 DB 长连接锁风险 — 场景不符**

本项目是单进程、每日一次的 cron 任务。SQLite 文件锁的前提是**并发写入**。没有并发进程的前提下，"雪崩"不会发生。解耦 I/O 与 DB 写入是好实践，但当前实际风险被夸大。若未来引入并发任务再处理。

**1.2 HTTP Keep-Alive — 收益断言失实**

报告声称"握手延迟降低 70%+"。但本项目对 OMDb 有硬编码 `sleep(1)` 频控限制——在频控瓶颈面前，TCP Keep-Alive 收益趋近于零。"70%" 是无根据的断言。引入 `httpx` 需要新依赖授权，不应轻率提出。

**1.3 串行请求 + hardcoded sleep — 误判正常设计为缺陷**

`sleep(1)` 不是设计缺陷，是**遵守 OMDb 频控的正确行为**。60 条记录 60 秒对一个日批任务完全可接受。异步化是 nice-to-have，不是痛点。

**1.5 SequenceMatcher 复杂度描述有误**

报告称"O(N²) 搜索"，但 SequenceMatcher `ratio()` 对两个字符串的复杂度是 O(m×n)（字符串长度之积），不是候选数量 N 的平方。这是概念错误，不影响前置粗筛方向的合理性，但原始描述不准确。

**1.6 Feishu Ledger 方案 — 过度工程**

`feishu_sync_ledger` 本地映射表对一个每天同步数十条记录的 MVP 系统属于重型工程。半同步问题可通过改进错误处理与重试机制解决，不需要完整 Ledger。

**1.8 CLI 职责分离 — 违反项目自身规则**

报告理由是"将来可能需要 Web API 或 Airflow"。这正是项目 CLAUDE.md 明文禁止的 **Speculative Code**："不为想象中的未来需求设计"。此条建议应当拒绝，不是推迟。

---

## 三、综合优先级判断

| 优先级 | 痛点 | 理由 |
|---|---|---|
| **P0 — 值得尽快做** | 1.7 数据源失败阻断 | 语义 bug，影响数据质量与 API 配额 |
| **P1 — 值得做** | 1.4 批量 commit | 低成本修复真实 anti-pattern |
| **P1 — 值得做** | 1.5 TMDb 搜索缓存 | 减少重复 API 调用，改进有限、风险低 |
| **P2 — 有价值但需评估规模** | 1.1 DB 连接解耦 | 若未来有并发任务再处理 |
| **P2 — 有价值但需评估规模** | 1.6 飞书重试机制 | 改重试逻辑可行，不建完整 Ledger |
| **不应做** | 1.8 CLI 重构 | 投机性重构，违反项目规则 |
| **收益存疑** | 1.2 HTTP 统一 + Keep-Alive | 在频控限制下实际收益趋近于零 |
| **可选优化** | 1.3 异步丰富化 | 日批任务 60 秒等待可接受，非紧急 |

---

## 四、结论

本次审查报告的核心偏差是：**用"高并发生产系统"的标准审计一个单用户、每日批处理脚本**，导致部分建议投入产出比极低，个别建议（1.8）与项目自身规则相悖。

真正值得跟进的改动集中在三处：**数据源失败阻断（1.7）、批量 commit（1.4）、TMDb 搜索缓存（1.5）**。这三项修复成本低、收益明确、不需要引入新依赖或改变架构边界，适合纳入后续任务包逐步推进。
