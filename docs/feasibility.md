# MovieTrace 可行性评估

状态：扩展评估版  
日期：2026-05-07  
评估依据：[docs/requirements.md](requirements.md)

## 1. 总体结论

MovieTrace 在工程上可行，适合作为一个“高价值影视更新候选发现系统”推进 MVP。

但在进入正式开发前，必须先做一轮小样本验证。原因是 API 能调用成功不等于数据覆盖足够，飞书能读写不等于现有线上内容表适合做去重基线，实体能匹配不等于误匹配率可接受。

但该项目的主要风险不是写代码，而是：

1. 数据源授权和商业使用边界。
2. 流媒体平台上线信息的数据完整性。
3. 电视剧 episode 级更新的准确识别。
4. 飞书多维表格作为轻量业务后台的容量边界。

推荐结论：

| 事项 | 结论 |
| --- | --- |
| 内部原型验证 | 可以做 |
| 每日高价值候选推荐 | 可以做 |
| 基于飞书多维表格做人工审核和状态流转 | 可以做 |
| 冷启动追赶最近 180 天 | 可以做，但必须限量分批 |
| 直接抓取 IMDb 或各流媒体平台官网 | 不建议 |
| 商业生产环境长期依赖 TMDb/IMDb 免费数据 | 不建议，需确认授权 |
| 精确判断所有平台 episode 级上线 | 风险较高，可能需要 Watchmode/JustWatch 等商业数据源 |

开发前必须优先验证：

1. 飞书线上内容表能否稳定读取并映射为基线。
2. 最近 30 天电视剧更新能否通过 Trakt + TMDb 发现到足够样本。
3. 线上内容到 TMDb/Trakt/IMDb 的实体匹配误判率是否可控。

## 2. 数据源可行性

### 2.1 TMDb

可用能力：

- 影视元数据、ID 映射、搜索、discover、trending/popular。
- movie、TV series、TV season 的 watch providers。
- TV season 和 episode 详情，可用于补充季集信息。
- 支持通过已有 IMDb ID 查找 TMDb 数据，适合处理现有线上内容基线。

限制和风险：

1. TMDb 开发者 API 免费用途主要面向非商业使用。TMDb 官方 FAQ 明确区分 developer API 和 commercial API，收入导向项目属于商业项目，商业使用需要联系销售取得授权。
2. TMDb 没有 SLA。
3. 速率限制不是固定配额，官方说明旧的 40 requests / 10 seconds 已停用，但仍有大约 40 requests / second 的上限，并要求尊重 `429`。
4. Watch provider 数据适合判断某内容在哪些服务可看，但不应假设它能精确表达“某一集刚刚在某平台上线”。
5. 平台来源数据可能存在延迟或不完整，必须保留 `source_records` 和 `baseline_match_status`，不能盲目自动提交供应商。

可行性判断：

| 用途 | 结论 |
| --- | --- |
| 标准化影视实体 | 可行 |
| 外部 ID 映射 | 可行 |
| 热度评分 | 可行 |
| 平台来源证据 | 基本可行 |
| episode 级平台上线精确判断 | 不应单独依赖 TMDb |
| 商业生产使用 | 需授权确认 |

MVP 建议：

- TMDb 作为元数据和 ID 映射主数据源。
- 不做大规模全库拉取。
- bootstrap 只处理最近 180 天高信号候选。
- 缓存 TMDb 响应，避免重复请求。
- 生产使用前联系 TMDb 确认商业授权。

参考：

- [TMDb FAQ](https://developer.themoviedb.org/docs/faq)
- [TMDb Rate Limiting](https://developer.themoviedb.org/docs/rate-limiting)
- [TMDb Finding Data](https://developer.themoviedb.org/docs/finding-data)
- [TMDb Movie Watch Providers](https://developer.themoviedb.org/reference/movie-watch-providers)
- [TMDb TV Watch Providers](https://developer.themoviedb.org/reference/tv-series-watch-providers)
- [TMDb TV Season Watch Providers](https://developer.themoviedb.org/reference/tv-season-watch-providers)

### 2.2 Trakt

可用能力：

- trending、popular、watched 等热度信号。
- TV calendars 和 episode 相关信息，适合辅助发现新剧、新季、新集。
- 可通过 Trakt ID、IMDb ID、TMDb ID 做跨源映射。

限制和风险：

1. Trakt API 有明确限流。公开资料显示 GET 请求限制为 1000 calls / 5 minutes，POST/PUT/DELETE 为 1 call / second。
2. Trakt 在 2025 年出现过因 API 滥用而加严限流的讨论，说明限流策略可能动态调整。
3. Trakt 更适合判断“影视热度和播出日历”，不提供 Netflix、Prime Video 等平台的完整可用性数据。
4. 商业使用口径在官方论坛中有 Trakt 团队成员说明 public API 无额外商业授权费用，但生产环境仍建议保留书面确认或至少保存官方答复链接。

可行性判断：

| 用途 | 结论 |
| --- | --- |
| 电视剧更新发现 | 可行 |
| 热度补充 | 可行 |
| 平台可用性判断 | 不适合单独承担 |
| API 调用量 | 对本项目足够 |

MVP 建议：

- Trakt 作为 TV episode/new season 的重要发现源。
- 实现统一限流队列，默认不超过 3 requests / second。
- 必须处理 `429` 和 `Retry-After`。
- 对 calendar、trending、popular 结果做本地缓存。

参考：

- [Trakt API rate limit announcement](https://github.com/trakt/trakt-api/issues/220)
- [Trakt API rate-limit discussion](https://forums.trakt.tv/t/is-my-account-api-limited/100717)
- [Trakt API commercial-use discussion](https://forums.trakt.tv/t/asking-about-api-commercial-uses-on-free-plan/99367)

### 2.3 IMDb

可用能力：

- IMDb ID 适合作为跨平台稳定标识。
- 非商业数据集包含 title、episode、ratings 等 TSV 文件，并且每日刷新。
- IMDb 商业元数据通过 IMDb Developer / AWS Data Exchange 提供。

限制和风险：

1. IMDb 官方明确禁止对网站做 data mining、robots、screen scraping 等自动化采集。
2. 非商业数据集仅限个人和非商业用途，不能直接用于商业视频网站运营决策的生产系统。
3. 商业使用需要走 IMDb Developer 授权。

可行性判断：

| 用途 | 结论 |
| --- | --- |
| 使用 IMDb ID 做主键/辅助映射 | 可行 |
| 使用非商业 IMDb 数据集做商业生产 | 不建议 |
| 抓取 IMDb 页面 | 不可取 |
| 购买 IMDb 商业数据 | 可行但需成本评估 |

MVP 建议：

- 不抓 IMDb 页面。
- MVP 中只把 IMDb ID 当成外部标识。
- 若需要 IMDb rating、votes、meters 作为生产热度依据，需要走 IMDb 商业授权。

参考：

- [IMDb data usage policy](https://help.imdb.com/article/imdb/general-information/can-i-use-imdb-data-in-my-software/G5JTRESSHJBBHTGX)
- [IMDb Non-Commercial Datasets](https://developer.imdb.com/non-commercial-datasets/)
- [IMDb Developer](https://developer.imdb.com/)

### 2.4 OMDb

可用能力：

- 通过 IMDb ID 查询标题、年份、类型、IMDb rating、IMDb votes、runtime、genre、country、language 等字段。
- 通过标题搜索返回 IMDb ID 和基础元数据。
- 支持 series 的 `totalSeasons` 字段，可作为 TV 实体辅助校验。
- 对英文 IMDb 标题检索效果较好，适合作为 TMDb / Trakt 匹配后的交叉验证来源。

限制和风险：

1. 官方免费 key 标注为每日 1,000 次请求限制。
2. OMDb 页面说明内容采用 CC BY-NC 4.0 许可；商业生产使用需要单独确认授权边界。
3. Poster API 仅 patron 可用，MVP 不应依赖海报能力。
4. 对原始外语标题覆盖不稳定。例如 `La casa de papel`、`O Rio do Desejo` 这类原始标题不一定能直接命中主实体。
5. OMDb 不是 IMDb 官方 API，不能等同于 IMDb 商业授权。

可行性判断：

| 用途 | 结论 |
| --- | --- |
| IMDb ID 补充 | 可行 |
| 英文标题交叉验证 | 可行 |
| IMDb rating / votes 内部验证 | 可行 |
| 原始外语标题匹配 | 不稳定 |
| 替代 TMDb / Trakt | 不建议 |
| 商业生产长期依赖 | 需授权确认 |

MVP 建议：

- Phase 0 先做 OMDb API 连通性和字段可用性验证。
- 只作为 TMDb / Trakt 实体匹配的补充验证源，不作为主实体源。
- 优先通过已有 IMDb ID 查询详情；标题搜索仅作为辅助。
- 所有 OMDb 响应进入本地缓存，避免重复请求。
- 不提交 OMDb API key；通过 `.env` 或本地 secrets 配置。
- 生产使用前确认 OMDb 授权边界，尤其是 rating / votes 是否可用于商业运营决策。

参考：

- [OMDb API](https://www.omdbapi.com/)
- [OMDb API Key](https://www.omdbapi.com/apikey.aspx)
- [Creative Commons BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)

### 2.5 Netflix Top 10

可用能力：

- Netflix 官方 Top 10 页面公开全球和国家榜单。
- 榜单按周更新，可作为 Netflix 热度强信号。
- 页面提供 Global、US 等榜单和 views/hours viewed 等指标。

限制和风险：

1. 它是榜单页面，不是稳定 API。
2. 只覆盖 Netflix，不覆盖 Prime Video、Disney+、Hulu、HBO/Max、Apple TV+。
3. 适合做热度证据，不适合做完整上线发现。
4. 自动化读取需要非常克制，避免高频抓取。

可行性判断：

| 用途 | 结论 |
| --- | --- |
| Netflix 热度信号 | 可行 |
| Netflix 新内容完整发现 | 不完整 |
| 多平台统一数据源 | 不适合 |

MVP 建议：

- 每周低频读取 Global 和 US 榜单。
- 只用于 `heat_signals` 和 `ai_reason`。
- 不把 Netflix Top 10 当成唯一采集入口。

参考：

- [Netflix Top 10](https://www.netflix.com/tudum/top10)
- [Netflix Top 10 methodology](https://about.netflix.com/en/news/new-top-10-on-netflix)

### 2.6 Watchmode / JustWatch 等商业流媒体可用性数据源

如果项目后续需要高准确度判断“某一季、某一集在哪个流媒体平台可看”，TMDb/Trakt 可能不够。

Watchmode 的官方 API 明确提供：

- 200+ 服务。
- 50+ 国家。
- episode-level streaming availability。
- 免费开发者额度，但非商业；商业套餐从 Startup 级别开始。

JustWatch 有 Partner API，文档描述支持按 TMDb ID 查询 movie/show offers，也支持 show season 和 episode 级别 offers。但这是 partner API，不应当使用非官方 npm 包或私有接口做商业生产。

可行性判断：

| 用途 | 结论 |
| --- | --- |
| 精确平台可用性 | 商业数据源更合适 |
| episode 级平台可用性 | Watchmode/JustWatch 更匹配 |
| MVP 必需 | 暂时不是 |
| 后续商业稳定性 | 建议纳入备选 |

参考：

- [Watchmode API](https://api.watchmode.com/)
- [Watchmode Terms](https://api.watchmode.com/tc)
- [JustWatch Partner API](https://apis.justwatch.com/docs/api/)

## 3. 本地数据库、飞书多维表格与文档可行性

### 3.0 架构调整：本地数据库作为事实源

Phase 0 验证发现，飞书多维表格可以稳定读取和写入，但其 API 读写效率、字段约束和分页模型不适合作为 MovieTrace 的核心数据库。

后续建议将 SQLite 作为 MVP 阶段的事实源：

- 保存当前库基线。
- 保存 TMDb / Trakt 原始响应和缓存。
- 保存实体匹配候选、外部 ID、置信度和人工复核状态。
- 保存内容更新、去重结果和运行记录。

飞书保留为：

- 当前节目库输入来源。
- 字段 schema 对齐表。
- 可选推荐结果协作视图。
- 后续人工审核视图。

### 3.1 多维表格能力

需求中的飞书多维表格用法是可行的：

- 读取现有线上内容基线表。
- 写入推荐更新表。
- 写入批次表。
- 写入供应商流转表。
- 人工审核、筛选、状态流转。
- 通过字段保存 `content_update_id`、`baseline_match_status`、`fulfillment_status`。

关键限制：

1. Lark 多维表格基础版每数据表 2,000 行，专业版 20,000 行，企业版 50,000 行。
2. 批量创建、批量更新记录接口适合分批写入。公开接口资料显示单次批量操作最多 500 条，常见调用频率为 10 QPS。
3. 列出记录接口一般需要分页，单页上限常见为 500 条。
4. 飞书应用需要正确配置权限并发布版本，且需要把应用添加到目标多维表格。
5. 日期字段需要毫秒时间戳，单选、多选、人员、关联记录等字段都有特定写入格式。
6. 飞书适合做人机协作视图和输入来源，不适合作为原始采集日志、全量数据仓库或高频状态读写事实源。

可行性判断：

| 用途 | 结论 |
| --- | --- |
| 每日候选写入 | 可行 |
| bootstrap 写入 200 条 P0/P1 | 可行 |
| 读取线上内容基线 | 可行 |
| 人工审核和批次管理 | 可行 |
| 保存全部原始采集记录 | 不建议 |
| 作为长期唯一数据库 | 不建议 |

容量判断：

- 如果线上内容基线表少于 20,000 行，专业版足够。
- 如果已有内容或后续候选超过 20,000 行，应以 SQLite/PostgreSQL 作为系统数据库，飞书只保留待处理业务视图。
- 如果免费版只有 2,000 行/表，冷启动和长期运营很快会碰到上限，不建议用免费版作为生产后台。

参考：

- [Lark Base plans](https://www.larksuite.com/lp/cn/base-plans)
- [飞书多维表格权限配置说明](https://www.feishu.cn/content/137710114294)
- [飞书批量新增记录接口镜像](https://s.apifox.cn/apidoc/docs-site/532425/api-9020913)
- [飞书批量更新记录接口镜像](https://s.apifox.cn/apidoc/docs-site/532425/api-9020915)
- [飞书列出记录接口镜像](https://apifox.com/apidoc/docs-site/532425/api-9020910)

### 3.2 飞书文档能力

日报和多日汇总可行。

限制：

1. 新版文档创建和块写入有频率限制，常见为单应用 3 QPS。
2. 文档块数量、层级、单次插入内容大小都有约束。
3. 报告不应写入太长的全量列表。建议报告只放摘要、P0/P1、关键 P2 和链接到多维表格视图。

参考：

- [飞书创建文档接口镜像](https://s.apifox.cn/apidoc/docs-site/532425/api-58540235)
- [飞书创建块接口镜像](https://s.apifox.cn/apidoc/docs-site/532425/api-58543084)
- [飞书云文档连接器说明](https://www.feishu.cn/content/383321056779)

## 4. 调用量和成本粗估

### 4.1 daily 模式

目标：每天输出 P0/P1 不超过 50 条。

推荐调用策略：

1. Trakt calendar/trending/popular 拉候选。
2. TMDb 批量补充元数据、外部 ID、watch provider。
3. Netflix Top 10 每周低频补充热度。
4. 本地缓存命中后不重复请求。
5. 飞书只写候选和状态，不写所有原始记录。

粗估：

| 项 | 估计 |
| --- | --- |
| 外部 API 请求 | 100-500 / day |
| 飞书写入 | 1-3 次 batch_create 或 batch_update |
| 飞书文档写入 | 1 篇日报，少量 block |
| 是否触及限流 | 正常不会 |

### 4.2 bootstrap 模式

目标：追赶最近 180 天，但 P0/P1 初始候选最多 200 条。

推荐策略：

1. 先读取飞书线上内容基线。
2. 只从高信号入口拿候选，不全量扫描 TMDb/Trakt。
3. 电视剧优先，新剧、新季、新集优先。
4. 对候选做本地去重、评分、状态过滤。
5. 分批写入飞书，每批 50-200 条。

粗估：

| 项 | 估计 |
| --- | --- |
| 读取线上基线 | 按 500 条/页分页 |
| 外部 API 请求 | 1,000-5,000 次，取决于候选池大小 |
| 飞书写入 | 1 次或少量 batch_create |
| 是否触及限流 | 可控，但需要队列、缓存、重试 |

### 4.3 生产成本判断

| 项 | 成本判断 |
| --- | --- |
| TMDb | 非商业免费；商业生产需联系授权 |
| Trakt | Public API 免费，但需遵守限流；商业口径建议确认 |
| IMDb | 非商业数据不能直接用于商业生产；商业数据需授权 |
| Netflix Top 10 | 免费公开页面，但不是 API |
| Watchmode | 免费开发者额度非商业；商业套餐公开价格从 $349/month 起 |
| Lark/飞书多维表格 | 免费版行数不够稳；专业版或企业版更适合 |

## 5. 主要风险

| 风险 | 等级 | 说明 | 缓解方案 |
| --- | --- | --- | --- |
| TMDb 商业授权 | 高 | 项目服务于商业视频网站运营，可能属于商业使用 | 生产前联系 TMDb；原型阶段限制为验证 |
| IMDb 数据使用 | 高 | 不可抓网页，非商业数据不能用于商业生产 | 仅用 IMDb ID；需要评分/热度时购买授权 |
| 平台上线准确性 | 高 | TMDb/Trakt 不保证 episode 级平台可用性完整 | MVP 只做推荐候选；需要精确可用性时接 Watchmode/JustWatch |
| 冷启动数据量 | 中 | 半年追赶可能产生过多候选 | P0/P1 上限 200，分批写入 |
| 飞书表容量 | 中 | 免费版 2,000 行/表，专业版 20,000 行/表 | 生产使用专业版以上；长期原始数据放本地 DB |
| API 限流 | 中 | Trakt/TMDb/飞书都有限流 | 统一限流队列、缓存、重试、断点续跑 |
| 实体映射误判 | 中 | 同名电影/剧集、季集缺失容易误合并 | `mapping_confidence` 和人工确认机制 |
| 飞书权限配置 | 中 | 应用权限、表格添加应用、版本发布缺一不可 | 初始化检查脚本和权限诊断 |

## 6. 开发前验证计划

本节用于避免“开发完成后才发现不可行”。这些验证应先于完整功能开发进行，目标是用小样本证明数据源、飞书、实体匹配和业务流程都能闭环。

### 6.1 验证清单

| 编号 | 验证项 | 验证方法 | 通过标准 | 失败后的处理 |
| --- | --- | --- | --- | --- |
| V1 | 飞书权限和读写能力 | 创建测试应用，读取线上内容基线表，写入测试推荐表，更新状态字段 | 能分页读取、批量写入、批量更新；状态字段不被覆盖 | 先修权限、表结构、应用发布流程，不进入采集开发 |
| V2 | 线上内容表质量 | 抽样 100-300 条线上内容，检查标题、类型、季集号、外部 ID、状态字段 | 至少 70% 可自动形成可用基线；低置信度项可被标记 | 先做基线清洗或增加外部 ID 字段 |
| V3 | 实体匹配准确率 | 用线上内容样本匹配 TMDb/Trakt/IMDb ID，人工复核结果 | 高置信度匹配准确率 >= 95%；误匹配率 <= 2% | 降低自动过滤范围，增加人工确认队列 |
| V4 | 数据源覆盖率 | 对最近 30 天 Netflix/Prime Video/主流英文剧集做 dry run，对比人工已知更新 | 主要热门剧集和新季能被发现；漏报原因可解释 | 增加 Watchmode/JustWatch 或人工补充入口 |
| V5 | episode 级识别能力 | 抽样 30-50 部连载剧，验证新集、季号、集号、air_date | episode 粒度可识别且不把不同集误合并 | MVP 降级为 season/show 级推荐，并标记需人工确认 |
| V6 | 冷启动候选规模 | 跑最近 180 天 bootstrap dry run，只输出统计和 top 候选 | P0/P1 可控制在 200 左右；人工可消化 | 提高阈值、缩短窗口、分批按周追赶 |
| V7 | 数据延迟 | 连续观察 7-14 天，记录 Trakt/TMDb/Netflix Top 10 发现时间 | daily 能覆盖近期高价值内容，延迟可接受 | 把 daily 定义为近期补漏推荐，而不是实时更新 |
| V8 | 商业授权边界 | 确认 TMDb、IMDb、Watchmode/JustWatch 的商业使用要求 | 原型和生产各自允许的数据源边界明确 | 原型仅内部验证；生产替换为商业授权源 |
| V9 | 供应商流程 | 用 10-20 条候选模拟批次、提交、下载、入库、上架 | 飞书字段能覆盖真实状态流转和导出格式 | 调整批次表和流转表后再开发自动化 |
| V10 | 运营可接受指标 | 让人工审核一批 dry run 结果，统计有用率、误报率、重复率 | P0/P1 有用率 >= 60%；重复率 <= 5% | 调整 hot_score、来源权重、过滤规则 |

### 6.2 最小验证顺序

建议先做三个最小验证，不要一开始就搭完整系统。

1. 飞书基线验证  
   读取现有线上内容表，抽样输出 `baseline_match_status`。验证权限、分页、字段类型和基线质量。

2. 最近 30 天 TV dry run  
   使用 Trakt + TMDb 生成最近 30 天电视剧候选，不写入飞书，只输出本地报告。

3. 人工复核闭环  
   人工复核 50-100 条候选，统计漏报、误报、重复、实体匹配错误和真正值得提交的比例。

### 6.3 Go / No-Go 标准

满足以下条件后，才建议进入正式 MVP 开发：

| 条件 | 标准 |
| --- | --- |
| 飞书 API | 能读取线上基线，能写入推荐表，能更新状态 |
| 基线质量 | 线上内容中大多数可形成 movie/season/episode 级基线 |
| 实体匹配 | 高置信度匹配准确率 >= 95% |
| 数据覆盖 | 最近 30 天主流热门剧集更新能被发现 |
| 候选质量 | P0/P1 人工认可率 >= 60% |
| 冷启动规模 | 最近 180 天 P0/P1 能被控制在可审核范围 |
| 授权边界 | 原型和生产的数据源使用边界明确 |
| 供应商流程 | 批次和履约状态能覆盖真实操作 |

出现以下任一情况，应暂停完整开发，先解决前置问题：

1. 飞书线上内容表无法通过 API 稳定读取。
2. 线上内容缺少季集号且自动匹配误判率高。
3. Trakt + TMDb 对最近 30 天核心英文剧集覆盖明显不足。
4. 需要生产依赖 TMDb/IMDb 商业数据，但授权尚未确认。
5. 供应商流程要求的字段和当前飞书表设计不匹配。

### 6.4 验证产物

开发前验证应输出以下文件或记录：

| 产物 | 说明 |
| --- | --- |
| baseline_quality_report.md | 线上内容基线质量、字段缺失、匹配结果 |
| source_coverage_report.md | 最近 30 天数据源覆盖率、漏报、误报 |
| bootstrap_dry_run_report.md | 180 天追赶候选规模和 P0/P1 分布 |
| supplier_flow_check.md | 供应商批次和履约状态验证结果 |
| authorization_decisions.md | 原型和生产阶段可用数据源边界 |

这些产物不一定都要在第一天完成，但前三个应在正式开发前完成。

## 7. 推荐架构

```text
Scheduler / CLI
-> Source collectors
   -> Trakt collector
   -> TMDb collector
   -> Netflix Top 10 collector
   -> Optional Watchmode / JustWatch collector
-> Local cache and raw store
-> Normalizer
-> Baseline matcher
-> Scorer
-> Business deduper
-> Feishu sync
-> Feishu report generator
```

关键设计建议：

1. 必须有本地数据库，例如 SQLite 或 PostgreSQL。
2. 飞书只保存业务结果和人工状态，不保存所有原始采集。
3. 所有外部 API 响应都要缓存，至少缓存 7-30 天。
4. 所有外部调用统一走限流队列。
5. bootstrap、daily、backfill 共用同一套去重和评分逻辑。
6. 先实现 dry run，再写飞书。

## 8. MVP 可行落地顺序

### Phase 0：开发前验证

- 完成 V1、V2、V3、V4 的最小验证。
- 输出 `baseline_quality_report.md` 和 `source_coverage_report.md`。
- 明确原型阶段和生产阶段可用数据源边界。

### Phase 1：飞书基线和手动 dry run

- 读取现有线上内容基线表。
- 做字段映射和 `baseline_match_status`。
- 先不写外部推荐，只验证飞书权限、分页、字段格式、状态读取。

### Phase 2：Trakt + TMDb 候选发现

- 接 Trakt trending/calendar。
- 接 TMDb search/find/details/watch providers。
- 生成 `content_update_id`。
- 输出本地 dry run 报告。

### Phase 3：bootstrap 追赶

- 最近 180 天追赶。
- P0/P1 上限 200。
- 写入推荐更新表。
- 生成 bootstrap 飞书报告。

### Phase 4：daily 自动化

- 每日运行。
- P0/P1 上限 50。
- 读取飞书业务状态做去重。
- 生成日报。

### Phase 5：数据源增强

- 加 Netflix Top 10。
- 评估 Watchmode/JustWatch 商业数据源。
- 若需要 IMDb 热度，评估 IMDb 商业授权。

## 9. 结论

MVP 可以做，但要把目标收窄为“候选发现和运营决策辅助”，不要承诺“完整、精确、全平台、episode 级上线数据库”。

当前最稳的路线：

1. 先用飞书线上内容表建立基线。
2. 用 Trakt 发现 TV 更新。
3. 用 TMDb 做元数据、ID 映射和基础平台来源。
4. 用 Netflix Top 10 做热度增强。
5. 用飞书做审核、批次和履约状态。
6. 原始数据和日志放本地数据库。
7. 生产商业使用前，优先确认 TMDb 授权；IMDb 只在授权后使用评分和热度数据。

如果后续业务要求“精确知道某一集在哪个平台上线”，应把 Watchmode 或 JustWatch Partner API 纳入商业数据源评估。
