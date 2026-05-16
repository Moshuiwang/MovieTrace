---
name: gotchas
description: MovieTrace 项目 4 个最易踩的坑速查（PYTHONPATH / Secrets / FlixPatrol / 飞书重试）。
include: ["**/*"]
---

# 4 个易踩坑速查

> 动手前 30 秒扫一眼。详细规则见对应 rule 文件。

## 1. `PYTHONPATH=src` 必带

src layout 项目。运行测试 / 脚本 / CLI 任何 `python -m movietrace.*` 都必须带：

```bash
PYTHONPATH=src python -m movietrace.cli daily-discover --dry-run
PYTHONPATH=src python -m pytest tests/ -v
```

缺少会报 `ModuleNotFoundError: No module named 'movietrace'`。详见 [`30-testing.md`](30-testing.md)。

## 2. TMDb Bearer Token 路径

正式路径：`~/.config/movietrace/secrets.json` → `tmdb.api_read_access_token`

旧路径 `/tmp/movietrace_phase0_secrets.json` 仍 fallback 兼容（会 warning）。详见 [`22-sources-compliance.md`](22-sources-compliance.md)。

## 3. FlixPatrol 合规（最严）

- 每 URL 每 24h ≤ 1 次
- 请求间隔 ≥ 2 秒
- UA = `MovieTraceBot/0.1`（**不得伪造**）
- 仅内部使用

违反会触发站点封禁，且违反我方合规承诺。详见 [`22-sources-compliance.md`](22-sources-compliance.md)。

## 4. 飞书失败不静默重试

任何飞书 API 失败 → 必须记录 timestamp + 来源 ID + HTTP 状态码 + 响应体（脱敏） → 向用户报告。

静默重试是 CLAUDE.md 第 3 条铁律（不掩盖失败）的违反。详见 [`23-feishu-integration.md`](23-feishu-integration.md)。
