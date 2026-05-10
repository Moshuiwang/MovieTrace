# ADR-0005: SUP-A 任务包仅使用 stdlib，不引入新依赖

**状态：** ✅ Accepted  
**日期：** 2026-05-10  
**决策者：** 用户 + Claude Code (Haiku 4.5)  
**相关 Commit：** `8ada68e`

---

## 上下文

SUP-A（FlixPatrol 可访问性测试）需要做 HTTP 请求，可选择：

- **stdlib：** `urllib.request` + `urllib.robotparser`（Python 内置）
- **第三方：** `requests`（业内事实标准）或 `httpx`（异步友好）

### 现状调研

**项目当前 HTTP 实现：**
- `src/movietrace/sources/http.py` 使用 `urllib.request`（stdlib）
- 仅支持 JSON 响应，不支持 HTML
- 无 `requirements.txt` / `pyproject.toml`，依赖未明确管理

**AGENTS.md 第 5 条约束：**
> 不主动引入新依赖，除非任务包明确允许。

## 决策

**SUP-A 验证脚本仅使用 Python 3.12 stdlib。**

具体使用：
- `urllib.request`（HTTP 请求）
- `urllib.robotparser`（robots.txt 解析）
- `time`（请求间隔）
- `json`（结构化输出）
- `pathlib`（文件操作）

**不引入：** `requests`、`httpx`、`beautifulsoup4`、`lxml` 等第三方库。

**SUP-B（HTML 解析）阶段再单独评估** 是否引入 BeautifulSoup（解析任务确实需要）。

## 后果

**正面：**
- 完全符合 AGENTS.md 第 5 条
- 与现有 `http.py` 风格一致（同代码库内代码风格统一）
- 验证脚本可立即运行，无需 `pip install`
- 没有依赖管理负担（`requirements.txt` 缺失问题暂可继续延后）

**负面 / 待解决：**
- `urllib.request` 的 API 比 `requests` 啰嗦（特别是 timeout、headers、retry）
- 重定向处理、Cookie 处理需要手写
- 错误异常类型不如 `requests` 直观（`URLError` vs `HTTPError`）
- SUP-B 阶段如果引入 BeautifulSoup，需要新写一份 ADR

## 备选方案

### 备选 A：引入 `requests`

- 优点：API 友好、社区标准、文档丰富
- 缺点：违反 AGENTS.md 第 5 条；项目目前没有依赖管理机制
- **拒绝原因：** 验证任务的成本不应高于它要验证的事情；为一次性脚本引入依赖不划算

### 备选 B：等创建 `requirements.txt` 后再做 SUP-A

- 优点：未来更标准
- 缺点：阻塞 SUP-A 执行；为了"以后好"延误"现在做"
- **拒绝原因：** 不必要的前置依赖；YAGNI

### 备选 C：本次决策（仅 stdlib）✅

详见"决策"章节。

---

## 引用

- 任务包：[`docs/tasks/sup_a_flixpatrol_accessibility.md`](../tasks/sup_a_flixpatrol_accessibility.md)
- 现有代码：[`src/movietrace/sources/http.py`](../../src/movietrace/sources/http.py)
- AGENTS.md 第 5、6 条
