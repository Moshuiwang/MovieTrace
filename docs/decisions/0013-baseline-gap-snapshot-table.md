# ADR-0013: A库缺口快照表

**状态：** Accepted
**日期：** 2026-05-16
**决策者：** moshuiwang + Claude Code (claude-sonnet-4-6)

## 上下文

### 事件回溯

2026-05-16，一次清理操作删除了 `content_updates` 中全部 151 条 `new_season` 记录，但 `virtual_series.local_max_season` 水位线**未随之回滚**。结果是 `baseline-track` 检测时以内存水位判断已无缺口，实际上 TMDb 已播新季对 A 库的缺口信息完全丢失。飞书"每日发现"子表也没有基线缺口视图——它只读 `content_updates` 事件，事件丢失则视图为空。

### 根本原因

`baseline-track` 的可观测层（飞书同步）依赖事件日志（`content_updates`）而非当前 DB 状态。事件日志天然有损（可被清理、可被人工操作），不适合作为运营视图的唯一数据源。

### ADR-0012 背景

ADR-0012 将 `content_updates` 语义化为事件历史表（而非全局去重池），保留了完整事件记录能力。但事件历史同样会因操作失误而丢失，无法保证运营视图的健壮性。

## 决策

**引入新 Feishu 子表"A库缺口"，作为 virtual_series 当前缺口状态的快照视图。**

该表：

- 直接读取 `virtual_series` + `canonical_items` + `external_ids` + `api_cache` 四张表，**不依赖** `content_updates`。
- 每次运行时全量计算当前缺口，以 `TMDb ID`（对应 virtual_series 唯一键）进行 upsert。
- 过滤条件：`poll_priority != 'skip'` AND `A库当前最大季 < TMDb 已播最大季`（即 gap > 0）。
- 每行对应一个 virtual_series，不按日期分行（状态快照，不是事件日志）。

## 范围

| 范围项 | 当前决策 |
|--------|----------|
| 季级缺口 | ✅ 本次实现 |
| 集级缺口 | ❌ 预留字段（缺口集），V2 实现 |
| 事件维度（首次发现时间） | ❌ 在 `content_updates` 中保留，本表不展示 |

## 数据流

```
virtual_series
  ↓ poll_priority != 'skip'
canonical_items  →  a_lib_max_season = MAX(season_number WHERE upstream link exists)
api_cache        →  tmdb_aired_season = json_extract(last_episode_to_air.season_number)
content_updates  →  hot_score = MAX(recent 30d) [辅助信息，非核心]
  ↓
gap_count = tmdb_aired_season - a_lib_max_season
gap_seasons = S{a+1}, S{a+2}, ..., S{tmdb_aired}
  ↓ gap_count > 0
Feishu "A库缺口" 子表  upsert by TMDb ID
```

## 字段设计

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 剧集名 | 文本 | virtual_series.name（主键显示列） |
| TMDb ID | 文本 | tmdb_tv_id（upsert 唯一键） |
| 缺口类型 | 单选 | 季 / 集（集为预留） |
| A库当前最大季 | 数字 | MAX(season_number) with upstream link |
| TMDb 已播季 | 数字 | last_episode_to_air.season_number |
| 缺口数 | 数字 | TMDb 已播季 - A库当前最大季 |
| 缺口季 | 文本 | "S4,S5" 格式，列举缺失季号 |
| 缺口集 | 文本 | 预留，暂为空 |
| TMDb 状态 | 单选 | Returning Series / Ended / Canceled 等 |
| hot_score | 数字 | 最近 30 天最高 hot_score |
| 运营状态 | 单选 | 待补 / 部分补充 / 已补 / 跳过 |
| 系统提示 | 单选 | 建议已补（gap=0 时自动标注） / - |
| 最近刷新时间 | 日期 | 本次同步时间 |
| 备注 | 文本 | 人工备注 |

## 状态机

```
运营状态:
  待补          ← 系统创建时默认；gap > 0
  部分补充      ← 运营人工修改；A库已有部分新季但未全补
  已补          ← 运营人工确认；gap=0 后可归档
  跳过          ← 运营决策不追踪此剧

系统提示:
  建议已补      ← 下次刷新时 gap=0，系统自动标注
  -             ← 默认值
```

系统不直接修改 `运营状态`（避免覆盖人工决策），仅在 `系统提示` 字段写入"建议已补"作为提示，由运营人工确认后改 `运营状态`。

## 取舍

**失去的：** 事件维度（"S4 首次被检测到的时间"）。该信息仍在 `content_updates` 中完整保留，但飞书展现层不展开——运营视图聚焦当前状态，不做时间线回溯。

**得到的：** 对 `content_updates` 事件丢失免疫。DB 当前状态才是权威，快照表每次从 DB 重新计算，不依赖任何可丢失的中间产物。

## 备选方案

### 备选 A：恢复 content_updates 事件并继续依赖事件日志

拒绝原因：事件日志本质上可操作可丢失，不适合作为运营视图的单一数据源，本次事故已证明其脆弱性。

### 备选 B：在飞书现有子表中新增基线缺口列

拒绝原因：现有"发现运行日志"子表按事件行，不能承载按 virtual_series 的状态快照语义；混用会造成歧义。

### 备选 C：物化视图 + 定时刷新（DB 侧）

拒绝原因：当前 SQLite 不支持定时任务；飞书子表本身就是最合适的展现层，无需在 DB 侧额外维护。

## 关联

- [ADR-0007](0007-repositioning-to-update-tracking.md) — 系统定位翻转，确立"追踪缺口"而非"推荐"的目标
- [ADR-0012](0012-content-updates-event-history.md) — content_updates 事件历史语义（本表不依赖它，但共存）

## 后续

- **集级扩展**：V2 阶段补全 `缺口集` 字段，`缺口类型` 单选增加"集"选项
- **自动归档**：当 `gap=0` 且 `运营状态=已补` 时，可将行移出活跃视图（过滤组实现）
- **状态推断**：如需自动推进 `运营状态`，需新增 ADR 说明覆盖人工状态的条件和边界
