# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MovieTrace** is a production-oriented system that automatically discovers English-language film and TV content updates across streaming platforms (Netflix, Prime Video, Disney+, Apple TV+, HBO/Max, Hulu), deduplicates them against a local content baseline, and generates audit-ready update recommendations for video platform operations teams.

The project is currently in **Phase 1 V1 MVP development** — Phase 0 and Phase 0+ (FlixPatrol validation) are both complete with GO decisions. Focus now is implementing the V1 pipeline: FlixPatrol HTTP client, multi-source scoring, Feishu write, and CLI.

**Key Reference:** Read `AGENTS.md` for comprehensive project rules, workflow stages, and decision gates. AGENTS.md is the authoritative source for project constraints, phase definitions, and execution discipline.

## Core Architecture

MovieTrace operates on a **local SQLite database** as the source-of-truth, with Feishu serving as baseline input and recommendation output.

**Data Flow:**
```
Feishu (baseline content read)
       ↓
SQLite (canonical items, baseline, external IDs, candidates, cache)
       ↓
Pipeline (entity_matching → canonical_promotion → candidate scoring)
       ↓
Feishu (recommendation table write, manual review, batch tracking)
```

**Key Modules:**

| Module | Purpose | Status |
|--------|---------|--------|
| `src/movietrace/feishu/` | Feishu API client for reading baseline content tables | Phase 0 validated |
| `src/movietrace/db/schema.py` | SQLite schema, migrations, connection pooling | Initialized; migrations TBD per Phase 1 |
| `src/movietrace/pipeline/baseline_import.py` | Import Feishu content into SQLite | Tested, used for Phase 0 baseline |
| `src/movietrace/pipeline/entity_matching.py` | Match baseline + candidate items to TMDb/Trakt/IMDb IDs | Core Phase 0 validation module |
| `src/movietrace/pipeline/canonical_promotion.py` | Deduplicate matched items into canonical records | Phase 0 validated |
| `src/movietrace/sources/` | HTTP clients for TMDb, Trakt, OMDb APIs | Core data sources; do not remove without re-evaluation |
| `src/movietrace/sources/flixpatrol.py` | FlixPatrol HTML parser (`parse_top10_page`) | Phase 0+ validated; 48 tests passing; ready for P1-B |

**Database Schema (SQLite):**
- `feishu_import_runs` — tracks Feishu baseline import operations
- `source_records` — raw API responses from external sources
- `baseline_items` — content existing on platform (from Feishu)
- `canonical_items` — deduplicated, matched items (parent: title; children: season → episode)
- `external_ids` — TMDb/Trakt/IMDb/OMDb ID mappings for canonical items
- `candidates` — recommended new/updated content for operational review

See `src/movietrace/db/schema.py` for full schema definition.

## Development Setup

**Requirements:**
- Python 3.12 (specified in AGENTS.md)
- Virtual environment: `.venv/` (create with `python3 -m venv .venv`)

**Activate environment:**
```bash
source .venv/bin/activate
```

**Install dependencies (when requirements.txt exists):**
```bash
pip install -r requirements.txt
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

Current dependencies: `beautifulsoup4` (FlixPatrol parser), `pytest` (tests). See `requirements.txt`.

## Commands

### Tests
```bash
# Run all tests (src layout requires PYTHONPATH)
PYTHONPATH=src python -m pytest tests/ -v

# Run specific test file
PYTHONPATH=src python -m pytest tests/test_flixpatrol_parsing.py -v

# Run single test
PYTHONPATH=src python -m pytest tests/test_entity_matching.py::test_exact_title_match -v
```

**Important:** Always prefix with `PYTHONPATH=src` — the project uses src layout and pytest will fail without it.

### Database
```bash
# Initialize/reset database (recreates schema)
python -c "from movietrace.db.schema import init_database; init_database()"

# Inspect database
sqlite3 data/movietrace.db ".schema"
```

### Configuration
- Copy `config/config.example.yaml` to `config/config.yaml`
- Set Feishu credentials in `.env` (never commit)
- Configure TMDb/Trakt API keys in `.env`

**Environment variables required:**
- `FEISHU_APP_ID` — Feishu app ID for baseline/schema tables
- `FEISHU_APP_SECRET` — Feishu app secret
- `TMDB_API_KEY` — TMDb API key
- `TRAKT_CLIENT_ID` — Trakt API client ID (optional, fallback without)

## When Receiving a Task

**Do not start coding until:**

Before accepting and starting a task, verify the task package contains all required fields (from AGENTS.md):

| 字段 | 说明 | 例子 |
|------|------|------|
| 任务名称 | Clear, specific task title | 实现实体匹配验证模块 |
| 任务类型 | feat / fix / docs / refactor / test | feat |
| 当前阶段 | Which phase (Phase 0/1/2/etc.) | Phase 0 验证 |
| 来源任务 | Link to design doc or task list | docs/next_steps_plan.md 第 3.2 节 |
| 目标 | Single, clear outcome | 验证 >95% 高置信度匹配准确率 |
| 非目标 | What is explicitly NOT included | 不负责 API 实现、不处理低于 medium 置信度的匹配 |
| 允许修改范围 | Which files/directories can change | `src/movietrace/pipeline/entity_matching.py`、`tests/test_entity_matching.py` |
| 禁止修改范围 | What must not be touched | `AGENTS.md`、`schema.py`、其他 pipeline 模块 |
| 验收标准 | How to judge "done" | 所有 entity_matching 测试通过、高置信度准确率 ≥95% |
| 验证命令 | Exact command to run | `python -m pytest tests/test_entity_matching.py -v` |
| 风险点 | Known unknowns or constraints | Feishu 数据质量未知、API 速率限制 |

**If task package is incomplete:** 停止。要求补充缺失字段，不要猜测。

### Pre-Execution Checklist

在开始编码前，确认以下项：

- ✅ 当前阶段明确（不跨越未完成的阶段 — 见下方 Stage Checkpoints）
- ✅ 来源设计文档存在且任务追溯清晰
- ✅ 目标和非目标没有冲突或歧义
- ✅ 修改范围清楚、禁止修改范围被理解
- ✅ 测试要求明确（单元 / 集成 / 手动）
- ✅ 验收标准可判断（不是"代码看起来不错"）
- ✅ 验证命令存在且可运行
- ✅ 已知风险和不确定点已列出

缺少任何一项，**不进入编码**。

### Stage Checkpoints（门控规则）

从 AGENTS.md，这些是硬性门控：

- **进入方案设计前：** 项目定义必须明确（目标、非目标、项目类型、严谨度）
- **进入编码执行前：** 必须有建筑设计、运行环境确认、验收测试标准和任务列表
- **声明完成前：** 验证命令必须运行且输出验证通过
- **交付前：** 风险点必须明确说明

**如果条件不满足，回到上一阶段，不前进。**

## Code Style & Conventions

**From AGENTS.md:**
- 4-space indentation
- Public functions: type hints required
- Naming: `snake_case` for modules, functions, variables
- Test files: behavior-focused names like `test_entity_matching.py`, `test_baseline_import.py`
- Commit messages: Conventional Commit format (`feat:`, `docs:`, `fix:`, etc.)

**Additional conventions:**
- No external package imports in schema init; use stdlib only
- API clients (TMDb, Trakt, OMDb) must include retry logic and error logging
- Database queries use prepared statements; no string concatenation for SQL
- Entity matching thresholds documented in code or config

## Verification Rules and Failure Signals

### 必须验证的规则（来自 AGENTS.md）

1. **如果任务包提供验证命令：** 必须运行并读取完整输出
2. **如果没有验证命令：** 要求补充；纯文档任务可用结构检查或人工阅读
3. **核心功能必须有测试或明确人工验证方式**
4. **Bug 修复必须说明原因并补充回归测试**
5. **测试失败时：** 禁止继续开发新功能（必须先修复或回滚）

### 失败信号：何时必须停止编码

遇到以下任何情况，立即停止编码、向用户报告现象和下一步诊断计划：

- ❌ 开始猜测需求（"也许应该...") 
- ❌ 单次任务跨越多个目标
- ❌ 修改范围无法清晰说明
- ❌ 验证命令不存在或无法运行
- ❌ 代码改动无法解释"为什么需要"
- ❌ 架构、运行环境或验收标准尚未确认
- ❌ 测试失败但试图继续开发新功能
- ❌ 需求理解错误（进入验证阶段后发现）

**不能声明完成的情况：**

- 验证命令未运行
- 测试失败
- 验收标准未达成
- 风险点未说明

## Completion Report Format

任务完成后，使用以下格式汇报（来自 AGENTS.md）：

```
任务理解：
- <本次任务的目标和边界，用一句话总结>

完成内容：
- <列出实际修改的文件和改动内容>
- <示例：修改 src/movietrace/pipeline/entity_matching.py，添加 validate_match_confidence() 函数>

验证结果：
- <列出运行过的验证命令及其输出摘要>
- <示例：python -m pytest tests/test_entity_matching.py -v → 15 passed, 0 failed>

剩余风险：
- <列出尚未解决的问题、依赖或不确定点；如无，写"未发现新的剩余风险">
- <示例：Feishu 数据质量验证仍需人工确认；外部 API 速率限制未测试在高并发下的表现>

后续建议：
- <只列和本任务直接相关的建议，不涉及其他功能模块>
- <示例：建议在 Phase 1 中评估 Netflix Top 10 API 作为补充数据源>
```

## Key Constraints (from AGENTS.md)

**12 条通用操作规则（核心摘取）：**

1. ✅ 优先使用中文沟通
2. ✅ 先确认当前阶段，再决定行动方式
3. ✅ 编码前必须有明确任务包
4. ✅ 只修改任务包允许范围内的文件
5. ⚠️ 不主动引入新依赖，除非任务包明确允许
6. ⚠️ 不擅自改变技术栈、目录结构、数据库设计或架构边界
7. ❌ 不删除已有逻辑来掩盖问题
8. ❌ 不删除或重写无关文件
9. ❌ 不隐藏失败或不确定点
10. ⚠️ 测试失败时，先解释失败，再修复当前任务范围内的问题
11. ❌ 没有运行验证命令，不声明完成
12. ✅ 完成后必须汇报修改内容、验证结果和剩余风险

**Do not:**
- Modify `AGENTS.md` rules or project phase definitions without explicit authorization
- Skip required verification steps or claim completion without running validation commands
- Introduce new dependencies without explicit approval in task package
- Change database schema without proposing migration plan first
- Circumvent Feishu compliance rules (no unauthorized API access, no high-frequency scraping)
- Delete or rewrite existing modules; propose refactoring with reason instead

**Do:**
- Run tests before committing
- Update this CLAUDE.md when adding new modules or changing major architecture
- Log all external API calls with timestamps and response status
- Document non-obvious design decisions (workarounds, performance tradeoffs, API quirks)

## Atomic Task Criteria（原子任务判断标准）

一个任务是否可执行，必须同时满足以下条件（来自 AGENTS.md）：

- ✅ 目标只有一个（不混合多个目标）
- ✅ 能追溯到设计文档或任务列表中的一个任务
- ✅ 修改范围清楚（知道改哪些文件，不改哪些）
- ✅ 验收标准可判断（不是主观的"看起来不错"）
- ✅ 验证方式可执行（能运行命令或人工验证）
- ✅ 完成后能独立提交（不依赖其他任务的输出）

**如果某项不满足，要求拆分任务。** 拆分建议必须包含：
- 子任务目标
- 修改范围
- 任务依赖顺序
- 每个子任务的验收标准和验证方式

## Phase Guidance

**Phase 0:** ✅ Complete — 96.6% entity matching rate, GO decision

**Phase 0+:** ✅ Complete — FlixPatrol validation (SUP-A~F all passed)
- SUP-B parser: `src/movietrace/sources/flixpatrol.py` (48 tests, 100% extraction)
- SUP-C matching: 118/118 = 100% TMDb match rate
- SUP-D compliance: Conditional GO (≤1 req/URL/24h, ≥2s interval, `MovieTraceBot/0.1` UA)

**Phase 1 (Current):** V1 MVP Development
- P1-A: Entity matching regression fix
- P1-B: FlixPatrol HTTP client + DB (reuse existing parser)
- P1-C: Multi-source merge + hot_score
- P1-D: Feishu baseline match tagging
- P1-E: Daily Markdown report
- P1-F: Feishu recommendation table write
- P1-G: CLI command
- P1-H: Integration test + first run

P1-A and P1-B can start in parallel. Task packages not yet written — write task package before coding.

**Phase 2+:** See `docs/next_steps_plan.md`

## Related Documentation

- `AGENTS.md` — Project rules, workflow stages, decision gates (authoritative)
- `docs/requirements.md` — Business goals, scope, data sources, compliance boundaries
- `docs/feasibility.md` — Technical risk assessment, architecture rationale
- `docs/next_steps_plan.md` — Phase roadmap, Phase 0 success criteria
- `docs/operating_cost_estimate.md` — API call budgets, cost modeling
- `reports/` — Phase 0 validation results (entity matching accuracy, candidate quality)

## Common Questions

**Q: Should I add a new library or framework?**
A: No. AGENTS.md rule: "不主动引入新依赖" (don't introduce dependencies proactively). Propose in task with explicit business justification first.

**Q: How do I add a new data source (e.g., Netflix Top 10)?**
A: FlixPatrol is now the platform heat signal source (ADR-0003 Accepted). Additional sources are V2 scope. Propose with cost/quality analysis.

**Q: What if the Feishu API call fails?**
A: Log with timestamp and source ID. Check `AGENTS.md` rule 9: "不隐藏失败或不确定点" (don't hide failures). Report in task output.

**Q: Can I refactor the entity matching module?**
A: Not without written task. It's a Phase 0 validation artifact. Propose scope, risks, and verification in task package first.

## Troubleshooting

**Tests fail:**
1. Ensure `.venv` is activated and dependencies installed
2. Check database is initialized (`python -c "from movietrace.db.schema import init_database; init_database()"`)
3. Run failing test with `-v` flag to see full error
4. Never continue development if tests fail (AGENTS.md rule 10)

**Entity matching reports mismatches:**
1. Check input baseline quality (100-300 sample, >70% valid recommended)
2. Review TMDb/Trakt/IMDb external ID coverage
3. Add test case to `tests/test_entity_matching.py` with expected match
4. Adjust confidence thresholds only after proposing reasoning in task

**Feishu connection timeout:**
1. Verify `.env` has correct `FEISHU_APP_ID` and `FEISHU_APP_SECRET`
2. Check network access to `api.feishu.cn`
3. Review Feishu app permissions in Feishu admin console
4. Log all attempts; never retry silently in loops
