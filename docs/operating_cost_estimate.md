# MovieTrace 运营成本预估

状态：初版估算  
日期：2026-05-08  
估算前提：代码已实现且功能正常，成本仅计算上线运行所需的第三方服务、服务器、API 和协作工具，不含开发人力。

> 汇率粗算：1 USD ≈ ¥7。实际结算以服务商账单和付款日汇率为准。

## 1. 总体结论

MovieTrace 的运营成本有三档：

| 档位 | 月成本粗估 | 适用场景 | 结论 |
| --- | ---: | --- | --- |
| 原型验证版 | 约 ¥50-200 / 月 | 内部 dry run、小样本验证、不依赖商业数据源 | 可以很低成本启动 |
| 推荐生产版 | 约 ¥200-600 / 月 | 每日运行、飞书协作、稳定服务器、少量 AI 推荐理由 | 建议 MVP 采用 |
| 增强数据源版 | 约 ¥2,500-5,000+ / 月 | 需要精确流媒体 availability、episode 级平台可用性 | 成本主要来自商业数据源 |

最重要的成本判断：

1. **服务器不是主要成本**，轻量 VPS 每月几十元到一百多元即可。
2. **飞书是否付费取决于行数和协作要求**。如果 Lark Base 免费版单表 2,000 行不够，至少需要 Pro；国内飞书协作套件则要以企业后台权益和销售口径确认。
3. **真正贵的是商业影视数据源**。Watchmode Startup 为 $349/month 起；IMDb、TMDb 商业授权一般需要联系销售。
4. **OpenAI/LLM 成本可控**。只生成推荐理由和摘要时，通常每月几十元人民币以内。
5. **MVP 不应一开始购买 IMDb 或 Watchmode**。先用 Trakt + TMDb + 飞书基线跑 dry run，确认覆盖率后再决定。

## 2. 必选成本

### 2.1 服务器

MovieTrace 是定时采集和写飞书，不是高并发用户系统。MVP 只需要一台小服务器即可。

推荐配置：

| 配置 | 适用 | 月成本 |
| --- | --- | ---: |
| 1 vCPU / 1GB RAM / 25GB SSD | 原型、daily 任务、SQLite | $5-6 / 月，约 ¥35-45 |
| 1-2 vCPU / 2GB RAM / 40-60GB SSD | 推荐 MVP，带本地缓存和日志 | $8-12 / 月，约 ¥55-85 |
| 2 vCPU / 4GB RAM / 80GB SSD | bootstrap 更频繁、PostgreSQL 同机 | $20-24 / 月，约 ¥135-165 |

可选服务商参考：

- DigitalOcean Droplet 1GB 公开价约 $6/month，4GB 约 $24/month。
- Hetzner CAX/CX 小规格约 $5-10/month 级别。
- Vultr 常规 1GB 约 $5/month，2GB 约 $10/month。

建议：

1. MVP 用一台 2GB RAM VPS。
2. 数据库先用 SQLite，本地文件备份到对象存储或 GitHub artifact。
3. 不建议一开始上 Kubernetes、GPU、复杂云服务。
4. 如果部署在中国大陆云服务器但不提供公网 Web 页面，通常不需要为了这个任务单独做网站备案；如果后续提供公网后台页面，则需要另行考虑备案和域名。
5. 服务器区域建议优先新加坡、香港、日本或美国，确保能稳定访问 TMDb、Trakt、OpenAI、飞书开放平台。

### 2.2 数据库和存储

MVP 推荐 SQLite：

| 方案 | 月成本 | 说明 |
| --- | ---: | --- |
| SQLite 同机 | ¥0 | 推荐 MVP，足够保存原始响应缓存、运行日志、去重状态 |
| 同机 PostgreSQL | ¥0 | 比 SQLite 重一点，但仍无需额外付费 |
| 托管 PostgreSQL | $15+/月，约 ¥100+ | 省维护，但 MVP 没必要 |
| 对象存储备份 | $1-5/月，约 ¥7-35 | 用于备份 SQLite、日志、导出文件 |

建议：

- MVP：SQLite + 每日压缩备份。
- 进入稳定生产后，如果数据量增长，再迁移 PostgreSQL。
- 飞书不是原始数据库，只保存业务视图和人工状态。

### 2.3 飞书 / Lark 多维表格

这里要区分两种情况：你实际用的是中国飞书，还是 Lark Base 国际版。公开价格口径不同，但成本判断类似。

Lark Base 公开价格：

| 版本 | 价格 | 行数限制 |
| --- | ---: | --- |
| Starter | Free | 2,000 rows / table |
| Pro | $8/user/month，年付 | 20,000 rows / table |
| Enterprise | 联系销售 | 50,000 rows / table |

飞书国内协作套件公开入口能确认的口径：

| 版本 | 价格口径 | 说明 |
| --- | ---: | --- |
| 免费系列 | ¥0 / 人 / 月 | 适合小团队基础协作，包含多维表格入口 |
| 商业系列 | ¥50 / 人 / 月起 | 公开入口显示为商业系列起步价，具体多维表格行数、权限和 API 权益需要以企业后台或销售确认为准 |
| 企业系列 | 联系销售 | 更强安全、组织管理和企业级权益 |

对 MovieTrace 的判断：

| 使用方式 | 是否够用 |
| --- | --- |
| 1 人运营、候选表不超过 2,000 行 | 免费版可能够用 |
| 需要长期保存推荐、批次、供应商流转 | 免费版大概率不够 |
| 需要行/列权限、稳定协作、更多行数 | 建议 Lark Base Pro / 国内商业系列或企业权益 |
| 线上内容基线超过 20,000 行 | 需要拆表、归档或企业版 |

推荐：

1. 原型阶段先用免费版验证 API 权限和表结构。
2. MVP 生产建议至少预留 1 个付费席位。
3. 如果按 Lark Base Pro 估算，1 人约 $8/月，约 ¥55/月。
4. 如果按国内飞书协作套件估算，至少按商业系列起步价 ¥50/人/月预留；如果多维表格容量、权限或自动化超出免费权益，再按实际报价调整。
5. 如果团队多人参与审核，按实际审核人数乘以席位价格。

## 3. 数据源 API 成本

### 3.1 Trakt

成本：公开 Public API 无额外 API 成本。

注意：

- 需要创建 Trakt API 应用。
- GET 限流公开口径为 1000 calls / 5 minutes。
- 应实现限流、缓存、`429` 重试。

对本项目：

- daily 模式足够。
- bootstrap 也够，但要慢速队列。
- 成本按 ¥0 估算。

### 3.2 TMDb

成本：

- 非商业开发使用：免费。
- 商业生产使用：需要联系 TMDb 销售，价格未公开。

对本项目：

- 技术上非常适合作为元数据和 ID 映射主源。
- 但你运营视频网站，存在商业用途，长期生产依赖前应确认授权。

成本估算：

| 阶段 | 成本 |
| --- | ---: |
| 原型 / 内部验证 | ¥0 |
| 生产商业使用 | 未公开，需联系销售 |

建议：

- MVP dry run 可以先用开发者 API 做验证。
- 上生产前，把“是否需要 TMDb 商业授权”作为 Go/No-Go 条件。

### 3.3 IMDb

成本：

- IMDb 非商业数据集免费但仅限非商业。
- IMDb API / 商业数据通过 IMDb Developer 和 AWS Data Exchange，价格通常需要查看 AWS Marketplace purchase options 或联系授权。

对本项目：

- 不建议把 IMDb 免费数据用于生产。
- 不抓取 IMDb 网页。
- MVP 只使用 IMDb ID 做辅助标识。

成本估算：

| 用途 | 成本 |
| --- | ---: |
| IMDb ID 辅助字段 | ¥0 |
| IMDb rating/votes/meters 商业生产 | 未公开，需授权 |

### 3.4 Netflix Top 10

成本：¥0。

注意：

- 这是公开页面，不是稳定 API。
- 适合做热度信号，不适合做完整更新源。
- 应低频读取，例如每周一次。

### 3.5 Watchmode / JustWatch

这类是精确流媒体 availability 的商业数据源。如果你需要知道某个 movie/season/episode 在 Netflix、Prime Video、Disney+ 等平台是否可看，它们比 TMDb/Trakt 更合适。

Watchmode 公开价格：

| 版本 | 价格 | 能力 |
| --- | ---: | --- |
| Developer | Free | 2,500 monthly requests，非商业，最多 3 countries |
| Startup | $349/month，约 ¥2,370/月 | 40,000 monthly requests，商业使用，50+ countries，episode level links |
| Business | $599/month，约 ¥4,070/月 | 100,000 monthly requests，商业使用，优先支持 |
| Enterprise | Custom | 无限请求、S3/sFTP dataset |

JustWatch：

- Partner API 有文档，但价格未公开，需要商务合作。
- 不建议使用非官方 JustWatch npm 包或私有接口做商业生产。

建议：

- MVP 先不买。
- 如果 dry run 证明 TMDb/Trakt 对平台上线信息不够，再评估 Watchmode Startup。
- 一旦业务要求 episode 级平台可用性，Watchmode/JustWatch 很可能成为最大月成本。

## 4. AI / LLM 成本

如果只用于：

- 生成 AI 推荐理由；
- 汇总日报；
- 解释热度依据；
- 对候选做轻量分类；

成本通常很低。

按 OpenAI 当前公开价格，便宜模型如 `gpt-5-mini` 是 $0.25 / 1M input tokens、$2 / 1M output tokens；更强模型如 GPT-5.4 mini 约 $0.75 / 1M input、$4.50 / 1M output。

粗算：

| 使用量 | 月成本估算 |
| --- | ---: |
| 每天 50 条候选，每条生成一句推荐理由 | $1-5/月，约 ¥7-35 |
| 每天 50 条候选 + 日报 + 多日汇总 | $5-20/月，约 ¥35-135 |
| 用高阶模型深度分析大量原始内容 | $20-100+/月，约 ¥135-680+ |

建议：

1. hot_score 不用 LLM 算，用规则引擎算。
2. LLM 只负责解释和摘要。
3. 每日把候选合并成批量 prompt，减少重复上下文。
4. 可以设置月预算上限，例如 $20/月。

## 5. 其他可选成本

| 项目 | 是否必要 | 月成本估算 | 建议 |
| --- | --- | ---: | --- |
| GitHub 仓库 | 否 | ¥0 | 当前公开/私有小项目一般够用 |
| GitHub Actions | 可选 | ¥0-几十元 | daily 任务不建议依赖 Actions，服务器 cron 更稳定 |
| 域名 | 可选 | ¥50-100/年 | 只有做后台页面才需要 |
| 监控告警 | 可选 | ¥0-50/月 | Uptime / Sentry 免费档通常够 |
| 对象存储备份 | 推荐 | ¥7-35/月 | 保存 SQLite 备份和运行日志 |
| 邮件/短信通知 | 可选 | ¥0-50/月 | 飞书消息即可替代 |
| 代理/VPN | 不建议作为架构依赖 | 不稳定 | 应选择能直接访问外部 API 的服务器区域 |

## 6. 三档成本方案

### 6.1 原型验证版

目标：验证数据覆盖率、飞书基线、实体匹配，不追求长期生产稳定。

| 项目 | 月成本 |
| --- | ---: |
| VPS 1GB-2GB | ¥35-85 |
| SQLite | ¥0 |
| 飞书免费版 | ¥0 |
| Trakt | ¥0 |
| TMDb 开发者 API | ¥0 |
| IMDb | ¥0，仅 ID |
| Netflix Top 10 | ¥0 |
| OpenAI | ¥0-35 |
| 备份/监控 | ¥0-20 |
| 合计 | **约 ¥35-140/月** |

适合：

- Phase 0 开发前验证。
- 最近 30 天 dry run。
- bootstrap 统计，不大规模写飞书。

### 6.2 推荐 MVP 生产版

目标：每日运行，写飞书，人工审核，生成日报。

| 项目 | 月成本 |
| --- | ---: |
| VPS 2GB | ¥55-85 |
| 备份/对象存储 | ¥10-35 |
| 飞书/Lark 1 人付费席位 | ¥55-80 |
| Trakt | ¥0 |
| TMDb | ¥0-待授权 |
| Netflix Top 10 | ¥0 |
| OpenAI | ¥35-135 |
| 监控 | ¥0-50 |
| 合计 | **约 ¥155-385/月，不含 TMDb 商业授权** |

如果 3 人参与飞书审核：

- 飞书成本约 ¥165-240/月；
- 总成本约 **¥265-545/月，不含 TMDb 商业授权**。

### 6.3 增强数据源生产版

目标：更准确的 episode 级流媒体 availability，减少平台上线信息漏报。

| 项目 | 月成本 |
| --- | ---: |
| 推荐 MVP 生产版基础成本 | ¥155-545 |
| Watchmode Startup | $349/month，约 ¥2,370 |
| 或 Watchmode Business | $599/month，约 ¥4,070 |
| IMDb 商业数据 | 未公开 |
| TMDb 商业授权 | 未公开 |
| 合计 | **约 ¥2,500-4,600+/月，不含 IMDb/TMDb 未公开授权** |

这档只有在你确认“平台可用性准确性”直接影响业务收益时才值得。

## 7. 我建议的成本路线

### 第 1 阶段：验证期，1-2 周

预算：**¥50-200/月级别**。

使用：

- 小 VPS。
- 飞书免费版。
- Trakt free。
- TMDb developer API。
- SQLite。
- 少量 OpenAI。

目标：

- 证明飞书基线能读。
- 证明最近 30 天 TV 候选能发现。
- 证明实体匹配误判率可控。

### 第 2 阶段：MVP 运行期，1-2 个月

预算：**¥200-600/月级别**。

增加：

- 飞书/Lark 付费席位。
- 稳定备份。
- OpenAI 月预算。
- 监控告警。

仍不建议立刻买 Watchmode 或 IMDb。

### 第 3 阶段：增强数据源期

预算：**¥2,500-5,000+/月级别**。

触发条件：

- TMDb/Trakt 漏报明显；
- 人工仍需大量查平台上线信息；
- 供应商提交价值足以覆盖商业数据源成本；
- 你需要 season/episode 级平台可用性。

此时再评估：

- Watchmode Startup / Business；
- JustWatch Partner API；
- IMDb commercial data；
- TMDb commercial API。

## 8. 开发前需要确认的付费问题

进入生产前，建议逐项确认：

1. 你的飞书线上内容表目前有多少行，预计一年后多少行。
2. 参与审核的人数是多少，是否需要每个人都有飞书付费席位。
3. TMDb 商业授权是否必须，或者是否可把 TMDb 限定为内部辅助数据源。
4. 是否需要 IMDb rating/votes/meters，还是用 Trakt/TMDb/Netflix Top 10 替代。
5. 是否真的需要平台 availability 精确到 episode。
6. 是否需要供应商导出 Excel/CSV，还是飞书视图即可。

## 9. 结论

最现实的 MVP 月成本不是几千元，而是 **约 ¥200-600/月**，前提是：

1. 不购买 Watchmode/JustWatch。
2. 不购买 IMDb 商业数据。
3. TMDb 先作为内部验证源，生产授权另行确认。
4. 飞书只购买必要席位。
5. 服务器用轻量 VPS。

真正会把成本抬高的是两件事：

1. **商业影视数据源**，尤其是 episode 级 streaming availability。
2. **飞书高级/多人协作席位**，如果审核和供应商流程参与人数很多。

建议先用低成本方案完成 Phase 0 验证。只有当验证证明数据覆盖率和运营价值足够，再考虑 Watchmode、IMDb、TMDb 商业授权。

## 10. 参考价格来源

- Lark Base pricing: https://www.larksuite.com/lp/en/base-plans
- 飞书国内商业系列公开入口：https://www.feishu.cn/content
- DigitalOcean Droplets pricing: https://www.digitalocean.com/products/droplets
- DigitalOcean Managed Databases pricing: https://www.digitalocean.com/pricing
- Hetzner 2026 cloud price adjustment: https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/
- Trakt commercial-use discussion: https://forums.trakt.tv/t/asking-about-api-commercial-uses-on-free-plan/99367
- Watchmode API pricing: https://api.watchmode.com/
- IMDb API / AWS Data Exchange: https://help.imdb.com/article/imdbpro/new-features-updates/welcome-to-the-imdb-api/G49M5Y59L5N4WABM
- OpenAI API pricing: https://openai.com/api/pricing/
