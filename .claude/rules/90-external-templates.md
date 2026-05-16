---
name: external-templates
description: 跨项目复用的提示词、决策清单、任务包、设计、复盘模板路径（本机外部目录）。
include: ["**/*"]
---

# 跨项目模板路径

> 本机外部目录 `~/ai-dev-workflow/`，跨多个项目复用的模板集合。
> 这些模板**不在本项目仓库内**；引用前确认本机存在该目录。

## 模板清单

| 类型 | 路径 |
|---|---|
| 提示词模板 | `~/ai-dev-workflow/docs/ai/prompt-templates.md` |
| 决策清单 | `~/ai-dev-workflow/docs/human/decision-checklists.md` |
| 任务包模板 | `~/ai-dev-workflow/docs/templates/task-brief.md` |
| 项目定义模板 | `~/ai-dev-workflow/docs/templates/project-brief.md` |
| 方案设计模板 | `~/ai-dev-workflow/docs/templates/design-brief.md` |
| 评审复盘模板 | `~/ai-dev-workflow/docs/templates/review-retro.md` |

## 使用约定

- 这些是**起点模板**，本项目落地版本见 [`docs/tasks/TEMPLATE.md`](../../docs/tasks/TEMPLATE.md)（任务包）等
- 跨项目复用时按本项目实际情况裁剪，**不要直接照搬**
- 模板更新优先级低于本项目内文档（项目内规则覆盖通用模板）
