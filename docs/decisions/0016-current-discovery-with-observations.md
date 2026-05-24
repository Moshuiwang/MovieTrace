# ADR-0016: daily-discover 改为当前发现项 + observation 留痕

**状态：** Accepted
**日期：** 2026-05-24
**决策者：** moshuiwang + Codex (GPT-5)

## 上下文

ADR-0012 将 `content_updates` 改为事件历史表，允许同一内容跨天重新命中时再次生成 discovery 事件。这个选择解决了“重新变热被静默吞掉”的问题，但在 V1 运行观察期暴露出新的运营成本：

- 同一内容连续多天命中时，飞书热点发现表会出现多行，运营表更像每日流水账，而不是待处理工作台。
- 重复命中的旧内容仍可能继续走重 enrichment、导出和同步流程，消耗 API 与运行时间。
- 下游需要用去重、人工字段保护、最近 N 天窗口解释等补丁逻辑处理重复事件副作用。

新的产品语义是：`daily-discover` 每天仍然采集和计算当天热度，但飞书中间表应以“一个稳定内容一行”的当前工作台为主。历史热度不丢弃，改由 B 库 observation 留痕承担。

本 ADR 修正 ADR-0012 中 discovery 类事件的输出语义；`new_season` 等基线追踪事件不在本次决策范围内。

**与 `new_season` 共存的语义裂缝**：本 ADR 只对 discovery 切换为 current item + observation；`new_season` 仍走 `content_updates` 事件历史。这意味着导出和飞书同步在过渡期内会同时承载两种语义：discovery 行使用稳定键 `discovery:{type}:{tmdb_id}`、按 current 表的最近发现日期窗口；`new_season` 行继续使用 `season:{...}` 事件键、按事件 created_at 窗口。这是有意识的局部取舍：`new_season` 的"每季一行"天然不会跨天重复，迁移成本不值得。后续如需统一，应另开 ADR。

## 决策

**将 daily-discover 的 discovery 输出从“每日事件行”改为“当前发现项 + observation 留痕”。**

具体边界：

- B 库持有业务状态，飞书只做投影；不得用“飞书里是否已有行”反向决定 discovery pipeline。
- discovery 使用稳定内容键，例如 `discovery:{movie|tv}:{tmdb_id}`，不再用日期制造跨天新运营项。
- B 库维护“当前发现项”概念：一个稳定内容一行，保存首次发现时间、最近发现时间、发现次数、最新 `hot_score`、最新优先级、最新来源摘要和稳定 metadata。
- B 库新增或等价实现 observation 留痕：每个稳定内容在每个有效观察日记录一条 observation，保存当天来源摘要、原始热度输入、score breakdown、当时算出的 `hot_score` 和优先级。
- 不新增 `score_version` / `scoring_config_hash` 字段。历史 `hot_score` 只视为当时规则下的快照；如未来需要趋势分析，应使用 observation 中保存的原始热度输入按当前规则回算。
- 首次发现的内容走完整 enrichment，创建当前发现项并写 observation。
- 已存在的内容再次命中时，默认跳过重 enrichment，只写 observation，并更新当前发现项的最近状态字段。
- 纯 source-date fallback 不计入有效 observation，不更新最近发现时间和发现次数；fresh + fallback 混合时可以写 observation，fallback 只作为上下文。
- 飞书热点发现表同步当前发现项，不同步 observation。旧内容再次命中时只更新系统字段，例如最近发现时间、发现次数、最新分数、最新优先级、数据源状态、同步时间。
- 现有飞书字段 `同步批次` 暂不改名、不移除。当前程序已使用它做系统同步查重/日期过滤；运营如需记录交给供应商的批次，应在多维表格中新增独立人工字段，例如 `供应商批次` 或 `运营批次`，程序不写该字段。

## 后果

**正面：**

- 飞书热点发现表从每日流水账收敛为运营工作台，同一内容跨天重复命中不会新增多行。
- 历史热度仍保留在 B 库 observation 中，不牺牲后续分析能力。
- 旧内容重复命中可以跳过重 enrichment，降低 API 调用和运行时间。
- 业务状态集中在 B 库，飞书同步层只负责幂等投影和人工字段保护，架构边界更清楚。
- 导出和同步不再需要围绕最近 N 天重复事件做大量解释或补丁式去重。

**负面 / 待解决：**

- 需要新增或调整 B 库 schema，并迁移 discovery 查询、导出和飞书同步语义。
- ADR-0012 的 discovery 事件历史模型被本 ADR 部分取代，后续任务包需要明确兼容旧 `content_updates` 数据。
- 飞书字段 `同步批次` 仍保留系统用途，命名与运营“供应商批次”概念可能继续有歧义；短期通过新增人工字段解决。
- 不记录 `score_version` 会让历史 `hot_score` 不能直接跨规则比较；这是有意取舍，换取 V1 复杂度收敛。

## 备选方案

### 备选 A：继续 ADR-0012 的每日事件历史模型

- 优点：实现已存在；重新变热天然可见；无需新增 current / observation 概念。
- 缺点：飞书重复行多，运营扫描成本高；旧内容重复加工；下游持续承担去重和人工字段保护压力。
- 拒绝原因：当前产品目标已从“每日事件都给运营看”转为“运营表一内容一行，重复命中只更新时间与热度”。

### 备选 B：只在飞书同步层折叠重复内容

- 优点：改动面较小，能快速减少飞书重复行。
- 缺点：B 库仍然每天生成重复 discovery 事件，重 enrichment、导出窗口、历史状态语义都没有真正收敛；飞书会变成隐含状态源。
- 拒绝原因：复杂度应收敛到 B 库状态更新，而不是推给飞书同步层。

### 备选 C：current 项 + observation，并记录 score_version

- 优点：历史分数可按版本分段解释，适合做长期趋势分析。
- 缺点：新增评分版本实体和维护成本；当前 V1 只需要运营工作台和基础留痕。
- 拒绝原因：已保存原始热度输入，未来需要趋势时可以回算；现阶段不增加 `score_version`。

### 备选 D：冷却期策略

- 优点：短期减少重复，同时允许长期重新提醒。
- 缺点：需要定义不同内容类型和更新类型的冷却窗口，仍然会把“何时再次展示”变成产品策略复杂度。
- 拒绝原因：当前需求更明确：稳定内容一行，重复命中更新当前状态并写 observation。

## 引用

- 修正：ADR-0012 `content_updates` discovery 每日事件历史语义
- 相关边界：ADR-0007 A 库 / B 库 / 中间表三层架构
- 后续任务包：P1.57a-l（schema、helper、回填、write gate、双写、export、飞书字段、飞书稳定键、停止旧事件写、repeat-hit enrichment skip、自动升级/重建验证、开发 shadow cron）
