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
| [0007](0007-repositioning-to-update-tracking.md) | 系统定位翻转 —— 从"推荐+人工审核"到"更新追踪+中间表" | ✅ Accepted（2026-05-12 修正：飞书全链路移除，见文末） | 2026-05-11 |

---

## 写一份新 ADR 的时机

应该写：
- 产品方向调整
- 技术选型（数据库、框架、库）
- 范围边界变更（V1 → V2 / 删减/新增）
- 不引入某项依赖的决定（拒绝也是决策）
- 任何"现在选 A 不选 B"且 B 是合理候选的判断

不应该写：
- 临时探索（写在 journal 即可）
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

- 相关讨论：journal/YYYY-MM-DD_xxx.md
- 相关任务：docs/tasks/xxx.md
- 相关代码：commit xxxxxxx
```
