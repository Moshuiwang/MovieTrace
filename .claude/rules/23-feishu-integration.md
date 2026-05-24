---
name: feishu-integration
description: 飞书集成不静默重试、字段 ID 与中文 field name 分流、Token 文件缓存、批量 API 偏好、常见错误码。
paths:
  - "src/movietrace/feishu/**"
  - "feedback/**"
---

# 飞书集成铁律

## 失败处置（与"不掩盖失败"硬绑定）

任何飞书 API 失败必须记录三项后**向用户报告**：
- timestamp（含时区）
- 来源 ID（base / table / record）
- HTTP 状态码 + 响应体片段（**脱敏 access_token**）

**禁止静默重试**——重试逻辑必须显式且有上限（指数退避，3 次为限）。

## 字段访问分流

| 场景 | 字段标识 |
|---|---|
| 写入（create / update record） | **field ID** |
| 读取 `records/search` 返回 | **中文 field name**（飞书 API 设计如此） |

读路径示例见 `feedback/pull.py`；写路径走 field ID（早期 `F` 字典已重构）。

## Token 缓存

- 路径：`~/.cache/movietrace/feishu_token.json`
- 权限：0600
- 过期 skew：5 min（提前刷新）
- 跨进程共享，避免一次 baseline_run 内 4 次重复获取

## 批量 API 偏好

- 创建 / 更新 / 删除多条记录 → 用 `batch_create_records` / `batch_update_records` / `batch_delete_records`
- 不要 per-record PUT 循环（违反配额且慢）
- 共享 helpers：[`src/movietrace/feishu/_http.py`](../../src/movietrace/feishu/_http.py)

## 常见错误码

| 错误码 | 含义 | 处置 |
|---|---|---|
| 99991661 / 99991663 / 1061045 | 权限不足 | 提示用户去飞书开发者后台申请对应 scope |
| 99991664 | tenant access token 过期 | 刷新缓存重试一次 |

## sync_doc 文档导入

P1.21.9 起改用 `drive/v1/import_task`（不是 docx blocks），需要 `drive:drive` scope。详见 [ADR-0015](../../docs/decisions/0015-feishu-doc-import-via-import-tasks.md)。

## 三张子表

修改子表结构前必须先在飞书 UI 同步字段定义，再改代码。表结构和飞书字段映射见 [`24-db-schema-map.md`](24-db-schema-map.md) + `src/movietrace/feishu/schema_setup.py`。
