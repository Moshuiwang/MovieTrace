# 项目范围边界（SCOPE）

> AI 做"任务可不可做"的硬边界仲裁。任务模糊时先对照本文件判断是否越界。
> 详细路线图见 [`docs/product_roadmap.md`](docs/product_roadmap.md)；阶段切换或范围调整时更新本文件。

**当前阶段：** Phase 1 全部任务包已完成；V1 运行观察期。

## V1 做什么

每日检测全网热门英文影视更新事件；A 库 TV 剧集新季更新由 `baseline-track` 独立执行，输出清单供运营挑选（[ADR-0007](docs/decisions/0007-repositioning-to-update-tracking.md)）。

**核心范围：** 全网热门追踪 · 基线 TV 主动追踪（电影跳过）· `hot_score` 综合评分 · A 库匹配标记 · 检测/导出解耦 · 三类输出（🆕 新增 / ♻️ 已有可补充 / ⚠️ 低置信度）· 本地 MD/JSON 报告 + 飞书运营三张子表 · `content_updates` 事件历史表（[ADR-0012](docs/decisions/0012-content-updates-event-history.md)）。
**数据源 / 技术栈：** TMDb · Trakt · OMDb · FlixPatrol 合规公开页面；Python 3.12 + SQLite 本地 B 库。

## V1 明确不做（scope creep 防线）

- **付费 API / 社交信号：** Watchmode、IMDb Pro、JustWatch Partner、社交评分或平台热度不进 V1
- **AI 推理：** LLM 用户契合度、多 Agent、Embedding、协同过滤、时序预测、AI 文案不进 V1
- **业务下游：** 自动提交供应商、自动下载/入库/上架、国家粒度上线追踪、资源版本管理、后台管理页不进 V1
- **V1.5 边界：** 电影主动追踪、TV episode 级追踪、抽象 Writer 多态、A 库写入、系统侧主观审核字段不进 V1
- **合规绝对线：** 详见 [`.claude/rules/22-sources-compliance.md`](.claude/rules/22-sources-compliance.md)

## V2 触发条件

仅当 V1 稳定运行 ≥ 1-2 个月、运营反馈具体短板、投入产出比清晰且业务方同意额外成本后启动。候选方向见 [`docs/product_roadmap.md § 3`](docs/product_roadmap.md)。

## 边界判断

任务在 V1 范围 → 继续读任务包；不在 → 是 V2（放入 backlog）/ 合规外（拒绝并报告）/ 边界模糊（向用户澄清，不擅自决策）。**默认按更窄解释**，争议写入任务包"风险点"。历史范围变更：[`docs/decisions/`](docs/decisions/README.md)（ADR-0001/0002/0003/0007/0012）。
