# ADR-0003: V1 引入 FlixPatrol 作为真实平台热度源

**状态：** 🔄 Proposed（待 Phase 0+ 验证通过后转为 Accepted）  
**日期：** 2026-05-10  
**决策者：** 用户 + Claude Code (Haiku 4.5)  
**相关 Commit：** `b584e94`

---

## 上下文

ADR-0001 决定"飞书基线作为标记参考"后，V1 必须有一个**独立的发现引擎**。

候选数据源分析（脱离 API 限制后的全景，详见 [`docs/product_roadmap.md`](../product_roadmap.md) § 2.1）：

| 信号维度 | 代表来源 | 现有 API 能给吗？ |
|---------|---------|------------------|
| 真实平台热度 | Netflix Top 10、FlixPatrol | ❌ 没有 |
| 社区热度 | TMDb / Trakt | ✅ 已接入 |
| 内容质量 | IMDb 评分 | ✅ OMDb 已接入 |
| 评分多源验证 | RT / Metacritic | ❌ V2 |
| 用户契合度 | LLM 判断 | ❌ V2 |

**核心缺口：** TMDb / Trakt 是社区热度（影迷为主），与 Netflix Top 10 等"大众真实收视"经常背离。如果 V1 缺这个维度，推荐内容会偏向"影迷小众"而非"大众热门"。

**FlixPatrol 是行业事实标准的"流媒体平台 TOP 聚合源"**：
- 聚合了 Netflix、Prime Video、Disney+、Apple TV+、HBO Max、Hulu 等所有主流平台的官方排行榜
- 按地区（Global / US / 各国）和按平台细分
- 公开网页可访问（不需要 API Key）
- 部分付费 API + 公开页面是常见组合

**符合 V1 准入标准（ADR-0002）：**
- ✅ 免费（公开页面）
- ✅ 低复杂度（HTML 解析 + 缓存）
- ✅ 价值已确认（覆盖核心信号缺口）
- ✅ 2-3 周可完成验证 + 实现

## 决策

**V1 引入 FlixPatrol 作为真实平台热度源。**

实施前置：**Phase 0+ 必须先完成接入验证（SUP-A 到 SUP-F）**，包括：
1. 可访问性（公开页面是否可稳定访问）
2. HTML 解析稳定性
3. 与 TMDb 候选的匹配率（≥ 80%）
4. 服务条款合规性
5. 长期访问稳定性（1 周观察）

**只有 Phase 0+ 通过，本 ADR 才转为 Accepted。否则按"备选方案"中的 fallback 处理。**

### V1 中的角色定位

- 在 `hot_score` 公式中权重 **30%**（占比最大）— 见 [`requirements.md`](../requirements.md) § 10.2
- 数据缓存 24 小时，礼貌访问频率（≥ 2 秒间隔）
- 失败时降级运行（不中断整体推荐），但记录 BLOCKER

## 后果

**正面：**
- 解决"缺真实平台热度"核心信号缺口
- 推荐内容更贴近大众真实收视
- 数据成本 = 0（公开页面）
- 与现有 TMDb / Trakt / OMDb 形成多维信号矩阵

**负面 / 待解决：**
- ⚠️ **服务条款风险**（待 SUP-D 评估）—— 商业生产前可能需要法律审视
- ⚠️ HTML 结构变化风险（FlixPatrol 改版会导致解析失败）—— 需监控告警
- ⚠️ IP 封禁风险（高频访问）—— 已通过缓存 + 礼貌频率缓解
- ⚠️ JavaScript 渲染风险（如果 Top 10 数据由前端动态加载，stdlib 抓不到）—— 待 SUP-B 验证

## 备选方案

### 备选 A：直接爬 Netflix Tudum + 各平台官方页面

- 优点：数据最权威
- 缺点：每个平台单独维护爬虫；合规风险更分散
- **拒绝原因：** 维护成本高于 FlixPatrol 聚合一处

### 备选 B：付费 Watchmode API（V2 方向）

- 优点：商业级数据，episode 级精确
- 缺点：$99-499/月，违反 V1 免费原则
- **拒绝原因：** 不符合 ADR-0002 V1 准入标准；放入 V2 backlog

### 备选 C：完全不引入真实平台热度（仅 TMDb/Trakt 社区热度）

- 优点：实现最简单，零接入风险
- 缺点：失去 V1 最关键的产品差异化信号
- **拒绝原因：** ADR-0001 决定独立发现，备选 C 让独立发现失去意义

### Fallback：如 Phase 0+ NO-GO

如果 SUP-A/B/C/D/E 任一不通过，**降级到备选 C**（仅 TMDb / Trakt / OMDb），V1 范围相应缩减，但产品上线进度不变。详见 [`docs/phase0_supplement.md`](../phase0_supplement.md) § 6（备选方案）。

---

## 引用

- 关联 ADR：[ADR-0001（飞书基线标记）](0001-feishu-baseline-as-marker-not-filter.md)、[ADR-0002（V1/V2 划分）](0002-v1-v2-strict-separation.md)
- 验证计划：[`docs/phase0_supplement.md`](../phase0_supplement.md)
- 任务包：[`docs/tasks/sup_a_flixpatrol_accessibility.md`](../tasks/sup_a_flixpatrol_accessibility.md)
- 评分公式：[`requirements.md`](../requirements.md) § 10.2
- FlixPatrol 官网：https://flixpatrol.com/
