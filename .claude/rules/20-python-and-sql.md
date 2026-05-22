---
name: python-and-sql
description: Python 编码风格、类型标注、SQL prepared statement、外部 API 日志要求、提交信息约定。
include: ["src/**", "scripts/**"]
---

# Python 与 SQL 编码细则

## Python 风格

- 4 空格缩进（不用 tab）
- 模块 / 函数 / 变量 `snake_case`；类 `PascalCase`
- 公共函数必须类型标注（私有 helper 可省略）
- 文件名小写下划线（如 `operating_cost_estimate.md`、`baseline_tracking.py`）
- 优先用 stdlib；引新依赖必须任务包授权（CLAUDE.md 第 4 条铁律）
- src layout：导入路径以 `movietrace` 为根（`from movietrace.pipeline import ...`）

## SQL 强约束

- **禁止字符串拼接 SQL**——必须用 prepared statements（`?` 占位 + 参数 tuple）
- 即便参数来自内部代码也不例外（防御深度 + 一致性）
- 多行 SQL 用三引号字符串，保留缩进可读性
- 复杂查询写注释说明"业务意图"，不写"做什么"（well-named identifiers 已经说了"做什么"）

## 外部 API 调用

- 每次调用必须记录到 `api_usage_log`：`service` / `endpoint` / `status` / `key_fingerprint` / `request_date`
- 失败不静默——记录 HTTP 状态码 + 响应体片段（脱敏）+ timestamp
- 缓存优先（`api_cache`，TTL 视数据变化频率设定；enrichment 类数据用 72h，search 类用 72h）；缓存 key 形式见 db schema
- 详细合规约束见 [`22-sources-compliance.md`](22-sources-compliance.md) 与 [`23-feishu-integration.md`](23-feishu-integration.md)

## 长耗时循环与可观测性

- **预计超过 30 秒的循环**（如逐条 API enrichment）必须每 N 次迭代（建议 20）打一行 `logger.info` 进度日志，格式含已处理条数 / 总条数
- **`time.sleep()` 必须有实测或文档依据**，注释写明限制类型（per-second / 每日配额 / 重试退避）；禁止仅写 `# polite` 等无依据注释
- 指数退避（backoff）用于**服务器主动拒绝**（429 / 5xx / 网络错误）；固定 sleep 用于**主动节流**（每日配额型 API）；两者不混用

## 提交信息

- Conventional Commit 前缀：`feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:`
- 元文档变更子前缀：`docs(meta):` / `docs(state):` / `docs(decision):`
- 不提交 API Key / Token / 飞书密钥 / `.env`；只提交脱敏示例
- 不带 emoji（除非用户明确要求）
