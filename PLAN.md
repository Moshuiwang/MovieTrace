# 近期规划（PLAN）

> 前瞻视角：接下来做什么、按什么顺序做。与 STATE.md（已发生）互补。
> **更新策略：** 任务包立项时在此登记；任务合并后移入 STATE.md "最近完成"并从本表删除。
> **Boot 顺序：** STATE → context_map → **本文件** → 具体任务包。

**当前里程碑：** V1 运行观察期（Phase 1 全部完成，等待 V2 触发条件满足）
**最后更新：** 2026-05-21 +08

---

## 即将立项的任务包

| 编号 | 名称 | 来源 | 说明 | 阻塞？ |
|---|---|---|---|---|
| P1.38 | fix-notify-bugs | Bug B-01 / B-02 | 修复飞书卡片缓存计数 0 + 重点内容重复（两 bug 共一 PR）| 无 |

---

## Backlog（V1 观察期内可做，无明确排期）

| 名称 | 来源 | 说明 |
|---|---|---|
| daily log 回填 | issue #4b（暂缓）| 补填历史运行日志 |
| `sync_gap_table` step 6 自动化测试 | Review 跟进项 | 目前仍无覆盖（需飞书桩） |

---

## V2 触发条件（全部满足才启动）

1. V1 稳定运行 ≥ 1-2 个月
2. 运营反馈**具体**需求短板（不是"感觉可以更好"）
3. 投入产出比清晰（LLM 月成本 vs 推荐质量可量化）
4. 业务方明确同意承担额外成本

**当前状态：** V1 上线约 1 周，观察期进行中。V2 候选方向见 [`10-scope-guardrails.md § 禁止引入`](.claude/rules/10-scope-guardrails.md)。

---

## 参考

- 任务包模板：[`docs/tasks/TEMPLATE.md`](docs/tasks/TEMPLATE.md)
- 越界规则：[`.claude/rules/10-scope-guardrails.md`](.claude/rules/10-scope-guardrails.md)
- 当前状态：[`STATE.md`](STATE.md)
- 技术地图：[`docs/context_map.md`](docs/context_map.md)
