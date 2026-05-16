# 运营反馈周报说明

> **本文件已于 P1.23（2026-05-16）改版。**
> 周报不再由运营手填，而是由 `export-feedback-report` 命令**自动生成**。
> 运营只需在飞书子表填写决策字段（详见 [feishu_feedback_spec.md](feishu_feedback_spec.md)）。

---

## 周报生成方式

```bash
# 步骤 1：拉取飞书反馈数据（需飞书凭据）
PYTHONPATH=src python3 -m movietrace.cli pull-feishu-feedback --days 7

# 步骤 2：生成周报 Markdown
PYTHONPATH=src python3 -m movietrace.cli export-feedback-report

# 或一键运行（建议每周日）
bash scripts/weekly_feedback.sh
```

输出位置：`reports/feedback/feedback_log_YYYY-Www.md`（ISO 周编号，如 `feedback_log_2026-W20.md`）

---

## 自动生成的周报结构

| 章节 | 内容 |
|------|------|
| **A. 基本信息** | 周编号、统计范围、生成时间 |
| **B. 热点发现表统计** | 总候选数、运营状态分布、回填率、采纳率、供应商状态 |
| **C. A 库缺口表统计** | 总缺口数、状态分布、推进率、Top 10 高热度待补 series |
| **D. 关键案例** | 被标「不加入」的 P0/P1（误报信号）；低分被采纳的案例（低估信号） |
| **E. V2 触发条件检查** | 四项触发条件的当前状态 |

---

## 数据输入：运营在飞书填写的字段

运营人员**不需要**手填本文件，只需在飞书两张子表填写以下字段：

**热点发现表**：`运营状态`（待看 / 确认加入 / 不加入）、`运营备注`、`供应商状态`

**A 库缺口表**：`运营状态`（待补 / 部分补充 / 已补 / 跳过）、`备注`

字段填写规范见 [feishu_feedback_spec.md](feishu_feedback_spec.md)。

---

## 历史周报

历史周报按 ISO 周编号存档在 `reports/feedback/` 目录，由 git 版本控制保留。
最新一份周报同时复制到 `reports/feedback/feedback_latest.md`。

---

## 注意事项

- `weekly_feedback.sh` **不接 cron**，每周人工触发一次。
- 同周内多次运行会覆盖同名文件（正常行为；跨周自动保留历史）。
- 当前飞书数据为只读拉取，不影响 B 库或发现/推荐逻辑。
