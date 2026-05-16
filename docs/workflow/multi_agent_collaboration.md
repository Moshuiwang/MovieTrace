# 多 AI Agent 协作框架建议

**作者：** Claude Code (Haiku 4.5)  
**审查：** Claude Code (Opus 4.7) — 见下方 § 0  
**日期：** 2026-05-10  
**状态：** ✅ 已审查，采纳精简版（详见 § 0）  
**适用项目：** MovieTrace（及其他 solo 开发者 + 多 AI Agent 协作的项目）

> **2026-05-17 注：** 本文撰写时 `AGENTS.md` 是项目宪法、本文档作为"实施细则"。治理体系重构（commit `f86f0f9`）后，`AGENTS.md` 退化为指针，规则中心迁移至 [`CLAUDE.md`](../../CLAUDE.md) 总纲 + [`.claude/rules/`](../../.claude/rules/) 9 个专项。本文档**作为历史 design 参考保留**，内部 "AGENTS.md 第 N 条" 引用语义已迁移至 [`.claude/rules/00-core-behaviors.md`](../../.claude/rules/00-core-behaviors.md) 同编号。

---

## 0. Opus Review（2026-05-10）

> 本章节由 Opus 4.7 在 Haiku 4.5 草案基础上添加。  
> 本文以下章节是 Haiku 的**完整候选清单**（保留作为"未来参考"）；  
> 本章节定义实际**采纳的精简实施版**。

### 0.1 实施范围（Accepted ✅）

立即建立的最小核心集（4 件）：

| 文件 / 目录 | 用途 | 状态 |
|------------|------|------|
| `STATE.md` | 项目状态实时快照（每次 commit 前更新） | ✅ 已建 |
| `SCOPE.md` | 当前阶段范围 + 明确不做（防止越界） | ✅ 已建 |
| `docs/decisions/` | ADR 决策日志（避免决策回撤） | ✅ 已建 |
| `journal/` | 日报（已有 2026-05-10 一份） | ✅ 已建 |

### 0.2 暂缓引入（Deferred ⏳）

按"实际遇到问题再加"原则：

| 文件 / 目录 | 引入触发条件 |
|------------|-------------|
| `agents/<agent>.md` 能力卡 | Agent 数量超过 3 时 |
| `docs/style/` 风格指南 | 出现明确的代码/文档风格冲突时 |
| `BLOCKERS.md` | 出现持续 >1 天的阻塞项时 |

### 0.3 不建立（Rejected ❌）

| 文件 / 目录 | 拒绝原因 |
|------------|---------|
| `docs/handoffs/` | 与 journal 信息严重重叠，重复维护成本 > 价值 |

### 0.4 对 Haiku 草案的关键修订

1. **新增 ADR 概念**（Haiku 草案遗漏）  
   决策日志比 journal 更重要——journal 记"做了什么"，ADR 记"为什么不选 X"。这是避免**决策回撤**（下个 Agent 把已否决方案重新拉回讨论）的关键。

2. **新增 SCOPE 概念**（Haiku 草案遗漏）  
   把 V1/V2 边界从 product_roadmap.md 中提取成单独文件，让 Agent 一眼看到"做什么 / 不做什么"。

3. **明确文档触发条件**（Haiku 草案不清晰）

   | 文档 | 何时更新 |
   |------|---------|
   | `STATE.md` | 每次 git commit 前 |
   | `journal/` | 主要工作完成时（不是每次会话） |
   | `docs/decisions/` | 重大决策时（产品/技术/范围） |
   | 不写 | 会话内的临时探索 |

4. **强化"用户的角色"**  
   用户不是"裁判 + 方向盘"（Haiku 措辞），而是 **路由器（router）**：决定哪个 Agent 做什么、何时切换、何时仲裁。  
   **Agent 之间不直接通信**，所有跨 Agent 状态通过文档 + 用户。

### 0.5 关于 Haiku 草案的处置

下文（§ 1 起）保留 Haiku 草案完整内容，**作为未来扩容时的参考清单**。  
不要按 Haiku 草案"4 阶段实施计划"逐项推进——以本 § 0 章节为准。

---

## 1. 问题陈述

### 1.1 现状

MovieTrace 项目由 solo 开发者 + 多个 AI Agent 协作完成。当前协作机制：

| 机制 | 当前实现 |
|------|---------|
| 共享约束 | `AGENTS.md` |
| Agent 专属指南 | `CLAUDE.md`（仅 Claude）|
| 产品需求 | `docs/requirements.md` |
| 路线图 | `docs/reference/next_steps_plan.md`、`docs/product_roadmap.md` |
| 任务流转 | `docs/tasks/`（刚开始建立）|
| 验证报告 | `reports/` |
| 日报 | `journal/`（今日新建）|

### 1.2 问题

随着 Agent 数量增多和会话延长，会出现：

1. **遗忘**：上一个 Agent 做了什么决定？为什么？
2. **冲突**：不同 Agent 对"什么是好的代码风格"判断不一致
3. **状态不明**：当前阶段是什么？谁在做什么？哪里阻塞？
4. **重复劳动**：A Agent 探索过的死胡同，B Agent 重新走一遍
5. **风格漂移**：每次 Agent 切换，文档/代码风格出现微妙差异
6. **信任成本**：用户每次都要重新介绍背景

### 1.3 目标

构建一个**轻量级、文档驱动、Git 追踪**的多 Agent 协作框架，使：

- 任何新 Agent 通过读 5-10 个文件能在 5 分钟内进入工作状态
- 每个 Agent 的工作有明确"输入/输出/边界"
- 决策有完整追溯链
- 风格和品味有显式记录，不靠"心领神会"

---

## 2. 核心设计原则

| 原则 | 含义 |
|------|------|
| **文档即事实** | 所有协作信息存在文件中，不依赖会话内存 |
| **Git 即时序** | 每次提交记录"谁在何时做了什么决定" |
| **显式优于隐式** | 品味、约束、决策依据都要写出来 |
| **状态可推导** | 当前项目状态从文件可读，不需要 Agent 自己揣摩 |
| **轻量优先** | 不引入新工具、新流程；只用 markdown + git |
| **角色清晰** | 每个 Agent 有明确"擅长的"和"不应做的" |

---

## 3. 推荐目录结构

```
MovieTrace/
├── AGENTS.md                       # 全员宪法（用户写）
├── CLAUDE.md                       # Claude Code 专用
├── GEMINI.md                       # Gemini 专用（按需）
├── CODEX.md                        # CODEX 专用（按需）
├── STATE.md                        # 当前项目状态快照（实时）
├── BLOCKERS.md                     # 当前阻塞项（实时）
│
├── agents/                         # 🆕 Agent 注册和能力描述
│   ├── README.md                   # 索引
│   ├── claude-code_haiku-4.5.md    # Claude Haiku 的能力卡
│   ├── claude-code_opus-4.7.md     # Claude Opus 的能力卡（不同模型）
│   ├── codex_gpt-5.md              # CODEX 能力卡
│   └── gemini_2.5.md               # Gemini 能力卡
│
├── docs/                           # 产品和设计决策
│   ├── requirements.md             # 需求
│   ├── product_roadmap.md          # 路线图
│   ├── reference/                  # 参考文档
│   │   ├── feasibility.md
│   │   ├── next_steps_plan.md
│   │   └── ...
│   ├── workflow/                   # 工作流
│   │   ├── multi_agent_collaboration.md # 本文档
│   │   └── ...
│   ├── tasks/                      # 任务包（输入）
│   │   ├── TEMPLATE.md
│   │   ├── archive/                # 旧版任务包
│   │   └── ...
│   │
│   ├── handoffs/                   # 任务交接文档（Agent 之间）
│   │   └── 2026-05-11_sup_a_to_sup_b.md
│   │
│   └── style/                      # 🆕 显式品味和风格
│       ├── code_style.md
│       ├── doc_style.md
│       └── decision_principles.md
│
├── journal/                        # 🆕 日报和会话纪要
│   ├── README.md                   # 索引
│   ├── 2026-05-10_claude-code_haiku-4.5.md
│   ├── 2026-05-11_codex_gpt-5.md   # 示例
│   └── sessions/                   # 重要决策的完整对话纪要
│       └── 2026-05-10_v2_alignment.md
│
├── reports/                        # 验证和度量报告（产出）
│   ├── phase0_completion_report.md
│   └── ...
│
├── src/movietrace/                 # 产品代码
├── tests/                          # 测试
├── scripts/                        # 临时脚本（验证/迁移）
├── data/                           # 本地数据
└── config/                         # 配置
```

### 3.1 重点新增目录说明

#### `agents/` — Agent 能力注册表

每个 Agent（按模型版本）一个文件，描述：

```markdown
# Agent: Claude Code (Haiku 4.5)

## 身份
- 模型: claude-haiku-4-5-20251001
- 提供方: Anthropic
- 接入方式: Claude Code CLI

## 擅长（recommended）
- 文档撰写（中英文）
- 代码实现（小到中型变更）
- 任务包执行
- SQL 操作
- Bash / shell 脚本
- 代码审查（已知规范的）

## 适合做（capable）
- 单文件重构
- Bug 调试（边界明确）
- 测试编写

## 不擅长（avoid）
- 大型架构决策（应让 Opus 或更高级 Agent 做）
- 跨文件深度重构（容易丢上下文）
- 模糊的"看着办"任务（需要明确任务包）

## 注意事项
- 知识截止 2025-02，需要 Web Fetch 验证最新 API
- 容易"过度方案化"，倾向于给多选项让用户选
- 严格遵守 AGENTS.md 不擅自做产品判断
```

#### `journal/` — 日报

文件名规范：`YYYY-MM-DD_<agent-name>_<model-version>.md`

例：
- `2026-05-10_claude-code_haiku-4.5.md`
- `2026-05-11_codex_gpt-5.md`
- `2026-05-12_gemini_2.5-pro.md`

每份日报包含：
1. **身份卡**（Agent、模型、会话信息）
2. **今日工作主线**（按主题，不按时间流水）
3. **关键决策记录**（重大决策 + 理由）
4. **当前项目状态快照**（YAML 格式）
5. **给下一个 Agent 的交接**（立即可做、不要重做、待决策）
6. **观察和反思**（自我评估）
7. **数字总结**

#### `STATE.md` — 项目状态实时快照

**目的：** 任何 Agent 进来读一眼就知道当前状态。

```markdown
# MovieTrace 项目状态

**最后更新：** 2026-05-10 by Claude Code (Haiku 4.5)
**Git Commit：** b584e94

## 当前阶段
✅ Phase 0 完成
🔄 Phase 0+ 准备中（FlixPatrol 验证）
⏳ Phase 1 待启动

## 数据库状态
- baseline_items: 855
- canonical_items: 826 (96.6%)
- baseline_quality_issues: 29

## 进行中任务
- SUP-A FlixPatrol 可访问性测试（任务包就绪，待执行）

## 阻塞项
- 无

## 待用户决策
- SUP-A 启动时间
- 多 Agent 协作框架是否采纳

## 最近 3 次决策
1. 2026-05-10 Phase 0 GO 决策（go_no_go_decision.md）
2. 2026-05-10 V2 产品方向调整（commit b584e94）
3. 2026-05-10 V1/V2 划分原则
```

**更新策略：** 每个 Agent 完成主要工作后必须更新 STATE.md。

#### `BLOCKERS.md` — 阻塞项追踪

**目的：** 把"卡住的事"显式化。

```markdown
# 当前阻塞项

## 🔴 高优先级（影响下阶段进入）
- 无

## 🟡 中优先级（影响某项工作）
- FlixPatrol 服务条款不明确（待 SUP-D 评估）

## 🟢 低优先级（备注）
- pytest 未安装（需补充 requirements.txt）

## 已解决（最近 7 天）
- ~~Phase 0 收尾未完成~~ (2026-05-10 by Claude)
```

#### `docs/handoffs/` — 任务交接

**目的：** Agent A 完成后，主动写一份给 Agent B（或下一次 Claude 会话）。

```markdown
# 任务交接：SUP-A → SUP-B

**From：** Claude Code (Haiku 4.5)，2026-05-11
**To：** 任意 Agent，建议 Claude Code 或 CODEX

## 我做完了什么
- SUP-A 验证脚本运行成功
- 7 个 URL 中 5 个 200 / 2 个 404
- robots.txt 允许访问 /top10/
- HTML 样本已保存到 tests/fixtures/flixpatrol/

## 给你的输入
- HTML 样本路径：tests/fixtures/flixpatrol/{netflix_global,netflix_us,...}.html
- 实际确认的 URL 模式（404 的 2 个待修正）
- 已知问题：apple-tv 路径有重定向

## 你接下来做什么
- 任务包：docs/tasks/sup_b_html_parsing.md（待我创建？还是用户分配？）
- 关键挑战：HTML 包含 JavaScript 渲染部分？需要验证

## 不要做的事
- 不要重新跑 SUP-A 的网络请求（HTML 已保存）
- 不要修改 sup_a_flixpatrol_check.py
```

#### `docs/style/` — 显式品味和风格

**目的：** 把"心照不宣"变成"白纸黑字"。

##### `style/code_style.md` 示例

```markdown
# 代码风格指南

## Python 风格
- 缩进：4 空格（PEP 8）
- 命名：snake_case（变量、函数、模块）；CamelCase（类）
- 类型注解：公共函数必须；内部辅助可省
- f-string > %  > .format()
- pathlib.Path > os.path
- dataclass > 普通类（数据载体）

## 错误处理
- 显式抛出 > 静默吞下
- 错误必须有上下文（避免裸 raise）
- API 失败必须记录请求 URL + 状态码

## 注释
- WHAT 不写（代码自解释）
- WHY 写（非显然的设计选择）
- 中英文皆可，模块内一致

## 反模式（不要做）
- ❌ 大写常量类（用模块级常量）
- ❌ try-except-pass（除非有明确理由）
- ❌ 单字母变量（i/j/k 例外）
- ❌ 引入新依赖（必须任务包授权）
```

##### `style/doc_style.md` 示例

```markdown
# 文档风格指南

## 语言
- 默认中文（用户偏好）
- 代码注释、API 名词可英文

## 结构
- 标题清晰（h2/h3 主导）
- 表格 > 列表 > 段落
- 代码块标注语言

## 内容
- 决策必须有"为什么"
- 风险必须显式列出
- 不写"显而易见的废话"
```

##### `style/decision_principles.md` 示例

```markdown
# 决策原则

## 通用
1. **YAGNI**：不为"未来需求"提前优化
2. **可解释 > 黑盒**：算法决策必须能说出 why
3. **安全降级**：单点失败不能拖垮整体
4. **测试可执行**：验收标准必须能跑命令验证

## 项目专属
1. **不擅自引入新依赖**（AGENTS.md 第 5 条）
2. **不修改未授权文件**（AGENTS.md 第 4 条）
3. **不隐藏失败**（AGENTS.md 第 9 条）
```

---

## 4. 任务流转模型

### 4.1 任务生命周期

```
[draft]               # 任务想法
   ↓
[ready]               # 任务包完整，可被任何 Agent 拾取
   ↓
[in_progress]         # 某 Agent 正在执行
   ↓
[blocked]             # 遇到阻塞，写到 BLOCKERS.md
   ↓
[review]              # 完成，等待人工/Agent 验收
   ↓
[completed]           # 通过验收
```

### 4.2 任务包索引：`docs/tasks/README.md`

```markdown
# 任务包索引（看板）

## 🟢 Ready（可拾取）
- SUP-A FlixPatrol 可访问性 (`docs/tasks/archive/sup_a_flixpatrol_accessibility.md`)
- SUP-D FlixPatrol 合规评估（待创建）

## 🔵 In Progress
- 无

## 🟡 Blocked
- 无

## ✅ Completed（最近 5 个）
- Phase 0 收尾（已完成）
- Entity Matching 4 case 修复（已完成）

## 📋 任务依赖图
- SUP-A → SUP-B、SUP-C
- SUP-D 独立
- SUP-A + SUP-B + SUP-D → SUP-F → Phase 1 决策
```

### 4.3 任务包前置检查清单

任何 Agent 拾取任务前必须确认：

```
[ ] 任务包字段完整（17 项必填，见 AGENTS.md）
[ ] 输入文件/数据可访问
[ ] 验证命令可运行
[ ] 没有未解决的依赖任务
[ ] 我（当前 Agent）的能力符合任务要求
```

如不满足，**不进入执行**，而是：
- 在任务包末尾添加注释说明
- 或写一份新的子任务包（拆分）
- 或在 BLOCKERS.md 记录

---

## 5. Agent 角色分工建议

### 5.1 按"判断深度"分类

| 角色 | 适合的 Agent | 适合的任务 |
|------|-------------|-----------|
| **架构师** | Claude Opus 4.7 / GPT-5 | 大型架构决策、跨模块重构、产品方向 |
| **执行者** | Claude Haiku 4.5 / GPT-4o-mini | 任务包执行、文档撰写、SQL/脚本 |
| **审查者** | Claude Opus 或专门 review agent | 代码审查、文档审查、决策审查 |
| **验证者** | 任意 Agent | 测试编写、验证报告、质量检查 |

### 5.2 按"能力维度"分类

| 维度 | 强项 Agent | 备注 |
|------|-----------|------|
| 长上下文 | Claude（200K+） | 适合读大量文档 |
| 代码生成 | Claude Sonnet/Opus、CODEX | 大型实现 |
| 推理深度 | Claude Opus 4.7、o1 | 架构和决策 |
| 速度 | Claude Haiku、GPT-4o-mini | 简单执行任务 |
| 成本 | Haiku、Mini | 高频小任务 |
| Web Fetch | Claude with WebFetch | 验证最新 API |

### 5.3 任务分配建议

```
产品方向决策     → 架构师（Opus）
任务包撰写       → 架构师 / 高级执行者
任务包执行       → 执行者（Haiku/Mini）
代码审查         → 审查者（Opus 或专门 review）
文档撰写         → 任意（按文档复杂度）
日常问答         → 执行者
紧急 debug      → 经验丰富的 Agent（架构师优先）
```

---

## 6. 协作场景示例

### 场景 1：用户启动新 Agent

**用户：** "Claude，今天继续做 MovieTrace 的工作"

**Agent 应该做的事（按顺序）：**
1. 读 `STATE.md` — 知道项目当前状态
2. 读 `AGENTS.md` — 了解约束（如果是新会话）
3. 读 `CLAUDE.md` 或对应 Agent 文档 — 了解执行规范
4. 读 `BLOCKERS.md` — 知道有什么卡着
5. 读 `journal/` 最新 1-2 篇 — 了解上次做到哪
6. 读 `docs/tasks/README.md` — 看看可拾取的任务
7. 报告："我已了解，当前状态是 X，建议下一步做 Y"

### 场景 2：任务交接

**Agent A（完成 SUP-A）：**
1. 更新任务包状态为 `[completed]`
2. 写 `journal/YYYY-MM-DD_agent-name.md`
3. 写 `docs/handoffs/SUP-A_to_SUP-B.md`
4. 更新 `STATE.md`
5. Git commit

**Agent B（拾取 SUP-B）：**
1. 读 `docs/handoffs/SUP-A_to_SUP-B.md`
2. 读 `docs/tasks/sup_b_*.md`
3. 读 `journal/2026-05-XX_agent-A.md`（了解 A 的发现）
4. 开始执行

### 场景 3：紧急 debug

**用户：** "Claude，prod 出问题了！数据库连不上！"

**Agent：**
1. 读 `STATE.md` — 当前部署状态
2. 读 `BLOCKERS.md` — 是否已知问题
3. 检查最近 commit
4. 不擅自动 prod，先报告诊断

### 场景 4：风格冲突

**Agent A 写的代码用 4 空格，Agent B 用 2 空格。**

**预防：**
- `style/code_style.md` 明确规定 4 空格
- 任何 Agent 接任务前必读 style 文档
- pre-commit hook（未来）自动检查

---

## 7. 实施建议（分阶段）

### 阶段 1：立刻可做（10 分钟）

- ✅ 创建 `journal/` 目录（今日已建）
- ✅ 创建 `docs/tasks/` 目录（今日已建）
- ⏳ 创建 `STATE.md` 初始版
- ⏳ 创建 `BLOCKERS.md` 初始版

### 阶段 2：本周内（1 小时）

- 创建 `agents/` 目录 + 当前 Claude Haiku 的能力卡
- 创建 `docs/style/code_style.md` 和 `decision_principles.md`
- 在 `docs/tasks/` 增加 `README.md`（看板索引）

### 阶段 3：随用随建（持续）

- 每个 Agent 接入：写一份 `agents/<agent>.md`
- 每个会话结束：写 `journal/YYYY-MM-DD_<agent>.md`
- 每个任务交接：写 `docs/handoffs/`
- 每个重大决策：更新 `STATE.md`

### 阶段 4：未来优化（可选）

- 引入工具自动化：
  - pre-commit hook 检查代码风格
  - GitHub Actions 自动更新 `STATE.md`
  - 每周自动汇总 journal 到 weekly summary
- 引入半结构化（YAML）格式
  - 让 Agent 解析 `STATE.md` 更容易
  - 但可能损失人类可读性

---

## 8. 风险和限制

### 8.1 已识别风险

1. **文档负担**：每次都写日报、handoff、更新 STATE，可能拖慢实际工作
   - **缓解：** 简短即可。日报 1 页足够。STATE 是 yaml 格式不超过 50 行。

2. **风格漂移**：`style/` 文档可能过时
   - **缓解：** 季度复查；新 Agent 接入时验证风格文档与现状一致

3. **Agent 不读文档**：明明写好了还是被忽略
   - **缓解：** 在 AGENTS.md 中加入"启动检查清单"，每个 Agent 必读

4. **Git 提交太多噪音**：每个状态更新都 commit
   - **缓解：** 状态更新可以与代码 commit 一起；或用 amend；或专门的 chore commit

### 8.2 边界

- 本框架适合 **2-5 个 Agent + 1 个人** 的项目
- 超过 10 个 Agent 协作需要更重型工具（Linear、Jira、Notion）
- 强实时性场景（如 prod incident）不适合纯文档驱动

---

## 9. 与现有 AGENTS.md 的关系

**AGENTS.md 是"宪法"，本文档是"实施细则"。**

- AGENTS.md 规定 **WHAT**（必须做什么、不能做什么）
- 本文档建议 **HOW**（用什么目录、什么命名、什么流程）

如有冲突：以 AGENTS.md 为准。本文档可独立调整。

---

## 10. 给用户的具体建议（精简版）

如果今天就采纳，建议从最小子集开始：

### 必做（本周）
1. ✅ `journal/` 目录 — 每个 Agent 会话结束写一份日报
2. ✅ `docs/tasks/` 目录 — 任务包统一存放
3. ⏳ `STATE.md` — 项目状态实时快照
4. ⏳ 在 AGENTS.md 加一句："新会话启动必读 STATE.md"

### 推荐（本月）
5. `agents/` 目录 + 各 Agent 能力卡
6. `docs/style/` 显式风格指南
7. `docs/handoffs/` 任务交接模板

### 可选（随用随建）
8. `BLOCKERS.md`
9. 自动化工具（commit hook、weekly summary）

---

## 11. 我的额外观察

### 11.1 多 Agent 协作的本质问题

是 **"上下文的传递成本"**。Solo + 1 Agent 时，上下文在会话内即可；多 Agent 时，上下文必须**外化为文档**。

文档的成本永远 < 重新建立上下文的成本。

### 11.2 用户在这个框架中的角色

不是"执行者"，而是 **"裁判 + 方向盘"**：
- 提供方向（AGENTS.md、需求）
- 仲裁分歧（Agent A 和 Agent B 不一致时）
- 验收成果（go/no-go 决策）
- 不做"具体执行"（让 Agent 做）

### 11.3 不要做的事

- ❌ 不要让 Agent 互相直接对话（容易跑偏）
- ❌ 不要让 Agent 自动执行其他 Agent 的任务（除非用户授权）
- ❌ 不要把所有决策都让 Agent 做（用户必须保留产品判断权）

---

**文档状态：** 建议稿  
**下次评审：** 用户决策是否采纳后  
**作者：** Claude Code (Haiku 4.5)，2026-05-10
