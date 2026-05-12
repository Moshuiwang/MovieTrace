# SUP-B FlixPatrol HTML Parsing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and validate a FlixPatrol HTML parser that extracts Top-10 rankings from 6 saved fixture HTML files with ≥ 95% field extraction success rate.

**Architecture:** Two discovered page formats (Format A: global pages with points column; Format B: regional pages with days_in_top10 column), detected per-row via link position. A single `parse_top10_page(html, platform, region)` function handles both. Parser lives in `src/movietrace/sources/flixpatrol.py`; tests in `tests/test_flixpatrol_parsing.py` use only fixture HTML — zero network calls.

**Tech Stack:** Python 3.12, `beautifulsoup4` (html.parser backend, stdlib — no lxml needed), `pytest`

---

## Context

SUP-A confirmed 6/7 FlixPatrol URLs return HTTP 200 with server-rendered HTML. The 6 fixture files are already saved at `tests/fixtures/flixpatrol/`. HTML structure analysis revealed two table formats:
- **Format A** (Netflix Global, Amazon Prime World, Disney World, Apple TV World): `td[1]` has title link + FlixPatrol points score
- **Format B** (Netflix US, Hulu US): `td[2]` has title link + `days_in_top10` column

Table selection: use only tables with h2 containing "Movie" or "TV Show/Shows" (skip "Overall", "and TV Shows", "Top ranked").

## File Map

| Action | Path |
|--------|------|
| Create | `src/movietrace/sources/flixpatrol.py` |
| Create | `tests/test_flixpatrol_parsing.py` |
| Create | `requirements.txt` |
| Create (after run) | `reports/flixpatrol_parsing_report.md` |

---

## Task 1: Install dependency and create requirements.txt

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Install beautifulsoup4**

```bash
pip install beautifulsoup4
```

Expected output ends with: `Successfully installed beautifulsoup4-4.x.x`

- [ ] **Step 2: Verify import works**

```bash
python3 -c "import bs4; print('bs4 version:', bs4.__version__)"
```

Expected: `bs4 version: 4.x.x`

- [ ] **Step 3: Create requirements.txt**

```bash
pip freeze > requirements.txt
grep beautifulsoup4 requirements.txt
```

Expected: line like `beautifulsoup4==4.x.x`

- [ ] **Step 4: Verify pytest can import movietrace modules**

```bash
PYTHONPATH=src python -m pytest tests/test_entity_matching.py --collect-only -q 2>&1 | head -5
```

Expected: shows test names, no `ModuleNotFoundError`. If it fails, all subsequent pytest commands need `PYTHONPATH=src`.

- [ ] **Step 5: Commit requirements.txt**

```bash
git add requirements.txt
git commit -m "chore: add requirements.txt with beautifulsoup4"
```

---

## Task 2: Write failing tests (TDD red phase)

**Files:**
- Create: `tests/test_flixpatrol_parsing.py`

- [ ] **Step 1: Create the test file with the following exact content**

```python
"""Tests for FlixPatrol HTML parser (SUP-B).

All tests use fixture HTML files — no network calls.
"""
from __future__ import annotations

import pathlib

import pytest

from movietrace.sources.flixpatrol import parse_top10_page

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "flixpatrol"

FIXTURE_FILES = [
    ("netflix_global.html",      "netflix",      "global"),
    ("netflix_us.html",          "netflix",      "us"),
    ("amazon_prime_world.html",  "amazon-prime", "world"),
    ("disney_world.html",        "disney",       "world"),
    ("apple_tv_world.html",      "apple-tv",     "world"),
    ("hulu_us.html",             "hulu",         "us"),
]


def _load(filename: str) -> str:
    return (FIXTURES / filename).read_text(encoding="utf-8", errors="replace")


# ── Basic parsing (Netflix Global, Format A) ─────────────────────────────────

def test_netflix_global_returns_20_items():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    assert len(items) == 20, f"Expected 20 (10 movies + 10 shows), got {len(items)}"


def test_netflix_global_rank1_movie_is_swapped():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    movies = [i for i in items if i["content_type"] == "movie"]
    rank1 = next((i for i in movies if i["rank"] == 1), None)
    assert rank1 is not None
    assert rank1["title"] == "Swapped"


def test_netflix_global_has_10_movies_and_10_shows():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    assert sum(1 for i in items if i["content_type"] == "movie") == 10
    assert sum(1 for i in items if i["content_type"] == "show") == 10


def test_netflix_global_movie_ranks_are_1_to_10():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    ranks = sorted(i["rank"] for i in items if i["content_type"] == "movie")
    assert ranks == list(range(1, 11))


def test_netflix_global_platform_field():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    assert all(i["platform"] == "netflix" for i in items)


def test_netflix_global_region_field():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    assert all(i["region"] == "global" for i in items)


def test_netflix_global_week_date():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    assert items[0]["week_date"] == "2026-05-10"


def test_netflix_global_points_are_ints():
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    for item in items:
        assert isinstance(item["points"], int), f"points should be int, got {type(item['points'])}"


def test_netflix_global_days_in_top10_is_none():
    # Format A pages have no days_in_top10 column
    items = parse_top10_page(_load("netflix_global.html"), "netflix", "global")
    assert all(i["days_in_top10"] is None for i in items)


# ── Format B (regional pages with days_in_top10) ──────────────────────────────

def test_netflix_us_returns_20_items():
    items = parse_top10_page(_load("netflix_us.html"), "netflix", "us")
    assert len(items) == 20


def test_netflix_us_rank1_movie_is_swapped():
    items = parse_top10_page(_load("netflix_us.html"), "netflix", "us")
    movies = [i for i in items if i["content_type"] == "movie"]
    rank1 = next((i for i in movies if i["rank"] == 1), None)
    assert rank1 is not None
    assert rank1["title"] == "Swapped"


def test_netflix_us_days_in_top10_are_ints():
    items = parse_top10_page(_load("netflix_us.html"), "netflix", "us")
    for item in items:
        assert isinstance(item["days_in_top10"], int), (
            f"days_in_top10 should be int for regional page, got {item['days_in_top10']!r} "
            f"for '{item['title']}'"
        )


def test_netflix_us_points_are_none():
    # Format B pages have no points column
    items = parse_top10_page(_load("netflix_us.html"), "netflix", "us")
    assert all(i["points"] is None for i in items)


def test_hulu_us_rank1_movie():
    items = parse_top10_page(_load("hulu_us.html"), "hulu", "us")
    movies = [i for i in items if i["content_type"] == "movie"]
    rank1 = next((i for i in movies if i["rank"] == 1), None)
    assert rank1 is not None
    assert rank1["title"] == "Send Help"


def test_hulu_us_overall_table_is_skipped():
    # "TOP 10 Overall" table must be excluded; only Movies and TV Shows included
    items = parse_top10_page(_load("hulu_us.html"), "hulu", "us")
    # If Overall is included, total items would be 3 × table_size; just Movies+Shows = 2 × table_size
    movies = [i for i in items if i["content_type"] == "movie"]
    shows  = [i for i in items if i["content_type"] == "show"]
    assert len(movies) > 0
    assert len(shows) > 0
    # No item should lack a content_type
    assert all(i["content_type"] in ("movie", "show") for i in items)


# ── Error handling ────────────────────────────────────────────────────────────

def test_empty_html_returns_empty_list():
    assert parse_top10_page("<html><body></body></html>", "netflix", "global") == []


def test_invalid_html_returns_empty_list():
    assert parse_top10_page("not html at all !!!!", "netflix", "global") == []


# ── Cross-platform parametrized tests ────────────────────────────────────────

@pytest.mark.parametrize("filename,platform,region", FIXTURE_FILES)
def test_all_fixtures_return_items(filename, platform, region):
    items = parse_top10_page(_load(filename), platform, region)
    assert len(items) >= 10, f"{filename}: expected ≥10 items, got {len(items)}"


@pytest.mark.parametrize("filename,platform,region", FIXTURE_FILES)
def test_all_fixtures_platform_field(filename, platform, region):
    items = parse_top10_page(_load(filename), platform, region)
    wrong = [i for i in items if i["platform"] != platform]
    assert not wrong, f"{filename}: {len(wrong)} items have wrong platform"


@pytest.mark.parametrize("filename,platform,region", FIXTURE_FILES)
def test_all_fixtures_region_field(filename, platform, region):
    items = parse_top10_page(_load(filename), platform, region)
    wrong = [i for i in items if i["region"] != region]
    assert not wrong, f"{filename}: {len(wrong)} items have wrong region"


@pytest.mark.parametrize("filename,platform,region", FIXTURE_FILES)
def test_all_fixtures_required_fields_present(filename, platform, region):
    items = parse_top10_page(_load(filename), platform, region)
    required = {"rank", "title", "platform", "region", "content_type",
                "points", "week_date", "days_in_top10"}
    for item in items:
        missing = required - set(item.keys())
        assert not missing, f"{filename}: item missing fields {missing}"


@pytest.mark.parametrize("filename,platform,region", FIXTURE_FILES)
def test_all_fixtures_titles_are_nonempty_strings(filename, platform, region):
    items = parse_top10_page(_load(filename), platform, region)
    bad = [i for i in items if not isinstance(i["title"], str) or not i["title"]]
    assert not bad, f"{filename}: {len(bad)} items have empty/invalid title"


# ── Extraction rate ───────────────────────────────────────────────────────────

def test_basic_field_extraction_rate_above_95_percent():
    """rank, title, content_type must be non-None in ≥95% of all items across all fixtures."""
    basic_fields = ["rank", "title", "content_type"]
    total = populated = 0
    for filename, platform, region in FIXTURE_FILES:
        for item in parse_top10_page(_load(filename), platform, region):
            for field in basic_fields:
                total += 1
                if item.get(field) is not None:
                    populated += 1
    rate = populated / total if total > 0 else 0
    assert rate >= 0.95, f"Basic field extraction rate {rate:.1%} < 95% ({populated}/{total})"
```

- [ ] **Step 2: Run tests to confirm they all fail with ImportError**

```bash
PYTHONPATH=src python -m pytest tests/test_flixpatrol_parsing.py -v --tb=no -q 2>&1 | head -15
```

Expected: `ModuleNotFoundError: No module named 'movietrace.sources.flixpatrol'` or similar — tests collected but failing.

- [ ] **Step 3: Commit the test file**

```bash
git add tests/test_flixpatrol_parsing.py
git commit -m "test(sup-b): add FlixPatrol HTML parsing tests (red)"
```

---

## Task 3: Implement the parser (TDD green phase)

**Files:**
- Create: `src/movietrace/sources/flixpatrol.py`

- [ ] **Step 1: Create the parser with the following exact content**

```python
from __future__ import annotations

import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_TABLE_CLASS = "card-table"


def parse_top10_page(html: str, platform: str, region: str) -> list[dict]:
    """Parse a FlixPatrol Top-10 page and return ranking entries.

    Handles two page formats discovered during SUP-B:
    - Format A (global/world pages): rank | title_link | points | progress_bar
    - Format B (regional pages):     rank | change     | title_link | days_in_top10

    Args:
        html: Raw HTML string of a FlixPatrol top10 page.
        platform: Platform slug, e.g. 'netflix', 'disney', 'amazon-prime', 'hulu'.
        region: Region slug, e.g. 'global', 'world', 'us'.

    Returns:
        List of dicts with keys: rank, title, platform, region, content_type,
        points, week_date, days_in_top10. Returns [] on total parse failure.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        week_date = _extract_week_date(soup)
        results: list[dict] = []

        for table in soup.find_all("table", class_=_TABLE_CLASS):
            h2 = table.find_previous(["h2", "h3"])
            h2_text = h2.get_text(strip=True) if h2 else ""
            is_relevant, content_type = _classify_table(h2_text)
            if not is_relevant:
                continue
            results.extend(_parse_table(table, platform, region, content_type, week_date))

        return results
    except Exception:
        logger.exception("Failed to parse page platform=%s region=%s", platform, region)
        return []


def _classify_table(h2_text: str) -> tuple[bool, str | None]:
    """Return (is_top10_table, content_type) based on the preceding h2/h3 text."""
    text = h2_text.lower()
    skip = ("movies and tv shows", "movies & tv shows", "top ranked", "most popular", "overall")
    if any(kw in text for kw in skip):
        return False, None
    has_movie = "movie" in text
    has_show = "show" in text or "tv shows" in text
    if has_movie and not has_show:
        return True, "movie"
    if has_show and not has_movie:
        return True, "show"
    return False, None


def _parse_table(
    table,
    platform: str,
    region: str,
    content_type: str,
    week_date: str | None,
) -> list[dict]:
    tbody = table.find("tbody")
    if not tbody:
        return []
    rows = tbody.find_all("tr")
    if not rows:
        return []

    row_fmt = _detect_row_format(rows[0])
    results: list[dict] = []

    for tr in rows:
        tds = tr.find_all("td")
        if not tds:
            continue

        rank = _parse_rank(tds[0])
        if rank is None:
            continue

        if row_fmt == "A":  # Global: rank | title_link | points | bar
            title = _parse_title(tds[1]) if len(tds) > 1 else None
            points = _parse_int(tds[2].get_text(strip=True)) if len(tds) > 2 else None
            days: int | None = None
        elif row_fmt == "B":  # Regional: rank | change | title_link | days
            title = _parse_title(tds[2]) if len(tds) > 2 else None
            points = None
            days = _parse_days(tds[3].get_text(strip=True)) if len(tds) > 3 else None
        else:
            logger.warning("Unknown row format rank=%s platform=%s", rank, platform)
            continue

        if title is None:
            logger.warning("No title at rank=%s platform=%s", rank, platform)
            continue

        results.append({
            "rank": rank,
            "title": title,
            "platform": platform,
            "region": region,
            "content_type": content_type,
            "points": points,
            "week_date": week_date,
            "days_in_top10": days,
        })

    return results


def _detect_row_format(tr) -> str:
    """Return 'A' if title link is in td[1], 'B' if in td[2], else 'unknown'."""
    tds = tr.find_all("td")
    if len(tds) > 1 and tds[1].find("a"):
        return "A"
    if len(tds) > 2 and tds[2].find("a"):
        return "B"
    return "unknown"


def _extract_week_date(soup: BeautifulSoup) -> str | None:
    """Extract 'YYYY-MM-DD' from page <title> text like '...on May 10, 2026...'."""
    title_tag = soup.find("title")
    if not title_tag:
        return None
    match = re.search(r"on (\w+ \d+, \d{4})", title_tag.get_text())
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _parse_rank(td) -> int | None:
    try:
        return int(td.get_text(strip=True).rstrip("."))
    except (ValueError, AttributeError):
        return None


def _parse_title(td) -> str | None:
    """Extract title text from a cell containing an <a> link."""
    link = td.find("a")
    if not link:
        return None
    # Skip SVG/script text nodes; return first substantive text
    for string in link.strings:
        s = string.strip()
        if s and string.parent.name not in ("svg", "script", "style"):
            return s
    return None


def _parse_int(text: str) -> int | None:
    try:
        return int(text.replace(",", "").strip())
    except ValueError:
        return None


def _parse_days(text: str) -> int | None:
    """Parse '8 d' or '337\xa0d' → 8 or 337."""
    clean = text.replace("\xa0", " ").strip()
    match = re.match(r"^(\d+)\s*d$", clean)
    return int(match.group(1)) if match else None
```

- [ ] **Step 2: Run all tests**

```bash
PYTHONPATH=src python -m pytest tests/test_flixpatrol_parsing.py -v 2>&1 | tail -30
```

Expected: all tests PASS. If any fail, check the error and fix the parser — do NOT move on.

- [ ] **Step 3: Commit the implementation**

```bash
git add src/movietrace/sources/flixpatrol.py
git commit -m "feat(sup-b): FlixPatrol HTML parser draft (formats A and B)"
```

---

## Task 4: Generate report data and write report

**Files:**
- Create: `reports/flixpatrol_parsing_report.md`

- [ ] **Step 1: Run extraction rate analysis**

```bash
PYTHONPATH=src python3 -c "
from movietrace.sources.flixpatrol import parse_top10_page
import pathlib, json

FIXTURES = pathlib.Path('tests/fixtures/flixpatrol')
FILES = [
    ('netflix_global.html',     'netflix',      'global'),
    ('netflix_us.html',         'netflix',      'us'),
    ('amazon_prime_world.html', 'amazon-prime', 'world'),
    ('disney_world.html',       'disney',       'world'),
    ('apple_tv_world.html',     'apple-tv',     'world'),
    ('hulu_us.html',            'hulu',         'us'),
]

print('=== Per-fixture results ===')
grand_total = grand_ok = 0
for fname, plat, region in FILES:
    html = (FIXTURES / fname).read_text(errors='replace')
    items = parse_top10_page(html, plat, region)
    fields = ['rank','title','content_type','points','week_date','days_in_top10']
    counts = {f: sum(1 for i in items if i.get(f) is not None) for f in fields}
    total = len(items)
    basic_ok = sum(counts[f] for f in ['rank','title','content_type'])
    grand_total += total * 3
    grand_ok += basic_ok
    print(f'{fname}: {total} items | rank={counts[\"rank\"]} title={counts[\"title\"]} content_type={counts[\"content_type\"]} points={counts[\"points\"]} week_date={counts[\"week_date\"]} days={counts[\"days_in_top10\"]}')
    if items:
        print(f'  rank1: {next((i for i in items if i[\"rank\"]==1 and i[\"content_type\"]==\"movie\"), items[0])}')
print()
print(f'Overall basic field rate: {grand_ok}/{grand_total} = {grand_ok/grand_total:.1%}')
"
```

- [ ] **Step 2: Write the report from the actual output above**

Create `reports/flixpatrol_parsing_report.md` with the following structure, filling in all values from the actual command output:

```markdown
# FlixPatrol 解析稳定性验证报告 (SUP-B)

> 验证目标：确认 FlixPatrol HTML 结构可稳定解析，提取 Top-10 排名数据  
> 验证日期：2026-05-10  
> 执行环境：Python 3.12 / beautifulsoup4 / html.parser  
> 任务包：docs/tasks/sup_b_flixpatrol_parsing.md  
> 解析器：src/movietrace/sources/flixpatrol.py

---

## 1. 验证摘要

| 指标 | 结果 |
|------|------|
| 测试 HTML 样本数 | 6 |
| 成功解析样本数 | [从命令输出填入] |
| 总提取条目数 | [总 items 数] |
| 基础字段提取成功率 | [grand_ok/grand_total %] |
| 初步结论 | ✅ 可解析 / ⚠️ 部分可解析 |

---

## 2. HTML 结构分析

FlixPatrol 页面使用两种表格格式：

### Format A（全球/世界榜页面）

触发条件：h2 标题含日期（如"TOP Movies on Netflix on May 10, 2026"）

列结构：

| td 索引 | 内容 | 提取方式 |
|--------|------|---------|
| td[0] | 排名（"1."） | `int(text.rstrip('.'))` |
| td[1] | 标题链接 + 海报图 | `link.strings` 首个非空文本 |
| td[2] | FlixPatrol 积分 | `int(text)` |
| td[3] | 进度条（跳过） | — |

### Format B（地区榜页面）

触发条件：h2 仅含"TOP 10 Movies/TV Shows"（无日期）

列结构：

| td 索引 | 内容 | 提取方式 |
|--------|------|---------|
| td[0] | 排名（"1."） | `int(text.rstrip('.'))` |
| td[1] | 排名变化（"–", "+8"，跳过） | — |
| td[2] | 标题链接 | `link.strings` 首个非空文本 |
| td[3] | 在榜天数（"8 d"） | `int(re.match)` |

---

## 3. 字段提取结果

| 文件 | 平台 | 格式 | 条目数 | rank | title | content_type | points | week_date | days_in_top10 |
|------|------|------|--------|------|-------|-------------|--------|-----------|---------------|
[从命令输出逐行填入实际数据]

---

## 4. 跨平台一致性

[描述 6 个样本是否使用同一解析逻辑，以及两种格式的分布]

---

## 5. 解析失败分析

[如有失败条目，说明原因；如无失败，写"所有样本解析完整，无失败条目"]

---

## 6. 给 P1-B 的输入

**可直接复用的代码：**
- `src/movietrace/sources/flixpatrol.py` 的 `parse_top10_page()` 函数
- 格式检测逻辑（`_detect_row_format`、`_classify_table`）可直接用于实时抓取

**P1-B 需要额外处理的边界情况：**
- Format B 的 `days_in_top10` 字段：Format A 无此字段（`None`），评分权重需区分处理
- HBO/Max 路径需修正（见 SUP-A 报告）
- 建议 P1-B 加入页面结构变化检测（当解析结果为空时告警）

---

## 7. 决策建议

**建议：** ✅ 进入 P1-B（完整 FlixPatrol 客户端实现）

**理由：**
[基于实际数据填写：成功率、两种格式均稳定解析等]

**前提条件：**
- SUP-D 合规评估结论不构成阻塞

**下一步：**
- [ ] P1-B：完整 FlixPatrol 客户端（HTTP 抓取 + 缓存 + schema）
- [ ] SUP-D：合规评估（可并行）

---

*解析器：`src/movietrace/sources/flixpatrol.py`*  
*pytest 测试：`tests/test_flixpatrol_parsing.py`*
```

---

## Task 5: Final verification and commit

- [ ] **Step 1: Run full acceptance checklist**

```bash
echo "=== Acceptance Criteria ===" &&
PYTHONPATH=src python -m pytest tests/test_flixpatrol_parsing.py -v 2>&1 | tail -10 &&
echo "---" &&
ls src/movietrace/sources/flixpatrol.py && echo "✅ parser exists" &&
ls tests/test_flixpatrol_parsing.py && echo "✅ tests exist" &&
ls requirements.txt && grep -q beautifulsoup4 requirements.txt && echo "✅ requirements.txt has bs4" &&
ls reports/flixpatrol_parsing_report.md && echo "✅ report exists" &&
python3 -c "
r = open('reports/flixpatrol_parsing_report.md').read()
for s in ['验证摘要','HTML 结构分析','字段提取结果','跨平台一致性','解析失败','P1-B','决策建议']:
    print('  ✅' if s in r else '  ❌', '章节:', s)
"
```

Expected: all pytest tests PASS, all files exist, all report sections present.

- [ ] **Step 2: Commit all SUP-B outputs**

```bash
git add src/movietrace/sources/flixpatrol.py
git add tests/test_flixpatrol_parsing.py
git add reports/flixpatrol_parsing_report.md
git add requirements.txt
git status
git commit -m "$(cat <<'EOF'
verify(sup-b): FlixPatrol HTML parsing stability test

- src/movietrace/sources/flixpatrol.py: draft parser (Format A + B)
- tests/test_flixpatrol_parsing.py: 20+ tests, all passing
- reports/flixpatrol_parsing_report.md: parsing accuracy report
- requirements.txt: added beautifulsoup4

Basic field extraction rate ≥ 95% across 6 HTML fixtures.
Decision: proceed to P1-B.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 3: Write completion report**

```
任务理解：
- 验证 FlixPatrol HTML 结构可稳定解析，提取 Top-10 排名数据

完成内容：
- 创建 src/movietrace/sources/flixpatrol.py（draft 解析器，~130 行）
- 创建 tests/test_flixpatrol_parsing.py（20+ 测试用例）
- 创建 requirements.txt
- 生成 reports/flixpatrol_parsing_report.md

验证结果：
- pytest: N passed / 0 failed
- 基础字段提取成功率: X%
- 发现两种页面格式：Format A（全球榜）/ Format B（地区榜）
- days_in_top10 在 Format B 页面可提取

剩余风险：
- 服务条款合规（待 SUP-D）
- FlixPatrol 前端更新可能导致选择器失效（建议 P1-B 加检测）

后续建议：
- 进入 P1-B（完整 FlixPatrol 客户端）
```

---

## Verification Commands

```bash
# Run all tests
PYTHONPATH=src python -m pytest tests/test_flixpatrol_parsing.py -v

# Quick smoke test
PYTHONPATH=src python3 -c "
from movietrace.sources.flixpatrol import parse_top10_page
import pathlib
html = pathlib.Path('tests/fixtures/flixpatrol/netflix_global.html').read_text()
items = parse_top10_page(html, 'netflix', 'global')
print('items:', len(items))
print('rank1 movie:', next(i for i in items if i['rank']==1 and i['content_type']=='movie'))
"

# Check report
cat reports/flixpatrol_parsing_report.md
```
