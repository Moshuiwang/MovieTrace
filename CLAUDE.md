# CLAUDE.md — MovieTrace 协作宪法

> Solo 开发者 + AI 中文协作。本文件是**总纲**（≤ 60 行）；细则按场景 Read 加载。
> 状态：[`STATE.md`](STATE.md) · 边界：[`SCOPE.md`](SCOPE.md) · 地图：[`docs/context_map.md`](docs/context_map.md)
> Codex / 其他工具入口：[`AGENTS.md`](AGENTS.md)（一行指针 → 本文件）

**Boot Order**：STATE → SCOPE → context_map → 当前任务包。历史层先 `rg` 再读片段，不整篇读。

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

完整 CLI 与排障：[`docs/context_map.md § 3`](docs/context_map.md) · [`docs/workflow/troubleshooting.md`](docs/workflow/troubleshooting.md)

---

## Git 工作流

`main` 已启用分支保护，**禁止直接 push**，所有变更必须走 PR。

```bash
git checkout -b feat/<task-id>-<slug>   # 每个任务包开一个分支
# ... 开发、测试、验证 ...
gh pr create --base main --title "..."  # 完成后开 PR（@moshuiwang 触发自动合并）
git checkout main && git pull           # 合并后同步本地 main
```

- 分支命名：`feat/`、`fix/`、`chore/` 前缀 + 任务包 ID + 简短描述
- PR 标题遵循 Conventional Commit 格式
- auto-merge workflow 已配置：PR 创建后自动 squash merge，无需手动操作

---

## Rule Index（按工作上下文按需 Read）

| 场景 | 必读 |
|---|---|
| 任何编辑前 | [`.claude/rules/00-core-behaviors.md`](.claude/rules/00-core-behaviors.md) · [`.claude/rules/40-gotchas.md`](.claude/rules/40-gotchas.md) |
| 改 `src/**` · `scripts/**` | [`.claude/rules/20-python-and-sql.md`](.claude/rules/20-python-and-sql.md) |
| 改 `src/movietrace/db/**` | [`.claude/rules/21-db-migrations.md`](.claude/rules/21-db-migrations.md) |
| 改 `src/movietrace/sources/**` | [`.claude/rules/22-sources-compliance.md`](.claude/rules/22-sources-compliance.md) |
| 改 `src/movietrace/feishu/**` · `feedback/**` | [`.claude/rules/23-feishu-integration.md`](.claude/rules/23-feishu-integration.md) |
| 改 `tests/**` | [`.claude/rules/30-testing.md`](.claude/rules/30-testing.md) |
| 任务包 / ADR / 收尾 | [`docs/tasks/TEMPLATE.md`](docs/tasks/TEMPLATE.md) · [`docs/decisions/README.md`](docs/decisions/README.md) · [`docs/workflow/session-checklist.md`](docs/workflow/session-checklist.md) |
