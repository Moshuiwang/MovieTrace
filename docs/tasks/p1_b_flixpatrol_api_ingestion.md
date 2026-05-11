# 任务包：P1-B FlixPatrol API 数据接入 + DB 存储

**任务包版本：** v1
**创建日期：** 2026-05-11
**预计完成：** 2026-05-12（0.5 - 1 天）

---

## 任务名称

P1-B：FlixPatrol 付费 API（$9.99/月）数据接入 + DB 存储

## 任务类型

`feat` — 新增功能（产品代码）

## 当前阶段

Phase 1（V1 MVP 开发）

## 执行环境

- **分支：** `main`（当前 working tree，不开 git worktree）
- **工作目录：** `/home/ubuntu/MovieTrace`

## 来源任务

- SUP-G 验证通过（`81f6f25`），确认 API 路径可行
- ADR-0006：P1-B 数据源从 HTML 切换到 API
- ADR-0003：FlixPatrol 作为 V1 真实平台热度源（核心决策仍有效）
- P1-C 依赖本任务的输出（平台热度数据用于 hot_score 评分）

## 目标

**实现 FlixPatrol API 客户端，每日拉取 6 平台 × 2 内容类型的 Top 10 数据，存入 SQLite，供 P1-C 评分使用。**

## 非目标

- ❌ 不实现 hot_score 评分（那是 P1-C）
- ❌ 不与 TMDb/Trakt/OMDb 做实体匹配（P1-C）
- ❌ 不写 CLI 命令（P1-G）
- ❌ 不生成日报或写入飞书（P1-E、P1-F）
- ❌ 不修改 `src/movietrace/sources/flixpatrol.py`（HTML 解析器保留不动）
- ❌ 不引入新 Python 依赖（优先 stdlib `urllib`；SUP-G 已证明可行）

## 允许修改范围

**新增文件：**

- `src/movietrace/sources/flixpatrol_api.py` — API 客户端
- `tests/test_flixpatrol_api.py` — API 客户端单元测试
- `src/movietrace/db/migrations/002_flixpatrol_top10.sql` — 新表 DDL

**修改文件：**

- `src/movietrace/db/schema.py` — 注册 migration 002，更新 SCHEMA_VERSION
- `.env.example`（如存在）— 说明 `FLIXPATROL_API_KEY` 配置方式

## 禁止修改范围

- 🚫 `src/movietrace/sources/flixpatrol.py`（HTML 解析器，保留不动）
- 🚫 `data/movietrace.db`（由 migration 自动创建/升级，不手动改）
- 🚫 `docs/decisions/0003-*.md`、`docs/decisions/0006-*.md`（ADR）
- 🚫 `STATE.md`、`SCOPE.md`、`AGENTS.md`、`CLAUDE.md`

## 相关上下文

**SUP-G 已验证的技术事实（来自 `reports/sup_g_flixpatrol_api_validation.md`）：**

| 项目 | 值 |
|------|-----|
| API Base URL | `https://api.flixpatrol.com/v2` |
| Endpoint | `GET /top10s` |
| Auth | `Authorization: Basic base64(<api_key>:)` |
| Response 格式 | JSON:API 风格复合文档 |
| Item 解包路径 | `response["data"][i]["data"]` |
| TMDb ID 路径 | `item["movie"]["data"]["tmdbId"]` |
| IMDB ID 路径 | `item["movie"]["data"]["imdbId"]` |
| Title 路径 | `item["movie"]["data"]["title"]` |
| 6 平台 Company ID | 见 SUP-G 脚本 `ENDPOINTS` 常量 |
| US Country ID | `cnt_iMUHNbZvnNHK5YdhgwtOoP4u` |
| Type 枚举 | 2=Movies, 3=TV Shows |
| 默认返回量 | 300 items（最早 30 天），需 `date[from][gte]` 过滤最新 |
| Apple TV+ 延迟 | 28-34s，需 60s timeout |

**DB 环境：**

- SQLite 位于 `data/movietrace.db`
- 现有 schema 见 `src/movietrace/db/schema.py`（v1）
- `api_cache` 表已存在，可用于缓存 API 响应（source=`flixpatrol`）

## 输入

### API key

- 位置：`/tmp/movietrace_phase0_secrets.json` → `flixpatrol.api_key`
- 客户端启动时读取，缺失则 raise 明确错误
- key 不在日志/DB/文件中明文出现

### 目标 endpoint 清单（12 个组合/天）

| # | 平台 | Company ID | 地区 | Type |
|---|------|-----------|------|------|
| 1 | Netflix | `cmp_IA6TdMqwf6kuyQvxo9bJ4nKX` | US | 2 (Movies) |
| 2 | Netflix | `cmp_IA6TdMqwf6kuyQvxo9bJ4nKX` | US | 3 (TV Shows) |
| 3 | Prime Video | `cmp_qypvowjqFhEIpCc0HlQ6VoYk` | US | 2 |
| 4 | Prime Video | `cmp_qypvowjqFhEIpCc0HlQ6VoYk` | US | 3 |
| 5 | Disney+ | `cmp_oGtsgdpOrjIu3XzTEnWPt87Y` | US | 2 |
| 6 | Disney+ | `cmp_oGtsgdpOrjIu3XzTEnWPt87Y` | US | 3 |
| 7 | Apple TV+ | `cmp_VvmYc7OphiUds0Hgjbz5MESn` | US | 2 |
| 8 | Apple TV+ | `cmp_VvmYc7OphiUds0Hgjbz5MESn` | US | 3 |
| 9 | HBO Max | `cmp_6UhCvnTeRkgZUtcNGslX9bJL` | US | 2 |
| 10 | HBO Max | `cmp_6UhCvnTeRkgZUtcNGslX9bJL` | US | 3 |
| 11 | Hulu | `cmp_9iwHIMYOCvD6zprSPoHgTJau` | US | 2 |
| 12 | Hulu | `cmp_9iwHIMYOCvD6zprSPoHgTJau` | US | 3 |

### 日期参数

- `date[type][eq]=1`（Day）
- `date[from][gte]=YYYY-MM-DD`（获取从指定日期起的数据）
- 日常运行取最近 2 天，bootstrap（180 天追赶）取更长范围

## 输出

### 1. API 客户端：`src/movietrace/sources/flixpatrol_api.py`

**公共接口（建议）：**

```python
class FlixPatrolClient:
    def __init__(self, api_key: str, timeout: int = 60): ...
    def fetch_top10(
        self, company: str, country: str, content_type: int,
        date_from: str | None = None, date_to: str | None = None
    ) -> list[dict]: ...
    def fetch_all_platforms(
        self, date_from: str | None = None
    ) -> dict[str, list[dict]]: ...

def load_api_key(secrets_path: str = SECRETS_PATH) -> str: ...
def unwrap_item(raw_item: dict) -> dict: ...
```

**`fetch_top10` 返回的 item dict（已解包）：**

```python
{
    "fp_id": "tpt_ye7U2UzROTNVv5JZ7Hu4m8MY",
    "title": "Spenser Confidential",
    "content_type": "movie",        # 2→"movie", 3→"tv_show"
    "ranking": 1,
    "ranking_last": 0,
    "value": 10,                    # FlixPatrol 热度分
    "days_total": None,
    "platform": "netflix",
    "country": "united-states",
    "snapshot_date": "2020-03-20",
    "tmdb_id": 581600,
    "imdb_id": 8629748,
    "updated_at": "2022-07-27T16:55:02",
}
```

### 2. DB migration：`src/movietrace/db/migrations/002_flixpatrol_top10.sql`

```sql
create table if not exists flixpatrol_top10 (
    id integer primary key autoincrement,
    fp_id text not null,                  -- FlixPatrol internal top10s ID
    title text not null,
    content_type text not null,           -- 'movie' | 'tv_show'
    platform text not null,               -- 'netflix' | 'prime-video' | ...
    country text not null,                -- 'united-states'
    snapshot_date text not null,          -- YYYY-MM-DD
    ranking integer not null check (ranking between 1 and 10),
    ranking_last integer,
    value integer,
    days_total integer,
    tmdb_id integer,
    imdb_id integer,
    raw_payload_json text not null,       -- original item JSON
    collected_at text not null default current_timestamp
);

create unique index if not exists ux_fp_top10_dedup
    on flixpatrol_top10(fp_id, snapshot_date);

create index if not exists idx_fp_top10_date
    on flixpatrol_top10(snapshot_date);

create index if not exists idx_fp_top10_tmdb
    on flixpatrol_top10(tmdb_id) where tmdb_id is not null;
```

### 3. 单元测试：`tests/test_flixpatrol_api.py`

- `unwrap_item` 复合文档解包测试（含真实 fixture）
- 字段映射测试（API type int → content_type str）
- `load_api_key` 成功/缺失/格式错误
- URL 构造参数正确性
- 去重逻辑测试（同 fp_id + 同 snapshot_date 不重复入库）
- 不强制网络测试

### 4. 更新 `src/movietrace/db/schema.py`

- 新增 `apply_migration_002(conn)` 函数
- `initialize_database()` 在 v1 schema 之后执行 migration 002
- `SCHEMA_VERSION` 更新为 2

## 具体要求

### R1: API 调用规范

- 间隔 ≥ 1 秒（保守，远低于 1,000/月配额但尊重服务器）
- 60s timeout（适配 Apple TV+ 慢端点）
- User-Agent: `MovieTraceBot/0.1`
- 401/403 → 立即 raise，不继续调用
- 429 → 退避 5s 重试 1 次，仍 429 则 skip 并记录
- 5xx / 网络超时 → 记录后继续下一 endpoint
- 每个 endpoint 的响应保存到 `api_cache` 表（source=`flixpatrol`, cache_key=URL）

### R2: 数据质量

- ranking 必须在 1-10 范围
- 同一天同一平台同一类型的同一排名位置的 item 不应重复入库（唯一约束）
- `content_type` 从 API 的 int（2/3）映射为 str（`movie`/`tv_show`）
- `platform` 从 company ID 映射为可读标识（如 `cmp_IA6TdMqw...` → `netflix`）
- `tmdb_id` 为 None 时记录 WARNING 但不阻塞（SUP-G 中 100% 有值，但防御性处理）

### R3: 日常运行 vs Bootstrap

客户端本身不区分模式，由调用方传入 `date_from` 决定：
- 日常模式：`date_from` = 昨天（YYYY-MM-DD），拿最近 1-2 天
- Bootstrap 模式（180 天追赶）：`date_from` = 180 天前，循环拉取
- 两种模式在 P1-G CLI 命令中区分，本任务只保证客户端支持参数

### R4: 不污染已有代码

- 新增文件与现有 HTML parser（`flixpatrol.py`）完全独立
- 不修改 `canonical_items`、`baseline_items` 等已有表
- `source_records` 表可记录本客户端的运行记录（source=`flixpatrol_api`），但不强制

### R5: 日志

- 使用 `logging` 模块，logger name = `movietrace.sources.flixpatrol_api`
- INFO：每次 API 调用（platform、status、items、elapsed）
- WARNING：字段缺失、tmdb_id 为 None、重试
- ERROR：API 失败（非 401/403）
- CRITICAL：认证失败（401/403）
- API key 脱敏后再写入日志

## 验收标准

### 必须达成

1. ✅ `FlixPatrolClient.fetch_all_platforms()` 返回 12 个组合的数据（6 平台 × 2 类型）
2. ✅ 返回的每个 item 含所有 P1-C 必须字段（title、content_type、ranking、platform、snapshot_date、tmdb_id）
3. ✅ Migration 002 可执行，`flixpatrol_top10` 表创建成功
4. ✅ 同一 fp_id + snapshot_date 不重复入库
5. ✅ 单元测试 `pytest tests/test_flixpatrol_api.py -v` 全部通过
6. ✅ 现有测试 `pytest tests/ -v` 无回归失败
7. ✅ 401/403 时 raise 明确异常（不静默跳过）

### 期望达成

8. ✅ 12/12 endpoint 全返回 200
9. ✅ TMDb ID 覆盖率 ≥ 95%
10. ✅ 每次完整拉取 ≤ 120s（含 Apple TV+ 34s）

### 不算失败但需记录

11. Apple TV+ 超时导致部分数据缺失
12. 个别 item 的 `days_total` 或 `tmdb_id` 为 None

## 验证命令

```bash
# 1. 单元测试
PYTHONPATH=src python -m pytest tests/test_flixpatrol_api.py -v

# 2. 全量回归
PYTHONPATH=src python -m pytest tests/ -v

# 3. DB migration 测试
PYTHONPATH=src python -c "
from movietrace.db.schema import initialize_database
initialize_database('data/movietrace.db')
# 检查 flixpatrol_top10 表存在
import sqlite3
conn = sqlite3.connect('data/movietrace.db')
tables = conn.execute(\"select name from sqlite_master where type='table'\").fetchall()
assert ('flixpatrol_top10',) in tables, 'Migration 002 failed'
print('OK: flixpatrol_top10 table exists')
conn.close()
"

# 4. 干跑（secrets 加载 + 客户端初始化，不发请求）
PYTHONPATH=src python -c "
from movietrace.sources.flixpatrol_api import FlixPatrolClient, load_api_key
key = load_api_key()
client = FlixPatrolClient(key)
print(f'Client initialized: timeout={client.timeout}s')
print('DRY RUN PASSED')
"

# 5. 实际 API 拉取（需 API key）
PYTHONPATH=src python -c "
from movietrace.sources.flixpatrol_api import FlixPatrolClient, load_api_key
client = FlixPatrolClient(load_api_key())
results = client.fetch_all_platforms(date_from='2026-05-10')
for platform_key, items in results.items():
    print(f'{platform_key}: {len(items)} items')
"
```

## 测试要求

| 类型 | 文件 | 说明 |
|------|------|------|
| 单元测试 | `tests/test_flixpatrol_api.py` | unwrap_item、字段映射、URL 构造、去重逻辑 |
| fixture | 测试中用硬编码 JSON fixture（来自 SUP-G 响应采样） | 不依赖网络 |
| 集成测试 | 验证命令 #5（手动运行） | 真 API 调用，确认 12 endpoint 可达 |

## 风险点

1. **Apple TV+ 慢响应**
   - 概率：高（SUP-G 两次验证均 >28s）
   - 影响：完整拉取时间延长
   - 缓解：60s timeout + 重试 + 独立日志；如持续超时则该平台数据缺失但不阻塞其他 5 平台

2. **API 配额不足**
   - 概率：低（12 calls/天 × 30 = 360/月，占 36%）
   - 影响：月末可能触发 429
   - 缓解：Bootstrap 模式（180 天）第一天消耗大（~180 calls），之后稳定

3. **TMDb ID 缺失导致 P1-C 匹配断裂**
   - 概率：极低（SUP-G 样本 300/300 有值）
   - 影响：该 item 无法与 canonical_items 链接
   - 缓解：记录 WARNING；P1-C 以 tmdb_id 为主、title+year 为 fallback

4. **API schema 变更**
   - 概率：低
   - 影响：解包逻辑失败
   - 缓解：`raw_payload_json` 保留原始数据，可回溯

5. **DB migration 冲突**
   - 概率：低（当前 SCHEMA_VERSION=1，无并发写入）
   - 影响：migration 执行失败
   - 缓解：migration 文件独立，幂等（`create table if not exists`）

## 完成后输出要求

按 [`docs/workflow/report-format.md`](../workflow/report-format.md) 汇报，重点：
- 12 endpoint 各自返回状态和条目数
- TMDb ID 覆盖率
- DB migration 执行结果
- 给 P1-C 的数据接口说明（表结构 + 字段语义）
