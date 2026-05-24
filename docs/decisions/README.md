# 架构决策记录（ADR）

> **目的：** 记录项目重要决策的"上下文 / 决策 / 后果 / 备选"，避免下一个 Agent 把已否决的方案重新拉回讨论（决策回撤）。

**格式：** Michael Nygard 风格（精简）
**命名：** `NNNN-kebab-case-title.md`
**编号：** 单调递增，不重用，不删除（即使被推翻也保留并标记 superseded）

---

## ADR 索引

| 编号 | 标题 | 状态 | 日期 |
|------|------|------|------|
| [0001](0001-feishu-baseline-as-marker-not-filter.md) | 飞书基线从过滤逻辑改为标记参考 | ✅ Accepted | 2026-05-10 |
| [0002](0002-v1-v2-strict-separation.md) | V1/V2 严格划分原则 | ✅ Accepted | 2026-05-10 |
| [0003](0003-flixpatrol-as-v1-data-source.md) | V1 引入 FlixPatrol 作为真实平台热度源 | ✅ Accepted | 2026-05-10 |
| [0004](0004-phase0-medium-no-auto-promotion.md) | Phase 0 不自动升级 26 条电影误标记录 | ✅ Accepted | 2026-05-10 |
| [0005](0005-sup-a-stdlib-only.md) | SUP-A 任务包仅使用 stdlib，不引入新依赖 | ✅ Accepted | 2026-05-10 |
| [0006](0006-flixpatrol-api-over-html.md) | P1-B 数据源从 HTML 爬虫切换到付费 API | ✅ Accepted | 2026-05-11 |
| [0007](0007-repositioning-to-update-tracking.md) | 系统定位翻转 —— 从"推荐+人工审核"到"更新追踪+中间表" | ✅ Accepted（2026-05-12 修正：飞书全链路移除；2026-05-14 修正：TV 新集追踪入 V2） | 2026-05-11 |
| [0008](0008-multi-source-union-discovery.md) | 多热门源独立采集与并集发现架构 | ✅ Accepted | 2026-05-13 |
| [0009](0009-p1-8-api-budget-and-rating-fallback.md) | P1.8 API 预算与评分兜底策略 | ✅ Accepted | 2026-05-13 |
| [0010](0010-no-real-api-calls-in-automated-tests.md) | 自动化测试不消耗真实外部 API | ✅ Accepted | 2026-05-14 |
| [0011](0011-secrets-path-migration.md) | Secrets 路径从 /tmp 迁移到 ~/.config/movietrace/ | ✅ Accepted | 2026-05-14 |
| [0012](0012-content-updates-event-history.md) | content_updates 改为事件历史表 | ✅ Accepted | 2026-05-14 |
| [0013](0013-baseline-gap-snapshot-table.md) | A 库缺口快照子表（实时从 virtual_series 算缺口）| ✅ Accepted | 2026-05-16 |
| [0014](0014-legacy-schema-cleanup.md) | ADR-0007 翻转前 6 张遗留表清理（migration 016）| ✅ Accepted | 2026-05-16 |
| [0015](0015-feishu-doc-import-via-import-tasks.md) | sync_doc 切换 drive/v1/import_task（删 docx-blocks API）| ✅ Accepted | 2026-05-16 |
| [0016](0016-current-discovery-with-observations.md) | daily-discover 改为当前发现项 + observation 留痕 | ✅ Accepted | 2026-05-24 |

---

## 写一份新 ADR 的时机

应该写：
- 产品方向调整
- 技术选型（数据库、框架、库）
- 范围边界变更（V1 → V2 / 删减/新增）
- 不引入某项依赖的决定（拒绝也是决策）
- 任何"现在选 A 不选 B"且 B 是合理候选的判断

不应该写：
- 临时探索（写在任务包、PR 描述或本轮对话即可）
- 显然不需要解释的事（如修复一个 typo）
- 单文件实现细节（写 commit message 即可）

---

## 状态语义

- `Proposed` — 提出，待验证或评审
- `Accepted` — 采纳，正在执行
- `Superseded by NNNN` — 被新 ADR 替代（保留可读，但不再生效）
- `Deprecated` — 已弃用但未被替代
- `Rejected` — 提出但未采纳（保留作为"为什么没选"的证据）

---

## ADR 模板

```markdown
# ADR-NNNN: 标题

**状态：** Proposed | Accepted | Superseded by NNNN | Deprecated | Rejected
**日期：** YYYY-MM-DD
**决策者：** 用户 + Agent (model)
**相关 Commit：** `xxxxxxx`

## 上下文

（问题是什么？为什么需要决策？现在的限制和选项是什么？）

## 决策

（选了什么？一句话核心，再展开。）

## 后果

**正面：**
- ...

**负面 / 待解决：**
- ...

## 备选方案

### 备选 A：...
- 优点：
- 缺点：
- 拒绝原因：

### 备选 B：...
（同上）

## 引用

- 相关讨论：PR / issue / 任务包链接
- 相关任务：docs/tasks/xxx.md
- 相关代码：commit xxxxxxx
```
