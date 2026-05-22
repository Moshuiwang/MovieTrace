# 故障排查

> 遇到具体故障时按场景查找。每节包含"现象 → 排查顺序 → 禁止行为"。

---

## 测试失败（`pytest` 报错）

**排查顺序：**
1. 确认 `.venv` 已激活，`pip install -r requirements.txt` 已执行
2. 命令是否带 `PYTHONPATH=src`？项目使用 src layout，缺少会报 `ModuleNotFoundError: No module named 'movietrace'`
3. 加 `-v` 查看完整 traceback；单测可用 `-k <test_name>` 定位
4. 若是导入错误，确认 `src/movietrace/<module>/__init__.py` 存在

**禁止：**
- 测试失败时继续开发新功能（[`.claude/rules/00-core-behaviors.md`](../../.claude/rules/00-core-behaviors.md) 第 10 条）
- 删除失败的测试以"修复"问题（[`.claude/rules/00-core-behaviors.md`](../../.claude/rules/00-core-behaviors.md) 第 7 条）

---

## 实体匹配率异常下降

**排查顺序：**
1. 检查基线数据质量——样本数（100-300）、有效建议占比（应 >70%）
2. 查看 TMDb / Trakt / IMDb ID 覆盖率，确认外部源响应正常
3. 在 `tests/test_entity_matching.py` 用最小复现样本补充测试用例
4. 调整置信度阈值前，先在任务包中说明原因并取得授权

---

## 飞书 API 失败（连接超时 / 401 / 429）

**排查顺序：**
1. 检查 `.env` 中 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 是否齐全
2. 检查 `api.feishu.cn` 网络可达性（`curl -I` 验证）
3. 检查飞书应用权限配置（contact、bitable 等）
4. 检查 access token 是否过期（飞书 token 有效期 2 小时）

**禁止：**
- 静默重试（[`.claude/rules/00-core-behaviors.md`](../../.claude/rules/00-core-behaviors.md) 第 9 条：不隐藏失败）
- 任何失败都必须记录时间戳、来源 ID、HTTP 状态码，并向用户报告

---

## FlixPatrol 访问异常

**排查顺序：**
1. 检查是否违反合规约束：每 URL 每 24h ≤ 1 次、间隔 ≥ 2 秒、UA = `MovieTraceBot/0.1`
2. 检查 `robots.txt`（参考 `reports/flixpatrol_accessibility_report.md`）
3. 检查 HTML 结构是否变化（解析器在 `src/movietrace/sources/flixpatrol.py`，有 48 个测试用例）

**禁止：**
- 在生产任务里跑批量抓取（仅 Phase 0+ 验证脚本可批跑且需间隔）
- 修改 UA 来绕过限制

---

## SQLite 写入失败 / 数据库锁

**排查顺序：**
1. 检查 `data/movietrace.db` 是否被另一个进程占用（`lsof data/movietrace.db`）
2. 检查 schema 是否需要迁移（对比 `src/movietrace/db/schema.py` 与实际表结构）
3. 写入操作必须使用 prepared statements（[`.claude/rules/20-python-and-sql.md`](../../.claude/rules/20-python-and-sql.md)），不允许字符串拼接 SQL

---

## 通用原则

- 排查不动产品代码——先复现、定位、报告，再走任务包流程修复
- 排查记录写到任务包、STATE.md 或 PR 描述，重大问题升级为 ADR
- 不清楚时报告"现象 + 已排除 + 下一步"，不靠猜测推进（[`.claude/rules/00-core-behaviors.md`](../../.claude/rules/00-core-behaviors.md) § 失败信号）
