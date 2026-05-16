---
name: sources-compliance
description: 外部数据源合规约束（FlixPatrol / TMDb / Trakt / OMDb）、API 配额日志、UA 与抓取节流、合规绝对线。
include: ["src/movietrace/sources/**"]
---

# 外部数据源合规

## FlixPatrol（最严，公开页面爬取）

- 每 URL 每 24h **≤ 1 次**请求
- 请求间隔 **≥ 2 秒**
- User-Agent 必须为 `MovieTraceBot/0.1`（不得伪造其他 UA）
- 仅内部使用，禁止公开传播或转售
- 生产任务里不跑批量抓取（仅 Phase 0+ 验证脚本可批跑且必须间隔）
- HTML 结构变化时只改解析器（`flixpatrol.py`），不调整 UA / 频率
- FP API 当前 402（订阅缺失），脚本依赖 fallback 机制运行（见 STATE.md 阻塞项）

## TMDb（Bearer Token）

- Token 路径：`~/.config/movietrace/secrets.json` → `tmdb.api_read_access_token`
- Fallback 兼容：`/tmp/movietrace_phase0_secrets.json`（仅旧环境，会 warning）
- detail endpoint 必须走 `api_cache` 24h TTL（见 [`21-db-migrations.md`](21-db-migrations.md)）

## Trakt / OMDb

- OMDb 免费 1000/日；多 key 轮换通过 `key_fingerprint` 区分
- Trakt 需 `trakt-api-key` header（client_id）

## 通用日志要求

每次外部 API 调用，**无论成功失败**，必须写入 `api_usage_log`：

| 字段 | 说明 |
|---|---|
| `service` | tmdb / trakt / omdb / flixpatrol |
| `endpoint` | API 路径 |
| `status` | ok / error / quota_error / rate_limited |
| `key_fingerprint` | 多 key 轮换时区分 |
| `request_date` | UTC |

## 合规绝对线（永远不做）

- ❌ 绕过登录 / 验证码 / 付费墙 / 反爬
- ❌ 高频无控制抓取
- ❌ IMDb 默认抓取（用 OMDb 代理）
- ❌ 修改 UA 绕过站点限制
