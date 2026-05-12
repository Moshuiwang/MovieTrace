# SUP-C FlixPatrol 匹配率验证 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 验证 FlixPatrol 解析出的 117 个唯一标题能否通过 TMDb Search API 匹配到 TMDb ID，给出匹配率统计，回答"FlixPatrol 内容能匹配到 TMDb ID 的比例是否 ≥ 80%"。

**Architecture:** 独立脚本 `scripts/sup_c_flixpatrol_matching.py`，读取已有的 `data/flixpatrol_parsed_items.json`（130 条），对 117 个唯一标题调用 TMDb Search API，复用已有的 `parse_title()` + `_title_similarity()` 逻辑判断匹配置信度，不写入数据库，结果输出到 `data/sup_c_match_results.json`，最终生成中文报告 `reports/flixpatrol_matching_report.md`。

**Tech Stack:** Python 3.12、`requests`（或 stdlib `urllib`）、`movietrace.pipeline.entity_matching`（复用已有逻辑）、TMDb Search API（`/search/multi`）、TMDB_BEARER_TOKEN 环境变量

---

## 背景上下文

- 项目目录：`/home/ubuntu/MovieTrace`
- 虚拟环境：`.venv/`，激活：`source .venv/bin/activate`
- 运行命令须加 `PYTHONPATH=src`
- FlixPatrol 解析结果：`data/flixpatrol_parsed_items.json`（130 条，117 个唯一标题）
- 已有匹配逻辑：`src/movietrace/pipeline/entity_matching.py`
  - `parse_title(title: str) -> ParsedTitle`：清洗标题，提取年份/季号
  - `_title_similarity(left: str, right: str) -> float`：0.0-1.0 字符串相似度
  - `ExternalSearchResult`：标准化搜索结果数据类
- 已有 TMDb 客户端：`src/movietrace/sources/tmdb.py`，`TmdbSearchClient.search()`
- API key：`TMDB_BEARER_TOKEN` 环境变量（用户运行时提供）
- **禁止修改**：`src/movietrace/pipeline/`、`src/movietrace/sources/tmdb.py`、`data/movietrace.db`、`tests/fixtures/`

## 文件结构

| 动作 | 路径 | 说明 |
|------|------|------|
| 新建 | `scripts/sup_c_flixpatrol_matching.py` | 匹配验证主脚本 |
| 新建 | `tests/test_sup_c_matching.py` | 单元测试（纯逻辑，无网络调用） |
| 运行时写入 | `data/sup_c_match_results.json` | 每条标题的匹配结果 JSON |
| 新建 | `reports/flixpatrol_matching_report.md` | 中文匹配率报告 |

---

## Task 1：实现匹配核心逻辑 + 单元测试

**Files:**
- Create: `scripts/sup_c_flixpatrol_matching.py`
- Create: `tests/test_sup_c_matching.py`

### 核心数据结构

```python
# scripts/sup_c_flixpatrol_matching.py 中使用的类型

@dataclass
class MatchResult:
    title: str                    # FlixPatrol 原始标题
    content_type: str             # "movie" / "show"
    platforms: list[str]          # 出现在哪些平台
    tmdb_id: str | None           # 匹配到的 TMDb ID（如有）
    tmdb_title: str | None        # TMDb 返回的标题
    tmdb_year: int | None         # TMDb 返回的年份
    similarity: float             # 标题相似度 0.0-1.0
    confidence: str               # "high" / "medium" / "low" / "no_match"
    match_reason: str             # 匹配原因说明
```

### 置信度规则

```python
def _classify_confidence(similarity: float, tmdb_year: int | None, flixpatrol_year: int | None) -> str:
    # high:   similarity >= 0.85
    # medium: similarity >= 0.60
    # low:    similarity >= 0.40
    # no_match: similarity < 0.40
    # 年份匹配加分：若两者均有年份且相差 <= 1 年，confidence 提升一档（low→medium，medium→high）
```

- [ ] **Step 1：写失败测试**

```bash
cat > tests/test_sup_c_matching.py << 'EOF'
"""单元测试：SUP-C 匹配逻辑（无网络调用）"""
from __future__ import annotations
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

from sup_c_flixpatrol_matching import (
    _classify_confidence,
    _deduplicate_flixpatrol_items,
    _select_best_tmdb_result,
)
from movietrace.pipeline.entity_matching import ExternalSearchResult


def _make_result(title: str, year: int | None = None, score: float = 1.0) -> ExternalSearchResult:
    return ExternalSearchResult(
        source="tmdb",
        external_id="123",
        title=title,
        media_type="movie",
        year=year,
        score=score,
    )


# ── _classify_confidence ─────────────────────────────────────────────────────

def test_high_confidence_above_85():
    assert _classify_confidence(0.90, None, None) == "high"

def test_medium_confidence_60_to_85():
    assert _classify_confidence(0.70, None, None) == "medium"

def test_low_confidence_40_to_60():
    assert _classify_confidence(0.50, None, None) == "low"

def test_no_match_below_40():
    assert _classify_confidence(0.30, None, None) == "no_match"

def test_year_match_upgrades_medium_to_high():
    # similarity=0.70 → medium，但年份匹配 → high
    assert _classify_confidence(0.70, 2024, 2024) == "high"

def test_year_match_upgrades_low_to_medium():
    assert _classify_confidence(0.50, 2023, 2024) == "medium"  # 相差1年也算

def test_year_mismatch_does_not_upgrade():
    assert _classify_confidence(0.70, 2020, 2024) == "medium"  # 相差4年，不升档

def test_missing_year_does_not_upgrade():
    assert _classify_confidence(0.70, None, 2024) == "medium"


# ── _deduplicate_flixpatrol_items ────────────────────────────────────────────

def test_dedup_merges_same_title_different_platforms():
    items = [
        {"title": "Swapped", "content_type": "movie", "platform": "netflix", "region": "global"},
        {"title": "Swapped", "content_type": "movie", "platform": "netflix", "region": "us"},
    ]
    deduped = _deduplicate_flixpatrol_items(items)
    assert len(deduped) == 1
    assert set(deduped[0]["platforms"]) == {"netflix"}

def test_dedup_keeps_different_titles_separate():
    items = [
        {"title": "Swapped", "content_type": "movie", "platform": "netflix", "region": "global"},
        {"title": "Apex",    "content_type": "movie", "platform": "netflix", "region": "global"},
    ]
    deduped = _deduplicate_flixpatrol_items(items)
    assert len(deduped) == 2

def test_dedup_collects_all_platforms():
    items = [
        {"title": "Send Help", "content_type": "movie", "platform": "disney",  "region": "world"},
        {"title": "Send Help", "content_type": "movie", "platform": "hulu",    "region": "us"},
    ]
    deduped = _deduplicate_flixpatrol_items(items)
    assert len(deduped) == 1
    assert set(deduped[0]["platforms"]) == {"disney", "hulu"}


# ── _select_best_tmdb_result ─────────────────────────────────────────────────

def test_select_best_picks_highest_similarity():
    results = [
        _make_result("Swapped", year=2024),
        _make_result("The Swap", year=2024),
    ]
    best, sim = _select_best_tmdb_result("Swapped", results)
    assert best.title == "Swapped"
    assert sim >= 0.99

def test_select_best_returns_none_on_empty():
    best, sim = _select_best_tmdb_result("Anything", [])
    assert best is None
    assert sim == 0.0

def test_select_best_exact_match_similarity_is_1():
    results = [_make_result("Squid Game")]
    best, sim = _select_best_tmdb_result("Squid Game", results)
    assert sim == 1.0
EOF
```

- [ ] **Step 2：运行测试，确认失败**

```bash
PYTHONPATH=src python -m pytest tests/test_sup_c_matching.py -v 2>&1 | head -30
```

预期：`ModuleNotFoundError` 或 `ImportError`（脚本尚未创建）

- [ ] **Step 3：创建主脚本骨架（只含被测函数，无网络调用）**

```python
# scripts/sup_c_flixpatrol_matching.py
from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# 添加 src/ 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from movietrace.pipeline.entity_matching import (
    ExternalSearchResult,
    parse_title,
    _title_similarity,
)
from movietrace.sources.tmdb import TmdbSearchClient, parse_tmdb_search_results

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
PARSED_ITEMS_FILE = PROJECT_ROOT / "data" / "flixpatrol_parsed_items.json"
RESULTS_FILE      = PROJECT_ROOT / "data" / "sup_c_match_results.json"
REPORTS_DIR       = PROJECT_ROOT / "reports"

REQUEST_INTERVAL = 1.0  # 秒，礼貌频率


@dataclass
class MatchResult:
    title: str
    content_type: str
    platforms: list[str]
    tmdb_id: str | None
    tmdb_title: str | None
    tmdb_year: int | None
    similarity: float
    confidence: str
    match_reason: str

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "content_type": self.content_type,
            "platforms": self.platforms,
            "tmdb_id": self.tmdb_id,
            "tmdb_title": self.tmdb_title,
            "tmdb_year": self.tmdb_year,
            "similarity": round(self.similarity, 4),
            "confidence": self.confidence,
            "match_reason": self.match_reason,
        }


def _classify_confidence(
    similarity: float,
    tmdb_year: int | None,
    flixpatrol_year: int | None,
) -> str:
    """置信度分类，年份匹配（相差 ≤ 1 年）可提升一档。"""
    if similarity >= 0.85:
        base = "high"
    elif similarity >= 0.60:
        base = "medium"
    elif similarity >= 0.40:
        base = "low"
    else:
        return "no_match"

    # 年份加分
    if tmdb_year is not None and flixpatrol_year is not None:
        if abs(tmdb_year - flixpatrol_year) <= 1:
            if base == "low":
                return "medium"
            if base == "medium":
                return "high"
    return base


def _deduplicate_flixpatrol_items(items: list[dict]) -> list[dict]:
    """合并同名条目，收集所有出现平台。"""
    seen: dict[str, dict] = {}
    for item in items:
        key = (item["title"], item["content_type"])
        if key not in seen:
            seen[key] = {
                "title": item["title"],
                "content_type": item["content_type"],
                "platforms": [item["platform"]],
            }
        else:
            p = item["platform"]
            if p not in seen[key]["platforms"]:
                seen[key]["platforms"].append(p)
    return list(seen.values())


def _select_best_tmdb_result(
    query: str,
    results: list[ExternalSearchResult],
) -> tuple[ExternalSearchResult | None, float]:
    """从 TMDb 搜索结果中选出与 query 相似度最高的条目。"""
    if not results:
        return None, 0.0
    best_result = None
    best_sim = 0.0
    for r in results:
        sim = _title_similarity(query, r.title)
        if sim > best_sim:
            best_sim = sim
            best_result = r
    return best_result, best_sim


def _match_single(
    item: dict,
    client: TmdbSearchClient,
) -> MatchResult:
    """对单个去重后的条目调用 TMDb 搜索并判断匹配置信度。"""
    title = item["title"]
    content_type = item["content_type"]
    platforms = item["platforms"]

    parsed = parse_title(title)
    try:
        from movietrace.pipeline.entity_matching import BaselineItem
        baseline = BaselineItem(
            id=0,
            title=title,
            content_type=content_type,
            content_granularity=None,
            season_number=None,
            episode_number=None,
            year=None,
            online_status=None,
        )
        results = client.search(parsed.query, baseline)
    except Exception as exc:
        logger.warning("TMDb search failed for %r: %s", title, exc)
        results = []

    best, sim = _select_best_tmdb_result(parsed.query, results)

    if best is None:
        confidence = "no_match"
        reason = "no_tmdb_results"
    else:
        confidence = _classify_confidence(sim, best.year, parsed.year)
        reason = f"similarity={sim:.2f}"
        if parsed.year and best.year:
            reason += f" year_delta={abs(parsed.year - best.year)}"

    return MatchResult(
        title=title,
        content_type=content_type,
        platforms=platforms,
        tmdb_id=best.external_id if best else None,
        tmdb_title=best.title if best else None,
        tmdb_year=best.year if best else None,
        similarity=sim,
        confidence=confidence,
        match_reason=reason,
    )


def run_matching(bearer_token: str) -> list[MatchResult]:
    """主流程：读取已解析条目 → 去重 → 逐条搜索 TMDb → 返回结果列表。"""
    raw = json.loads(PARSED_ITEMS_FILE.read_text(encoding="utf-8"))
    deduped = _deduplicate_flixpatrol_items(raw)
    logger.info("去重后 %d 个唯一标题", len(deduped))

    client = TmdbSearchClient(bearer_token=bearer_token)
    results: list[MatchResult] = []

    for i, item in enumerate(deduped, 1):
        logger.info("[%d/%d] 匹配: %s", i, len(deduped), item["title"])
        result = _match_single(item, client)
        results.append(result)
        if i < len(deduped):
            time.sleep(REQUEST_INTERVAL)

    return results


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )

    bearer_token = os.environ.get("TMDB_BEARER_TOKEN", "").strip()
    if not bearer_token:
        print("ERROR: TMDB_BEARER_TOKEN 环境变量未设置", file=sys.stderr)
        sys.exit(1)

    results = run_matching(bearer_token)

    # 保存 JSON
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(
        json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("结果已写入 %s", RESULTS_FILE)

    # 打印摘要
    total = len(results)
    by_conf = {c: sum(1 for r in results if r.confidence == c)
               for c in ("high", "medium", "low", "no_match")}
    matched = by_conf["high"] + by_conf["medium"]
    print(f"\n=== SUP-C 匹配摘要 ===", file=sys.stderr)
    print(f"总计: {total}", file=sys.stderr)
    print(f"high: {by_conf['high']}  medium: {by_conf['medium']}  low: {by_conf['low']}  no_match: {by_conf['no_match']}", file=sys.stderr)
    print(f"高/中置信度匹配率: {matched}/{total} = {matched/total*100:.1f}%", file=sys.stderr)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4：运行测试，确认通过**

```bash
PYTHONPATH=src python -m pytest tests/test_sup_c_matching.py -v
```

预期：所有测试通过（`XX passed`）

- [ ] **Step 5：提交**

```bash
git add scripts/sup_c_flixpatrol_matching.py tests/test_sup_c_matching.py
git commit -m "feat(sup-c): add FlixPatrol-TMDb matching script and unit tests

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2：运行匹配，保存结果 JSON

**Files:**
- Run: `scripts/sup_c_flixpatrol_matching.py`
- Written at runtime: `data/sup_c_match_results.json`

> ⚠️ 本任务需要 `TMDB_BEARER_TOKEN` 环境变量。若未设置，脚本会报错退出。

- [ ] **Step 1：确认环境变量存在**

```bash
python3 -c "import os; t=os.environ.get('TMDB_BEARER_TOKEN',''); print('Token set:', bool(t), f'({len(t)} chars)' if t else '')"
```

预期：`Token set: True (XXX chars)`。若显示 `False`，停止本任务，向用户报告：需要设置 `TMDB_BEARER_TOKEN` 后继续。

- [ ] **Step 2：运行匹配脚本**

```bash
PYTHONPATH=src python scripts/sup_c_flixpatrol_matching.py 2>&1
```

预期 stderr 输出：
- 逐条 `[N/117] 匹配: <title>` 日志
- 最终摘要：`高/中置信度匹配率: XX/117 = XX.X%`

耗时约 2–3 分钟（117 条 × 1 秒间隔）。

- [ ] **Step 3：验证结果文件**

```bash
python3 -c "
import json
results = json.load(open('data/sup_c_match_results.json'))
print(f'结果条数: {len(results)}')
print('前3条:')
for r in results[:3]:
    print(f'  {r[\"title\"]} → {r[\"tmdb_title\"]} ({r[\"confidence\"]}, sim={r[\"similarity\"]})')
"
```

预期：结果条数 = 117，每条有完整字段。

- [ ] **Step 4：提交结果文件**

```bash
git add data/sup_c_match_results.json
git commit -m "data(sup-c): save TMDb matching results for 117 FlixPatrol titles

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3：生成匹配率报告

**Files:**
- Create: `reports/flixpatrol_matching_report.md`
- Read: `data/sup_c_match_results.json`

- [ ] **Step 1：运行分析脚本，收集报告所需数据**

```bash
PYTHONPATH=src python3 -c "
import json
from collections import defaultdict

results = json.load(open('data/sup_c_match_results.json'))
total = len(results)

# 置信度统计
by_conf = defaultdict(list)
for r in results:
    by_conf[r['confidence']].append(r)

high   = len(by_conf['high'])
medium = len(by_conf['medium'])
low    = len(by_conf['low'])
no_match = len(by_conf['no_match'])
matched = high + medium

print(f'总计: {total}')
print(f'high: {high} ({high/total*100:.1f}%)')
print(f'medium: {medium} ({medium/total*100:.1f}%)')
print(f'low: {low} ({low/total*100:.1f}%)')
print(f'no_match: {no_match} ({no_match/total*100:.1f}%)')
print(f'高/中匹配率: {matched}/{total} = {matched/total*100:.1f}%')
print()

# 按 content_type 分组
for ct in ('movie', 'show'):
    items = [r for r in results if r['content_type'] == ct]
    m = sum(1 for r in items if r['confidence'] in ('high','medium'))
    print(f'{ct}: {m}/{len(items)} = {m/len(items)*100:.1f}%')
print()

# 无法匹配的条目
print('no_match 条目:')
for r in by_conf['no_match']:
    print(f'  {r[\"title\"]} ({r[\"content_type\"]})')
print()
print('low 置信度条目:')
for r in by_conf['low']:
    print(f'  {r[\"title\"]} → {r[\"tmdb_title\"]} (sim={r[\"similarity\"]})')
"
```

- [ ] **Step 2：创建报告文件**

基于 Step 1 的实际输出数据，创建 `reports/flixpatrol_matching_report.md`，内容如下（用实际数值替换占位符）：

```markdown
# FlixPatrol × TMDb 匹配率验证报告 (SUP-C)

> 验证目标：确认 FlixPatrol Top-10 内容能否匹配到 TMDb ID，验证匹配率 ≥ 80%  
> 验证日期：2026-05-10  
> 数据来源：`data/flixpatrol_parsed_items.json`（130 条，117 个唯一标题）  
> 任务包：`docs/tasks/sup_c_flixpatrol_matching.md`

---

## 1. 验证摘要

| 指标 | 结果 |
|------|------|
| 唯一标题总数 | [total] |
| 高置信度匹配（similarity ≥ 0.85） | [high] ([high%]) |
| 中置信度匹配（similarity 0.60-0.85） | [medium] ([medium%]) |
| 低置信度匹配（similarity 0.40-0.60） | [low] ([low%]) |
| 无法匹配 | [no_match] ([no_match%]) |
| **高/中置信度匹配率（验收指标）** | **[matched]/[total] = [rate]%** |
| 验收标准 | ≥ 80% |
| 初步结论 | ✅ 达标 / ❌ 未达标 |

---

## 2. 按内容类型分析

| 内容类型 | 总计 | 匹配（高/中） | 匹配率 |
|---------|------|-------------|--------|
| movie | [movie_total] | [movie_matched] | [movie_rate]% |
| show  | [show_total]  | [show_matched]  | [show_rate]%  |

---

## 3. 匹配结果详情

### 3.1 无法匹配条目（no_match）

| 标题 | 内容类型 | 平台 | 可能原因 |
|------|---------|------|---------|
[每行一条 no_match 条目，分析可能原因]

### 3.2 低置信度条目（low）

| FlixPatrol 标题 | TMDb 最高相似标题 | 相似度 | 分析 |
|---------------|----------------|--------|------|
[每行一条 low 条目]

---

## 4. 匹配质量分析

[分析高置信度匹配的典型案例；分析无法匹配的原因类型（标题差异、仅在流媒体发布未收录 TMDb、语言差异等）]

---

## 5. 给 P1-B 的输入

- 匹配率 [rate]%，[达标/未达标] ≥ 80% 验收标准
- 解析器代码：`scripts/sup_c_flixpatrol_matching.py` 中 `_match_single()` 可复用
- P1-B 匹配策略建议：[high/medium 直接采用；low 人工审核；no_match 原因分析]
- 无法匹配的 [no_match] 条目需在 P1-B 中考虑：[标题清洗、备用搜索词、OMDb 补查]

---

## 6. 决策建议

**建议：** ✅ 进入 P1-B / ⚠️ 加强匹配后重验 / ❌ 暂不接入 FlixPatrol

**理由：** [基于实际匹配率给出结论]

**前提条件（如适用）：**
- [如匹配率未达标：建议改进方向]

---

*匹配脚本：`scripts/sup_c_flixpatrol_matching.py`*  
*原始结果：`data/sup_c_match_results.json`*
```

- [ ] **Step 3：提交报告**

```bash
git add reports/flixpatrol_matching_report.md
git commit -m "verify(sup-c): FlixPatrol-TMDb matching rate report

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4：同步写 SUP-C 任务包

**Files:**
- Create: `docs/tasks/sup_c_flixpatrol_matching.md`

- [ ] **Step 1：创建任务包文档**

```markdown
# 任务包：SUP-C FlixPatrol × TMDb 匹配率验证

**任务包版本：** v1  
**创建日期：** 2026-05-10  
**预计完成：** 2026-05-10（0.5 天）

---

## 任务名称

SUP-C：FlixPatrol 内容与 TMDb 匹配率验证

## 任务类型

`verify` — 验证任务（含匹配脚本实现）

## 当前阶段

Phase 0+（FlixPatrol 接入验证）

## 来源任务

- `docs/reference/phase0_supplement.md` § 任务 SUP-C
- SUP-B 已完成：`data/flixpatrol_parsed_items.json` 就绪

## 目标

回答一个问题：FlixPatrol Top-10 内容能否以 ≥ 80% 的比例匹配到 TMDb ID？

## 非目标

- ❌ 不写入数据库
- ❌ 不实现完整匹配 pipeline
- ❌ 不做跨源（OMDb/Trakt）联合匹配
- ❌ 不评估合规性（SUP-D）

## 允许修改范围

- 新增 `scripts/sup_c_flixpatrol_matching.py`
- 新增 `tests/test_sup_c_matching.py`
- 新增 `data/sup_c_match_results.json`（运行时写入）
- 新增 `reports/flixpatrol_matching_report.md`
- 新增 `docs/tasks/sup_c_flixpatrol_matching.md`（本文件）

## 禁止修改范围

- 🚫 `src/movietrace/pipeline/`
- 🚫 `src/movietrace/sources/`
- 🚫 `data/movietrace.db`
- 🚫 `tests/fixtures/`
- 🚫 `AGENTS.md`、`CLAUDE.md`

## 验收标准

1. ✅ `pytest tests/test_sup_c_matching.py -v` 全部通过
2. ✅ 脚本在 `TMDB_BEARER_TOKEN` 存在时可正常运行
3. ✅ 高/中置信度匹配率 ≥ 80%
4. ✅ `reports/flixpatrol_matching_report.md` 包含全部6节

## 验证命令

```bash
PYTHONPATH=src python -m pytest tests/test_sup_c_matching.py -v
TMDB_BEARER_TOKEN=<token> PYTHONPATH=src python scripts/sup_c_flixpatrol_matching.py
```
```

- [ ] **Step 2：提交**

```bash
git add docs/tasks/sup_c_flixpatrol_matching.md
git commit -m "docs(sup-c): add SUP-C task package

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 验收检查（Task 4 完成后运行）

```bash
# 1. 单元测试
PYTHONPATH=src python -m pytest tests/test_sup_c_matching.py -v

# 2. 脚本语法检查
python3 -c "import ast; ast.parse(open('scripts/sup_c_flixpatrol_matching.py').read()); print('Syntax OK')"

# 3. 确认报告存在且包含必要节
python3 -c "
r = open('reports/flixpatrol_matching_report.md').read()
for s in ['验证摘要', '内容类型', '匹配结果', '匹配质量', 'P1-B', '决策建议']:
    print('✅' if s in r else '❌', s)
"

# 4. 确认结果文件字段完整
python3 -c "
import json
results = json.load(open('data/sup_c_match_results.json'))
required = {'title','content_type','platforms','tmdb_id','tmdb_title','tmdb_year','similarity','confidence','match_reason'}
for r in results:
    missing = required - set(r.keys())
    if missing: print('MISSING:', missing, r['title'])
print(f'字段完整性: {len(results)} 条全部OK')
"
```
