# CLAUDE.md

> 本文件供 **Claude Code**（claude.ai/code）读取。  
> 项目规则、工作流阶段、决策门控的权威来源是 **`AGENTS.md`**，本文件是在此基础上的 Claude 专用补充。

---

## 项目概览

**MovieTrace** 是一个生产级内容更新推荐系统，自动发现英语影视内容在流媒体平台（Netflix、Prime Video、Disney+、Apple TV+、HBO/Max、Hulu）的热度变化，标记是否已在飞书基线中，并为运营团队生成可审核的更新推荐清单。

**当前阶段：Phase 1 V1 MVP 开发**  
Phase 0（实体匹配验证）和 Phase 0+（FlixPatrol 接入验证）均已完成，GO 决策通过。  
当前目标：实现 V1 完整流水线——FlixPatrol 数据采集、多源评分、飞书写入、CLI 入口。

---

## 核心架构

```
飞书（基线内容读取）
       ↓
SQLite（canonical_items / baseline / external_ids / candidates / cache）
       ↓
Pipeline（entity_matching → canonical_promotion → candidate_scoring）
       ↓
飞书（推荐表写入 → 人工审核 → 批次追踪）
```

**关键模块：**

| 模块 | 用途 | 状态 |
|------|------|------|
| `src/movietrace/feishu/` | 飞书 API 客户端（基线读取） | Phase 0 已验证 |
| `src/movietrace/db/schema.py` | SQLite schema + 迁移 + 连接池 | 已初始化 |
| `src/movietrace/pipeline/baseline_import.py` | 飞书基线导入 SQLite | 已测试 |
| `src/movietrace/pipeline/entity_matching.py` | 基线 + 候选条目匹配 TMDb/Trakt/IMDb | Phase 0 核心模块 |
| `src/movietrace/pipeline/canonical_promotion.py` | 去重合并为 canonical 记录 | Phase 0 已验证 |
| `src/movietrace/sources/` | TMDb / Trakt / OMDb HTTP 客户端 | 核心数据源，不得删除 |
| `src/movietrace/sources/flixpatrol.py` | FlixPatrol HTML 解析器（`parse_top10_page`） | Phase 0+ 已验证，48 个测试通过，P1-B 直接复用 |

**SQLite 表：**
- `feishu_import_runs` — 飞书基线导入记录
- `source_records` — 外部 API 原始响应
- `baseline_items` — 平台现有内容（来自飞书）
- `canonical_items` — 去重匹配后的内容（父：片名；子：季 → 集）
- `external_ids` — TMDb/Trakt/IMDb/OMDb ID 映射
- `candidates` — 推荐内容候选（待运营审核）

完整 schema 见 `src/movietrace/db/schema.py`。

---

## 开发环境

```bash
# 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

当前依赖：`beautifulsoup4`（FlixPatrol 解析器）、`pytest`（测试）。

**环境变量（`.env`，不提交）：**
- `FEISHU_APP_ID` / `FEISHU_APP_SECRET` — 飞书凭证
- `TMDB_API_KEY` — TMDb API key
- `TRAKT_CLIENT_ID` — Trakt client ID（可选）

**TMDb Bearer Token**：从 `/tmp/movietrace_phase0_secrets.json` 读取（`tmdb.api_read_access_token`）。参考 `scripts/sup_c_flixpatrol_matching.py` 中的 `_load_bearer_token()` 模式。

---

## 常用命令

```bash
# 运行全部测试（项目使用 src layout，必须加 PYTHONPATH）
PYTHONPATH=src python -m pytest tests/ -v

# 运行单个测试文件
PYTHONPATH=src python -m pytest tests/test_flixpatrol_parsing.py -v

# 初始化 / 重置数据库
PYTHONPATH=src python -c "from movietrace.db.schema import init_database; init_database()"

# 查看数据库 schema
sqlite3 data/movietrace.db ".schema"

# 检查 git 状态
git status --short --branch
```

---

## 接收任务前的检查

**任务包必须包含以下字段，缺一不填，不进入编码：**

| 字段 | 说明 |
|------|------|
| 任务名称 | 明确具体 |
| 任务类型 | feat / fix / docs / refactor / test |
| 当前阶段 | Phase 1 等 |
| 来源任务 | 设计文档或任务列表的具体位置 |
| 目标 | 单一、可判断的结果 |
| 非目标 | 明确排除什么 |
| 允许修改范围 | 哪些文件可以动 |
| 禁止修改范围 | 哪些文件不能动 |
| 验收标准 | 怎么判断完成 |
| 验证命令 | 可执行的命令 |
| 风险点 | 已知不确定因素 |

**编码前确认清单：**
- ✅ 当前阶段明确
- ✅ 来源文档存在且可追溯
- ✅ 目标与非目标无冲突
- ✅ 修改范围清楚
- ✅ 验收标准可判断
- ✅ 验证命令可运行
- ✅ 风险点已列出

---

## Phase 状态

**Phase 0：** ✅ 完成 — 实体匹配率 96.6%，GO 决策

**Phase 0+：** ✅ 完成 — FlixPatrol 接入验证（SUP-A~F 全部通过）
- 解析器：`src/movietrace/sources/flixpatrol.py`（48 个测试，100% 提取率）
- TMDb 匹配率：118/118 = 100%
- 合规约束：每 URL 每 24h ≤ 1 次，间隔 ≥ 2 秒，`MovieTraceBot/0.1` UA，仅内部使用

**Phase 1（当前）：** V1 MVP 开发
- P1-A：实体匹配回归修复（可立即启动）
- P1-B：FlixPatrol HTTP 客户端 + DB（可立即启动，与 P1-A 并行）
- P1-C：多源合并 + hot_score 评分
- P1-D：飞书基线匹配标记
- P1-E：每日 Markdown 日报
- P1-F：飞书推荐表写入
- P1-G：CLI 命令
- P1-H：集成测试 + 首次运行

任务包尚未写。**写任务包，再开始编码。**

---

## 会话结束检查清单

每次会话结束前（用户说"收尾"，或主线工作完成时），**必须依次执行**：

- [ ] **STATE.md** — 更新当前阶段、进行中任务、阻塞项、待用户决策
- [ ] **日报** — 写 `journal/YYYY-MM-DD_<tool>_<model>.md`（见 AGENTS.md 日报规范）
- [ ] **ADR** — 如有新决策或状态变更（Proposed→Accepted 等），更新对应文件和 `docs/decisions/README.md`
- [ ] **CLAUDE.md / AGENTS.md** — 如有阶段变化、新模块、新约定，同步更新
- [ ] **git commit** — 上述文档变更统一提交，message 以 `docs(meta):`、`docs(state):`、`docs(journal):` 开头

即使用户没有明确说"收尾"，只要会话中有阶段推进、重大决策或产出物，也必须执行上述清单。

---

## 代码规范

- 4 空格缩进
- 公共函数必须有类型标注
- 命名：`snake_case`（模块、函数、变量）
- 测试文件按行为命名：`test_entity_matching.py`、`test_flixpatrol_parsing.py`
- Commit message：Conventional Commit 格式（`feat:`、`fix:`、`docs:` 等）
- SQL 查询必须用 prepared statements，禁止字符串拼接
- 外部 API 调用必须记录时间戳和响应状态

---

## 常见问题

**Q：能引入新依赖吗？**  
A：不能主动引入。需要在任务包中提出，说明业务理由，用户授权后才能引入。

**Q：FlixPatrol 怎么用？**  
A：使用 `src/movietrace/sources/flixpatrol.py` 中的 `parse_top10_page(html, platform, region)`。合规约束见上方 Phase 0+ 节。

**Q：TMDb Token 在哪？**  
A：`/tmp/movietrace_phase0_secrets.json` → `tmdb.api_read_access_token`。参考 `scripts/sup_c_flixpatrol_matching.py`。

**Q：飞书 API 调用失败怎么办？**  
A：记录时间戳和来源 ID，向用户报告，不静默重试。遵守 AGENTS.md 规则 9：不隐藏失败。

---

## 故障排查

**测试失败：**
1. 确认 `.venv` 已激活，依赖已安装
2. 命令必须加 `PYTHONPATH=src`（src layout）
3. 加 `-v` 查看完整错误
4. 测试失败时禁止继续开发新功能

**实体匹配率低：**
1. 检查基线数据质量（100-300 样本，>70% 有效建议）
2. 查看 TMDb/Trakt/IMDb ID 覆盖率
3. 在 `tests/test_entity_matching.py` 补充测试用例
4. 调整置信度阈值前，需在任务中说明原因

**飞书连接超时：**
1. 检查 `.env` 中 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`
2. 检查 `api.feishu.cn` 网络可达性
3. 检查飞书应用权限配置

---

## 相关文档

- `AGENTS.md` — 项目宪法（规则、阶段、决策门控，权威来源）
- `STATE.md` — 当前项目状态快照（每次会话必读）
- `SCOPE.md` — V1 范围边界（防止 scope creep）
- `docs/decisions/` — 架构决策记录（ADR）
- `docs/tasks/` — 任务包
- `journal/` — 工作日报
- `reports/` — 验证报告
