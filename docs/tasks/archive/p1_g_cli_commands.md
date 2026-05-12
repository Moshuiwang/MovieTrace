# 任务包：P1-G CLI 命令（4 条）

**任务包版本：** v1
**创建日期：** 2026-05-11
**预计完成：** TBD（依赖 P1-F 完成）

---

## 任务名称

P1-G：在 `src/movietrace/cli.py` 中实现 4 条 CLI 子命令，支持日常运维、基线查询、飞书 schema 验证

## 任务类型

`feat` — 新增功能

## 当前阶段

Phase 1（V1 MVP 开发）

## 执行环境

- **分支：** `main`（当前 working tree，不开 git worktree）
- **工作目录：** `/home/ubuntu/MovieTrace`
- **commit 策略：** 完成后准备 commit，不要 push
- **CLI 框架：** 无外部依赖；使用 Python 内置 `argparse` 或自行路由（参考 Phase 0 实现）

## 来源任务

- [`docs/next_steps_plan.md`](../next_steps_plan.md) § 5.2 P1-G
- Phase 0 CLI 架构参考：`src/movietrace/cli.py`（已有）
- **前置：** P1-B ~ P1-F 完成（各命令依赖相应模块）

## 目标

补充 4 条 CLI 子命令到现有 CLI 框架，支持日常操作：日发现流水线、基线查询、飞书连通性验证、配置管理，使用户无需直接调用 Python 函数或 Feishu API。

## 非目标

- ❌ 不修改 Python 依赖（用 argparse，不用 Click / Typer）
- ❌ 不创建新的配置文件格式（用现有 config.yaml）
- ❌ 不支持数据库 SQL 命令行工具（仅限应用层 CLI）
- ❌ 不修改已有的 CLI 子命令（只新增）
- ❌ 不实现 UI / TUI（纯命令行）

## 允许修改范围

**修改文件：**

- `src/movietrace/cli.py`（新增 4 条子命令）
- `config/config.example.yaml`（示例配置，可新增注释）

**新增文件：**

- （无新增）

## 禁止修改范围

- 🚫 `src/movietrace/pipeline/`（P1-B ~ P1-E 产物，只调用）
- 🚫 `src/movietrace/feishu/`（只调用 API）
- 🚫 `src/movietrace/db/`（只调用 DB API）
- 🚫 `requirements.txt`（不新增依赖）
- 🚫 `STATE.md`、`SCOPE.md`、`AGENTS.md`、`CLAUDE.md`、`docs/decisions/`

## 相关上下文

### 4 条命令概览

| 命令 | 目的 | 依赖 | 用户 |
|------|------|------|------|
| `movietrace daily-discover` | 主流水线：读 P1-B → 评分 P1-C → 匹配 P1-D → 日报 P1-E → 写飞书 P1-F | P1-B ~ P1-F | 运维 / CI-CD |
| `movietrace validate-feishu` | 飞书连通性 + token 有效性 | Phase 0 API 封装 | 运维 / 故障排查 |
| `movietrace inspect-baseline` | 查询本地基线（canonical_items + baseline_items）| DB | 产品 / 内容运营 |
| `movietrace check-feishu-schema` | 验证飞书推荐表 schema 与预期一致 | Feishu API | 运维 / 配置验证 |

### 命令设计细节

#### 1. `movietrace daily-discover [--date YYYY-MM-DD] [--dry-run] [--filter FILTER]`

**目的：** 主入口，执行完整日发现流水线。

**选项：**

- `--date YYYY-MM-DD` (可选，默认今天)
  - 指定处理日期；可用于补跑历史数据或测试
  - 验证格式：如格式错误，报错"Invalid date format, use YYYY-MM-DD"

- `--dry-run` (可选，默认 False)
  - 执行全部步骤但不写飞书；生成本地审计日志和日报
  - 用于测试和验证

- `--filter FILTER` (可选，默认无)
  - 可选值：`new` (新发现) / `existing` (已有) / `pending` (待确认) / `all`
  - 控制哪些候选类别写入飞书
  - 示例：`--filter new` 只写入新发现的候选，已有和待确认的跳过

**输出：**

- Stdout：每个步骤的进度（如 "Reading candidates... OK", "Writing to Feishu... 50/50 success"）
- Stderr：警告和错误
- 日报：`reports/daily/YYYY-MM-DD.md`
- 审计日志：`source_records/YYYY-MM-DD.jsonl`

**行为：**

```
1. 检查配置 (config/config.yaml)：feishu token 存在
2. 读取 match_candidates 表
   - 按 --date 过滤（默认今天的 created_at）
   - 按 --filter 过滤（可选）
3. 生成日报 (P1-E)
4. 写入飞书 (P1-F，可 --dry-run)
5. 输出成功/失败统计
```

**示例用法：**

```bash
# 今天的发现，干运行
movietrace daily-discover --dry-run

# 指定日期，只新发现
movietrace daily-discover --date 2026-05-10 --filter new --dry-run

# 实际写入（非 dry-run）
movietrace daily-discover
```

#### 2. `movietrace validate-feishu`

**目的：** 验证飞书 API 连通性和认证。

**选项：**

- 无

**输出：**

- 如连通且认证正确：
  ```
  ✓ Feishu API reachable
  ✓ Access token valid
  ✓ Can access table: 推荐表 (table_id=xxx)
  ```
- 如失败，逐项输出失败原因和 HTTP status code

**行为：**

```
1. 从 /tmp/movietrace_phase0_secrets.json 读 feishu.access_token
   - 如文件缺失，报错"Secrets file not found"
   - 如 token 缺失，报错"feishu.access_token not configured"

2. 调用飞书 API 验证 token 有效性（如 GET /open-apis/auth/v3/tenant_access_token/internal 或类似）
   - 返回 200 OK → "Valid token"
   - 返回 401 → "Token expired or invalid"
   - 返回 5xx → "Service error"

3. 查询推荐表 schema（表是否存在，字段是否完整）
   - 返回字段列表 → "OK"
   - 缺少关键字段 → "Warning: Missing fields: ..."

4. 输出整体状态
```

**示例用法：**

```bash
movietrace validate-feishu
# Output:
# ✓ Feishu API reachable
# ✓ Access token valid
# ⚠ Missing field: fulfillment_status
```

#### 3. `movietrace inspect-baseline [--query QUERY] [--format json|table|csv]`

**目的：** 查询本地基线，用于内容运营或调试。

**选项：**

- `--query QUERY` (可选)
  - 快速查询：`title=The Crown` 或 `year=2016` 或 `content_type=tv_show`
  - 支持简单 AND：`title=The Crown AND year=2016`
  - 如无 `--query`，输出基线统计摘要

- `--format` (可选，默认 `table`)
  - `table`：Markdown 表格（适合展示）
  - `json`：JSON 数组（适合脚本处理）
  - `csv`：CSV 格式（适合导出 Excel）

**输出：**

- 无 `--query` 时，显示统计摘要：
  ```
  Baseline Summary:
  - Total items: 5,234
  - Movies: 3,100
  - TV Shows: 2,134
  - Recent additions (7 days): 45
  ```

- 有 `--query` 时，显示匹配结果（表格、JSON 或 CSV 格式）

**行为：**

```
1. 连接本地 DB (data/movietrace.db)
2. 如无 --query，显示基线统计
3. 如有 --query，解析 query，执行 SQL SELECT，格式化输出
```

**示例用法：**

```bash
movietrace inspect-baseline
# Output:
# Baseline Summary:
# - Total items: 5234
# - Movies: 3100
# - TV Shows: 2134

movietrace inspect-baseline --query "title=The Crown" --format table
# Output:
# | title | release_year | content_type |
# |-------|--------------|--------------|
# | The Crown | 2016 | tv_show |

movietrace inspect-baseline --query "year=2024" --format json
# Output:
# [{"title": "...", "release_year": 2024, ...}, ...]
```

#### 4. `movietrace check-feishu-schema`

**目的：** 验证飞书推荐表 schema 与预期一致，用于初始化或升级验证。

**选项：**

- 无

**输出：**

- 逐字段检查，OK 或警告：
  ```
  Checking Feishu recommendation table schema...
  ✓ content_update_id (String)
  ✓ title (String)
  ✓ hot_score (Number)
  ⚠ batch_id (Missing)
  ✗ review_status (Wrong type: Text instead of SingleSelect)
  
  Summary: 3 OK, 1 Warning, 1 Error
  ```

**行为：**

```
1. 从 config.yaml 读飞书表 ID
2. 调用 Feishu API 获取表 schema
3. 与预期 schema （定义在 docs/baseline_export_schema.md 或代码中） 对比
4. 输出检查结果和修复建议
```

**示例用法：**

```bash
movietrace check-feishu-schema
# Output as above
```

### 配置示例（`config/config.example.yaml`）

```yaml
# MovieTrace 配置示例

# 飞书连接
feishu:
  # 推荐表 ID（Feishu share link 中可提取）
  recommendation_table_id: tbl_xxx
  # API 端点（可选，默认 https://open.feishu.cn）
  api_base_url: https://open.feishu.cn

# 数据库
database:
  path: data/movietrace.db

# CLI
cli:
  # 默认日期（可选，默认 today）
  default_date_offset: 0  # 0 = 今天，-1 = 昨天
  # 默认 filter
  default_filter: all  # all / new / existing / pending

# 评分权重（可选，默认使用 config/scoring_weights.yaml）
scoring:
  weights_file: config/scoring_weights.yaml
```

## 具体要求

1. **argparse 使用**
   - 定义 main parser 和 subparsers
   - 每条命令为一个 subcommand
   - 所有 `--help` 输出清晰、包含示例

2. **错误处理**
   - 配置缺失 → 明确报错 "Config file not found: config.yaml"
   - API 调用失败 → 报错并记录 HTTP status
   - DB 连接失败 → 报错 "Cannot connect to database"
   - 用户输入格式错误 → 报错并提示正确格式

3. **进度指示**
   - `daily-discover` 命令应输出进度（如 "Step 1/4: Reading candidates...", "Step 4/4: Writing Feishu... 45/50 success"）
   - 不用 progress bar，简单的文本输出

4. **配置文件加载**
   - 从 `config/config.yaml` 读取，不存在则用 `config/config.example.yaml` 作默认
   - 或从 `~/.movietrace/config.yaml` 读取（支持用户本地配置）
   - 命令行参数优先于配置文件

5. **日志级别**
   - 默认输出 INFO 级别（进度、统计）
   - Verbose 模式（可选 `-v` 或 `--verbose`）输出 DEBUG

## 验收标准

1. ✅ 4 条命令都可执行：`movietrace daily-discover --help` 等打印帮助文本
2. ✅ `movietrace daily-discover --dry-run` 无错误，生成日报和审计日志
3. ✅ `movietrace validate-feishu` 正确检测 token 有效性
4. ✅ `movietrace inspect-baseline` 查询和输出格式正确
5. ✅ `movietrace check-feishu-schema` 逐字段对比，输出准确
6. ✅ 配置缺失时，报错明确（如 "Missing config key: feishu.recommendation_table_id"）
7. ✅ API 错误（如网络超时）不导致 CLI 崩溃，有恰当的错误提示
8. ✅ 所有命令的 `--help` 输出包含说明和示例
9. ✅ 单元测试覆盖每条命令的主路径

## 测试要求

### 单元测试（`tests/test_cli.py` or similar）

1. **daily-discover 命令**
   - 无参数默认运行（今天，all filter，dry-run）
   - 指定日期和 filter
   - Dry-run vs 实际写入的行为差异验证

2. **validate-feishu 命令**
   - Token 有效时输出"OK"
   - Token 无效时输出错误信息
   - API 不可达时输出"Service error"

3. **inspect-baseline 命令**
   - 无 `--query` 输出统计摘要
   - 有 `--query` 输出匹配结果
   - 不同 `--format` 的输出格式验证

4. **check-feishu-schema 命令**
   - 正常 schema 输出"OK"
   - 缺少字段时输出"Warning"
   - 字段类型错误时输出"Error"

5. **配置加载**
   - 默认配置文件存在时，正确加载
   - 配置文件缺失时，报错清晰
   - 命令行参数覆盖配置文件值

### 回归测试

- P1-B ~ P1-F 的功能测试仍通过

## 验证命令

```bash
# 显示帮助
movietrace --help
movietrace daily-discover --help
movietrace validate-feishu --help
movietrace inspect-baseline --help
movietrace check-feishu-schema --help

# 执行 daily-discover dry-run
PYTHONPATH=src python -m movietrace daily-discover --dry-run
# 预期输出：进度信息 + 生成日报和审计日志

# 验证 Feishu 连通性
PYTHONPATH=src python -m movietrace validate-feishu
# 预期输出：✓ 或 ✗ + 说明

# 查询基线摘要
PYTHONPATH=src python -m movietrace inspect-baseline
# 预期输出：统计摘要

# 查询特定内容
PYTHONPATH=src python -m movietrace inspect-baseline --query "title=The Crown" --format table
# 预期输出：Markdown 表格

# 检查飞书表 schema
PYTHONPATH=src python -m movietrace check-feishu-schema
# 预期输出：逐字段检查结果

# 单元测试
PYTHONPATH=src python -m pytest tests/test_cli.py -v
```

## 风险点

1. **配置文件位置不统一**
   - 预期：config.yaml 在 `config/` 目录
   - 风险：用户误放在其他位置，导致 CLI 找不到
   - 缓解：CLI 启动时检查并打印当前用的配置文件路径；支持环境变量 `MOVIETRACE_CONFIG` 覆盖

2. **Feishu 表 ID 不一致**
   - 预期：config.yaml 中的 table_id 与飞书实际表一致
   - 风险：写错 table_id，导致数据写到错误的表
   - 缓解：`check-feishu-schema` 命令可验证表存在性；写入前提示确认

3. **日期参数格式校验**
   - 预期：`--date 2026-05-11` 格式正确
   - 风险：用户输入 `--date 2026-5-11` 或 `--date May 11` 导致解析失败
   - 缓解：提供清晰的错误消息"Invalid date format, use YYYY-MM-DD"

4. **权限和密钥管理**
   - 预期：Feishu token 从 `/tmp/movietrace_phase0_secrets.json` 读取
   - 风险：token 泄露或权限不足
   - 缓解：检查文件权限（不可被其他用户读），错误消息不输出完整 token

5. **输出格式向后兼容性**
   - 预期：CLI 输出格式稳定，用脚本解析时不破坏
   - 风险：后续版本修改输出格式，导致依赖脚本失效
   - 缓解：JSON 格式输出定版本；Text 格式标注"for human reading only"

## 完成后输出要求

按 [`docs/workflow/report-format.md`](../workflow/report-format.md) 格式汇报。

**汇报要点：**
- 4 条命令的实现状态（代码行数、覆盖的功能点）
- `--help` 输出示例
- 配置文件加载成功验证
- 每条命令的执行示例和输出
- 单元测试覆盖率
- 任何特殊的错误处理或边界条件的处理方式
