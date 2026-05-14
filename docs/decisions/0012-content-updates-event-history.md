# ADR-0012: content_updates 改为事件历史表

**状态：** Accepted
**日期：** 2026-05-14
**决策者：** moshuiwang + Codex (GPT-5)

## 上下文

当前 `content_updates` 由唯一索引 `(canonical_item_id, update_type)` 去重，写入逻辑使用 `insert or ignore`。这导致同一内容同一更新类型只要曾经入库，之后即使隔天、隔周或隔月重新变热，也不会再次写入。

这和产品预期冲突：`daily-discover` 的核心价值是让运营看到“今天值得看”的更新事件。重复出现虽然会增加运营扫描量，但代价可控；系统静默吞掉重新变热内容的风险更高。

## 决策

**将 `content_updates` 语义从“全局去重建议池”改为“事件历史表”。**

具体边界：

- 每天 `daily-discover` 命中的内容，允许生成当天的 `content_update` 事件。
- 去重只限制“同一个业务事件被同一天/同一次流程重复写入”，不阻止跨天再次出现。
- 使用 `content_update_id` 作为事件级唯一键。
- discovery 类事件的 `content_update_id` 必须包含 TMDb 媒体命名空间和日期，例如 `discovery:{movie|tv}:{tmdb_id}:{snapshot_date}`，避免 movie/tv 共享数字 ID 时发生事件冲突。
- `new_season` 事件的 `content_update_id` 必须包含 season，例如 `new_season:vs_{id}:s{season}`。
- 暂不新增冷却期、物化当前建议表或 observation 明细表。
- 当前建议清单由查询窗口承担：`export-recommendations --days N` / `inspect-updates --days N`。

## 后果

**正面：**
- 重新变热的内容会重新进入最近 N 天导出，不再被历史去重吞掉。
- `content_updates` 语义更接近“检测到的业务更新事件历史”。
- 实现复杂度低，不需要引入冷却期调度或额外视图表。
- 每日重复出现本身可作为持续热门信号。

**负面 / 待解决：**
- 最近 N 天导出里可能出现同一内容多天重复记录，运营需要快速扫过或后续在导出层折叠。
- 历史表会增长，需要未来按实际规模决定是否归档或增加查询索引。
- 旧数据需要 migration 处理唯一索引；必须避免破坏现有 `content_update_id`。

## 备选方案

### 备选 A：保持 `(canonical_item_id, update_type)` 全局去重
- 优点：运营不会看到重复内容。
- 缺点：重新变热的内容会被静默吞掉，最近 N 天导出不完整。
- 拒绝原因：漏掉今天的有效信号比重复展示更危险。

### 备选 B：事件历史表 + 物化当前建议视图
- 优点：既保留历史，又能给运营一个折叠后的当前清单。
- 缺点：需要新增表/视图语义、刷新策略和更多测试，当前阶段复杂度过高。
- 拒绝原因：用户明确认为现阶段没必要为“每天刷屏”增加复杂性。

### 备选 C：冷却期策略
- 优点：避免短期重复，同时允许长期重新提醒。
- 缺点：需要为不同 `update_type` 设计窗口，属于产品策略而非当前必要修复。
- 拒绝原因：先采用更直接的每日事件历史模型，后续根据运营反馈再折叠。

## 引用

- 来源：CR-005（`reports/code_review_2026-05-14.md`）
- 任务包：`docs/tasks/p1.13_content_updates_event_history.md`
- 相关代码：`src/movietrace/db/schema.py`、`src/movietrace/pipeline/discovery.py`、`src/movietrace/pipeline/baseline_tracking.py`
