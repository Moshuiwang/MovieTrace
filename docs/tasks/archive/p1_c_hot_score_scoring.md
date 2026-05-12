# 任务包：P1-C hot_score 评分 + 多源候选合并

**任务包版本：** v1
**创建日期：** 2026-05-11
**预计完成：** TBD（依赖 P1-B 完成）

---

## 任务名称

P1-C：实现 V1 hot_score 综合评分公式（9 因素加权）+ 多源候选按 external_id 合并去重

## 任务类型

`feat` — 新增功能

## 当前阶段

Phase 1（V1 MVP 开发）

## 执行环境

- **分支：** `main`（当前 working tree，不开 git worktree）
- **工作目录：** `/home/ubuntu/MovieTrace`
- **commit 策略：** 完成后准备 commit，不要 push

## 来源任务

- [`docs/next_steps_plan.md`](../next_steps_plan.md) § 5.2 P1-C
- [`docs/requirements.md`](../requirements.md) § 10.2（hot_score 9 因素公式）
- [`docs/requirements.md`](../requirements.md) § 10.3（priority 映射 P0/P1/P2/P3）
- [`docs/requirements.md`](../requirements.md) § 11.1（R4 内容更新去重）
- **前置：** P1-B 必须完成（`flixpatrol_top10` 表存在并有数据）

## 目标

读取 P1-B 输出的 `flixpatrol_top10` + 现有 `canonical_items` / `external_ids`，按 9 因素加权公式计算 `hot_score`（0-100），按 `external_id` 合并多源候选，写入新表 `candidates`，供 P1-D 基线匹配使用。

## 非目标

- ❌ 不做基线匹配标记（那是 P1-D）
- ❌ 不生成日报或写飞书（P1-E、P1-F）
- ❌ 不实现 V2 因素（LLM、Rotten Tomatoes、Metacritic）
- ❌ 不调用 TMDb / Trakt / OMDb API（信号从已有缓存或 `canonical_items` 读，不发新请求）
- ❌ 不修改 `entity_matching.py` 或 `canonical_promotion.py`
- ❌ 不引入新依赖（YAML 解析用 `pyyaml`，项目已有则用，无则用 stdlib `tomllib` 替代）

## 允许修改范围

**新增文件：**

- `src/movietrace/pipeline/scoring.py`
- `src/movietrace/pipeline/discovery.py`
- `src/movietrace/db/migrations/003_candidates.sql`
- `tests/test_scoring.py`
- `tests/test_discovery.py`
- `config/scoring_weights.yaml`

**修改文件：**

- `src/movietrace/db/schema.py`（注册 migration 003，`SCHEMA_VERSION` → 3）

## 禁止修改范围

- 🚫 `src/movietrace/sources/`（不调外部 API）
- 🚫 `src/movietrace/sources/flixpatrol_api.py`（P1-B 产物，本任务只读）
- 🚫 `src/movietrace/pipeline/entity_matching.py`、`canonical_promotion.py`
- 🚫 `flixpatrol_top10`、`canonical_items`、`external_ids`、`baseline_items` 等已有表 schema
- 🚫 `STATE.md`、`SCOPE.md`、`AGENTS.md`、`CLAUDE.md`、`docs/decisions/`

## 相关上下文

### hot_score 公式（来自 [`docs/requirements.md`](../requirements.md) § 10.2）

| 因素 | 权重 | 取值方式 |
|------|------|----------|
| **FlixPatrol 平台热度** | **0.30** | 排名归一（1→100、10→10）+ 在榜天数加成 |
| TMDb 社区热度 | 0.15 | popularity 归一到 0-100 |
| Trakt 社区热度 | 0.10 | watcher / play count 归一 |
| TMDb 评分 | 0.10 | vote_average × log10(vote_count + 1) 归一 |
| IMDb 评分 | 0.10 | imdb_rating × log10(imdb_votes + 1) 归一 |
| 平台来源权重 | 0.10 | Netflix/Prime 1.0，Disney 0.9，HBO 0.85，Apple/Hulu 0.8 |
| 内容类型 | 0.05 | tv_show > movie（剧集 100、电影 80） |
| 新鲜度 | 0.05 | 90 天内上线 100，180 天内 50，更老 0 |
| 语言相关性 | 0.05 | 英文 100，非英文但 FlixPatrol 高排名 80，其他 50 |

每个因素返回 0-100，最终 `hot_score = Σ(因素得分 × 权重)`。

### priority 映射（[`docs/requirements.md`](../requirements.md) § 10.3）

| priority | hot_score 范围 |
|----------|---------------|
| P0 | ≥ 85 |
| P1 | 70 - 84 |
| P2 | 50 - 69 |
| P3 | < 50 |

### 去重规则（[`docs/requirements.md`](../requirements.md) § 11.1 R4）

按 `external_id` 合并：`tmdb_id` 优先，`imdb_id` 次之。同 `canonical_item_id + snapshot_date` 视为同一 candidate。

## 输入

**数据库（只读）：**

- `flixpatrol_top10`（P1-B，含 tmdb_id、ranking、value、days_total、platform、snapshot_date）
- `canonical_items`（Phase 0）
- `external_ids`（Phase 0，含 tmdb_id、imdb_id）
- `baseline_items`（Phase 0）
- `api_cache`（含 TMDb / Trakt / OMDb 历史响应，按 cache_key 读，不发新请求）

**配置：** `config/scoring_weights.yaml`（首次启动时如不存在，由代码生成默认值）

## 输出

### 1. `config/scoring_weights.yaml`

所有数值可调；不写硬编码。示例结构：

```yaml
weights:
  flixpatrol: 0.30
  tmdb_popularity: 0.15
  trakt: 0.10
  tmdb_rating: 0.10
  imdb_rating: 0.10
  platform_weight: 0.10
  content_type: 0.05
  freshness: 0.05
  language: 0.05

priority_thresholds:
  P0: 85
  P1: 70
  P2: 50

platform_weight:
  netflix: 1.0
  prime-video: 1.0
  disney: 0.9
  hbo: 0.85
  apple-tv: 0.8
  hulu: 0.8

freshness:
  full_score_days: 90
  half_score_days: 180
```

### 2. `src/movietrace/pipeline/scoring.py`

```python
def compute_flixpatrol_score(item: dict) -> float: ...
def compute_tmdb_popularity_score(canonical_id: int) -> float: ...
def compute_trakt_score(canonical_id: int) -> float: ...
def compute_tmdb_rating_score(canonical_id: int) -> float: ...
def compute_imdb_rating_score(canonical_id: int) -> float: ...
def compute_platform_weight_score(platform: str, cfg: dict) -> float: ...
def compute_content_type_score(content_type: str) -> float: ...
def compute_freshness_score(release_date: str | None, cfg: dict) -> float: ...
def compute_language_score(original_language: str | None, fp_top: bool) -> float: ...

def compute_hot_score(candidate: dict, weights: dict) -> tuple[float, dict]:
    """返回 (hot_score, breakdown_dict)"""

def map_priority(hot_score: float, thresholds: dict) -> str: ...
```

### 3. `src/movietrace/pipeline/discovery.py`

```python
def collect_flixpatrol_candidates(date_from: str | None = None) -> list[dict]: ...
def merge_by_external_id(items: list[dict]) -> list[dict]: ...
def assign_discovery_source(candidate: dict, in_baseline: bool) -> str:
    """返回 'new_release' | 'global_hot' | 'both'"""

def build_reason_text(breakdown: dict, candidate: dict) -> str: ...

def write_candidates(candidates: list[dict], conn) -> int: ...

def run_discovery(
    date_from: str | None = None,
    dry_run: bool = False,
    weights_path: str = "config/scoring_weights.yaml",
) -> dict:
    """端到端入口；dry_run=True 不写库，返回 list 供审查"""
```

### 4. DB migration `src/movietrace/db/migrations/003_candidates.sql`

```sql
create table if not exists candidates (
    id integer primary key autoincrement,
    canonical_item_id integer,                       -- nullable fk
    tmdb_id integer,
    imdb_id text,
    title text not null,
    content_type text not null check (content_type in ('movie', 'tv_show')),
    hot_score real not null check (hot_score between 0 and 100),
    priority text not null check (priority in ('P0', 'P1', 'P2', 'P3')),
    discovery_source text not null check (discovery_source in ('new_release', 'global_hot', 'both')),
    score_breakdown_json text not null,
    reason_text text,
    snapshot_date text not null,
    computed_at text not null default current_timestamp,
    unique (canonical_item_id, snapshot_date)
);

create index if not exists idx_candidates_priority on candidates(priority);
create index if not exists idx_candidates_score on candidates(hot_score desc);
create index if not exists idx_candidates_snapshot on candidates(snapshot_date);
```

### 5. 单元测试

- `tests/test_scoring.py`：每个因素函数（含边界值）+ `compute_hot_score` 加权 + `map_priority` 4 档（85/70/50 边界）
- `tests/test_discovery.py`：`merge_by_external_id` tmdb_id 优先 + `assign_discovery_source` 三态 + `run_discovery(dry_run=True)` 不写库

## 具体要求

### R1: 评分透明可解释

每个 candidate 必须含 `score_breakdown_json`，记录 9 个因素得分。`reason_text` 是人类可读字符串（参考 requirements § 10.3 示例：「进入 FlixPatrol Netflix Top 10（排名 #3）。TMDb popularity 95.6。IMDb 8.2/1.2万投票。」）。

### R2: 配置驱动

所有权重 + priority 阈值 + 平台权重 + freshness 天数从 `config/scoring_weights.yaml` 读取，不硬编码。配置文件缺失时生成默认值并写回。

### R3: 去重规则

- 同 `tmdb_id`：合并；FlixPatrol 信号在合并时优先（如取最高 ranking）
- 同 `imdb_id` 但 `tmdb_id` 不同：保留两条 + WARNING 日志（罕见）
- 同 `canonical_item_id + snapshot_date`：DB 唯一约束，不重复写

### R4: discovery_source 三态

- `new_release`：candidate 不在 baseline（`is_in_baseline` 由 P1-D 标记，本任务用 `canonical_item_id` 是否来源 baseline 作代理）
- `global_hot`：在 baseline，且 FlixPatrol 排名 ≤ 5 或在榜 ≥ 7 天
- `both`：不在 baseline 且 FlixPatrol 排名 ≤ 5（强信号 + 新）

最终标记以 P1-D 为准；本任务的 `discovery_source` 是初步分类。

### R5: dry_run 模式

`run_discovery(dry_run=True)` 不写 DB，返回 `{"candidates": [...], "stats": {...}}`，供 P1-G CLI 调用。

### R6: 信号缺失容忍

某 candidate 缺 Trakt 或 OMDb 信号时，对应因素得分为 0，候选不消失。`breakdown_dict` 中标注 `tmdb_popularity_score: null`（区分"0 分"和"无数据"）。

## 验收标准

### 必须达成

1. ✅ `compute_hot_score(...)` 对同一输入返回稳定值
2. ✅ `map_priority` 在 85/70/50 边界值取上界（≥85 → P0、≥70 → P1、≥50 → P2、其他 P3）
3. ✅ `run_discovery()` 端到端跑通，写入 `candidates` 表
4. ✅ 同 `canonical_item_id + snapshot_date` 不重复入库（约束生效）
5. ✅ `score_breakdown_json` 含全部 9 因素字段
6. ✅ `pytest tests/test_scoring.py tests/test_discovery.py -v` 全部通过
7. ✅ 现有测试 `pytest tests/ -v` 无回归
8. ✅ Migration 003 在空库 / 现有库都能幂等执行

### 期望达成

9. ✅ `run_discovery(dry_run=True)` 输出 ≥ 50 candidates（前提：P1-B 已拉至少 1 天数据）
10. ✅ P0 + P1 候选 ≤ 100（避免人工审核过载）
11. ✅ FlixPatrol 缺失时 candidate 不消失，只是 score 降级

## 验证命令

```bash
# 1. 单元测试
PYTHONPATH=src python -m pytest tests/test_scoring.py tests/test_discovery.py -v

# 2. 全量回归
PYTHONPATH=src python -m pytest tests/ -v

# 3. Migration 003
PYTHONPATH=src python -c "
from movietrace.db.schema import initialize_database
initialize_database('data/movietrace.db')
import sqlite3
conn = sqlite3.connect('data/movietrace.db')
assert ('candidates',) in conn.execute(\"select name from sqlite_master where type='table'\").fetchall()
print('OK: candidates table exists')
"

# 4. 端到端 dry-run
PYTHONPATH=src python -c "
from movietrace.pipeline.discovery import run_discovery
result = run_discovery(dry_run=True)
print(f'Candidates: {len(result[\"candidates\"])}')
print(f'P0: {sum(1 for c in result[\"candidates\"] if c[\"priority\"]==\"P0\")}')
print(f'P1: {sum(1 for c in result[\"candidates\"] if c[\"priority\"]==\"P1\")}')
"

# 5. 实际写库（先 dry-run 确认数据合理，再正式写）
PYTHONPATH=src python -c "
from movietrace.pipeline.discovery import run_discovery
result = run_discovery(dry_run=False)
print(result['stats'])
"
```

## 风险点

1. **`flixpatrol_top10` 字段名与 P1-B 实际产出不一致**
   - 缓解：实施前先 `pragma table_info(flixpatrol_top10)` 核对 schema

2. **TMDb / Trakt 信号 stale**（缓存来自 Phase 0）
   - 缓解：本任务不刷新外部信号；在 stats 中记录"信号最新时间"作为透明信息；P1-G CLI 后续可加 `refresh-signals`

3. **权重默认值不优**（requirements § 10.2 是初版）
   - 缓解：配置文件可调；P1-H 集成测试时再调整

4. **`discovery_source` 划分需依赖 baseline，与 P1-D 有循环关系**
   - 缓解：本任务用 `canonical_items.source = 'feishu'` 作代理；P1-D 写 `match_candidates.is_in_baseline` 后是最终事实

5. **配额：FlixPatrol 当天某平台缺失**（如 Apple TV+ 超时）
   - 缓解：评分按当前可见数据计算，candidate 不消失

## 完成后输出要求

按 [`docs/workflow/report-format.md`](../workflow/report-format.md) 汇报，重点：

- candidates 总数 + priority 分布
- P0 候选 5 条示例（含 hot_score、breakdown、reason_text）
- 哪些信号缺失（Trakt 不全 / IMDb votes 为 0 等）
- 给 P1-D 的输入接口说明（candidates 表字段 + 调用方式）
