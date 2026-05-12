# ADR-0006: P1-B 数据源从 HTML 爬虫切换到付费 API

**状态：** Accepted
**日期：** 2026-05-11
**决策者：** 用户 + Agent B (deepseek-v4-pro)
**相关 Commit：** `81f6f25`（SUP-G 验证通过）

## 上下文

ADR-0003 决定 V1 引入 FlixPatrol 作为真实平台热度源，实施方式为 **HTML 页面解析**（免费），前置验证为 SUP-A~F。

SUP-B 已完成 HTML 解析器实现（48 测试通过），SUP-D 给出 HTML 路径"条件接入"约束（24h 缓存 + 2s 间隔 + UA + 仅供内部使用）。

2026-05-11 用户决定：先验证 FlixPatrol $9.99/月付费 API（SUP-G），如果通过则走 API 路径，否则按原 HTML 路径推进。

SUP-G 验证结果（`81f6f25`）：
- **三项验证全部通过**：认证 ✅ · 6 平台覆盖 ✅ · 字段完整度 ✅
- **TMDb ID 直接返回**（`movie.data.tmdbId`），无需 title+year 二次检索
- 1,000 calls/月配额下，6 平台 × 2 类型 × 30 天 = 360 calls/月，占 36%
- API 采用 JSON:API 风格复合文档格式，字段稳定

## 决策

**P1-B 数据获取走 FlixPatrol 付费 API（$9.99/月），废弃 HTML 爬虫路径。**

保留 `src/movietrace/sources/flixpatrol.py`（HTML 解析器）作为备选代码不删除，但 P1-B 实现以 API 客户端为准。

ADR-0003 的核心决策（FlixPatrol 作为数据源）不受影响；本 ADR 仅切换实施方式。ADR-0003 中与 HTML 路径相关的约束（§ 合规、§ 缓存策略、§ 礼貌频率）由本 ADR 覆盖。

## 后果

**正面：**
- TMDb ID 直接可用，P1-B 跳过整个"title+year → TMDb 搜索"环节
- API schema 稳定，不受 HTML 改版影响，不再需要维护 CSS selector
- 合规更清晰：付费订阅关系覆盖使用条款
- 响应速度快：~1s/call vs HTML ~4s/call（含 2s 合规间隔）
- 字段更丰富：IMDB ID、value 热度分、rankingLast 历史排名
- 配额充足：每日 12 calls（6 平台 × 2 类型），月耗 ~360/1,000

**负面 / 待解决：**
- 月度成本 $9.99（但低于人力维护 HTML parser 成本）
- Apple TV+ endpoint 响应异常慢（28-34s），需要 60s timeout + 重试
- 如后续扩展到更多地区（ADR-0003 未要求但可能），配额消耗线性增长
- 依赖第三方 API 可持续性（涨价/停服风险，概率未知）
- API key 管理：需在 secrets 文件中持久化，不进 git

## 备选方案

### 备选 A：混合路径（API 为主，HTML 补缺）

- 优点：字段不全时有 fallback
- 缺点：维护两套代码，复杂度翻倍
- **拒绝原因：** SUP-G 证明 API 字段完整，无需 HTML 补缺

### 备选 B：维持 HTML 路径（原 ADR-0003 计划）

- 优点：零月度成本
- 缺点：TMDb ID 需二次检索（增加 TMDb API 调用 + 匹配逻辑）；受 HTML 改版影响；合规约束严格
- **拒绝原因：** $9.99/月成本可接受，API 路径综合收益（TMDb ID + 稳定性 + 速度）显著优于 HTML

## 引用

- 被覆盖：ADR-0003 § 实施前置（SUP-A~F HTML 验证）、§ 负面（ToS/改版/封禁风险）
- SUP-G 验证报告：[`reports/sup_g_flixpatrol_api_validation.md`](../../reports/sup_g_flixpatrol_api_validation.md)
- SUP-G 验证脚本：[`scripts/sup_g_flixpatrol_api_check.py`](../../scripts/sup_g_flixpatrol_api_check.py)
- 评分公式（P1-C 依赖）：[`docs/requirements.md`](../requirements.md) § 10.2
- P1-B 任务包：[`docs/tasks/p1_b_flixpatrol_api_ingestion.md`](../tasks/archive/p1_b_flixpatrol_api_ingestion.md)
