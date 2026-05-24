# CLAUDE.md — MovieTrace 协作宪法

> Solo 开发者 + AI 中文协作。本文件是**总纲**（≤ 60 行）；细则按场景 Read 加载。
> 状态：[`STATE.md`](STATE.md) · 边界：[`SCOPE.md`](SCOPE.md) · Codex / 其他工具入口：[`AGENTS.md`](AGENTS.md)（一行指针 → 本文件）

**Boot Order**：STATE → SCOPE → 当前任务包。代码结构 `ls src/movietrace/` 探索；Rule Index 所有规则均为 lazy load，按场景按需 Read，不自动载入。历史层先 `rg` 再读片段，不整篇读。

---

## 行为模式（硬铁律，对每次编辑生效）

1. **Critique-First** — 先批判方案、列假设和未知、回答"为什么这里改、改这一处够不够"，再动键盘。无任务包不编码（[`docs/tasks/TEMPLATE.md`](docs/tasks/TEMPLATE.md)）。
2. **No Speculative Code** — 不写未请求的抽象、不顺手重构邻近代码、不为想象中的未来需求设计。三行重复优于过早抽象。
3. **不掩盖失败** — 测试/验证失败：先报**现象 → 已排除 → 下一步定位**；禁止删逻辑掩盖问题、删测试以"通过"、静默重试。
4. **不擅自越界** — 只改任务包允许范围内的文件；不引新依赖；不改技术栈 / 目录 / 数据库 / 架构；模型名与运行环境**每次从 system prompt 自取**，禁止沿用。
5. **不声明完成** — 未运行验证命令并读取输出，不写"完成"；汇报按 [`docs/workflow/report-format.md`](docs/workflow/report-format.md)。

---

## Build / Test / Lint

```bash
source .venv/bin/activate                                          # 环境
PYTHONPATH=src python -m pytest tests/ -v                          # 全量测试
PYTHONPATH=src python -m movietrace.cli daily-discover --dry-run   # 日发现 dry-run
git status --short --branch                                        # 工作树状态
```

CLI 列表：`PYTHONPATH=src python -m movietrace.cli --help` · 排障：[`docs/workflow/troubleshooting.md`](docs/workflow/troubleshooting.md)

---

## Git 工作流

`main` 分支保护，禁止直接 push；PR 必须经人类事前/当下明确确认才能创建（auto-merge 已配置）。分支命名、commit 前缀、PR 前后检查、合并后同步 → [`.claude/rules/50-git-workflow.md`](.claude/rules/50-git-workflow.md)。

---

## Rule Index（按工作上下文按需 Read）

| 场景 | 必读 |
|---|---|
| 任何编辑前 | [`.claude/rules/00-core-behaviors.md`](.claude/rules/00-core-behaviors.md) · [`.claude/rules/40-gotchas.md`](.claude/rules/40-gotchas.md) |
| 改 `src/**` · `scripts/**` | [`.claude/rules/20-python-and-sql.md`](.claude/rules/20-python-and-sql.md) |
| 改 `src/movietrace/db/**`（schema / migration）| [`.claude/rules/21-db-migrations.md`](.claude/rules/21-db-migrations.md) |
| 写 / 改 SQL 查询；查表结构 / 字段 / 唯一索引 / 数据流 | [`.claude/rules/24-db-schema-map.md`](.claude/rules/24-db-schema-map.md) |
| 改 `src/movietrace/sources/**` | [`.claude/rules/22-sources-compliance.md`](.claude/rules/22-sources-compliance.md) |
| 改 `src/movietrace/feishu/**` · `feedback/**` | [`.claude/rules/23-feishu-integration.md`](.claude/rules/23-feishu-integration.md) |
| 改 `tests/**` | [`.claude/rules/30-testing.md`](.claude/rules/30-testing.md) |
| commit / push / PR / CI-CD | [`.claude/rules/50-git-workflow.md`](.claude/rules/50-git-workflow.md) |
| 任务包 / ADR / 收尾 | [`docs/tasks/TEMPLATE.md`](docs/tasks/TEMPLATE.md) · [`docs/decisions/README.md`](docs/decisions/README.md) · [`docs/workflow/session-checklist.md`](docs/workflow/session-checklist.md) |

**可选 subagent：** `explorer`（haiku，只读搜索 / 代码定位）· `implementer`（sonnet，任务包范围内实施）。详见 [`.claude/agents/`](.claude/agents/)。
