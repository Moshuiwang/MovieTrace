# MovieTrace 上下文加载地图

> Agent 启动时按此地图**分层加载**，不做全量读取。
> 最后更新：2026-05-14（P1.16）

---

## 第一层：当前层（每次启动默认读取）

| 文件 | 内容 | 为什么 |
|------|------|--------|
| `STATE.md` | 当前阶段、进行中任务、阻塞项、交接 | 知道现在在哪 |
| `SCOPE.md` | V1/V2 边界、当前阶段做什么不做什么 | 防止越界 |
| 本文件 | 加载规则地图 | 知道去哪找 |

**预算：** 3 个文件，~300 行。

---

## 第二层：操作层（运行、排障、反馈时读取）

| 场景 | 文件 | 为什么 |
|------|------|--------|
| 日常运行 | `docs/operations/runbook.md` | CLI 命令、备份、排障 |
| 运营反馈 | `docs/operations/feedback_log_template.md` | 反馈格式 |
| 排查故障 | `docs/workflow/troubleshooting.md` | 排查方法论 |
| 写日报 | `docs/workflow/journal-spec.md` | 日报格式 |
| 会话收尾 | `docs/workflow/session-checklist.md` | 收尾清单 |
| 完成任务汇报 | `docs/workflow/report-format.md` | 报告格式 |

---

## 第三层：决策层（边界争议、产品判断、架构问题时读取）

| 场景 | 文件 | 为什么 |
|------|------|--------|
| V1/V2 边界争议 | `SCOPE.md` + `docs/product_roadmap.md` | 定位和路线图 |
| 架构判断 | `docs/decisions/` 下相关 ADR | 历史决策 |
| 需求变更 | `docs/requirements.md` + `SCOPE.md` | 当前需求基线 |
| 飞书运营同步 | `docs/notes/feishu_ops_sync_requirements.md` | 运行观察期新增需求草案，记录 lark-cli 调研和产品边界 |
| V1 复盘 | `docs/reviews/v1_closeout_review.md` | 能力和边界总结 |

**ADR 索引：** `docs/decisions/README.md`

---

## 第四层：历史层（默认不整篇读取）

**原则：** 先 `rg` 搜索关键词，再打开命中片段。

| 内容 | 文件 | 搜索关键词示例 |
|------|------|---------------|
| Phase 1 历史 | `docs/history/phase1_state_archive.md` | `Phase 1.7` `P1.8-D` `virtual_series` |
| 已完成任务包 | `docs/tasks/p1.*.md` | `OMDb` `migration 012` `FatalApiError` |
| 历史日报 | `journal/` | `2026-05-13` `daily-discover` |
| 旧验证报告 | `reports/` | `flixpatrol_zero` `e2e_validation` |

```bash
# 例：查某个 Phase 的详细执行结果
rg -n "P1.8-D|P1.8-E|008_api_usage" docs/history/phase1_state_archive.md docs/tasks/

# 例：查某个功能的实现记录
rg -n "virtual_series|canonical_items|OMDb" docs/history/phase1_state_archive.md
```
