# AGENTS.md — MovieTrace 项目宪法

> 本文件是 **Codex** 入口；Claude Code 入口是 [`CLAUDE.md`](CLAUDE.md)。
> 两者**内容等价**，无需交叉读取——修改时两边同步即可。
> 当前项目状态权威：[`STATE.md`](STATE.md)（每次会话先读它）。

---

## 角色与核心判断

- solo 开发者的 AI 协作助手；中文沟通。
- AI 可提问、整理、建议、实现、验证、复盘；不能替开发者做最终产品判断或架构拍板。
- 核心原则：不是"AI 能不能写"，而是"现在是否已经清楚到可以让 AI 写"。

---

## 项目一句话

**MovieTrace** 自动发现英语影视在 6 个流媒体平台（Netflix / Prime Video / Disney+ / Apple TV+ / HBO·Max / Hulu）的热度变化，标记是否在飞书基线，生成可审核推荐清单。生产商业型严谨度。

---

## 项目约束

| 项目项 | 当前约定 |
| --- | --- |
| 项目名称 | MovieTrace |
| 当前阶段 | 见 [`STATE.md`](STATE.md) |
| 项目类型 | 生产商业型；按较高严谨度推进 |
| 技术栈 | Python 3.12 + `.venv/` + `.env` + `config.yaml`；依赖见 `requirements.txt` |
| 框架 | 无；引入任何新依赖前必须有任务包授权 |
| 数据库 | SQLite（`data/movietrace.db`）；schema 见 `src/movietrace/db/schema.py`；变更须提 migration plan |
| 目录结构 | `src/movietrace/` 源码 · `tests/` 测试 · `docs/` 文档 · `reports/` 验证报告 · `journal/` 日报 · `scripts/` 验证脚本 |

---

## 启动顺序（每次会话）

1. [`STATE.md`](STATE.md) — 当前阶段、进行中任务、阻塞项
2. 本文件 12 条规则
3. `journal/` 最新 1-2 篇日报 — 上个 Agent 做了什么
4. 任务相关的 `docs/tasks/<task>.md`（如有）

---

## 12 条操作规则

1. 中文沟通。
2. 先确认当前阶段，再决定行动方式。
3. 编码前必须有明确任务包（模板见 [docs/tasks/TEMPLATE.md](docs/tasks/TEMPLATE.md)）。
4. 只修改任务包允许范围内的文件。
5. 不主动引入新依赖。
6. 不擅自改变技术栈、目录结构、数据库设计或架构边界。
7. 不删除已有逻辑来掩盖问题。
8. 不删除或重写无关文件。
9. 不隐藏失败或不确定点。
10. 测试失败时，先解释失败，再修复当前任务范围内的问题。
11. 没有运行验证命令，不声明完成。
12. 完成后必须汇报修改内容、验证结果和剩余风险（格式见 [docs/workflow/report-format.md](docs/workflow/report-format.md)）。
13. **写 STATE.md / 日报 / commit 时，必须从 system prompt 自行获取当前模型名和运行环境**（`You are powered by the model ...` + `VSCode Extension Context` 等标签），禁止假设、继承或沿用上一会话的值。

---

## 验证规则

- 任务包提供验证命令 → 必须运行并读取输出
- 任务包没有验证命令 → 应要求补充；纯文档任务可用结构检查、链接检查、人工阅读
- 核心功能必须有测试或明确人工验证方式
- Bug 修复必须说明原因，并补充或更新回归验证
- 测试失败时，禁止继续开发新功能
- 验证失败时，不能声明完成
- 失败原因不明时，报告**现象、已排除内容、下一步定位计划**


---

## 失败信号：何时停止编码

出现下列任一情形，停下来澄清，**不要继续敲键盘**：

- AI 开始猜测需求
- 单次任务跨越多个目标
- 修改范围无法说清楚
- 验证命令不存在或无法运行
- 代码改动无法解释为什么需要
- 架构、环境或验收用例还没有确认
- 测试失败但仍想继续开发新功能

---

## 4 个易踩坑

- **`PYTHONPATH=src`** — 运行测试/脚本必须带，src layout。
- **TMDb Bearer Token** — `~/.config/movietrace/secrets.json` → `tmdb.api_read_access_token`（旧路径 `/tmp/movietrace_phase0_secrets.json` 仍 fallback 兼容）。
- **FlixPatrol 合规** — 每 URL 每 24h ≤ 1 次、间隔 ≥ 2 秒、UA = `MovieTraceBot/0.1`、仅内部使用。
- **飞书失败不静默重试** — 记录时间戳、来源 ID、HTTP 状态，向用户报告（规则 9）。

---

## 按需加载（在做这件事前先读对应文件）

| 准备做的事 | 先读 |
|-----------|------|
| 写新任务包 | [docs/tasks/TEMPLATE.md](docs/tasks/TEMPLATE.md) |
| 会话收尾 | [docs/workflow/session-checklist.md](docs/workflow/session-checklist.md) |
| 写日报 | [docs/workflow/journal-spec.md](docs/workflow/journal-spec.md) |
| 完成任务汇报 | [docs/workflow/report-format.md](docs/workflow/report-format.md) |
| 写新 ADR | [docs/decisions/README.md](docs/decisions/README.md) |
| 排查故障 | [docs/workflow/troubleshooting.md](docs/workflow/troubleshooting.md) |
| 新项目/阶段切换/方法论参考 | [docs/workflow/phases.md](docs/workflow/phases.md) |
| 判断任务是否在 V1 范围内 / 用户请求可能超界 | [SCOPE.md](SCOPE.md) |

---

## 常用命令

```bash
# 激活环境
source .venv/bin/activate
pip install -r requirements.txt

# 全部测试
PYTHONPATH=src python -m pytest tests/ -v

# 日发现流水线（dry-run）
PYTHONPATH=src python -m movietrace.cli daily-discover --dry-run

# 基线查询
PYTHONPATH=src python -m movietrace.cli inspect-baseline

# 初始化/重置数据库
PYTHONPATH=src python -c "from movietrace.db.schema import initialize_database; initialize_database('data/movietrace.db')"

# git 状态
git status --short --branch
```

---

## 仓库与代码风格

| 主题 | 约定 |
| --- | --- |
| 项目结构 | `docs/` 文档为主 · `src/movietrace/` 源码 · `tests/` 测试 · `scripts/` 验证脚本 |
| 现有文档 | `STATE.md`、`SCOPE.md`、`docs/requirements.md`、`docs/decisions/`、`docs/tasks/`、`docs/workflow/`、`journal/` |
| Markdown 风格 | 标题清晰、段落短、列表直接；文件名小写下划线（如 `operating_cost_estimate.md`） |
| Python 风格 | 4 空格缩进；公共函数类型标注；模块/函数/变量 `snake_case` |
| 测试命名 | 按行为命名，如 `test_scoring.py`、`test_deduplication.py` |
| SQL | 必须用 prepared statements，禁止字符串拼接 |
| 外部 API | 必须记录时间戳和响应状态 |
| 提交信息 | Conventional Commit，如 `docs: update feasibility plan`、`feat: add scoring configuration` |
| PR | 摘要 · 关键改动 · 验证结果 · 配置或密钥处理说明 |
| 安全 | 不提交 API Key、Token、飞书密钥、`.env`；只提交脱敏示例 |

---

## 外部参考路径（跨项目模板）

- 提示词模板：`~/ai-dev-workflow/docs/ai/prompt-templates.md`
- 决策清单：`~/ai-dev-workflow/docs/human/decision-checklists.md`
- 任务包模板：`~/ai-dev-workflow/docs/templates/task-brief.md`
- 项目定义模板：`~/ai-dev-workflow/docs/templates/project-brief.md`
- 方案设计模板：`~/ai-dev-workflow/docs/templates/design-brief.md`
- 评审复盘模板：`~/ai-dev-workflow/docs/templates/review-retro.md`