---
name: git-workflow
description: 分支、commit、push、PR、CI/CD、合并后同步的硬规则。任何需要提交或开 PR 的任务必读。
include: ["**/*"]
---

# Git / PR 工作流规则

## 目标

所有变更必须可追溯、可独立 review、可由 CI/CD 验证。禁止把本地状态漂移、错误分支基底、未同步的 `STATE.md` 或未验证的 workflow 改动带进 PR。流程默认节省：不需要进 `main` 的事项不开 PR；可以合并验证和 review 的相关小改不拆碎 PR。

## 开工前

在创建任务分支前必须确认基底：

```bash
git checkout main
git pull --ff-only
git status --short --branch
```

- `git status` 必须显示在 `main...origin/main`，且没有未提交改动。
- 如有未提交改动，先判断是否是用户改动；不能为了开分支而丢弃或覆盖。
- 从非 `main` 分支开出的任务分支必须视为高风险；发现后先 stash 本次改动，从 `main` 重建分支，再恢复改动。

## 分支与提交

- 每个任务包一个分支，命名使用 `feat/`、`fix/`、`refactor/`、`chore/`、`docs/` 前缀 + 任务编号或明确 slug。
- commit message 使用 Conventional Commit：
  - `feat:` 新功能
  - `fix:` 修复
  - `refactor:` 行为不变重构
  - `docs(state):` 仅 `STATE.md`
  - `docs(meta):` harness / 规则 / 流程文档
  - `docs(decision):` ADR
- commit 前必须运行并读取任务包要求的验证命令；纯文档变更至少运行 `git diff --check`。

## 人类确认门禁

Agent 创建 PR 前必须取得人类明确确认，且确认可以来自：

- **事前确认**：任务包、issue、对话中明确写了“完成后开 PR / 提 PR / 走 PR”。
- **当下确认**：Agent 完成本地改动、验证和 PR 前检查后，向用户说明将创建 PR，并收到明确同意。

以下表述不等于开 PR 确认：`收尾`、`完成`、`提交一下`、`按流程走`、`处理掉`。这些只允许 Agent 做本地验证、整理汇报或按需 commit；是否创建 PR 必须另行确认。

如果没有确认，Agent 必须停在“本地已验证、待人类确认是否开 PR”的状态，汇报分支、commit（如有）、验证结果和建议的 PR 标题；不得执行 `gh pr create`。由于本仓库配置 auto-merge，PR 创建本身可能触发合并链路，不能把开 PR 当成普通收尾动作。

## PR 前检查

创建 PR 前必须检查：

```bash
git status --short --branch
git log --oneline --decorate --max-count=5
git diff --check
```

还必须检查 `STATE.md`：

- 当前任务状态不能仍写 `进行中`、`本地完成（待 PR）` 等过期状态。
- 与本次 PR 直接相关的旧任务状态必须同步，例如已合并任务不能继续标 `待 PR`。
- 如果发现表格里有明显过期状态，优先在当前 PR 中修掉；不要留到下一个补丁 PR，除非会扩大无关范围。

PR 描述必须包含：

- Summary：实际改动，不写泛泛而谈。
- Tests：实际运行过的命令和关键结果。
- 对 workflow / deploy 变更，必须说明 PR 阶段验证什么、main 合并后验证什么。

## PR 粒度判断

先判断是否需要改仓库：

- 只读检查、命令输出、CI/CD 状态确认、日志分析、纯口头结论，不需要 PR。
- 只要变更需要进入 `main`，就必须走 PR，禁止直推。
- “需要走 PR”不等于“Agent 立即创建 PR”；仍必须先满足人类确认门禁。

再判断是否值得单独 PR：

- 一句话文档、typo、措辞、格式等低风险小改，通常不单独开 PR；等下一次相关 PR 一起带上。
- 如果已经本地改了但决定等下次，不要提交；保持工作树清楚，或在任务包 / 对话里记录待带入项。
- 会影响后续 Agent 行为、CI/CD、部署、密钥、合规边界、任务状态或范围边界的文档小改，必须尽快落库并走 PR。
- 修正 `STATE.md` 中“待 PR / 进行中 / 已合并”等错误状态时，如果有相关功能 PR 尚未合并，应并入同一 PR；如果已经合并且状态会误导后续 Agent，可以单独 PR。

判断句：不改仓库，不需要 PR；要进 `main`，最终必须 PR；但 Agent 创建 PR 前必须有人类明确确认，低风险一句话文档也不急着单独 PR，优先等相关 PR 一起带上。

## 集体 PR 判断

以下情况应该本地多改一些东西后一起 PR：

- 同一个任务包的实现、测试、`STATE.md`、任务包边界和必要文档同步。
- 一个 bug 的完整闭环：修复代码、回归测试、相关 runbook / 状态说明。
- workflow / CI/CD 改动及其配套 harness 说明、验证说明、状态同步。
- 同一决策导致的多处文档入口更新，例如取消 journal 规则时同步 checklist、spec、总纲和地图。
- 调用方 / 被调用方、schema / 代码 / 测试、workflow input / 触发方传参等必须一起合并才不留下半成品的改动。

以下情况不要集体 PR：

- 目标不同，只是碰巧都很小。
- 一个是紧急修复，另一个是无关整理。
- 会显著扩大验证范围或 review 范围。
- 跨出任务包允许范围或需要不同上线节奏。

判断句：如果只合其中一半会留下错误状态、断链、半成品或误导后续 Agent，就应该集体 PR；如果拆开后每个 PR 都能独立成立、独立验证、独立回滚，就应该拆开。

## Workflow / CI/CD 改动

改 `.github/workflows/**` 时必须额外说明 GitHub Actions 的时序限制：

- PR check 使用 PR 分支里的 workflow。
- `workflow_run` 触发的 auto-merge job 可能 checkout 的是合并前 `main` 上的 workflow。
- 因此修改 auto-merge 自身时，本 PR 的 auto-merge run 不一定能自然验证新逻辑；必要时在合并后用新 workflow 手动触发一次 main CI/CD 验证。

推荐验证：

```bash
python3 - <<'PY'
import pathlib, yaml
for path in [".github/workflows/ci.yml", ".github/workflows/auto-merge.yml"]:
    yaml.safe_load(pathlib.Path(path).read_text())
print("workflow yaml ok")
PY
```

如 workflow 内嵌 Python，必须抽取或编译对应脚本片段，确认语法通过。

## PR 后检查

只有在本会话已按人类确认创建 PR 后，才进入本段。创建 PR 后必须：

```bash
gh pr checks <PR_NUMBER> --watch --interval 5
gh pr view <PR_NUMBER> --json state,mergedAt,mergeCommit,statusCheckRollup,url
```

- PR 阶段 `deploy` / `notify` skipped 是正常的，只要配置限定 main 才 deploy。
- 不能只看到 PR test 通过就结束；auto-merge 项目必须继续确认 PR 是否已合并。
- 合并后必须检查 main CI/CD run，至少确认 `test`、`deploy`、`notify` 结果是否符合预期。

## 合并后同步

PR 合并后必须同步本地：

```bash
git checkout main
git pull --ff-only
git status --short --branch
git log --oneline --decorate --max-count=3
```

- `HEAD` 必须是合并后的 `origin/main`。
- 如果合并后发现 `STATE.md` 仍有过期状态，立刻修正；优先避免创建只为补状态漂移的后续 PR。

## 本次复盘固化

2026-05-23 连续 PR 暴露出以下问题，后续按本规则避免：

- **错误分支基底**：P1.47 最初从本地非 main 分支开出，差点混入无关提交。后续开分支前必须先 `checkout main && pull --ff-only`。
- **状态审计不足**：P1.42/P1.43/P1.44/P1.45/P1.46/P1.38 已随 PR #40 合并，但 `STATE.md` 仍写 `本地完成（待 PR）`，导致补开 PR #45。后续 PR 前必须审计相关任务状态。
- **workflow 时序误判**：P1.53 修改 auto-merge dispatch 参数，但 PR #44 自己的 auto-merge run 仍用旧 main workflow；后续 workflow 改动必须明确“本 PR 能验证什么”和“合并后如何验证新路径”。
- **PR 粒度偏碎**：本可在 #44 中同步的状态漂移被拖到 #45。后续发现直接相关的状态文档漂移，应在同一 PR 内修正。
- **收尾不够清单化**：虽然最终都完成了 commit/push/PR/CI/main pull，但过程依赖临时判断。后续必须按本文档的开工、PR 前、PR 后、合并后四段检查执行。
- **PR 创建过于自动化**：后续即使本地已完成并验证，Agent 也必须先取得人类事前或当下明确确认，才能执行 `gh pr create`。
