# 工作日报规范

> 触发：每次会话有产出物或阶段推进时（见 [session-checklist.md](session-checklist.md)）。

---

## 位置与命名

**位置：** `journal/`
**文件命名：** `YYYY-MM-DD_<tool>_<model>.md`

| 字段 | 说明 | 示例 |
|------|------|------|
| `YYYY-MM-DD` | 会话日期 | `2026-05-11` |
| `<tool>` | AI 工具名（小写，连字符分隔） | `claude-code`、`codex`、`cursor` |
| `<model>` | 实际使用的模型（小写，连字符分隔） | `sonnet-4.6`、`opus-4.7`、`o3` |

**示例：** `2026-05-11_claude-code_opus-4.7.md`

同一天同一工具同一模型多次会话，追加到同一文件即可（分小节）。

---

## 必填内容

1. **Agent 身份卡** — 工具名、模型、模型 ID、运行环境、起止 commit hash
2. **今日工作主线** — 每条主线包含：触发原因、结论、完成内容、关键发现
3. **关键决策记录** — 每个决策：背景、判断、取舍（重大决策应同时落到 ADR）
4. **当前项目状态快照** — 与 STATE.md 同步的一段摘要
5. **给下一个 AI Agent 的交接** — 可接任务、不要重做的事、容易被忽略的知识
6. **数字总结** — commit 数、修改文件数、测试用例数变化

---

## 参考样例

- [`journal/2026-05-10_claude-code_sonnet-4.6.md`](../../journal/2026-05-10_claude-code_sonnet-4.6.md) — 完整范本
- [`journal/2026-05-10_claude-code_haiku-4.5.md`](../../journal/2026-05-10_claude-code_haiku-4.5.md) — 单主线短日报样例

---

## 注意

- **不要重复 STATE.md 的全部内容**——日报是过程，STATE.md 是当前快照
- **不要重复 ADR**——日报里只写"做了 ADR-NNNN 决策"+ 一句话，详情留在 ADR 文件
- **失败也要写**——隐藏失败违反 AGENTS.md 第 9 条