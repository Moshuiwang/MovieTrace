# ADR-0015: 飞书文档导入改用 drive/v1/import_task 三步流程

- **状态**: 已接受
- **日期**: 2026-05-16
- **任务包**: P1.21.9

---

## 背景

`sync_doc` 原来通过 `POST /open-apis/docx/v1/documents` 创建空文档，再逐块追加 text block 写入内容。

这套方案有两个问题：

1. **无格式**：Feishu docx v1 blocks API 只支持 plain text `block_type=2`，Markdown 的标题、表格、代码块全部变成连续纯文本，可读性极差。
2. **权限范围窄**：需要 `docx:document:create` 这个专用 scope，但 Feishu 对该 scope 审核严格，实际申请难度高。

---

## 决策

将 `sync_doc` 改用 **drive/v1/import_task** 三步异步导入流程：

1. `POST /open-apis/drive/v1/medias/upload_all`（multipart/form-data）上传 .md 文件，返回 `file_token`。
2. `POST /open-apis/drive/v1/import_tasks`，指定 `file_extension=md`、`type=docx`、`point.mount_type=1`，返回 `ticket`。
3. 轮询 `GET /open-apis/drive/v1/import_tasks/{ticket}`，`job_status` 0=成功，1/2=处理中，≥3=失败，取 `result.token` 和 `result.url`。

所需 scope 统一为 `drive:drive`，与 gap_sync 等模块一致。

---

## 实现细节

### multipart 构建（`_http.py: build_multipart_body`）

stdlib-only，不依赖 `requests` 或 `httpx`，以保持零外部依赖约束。boundary 用 `secrets.token_hex(16)` 生成，保证唯一性。

Upload all 的 form 字段：

| 字段 | 值 |
|------|-----|
| `file_name` | 文件名（含 `.md` 扩展名）|
| `parent_type` | `ccm_import_open` |
| `size` | 文件字节数（str）|
| `extra` | `{"obj_type":"docx","file_extension":"md"}` |
| `file` | 文件二进制内容 |

### 轮询策略

退避延迟序列：`[1, 2, 4, 8, 16, 30, 30, 30, 30, 30]` 秒，硬超时 300 秒（5 分钟）。
实测导入一个几 KB 的 Markdown 通常在 2-5 秒内完成，序列第一个间隔（1s）已足够。

### 权限错误处理

错误码 `99991661`、`99991663`、`1061045` 统一抛 `RuntimeError` 并附带"在飞书控制台申请 `drive:drive` scope"提示。  
这与任务包要求"权限错误必须停止并报告"一致。

---

## 被删除的代码

| 删除对象 | 原因 |
|----------|------|
| `_DOCX_BLOCK_MAX_CHARS = 10_000` | docx blocks 方案已废弃 |
| `POST /docx/v1/documents` 逻辑 | 同上 |
| `POST /docx/v1/.../blocks/{id}/children` 循环 | 同上 |

---

## 后果

**正面**：
- 飞书文档保留完整 Markdown 格式（标题层级、表格、代码块）。
- 所需 scope（`drive:drive`）与其他 drive 操作复用，无需单独申请。
- `sync_doc` 代码量从 ~50 行降到 ~45 行，逻辑更直观。

**风险**：
- 异步任务：极少数情况下任务可能超 5 分钟（大文件、飞书服务压力），此时会超时并报错，需人工重试。
- 依赖飞书 import API 稳定性：历史上该 API 改过参数，需跟踪飞书 changelog。

---

## 替代方案

| 方案 | 理由放弃 |
|------|----------|
| 保留 docx blocks API | 无格式，scope 难申请 |
| 用 `requests` 库处理 multipart | 违反"不引入新依赖"原则（CLAUDE.md 规则 5）|
| 直接改用 Feishu Wiki | V1 范围外（SCOPE.md）|
