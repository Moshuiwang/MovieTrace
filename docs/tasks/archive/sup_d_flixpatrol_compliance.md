# 任务包：SUP-D FlixPatrol 服务条款合规评估

**任务包版本：** v1  
**创建日期：** 2026-05-10  
**完成日期：** 2026-05-10

---

## 任务名称

SUP-D：FlixPatrol 服务条款和合规边界评估

## 任务类型

`verify` — 评估任务（无代码实现，纯文档输出）

## 当前阶段

Phase 0+（FlixPatrol 接入验证）

## 来源任务

- `docs/phase0_supplement.md` § 任务 SUP-D
- SUP-A 已完成：`data/flixpatrol_robots.txt` 就绪

## 目标

明确 FlixPatrol 数据爬取的合规边界，给出可接入 / 限制接入 / 不可接入结论。

## 非目标

- ❌ 不提供法律意见（仅作技术合规分析）
- ❌ 不评估其他数据源
- ❌ 不实现任何代码

## 评估步骤

1. ✅ 读取已保存的 `data/flixpatrol_robots.txt`，分析爬虫许可规则
2. ✅ 访问 `https://flixpatrol.com/about/terms-and-conditions/`，读取条款
3. ✅ 访问 `https://flixpatrol.com/about/privacy-policy/`，读取隐私政策
4. ✅ 访问 `https://flixpatrol.com/about/api/`，了解商业 API 存在情况
5. ✅ 综合评估，给出结论

## 实际发现

- **robots.txt**：`User-agent: *; Allow: /`，MovieTraceBot 明确允许
- **服务条款**：页面内容为空，无实质性约束条款
- **隐私政策**：页面内容为空
- **商业 API**：存在（$9.99/月起），意味着数据有商业价值

## 验收标准

1. ✅ 明确合规结论（不留模糊地带）
2. ✅ 如有限制，明确边界（频率、范围、用途）
3. ✅ `reports/flixpatrol_compliance_report.md` 包含完整评估

## 最终结论

**⚠️ 条件接入（Conditional GO）**

V1 阶段在以下条件下可接入：
- 每 URL 每 24 小时最多访问 1 次，间隔 ≥ 2 秒
- 使用 `MovieTraceBot/0.1` User-Agent
- 仅访问 Top-10 榜单页面
- 数据仅用于内部推荐，不公开发布原始数据
- 每季度监控 robots.txt 和条款变化
