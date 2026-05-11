# 任务包：P1-F 飞书推荐表写入 + 去重 + 人工字段保护

**任务包版本：** v1
**创建日期：** 2026-05-11
**预计完成：** TBD（依赖 P1-E 完成）

---

## 任务名称

P1-F：将 P1-D/P1-E 的发现和确认候选写入飞书推荐表，按 `content_update_id` 去重避免重复，保护人工填充的字段不被覆盖

## 任务类型

`feat` — 新增功能

## 当前阶段

Phase 1（V1 MVP 开发）

## 执行环境

- **分支：** `main`（当前 working tree，不开 git worktree）
- **工作目录：** `/home/ubuntu/MovieTrace`
- **commit 策略：** 完成后准备 commit，不要 push
- **飞书认证：** 需要飞书 API token（从 `/tmp/movietrace_phase0_secrets.json` 的 `feishu.access_token` 读取）

## 来源任务

- [`docs/next_steps_plan.md`](../next_steps_plan.md) § 5.2 P1-F
- [`docs/requirements.md`](../requirements.md) § 11.1（`content_update_id = canonical_item_id + update_type`，去重规则）
- [`docs/baseline_export_schema.md`](../baseline_export_schema.md)（飞书推荐表 schema 参考）
- **前置：** P1-E 必须完成（日报已审核，人工决策哪些候选写入飞书）
- **复用：** Phase 0 [`src/movietrace/feishu/baseline.py`](../../src/movietrace/feishu/baseline.py)（飞书 API 封装）

## 目标

从 P1-D match_candidates 表读取经过人工确认的候选（由 P1-E 日报指导），通过 `content_update_id` 去重检查，调用飞书 API 写入推荐表，并保留本地 `source_records` 日志供审计和回滚。重复运行同一批候选时，应不产生重复行；修改已有候选时，不覆盖人工填充的 `review_status`, `batch_id`, `fulfillment_status` 三个字段。

## 非目标

- ❌ 不修改飞书推荐表 schema（只写入，按已有 schema 对齐）
- ❌ 不生成或修改日报（P1-E）
- ❌ 不做人工审核决策（由人在 P1-E 日报或飞书中手工标记，本任务只执行写入）
- ❌ 不自动删除已写入的候选（如需撤回，由人工在飞书中操作）
- ❌ 不调用 TMDb / Trakt / 其他外部 API（所有数据从本地 DB 读）
- ❌ 不引入新依赖

## 允许修改范围

**新增文件：**

- `src/movietrace/feishu/recommendation_writer.py`（新模块）
- `tests/test_recommendation_writer.py`
- `source_records/` 目录（本地审计日志，non-repo）

**修改文件：**

- （无需修改 schema.py，不创建表）

## 禁止修改范围

- 🚫 `src/movietrace/feishu/baseline.py`（Phase 0 API 封装，只调用）
- 🚫 `src/movietrace/pipeline/`（P1-C、P1-D 产物，只读）
- 🚫 `candidates`, `match_candidates`, `baseline_items` 表（只读）
- 🚫 飞书推荐表 schema（写入方式由飞书已有 schema 决定）
- 🚫 `STATE.md`、`SCOPE.md`、`AGENTS.md`、`CLAUDE.md`、`docs/decisions/`

## 相关上下文

### 飞书推荐表 schema（来自 [`docs/baseline_export_schema.md`](../baseline_export_schema.md)）

**前提：** 飞书推荐表由人工创建或通过 Phase 0 导出。本任务假设表已存在，字段如下：

```
推荐表字段（预期）：
- record_id           (Feishu record ID，UUID)
- content_update_id   (MovieTrace 唯一键，PK 或 unique index)
- canonical_item_id   (FK → canonical_items)
- title               (内容标题)
- release_year        (发布年)
- content_type        (movie / tv_show)
- hot_score           (0-100)
- platforms           (JSON array: ["Netflix", "Prime Video", ...])
- discovery_source    (new_release / global_hot / both)
- reason_text         (推荐理由)
- review_status       (待审 / 已审 / 驳回，人工填充，不覆盖)
- batch_id            (批次号，人工填充，不覆盖)
- fulfillment_status  (待补 / 已补，人工填充，不覆盖)
- created_at          (MovieTrace 本地时间戳)
- updated_at          (最后写入时间)
```

### content_update_id 去重规则（[`docs/requirements.md`](../requirements.md) § 11.1 R4）

```
content_update_id = "{canonical_item_id}#{update_type}"

update_type 分类：
- "discovery"     : 新发现候选（is_in_baseline = False）
- "existing"      : 已有基线内容（is_in_baseline = True）
- "pending_review": 待人工确认（match_confidence = 'low'）

同一 content_update_id 只应写入一次；重复写入时应检查 created_at 或用 Feishu update API 而不是 insert
```

### 人工字段保护机制

三个字段禁止覆盖，仅在首次创建时初始化为 NULL：
- `review_status`
- `batch_id`  
- `fulfillment_status`

如果飞书中已有这三个字段的值，本任务应读出并保留，更新其他字段时使用 Feishu update API 而非 insert。

### 本地审计日志结构

在 `source_records/` 目录中，按日期生成审计文件 `source_records/YYYY-MM-DD.jsonl`，每行一个 JSON 对象：

```json
{
  "timestamp": "2026-05-11T12:34:56Z",
  "action": "insert|update|skip|error",
  "content_update_id": "canonical_123#discovery",
  "feishu_record_id": "rec_xxx" or null,
  "status_code": 200 or http_code,
  "reason": "Successfully inserted" or "Skipped: already exists" or "Error: ..."
}
```

## 具体要求

1. **读取候选数据**
   - 从 match_candidates 表读取所有行（或支持 `--filter` 参数只读特定分类如 `is_in_baseline=False`）
   - 每条候选对应一个推荐表记录

2. **生成 content_update_id**
   - 算法：`f"{row['canonical_item_id']}#{update_type}"`
   - `update_type` 由 `is_in_baseline` 和 `match_confidence` 判断：
     - `is_in_baseline = False` → "discovery"
     - `is_in_baseline = True` → "existing"
     - `match_confidence = 'low'` → "pending_review"
   - 优先级：pending_review > discovery > existing（如行同时满足多个条件，用最高优先级）

3. **去重检查**
   - 调用 Feishu API 查询 `content_update_id` 字段，检查是否已存在
   - 如已存在：
     - 如本地数据与飞书完全相同，跳过（log: "Skipped: already exists"）
     - 如本地数据有更新（hot_score / reason_text / platforms 变化），调用 update API，但不覆盖三个人工字段
   - 如不存在：插入新行（log: "Inserted"）

4. **人工字段读取和保护**
   - 更新前，从飞书读取该行的 `review_status`, `batch_id`, `fulfillment_status`
   - 在 update API payload 中，显式包含这三个字段的原值，不修改
   - 如果本地 DB 中这三个字段有值（从飞书同步），也应遵守同样逻辑

5. **Feishu API 调用**
   - 复用 Phase 0 的 `src/movietrace/feishu/baseline.py` 中的 API 封装
   - 需要的方法：`search_records(table_id, filter_condition)`, `insert_record(table_id, payload)`, `update_record(table_id, record_id, payload)`
   - 如不存在，在 baseline.py 中补充相应方法（确保 Phase 0 API 可覆盖 CRUD）

6. **错误处理和重试**
   - HTTP 4xx（验证错误）：记录到本地审计日志，不重试，跳过该行
   - HTTP 5xx（服务错误）：记录，可选重试（指数退避，最多 3 次）
   - 网络超时：视为 5xx，重试
   - 所有错误都记录到 stderr 和本地日志，任务继续处理下一行（不中断）

7. **批量操作优化**
   - 支持 `--batch-size 100` 参数，控制单次 API 调用数量（飞书可能有 rate limit）
   - 默认 batch_size = 50
   - 批次间延迟 1 秒，避免触发 rate limit

8. **Dry-run 模式**
   - 支持 `--dry-run` 标志，生成审计日志但不调用 Feishu API
   - Dry-run 输出应与实际运行相同（便于提前检查）

## 验收标准

1. ✅ 从 match_candidates 表成功读取所有候选（无 SQL 错误）
2. ✅ 为每个候选生成正确的 `content_update_id`（公式正确，不重复）
3. ✅ 去重检查有效：重复运行同一批候选，不产生重复行
4. ✅ 人工字段保护有效：更新已有候选时，不覆盖 review_status / batch_id / fulfillment_status
5. ✅ 本地审计日志记录完整，每行包括时间戳、操作、结果、错误原因
6. ✅ Feishu API 调用返回的 record_id 正确记录到审计日志
7. ✅ Dry-run 模式下，不修改飞书数据，输出日志与实际运行一致
8. ✅ 错误处理：网络错误时不中断，继续处理下一行
9. ✅ 全部单元测试通过

## 测试要求

### 单元测试（`tests/test_recommendation_writer.py`）

1. **content_update_id 生成**
   - 入参：match_candidates 行（is_in_baseline=False, match_confidence='high'）
   - 预期：content_update_id = "123#discovery"
   - Case：discovery / existing / pending_review 三种类型各测一条

2. **去重检查逻辑**
   - 场景 A：飞书中无该 content_update_id
     - 预期：返回 "insert"，应调用 insert API
   - 场景 B：飞书中有，数据完全相同
     - 预期：返回 "skip"，不调用 API
   - 场景 C：飞书中有，hot_score 更新
     - 预期：返回 "update"，应调用 update API

3. **人工字段保护**
   - 入参：本地 match_candidates 行（hot_score=75, reason="..."）
   - 入参：飞书已有行（review_status="已审", batch_id="B001", fulfillment_status="已补"）
   - 执行 update
   - 预期：更新 hot_score, reason，但保留 review_status, batch_id, fulfillment_status 原值

4. **Dry-run 模式**
   - 入参：20 条候选 + dry_run=True
   - 预期：返回操作日志，无 API 调用，本地审计文件已生成
   - 对比：日志与 dry_run=False 的日志结构相同（除了 HTTP response 外）

5. **错误处理**
   - 网络超时模拟：Feishu API 返回 500
   - 预期：记录错误，继续下一行，最后汇报"成功 19，失败 1"

6. **批量操作**
   - 入参：100 条候选 + batch_size=10
   - 预期：10 个批次，每个批次间有 1 秒延迟，所有都成功写入

### 回归测试

- P1-D 和 P1-E 测试仍通过

## 验证命令

```bash
# Dry-run 模式：模拟写入，生成审计日志
PYTHONPATH=src python -c "
from movietrace.feishu.recommendation_writer import write_recommendations
write_recommendations(dry_run=True, batch_size=50)
print('✓ Dry-run completed')
"

# 验证审计日志格式
PYTHONPATH=src python -c "
import json
with open('source_records/2026-05-11.jsonl', 'r') as f:
    for line in f:
        record = json.loads(line)
        assert 'timestamp' in record, 'Missing timestamp'
        assert 'action' in record, 'Missing action'
        assert 'content_update_id' in record, 'Missing content_update_id'
        print(f'✓ {record[\"action\"]}: {record[\"content_update_id\"]}')
"

# 单元测试
PYTHONPATH=src python -m pytest tests/test_recommendation_writer.py -v

# 全量集成验证
PYTHONPATH=src python -m pytest tests/test_recommendation_writer.py tests/test_baseline_matching.py tests/test_daily_report.py -v
```

## 风险点

1. **飞书 API 认证失败**
   - 预期：`/tmp/movietrace_phase0_secrets.json` 包含有效的 `feishu.access_token`
   - 风险：token 过期或无效，API 调用返回 401 Unauthorized
   - 缓解：任务前检查 token 有效性；失败则报错并记录，不继续写入

2. **飞书推荐表 schema 不一致**
   - 预期：飞书表包含 `content_update_id`, `review_status`, `batch_id`, `fulfillment_status` 等字段
   - 风险：如飞书表没有这些字段，导致查询或写入失败
   - 缓解：**任务执行前，与飞书表对齐 schema**；任务包中标注"前置条件：验证飞书表有以下字段..."

3. **去重索引性能**
   - 预期：Feishu 按 `content_update_id` 查询返回 0 或 1 行
   - 风险：如飞书表很大（>10万行），查询变慢或超时
   - 缓解：与飞书团队确认 `content_update_id` 上建立了索引；任务包中标注"查询耗时预期"

4. **人工字段同步延迟**
   - 预期：P1-F 读飞书时，`review_status` 等字段已被人工填充
   - 风险：如人工还没来得及填，P1-F 会读到 NULL，之后人工填充无法再更新（因为 P1-F 保护了这三个字段）
   - 缓解：工作流中说明"P1-F 执行后，人工再填充三个字段；不要先手动填，再运行 P1-F"；或者任务支持 `--sync-human-fields` 从飞书读取后再写入

5. **content_update_id 冲突**
   - 预期：同一 canonical_item_id 在不同日期的 discovery，应有不同的 content_update_id（加时间戳）
   - 风险：如 content_update_id 仅用 canonical_item_id，重复发现会被认为去重
   - 缓解：确认 content_update_id 规则是否需要加时间戳；如需要，修改公式为 `f"{canonical_item_id}#{update_type}#{snapshot_date}"`

6. **并发修改**
   - 预期：单进程运行 P1-F，飞书中无其他并发修改
   - 风险：如多个 Agent 同时写飞书，可能产生冲突或重复
   - 缓解：任务说明"同一时间仅运行一个 P1-F 实例"；考虑加分布式锁（低优先级）

## 完成后输出要求

按 [`docs/workflow/report-format.md`](../workflow/report-format.md) 格式汇报。

**汇报要点：**
- 成功写入飞书的候选数（新增/更新各多少）
- 去重跳过的候选数
- 错误处理：网络错误数、API 验证错误数
- 本地审计日志文件路径和样本内容
- 人工字段保护验证：更新 1 条已有行，确认三个字段未被覆盖
- Dry-run 与实际运行的日志对比
- 任何飞书 schema 对齐的调整或遗留问题
