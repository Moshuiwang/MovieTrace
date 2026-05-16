# 工作日报规范

> 触发：每次会话有产出物或阶段推进时（见 [session-checklist.md](session-checklist.md)）。

---

## 位置与命名

**位置：** `journal/`
**文件命名：** `YYYY-MM-DD_HHMM_<tool>_<model>.md`

| 字段 | 说明 | 示例 |
|------|------|------|
| `YYYY-MM-DD` | 会话开始日期 | `2026-05-12` |
| `HHMM` | 会话开始时分（24 小时制，4 位数字） | `0035`、`1430`、`2200` |
| `<tool>` | AI 工具名（小写，连字符分隔） | `claude-code`、`codex`、`cursor` |
| `<model>` | 实际使用的模型（小写，连字符分隔） | `sonnet-4.6`、`opus-4.7`、`o3` |

**示例：** `2026-05-12_0035_claude-code_opus-4.7.md`

每次会话单独建一份日报（即使同一天同一工具同一模型多次会话，也分别建多份文件，由 `HHMM` 区分）。

**跨日会话：** 文件名沿用会话开始的日期+时分；在日报内部"会话收尾"段标明跨日时间，如"2026-05-12 00:35 +08 继续"。

**既有日报：** 2026-05-12 之前的日报沿用旧格式（`YYYY-MM-DD_<tool>_<model>.md`），不强制重命名，避免破坏已有 git history 和文档交叉引用。

---

## 必填内容

1. **Agent 身份卡** — 工具名、模型、模型 ID、运行环境、起止 commit hash、**会话起止时间（精确到分钟+时区，如 `2026-05-12 00:35 +08 ~ 02:10 +08`）**
2. **今日工作主线** — 每条主线包含：触发原因、结论、完成内容、关键发现；**关键事件标明发生时间（精确到分钟+时区）**
3. **关键决策记录** — 每个决策：背景、判断、取舍（重大决策应同时落到 ADR）
4. **当前项目状态快照** — 与 STATE.md 同步的一段摘要
5. **给下一个 AI Agent 的交接** — 可接任务、不要重做的事、容易被忽略的知识
6. **数字总结** — commit 数、修改文件数、测试用例数变化
7. **成本统计** — 会话总耗时（墙钟时间，如 `~11.5 小时`）+ Token 消耗（输入/输出/总计，如 `输入 120K + 输出 15K = 总计 135K`；如无法获取精确值，标注估算或"未记录"）

**时间精度要求（2026-05-12 起）：** 所有报告类文档（日报、任务完成报告、收尾报告、STATE.md）的时间字段必须精确到分钟，不能只写日期。理由是同一天可能有多次会话或多个 Agent 协作，只写日期无法分辨先后顺序和实际工作时长。

**时区要求（2026-05-12 起）：** 所有文档内的时间戳（文件名除外）必须标注时区偏移 `+08`（中国标准时间 CST）。理由：项目涉及多时区外部 API（TMDb 返回 UTC、FlixPatrol 带时区数据），SQLite `current_timestamp` 为 UTC，不加时区会导致日志/报表时间无法对齐。

**模型与环境自识别要求（2026-05-12 起）：** Agent 身份卡中的"模型"和"运行环境"必须从 system prompt 开头自行获取，**禁止假设、继承或沿用上一会话的值**。获取方式：
- **模型名称**：看 system prompt 中的 `You are powered by the model <model-name>`（如 `deepseek-v4-pro`、`claude-opus-4-7`）
- **运行环境**：看 system prompt 中 `# VSCode Extension Context` 或类似的平台标签（区分 CLI / 桌面 App / VSCode 插件 / JetBrains 插件）
- **工具名**：始终从 system prompt 中 `Claude Code` 标识确认，不猜测

**成本统计要求（2026-05-12 起）：** 日报必须记录会话总耗时和 Token 消耗（详见 [report-format.md](report-format.md) § 成本统计要求）。Token 值从会话结束时终端输出获取；如无法获取，标注估算或"未记录"，禁止编造。

---

## 参考样例

- [`journal/2026-05-10_claude-code_sonnet-4.6.md`](../../journal/2026-05-10_claude-code_sonnet-4.6.md) — 完整范本
- [`journal/2026-05-10_claude-code_haiku-4.5.md`](../../journal/2026-05-10_claude-code_haiku-4.5.md) — 单主线短日报样例

---

## 已废弃的命名模式

以下为历史命名模式，不再使用。旧文件保留不动（避免破坏 git history 和交叉引用），但新日报严格遵循 `YYYY-MM-DD_HHMM_<tool>_<model>.md`：

| 废弃模式 | 示例 | 说明 |
|---------|------|------|
| `YYYY-MM-DD_<tool>_<model>.md` | `2026-05-10_claude-code_sonnet-4.6.md` | 缺 HHMM，无法区分同日多次会话 |
| `YYYY-MM-DD_p1_X.md` | `2026-05-11_p1_b.md` | Phase 简写替代 tool/model，实际是任务完成报告而非日报 |
| `phase0_dayX_summary.md` | `phase0_day1_summary.md` | 无日期前缀的阶段摘要，已被日报规范取代 |

## 任务包归档引用

旧版任务包移入 `docs/tasks/archive/` 后，原链接可能失效。引用任务包文档时注意检查路径是否正确。

---

## 注意

- **不要重复 STATE.md 的全部内容**——日报是过程，STATE.md 是当前快照
- **不要重复 ADR**——日报里只写"做了 ADR-NNNN 决策"+ 一句话，详情留在 ADR 文件
- **失败也要写**——隐藏失败违反 [`.claude/rules/00-core-behaviors.md`](../../.claude/rules/00-core-behaviors.md) 第 9 条