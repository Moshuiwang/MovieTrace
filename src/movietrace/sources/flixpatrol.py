from __future__ import annotations
import logging
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_TABLE_CLASS = "card-table"

# 月份映射（英文 → 数字）
_MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}

def parse_top10_page(html: str, platform: str, region: str) -> list[dict]:
    """从 HTML 字符串解析 Top-10 条目列表。

    返回格式：
    [
        {
            "rank": 1,
            "title": "...",
            "platform": "netflix",
            "region": "global",
            "content_type": "show",
            "week_date": "2026-05-10",  # 如有
            "days_in_top10": 14,         # 如有（Format B）
            "points": 882,               # 如有（Format A）
        },
        ...
    ]
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        week_date = _extract_week_date(soup)
        results: list[dict] = []

        for table in soup.find_all("table", class_=_TABLE_CLASS):
            # 找到最近的 heading（card 内或 h2）
            heading = _get_table_heading(table)
            if heading is None:
                continue

            keep, content_type = _classify_heading(heading)
            if not keep:
                continue

            # 检测行格式
            data_rows = [r for r in table.find_all("tr") if r.find("td")]
            if not data_rows:
                continue

            fmt = _detect_row_format(data_rows[0])
            if fmt == "unknown":
                continue

            for row in data_rows:
                item = _parse_row(row, fmt, platform, region, content_type, week_date)
                if item is not None:
                    results.append(item)

        return results
    except Exception as exc:
        logger.error("parse_top10_page failed: %s", exc)
        return []


def _get_table_heading(table) -> str | None:
    """返回表格所在 card div 内的标题文本，或最近的 h2 文本。"""
    card = table.find_parent("div", class_="card")
    if card:
        for tag in ["h2", "h3", "h4", "h5", "h6"]:
            h = card.find(tag)
            if h:
                return h.get_text(strip=True)
    h2 = table.find_previous("h2")
    return h2.get_text(strip=True) if h2 else None


def _classify_heading(heading: str) -> tuple[bool, str | None]:
    """根据标题文本判断是否保留，并返回 content_type。"""
    lower = heading.lower()
    # 跳过汇总/整体/时序表
    skip_patterns = ["overall", "and tv shows", "by country", "by day", "by week", "most popular", "top ranked"]
    if any(p in lower for p in skip_patterns):
        return False, None
    # 判断类型
    if "movie" in lower and "show" not in lower and "tv" not in lower:
        return True, "movie"
    if "tv show" in lower or ("tv" in lower and "movie" not in lower):
        return True, "show"
    # "TOP 10 Movies" / "TOP 10 TV Shows" 也需处理
    if "movies" in lower and "shows" not in lower:
        return True, "movie"
    if "shows" in lower and "movies" not in lower:
        return True, "show"
    return False, None


def _detect_row_format(row) -> str:
    """检测行格式：A（td[1] 有链接）或 B（td[2] 有链接）。"""
    tds = row.find_all("td")
    if len(tds) < 2:
        return "unknown"
    if tds[1].find("a"):
        return "A"
    if len(tds) > 2 and tds[2].find("a"):
        return "B"
    return "unknown"


def _parse_row(
    row,
    fmt: str,
    platform: str,
    region: str,
    content_type: str,
    week_date: str | None,
) -> dict | None:
    """解析单行，返回条目 dict 或 None。"""
    tds = row.find_all("td")
    try:
        if fmt == "A":
            rank = _parse_rank(tds[0].get_text(strip=True))
            title = _parse_title(tds[1])
            points = _parse_int(tds[2].get_text(strip=True).replace(",", "")) if len(tds) > 2 else None
            days_in_top10 = None
        else:  # fmt == "B"
            rank = _parse_rank(tds[0].get_text(strip=True))
            title = _parse_title(tds[2])
            days_in_top10 = _parse_days(tds[3].get_text(strip=True)) if len(tds) > 3 else None
            points = None

        if rank is None or title is None:
            return None

        return {
            "rank": rank,
            "title": title,
            "platform": platform,
            "region": region,
            "content_type": content_type,
            "week_date": week_date,
            "days_in_top10": days_in_top10,
            "points": points,
        }
    except Exception as exc:
        logger.debug("Row parse error: %s", exc)
        return None


def _parse_rank(text: str) -> int | None:
    m = re.match(r"^(\d+)", text.strip())
    return int(m.group(1)) if m else None


def _parse_title(td) -> str | None:
    a = td.find("a")
    if a is None:
        return None
    text = a.get_text(strip=True)
    return text if text else None


def _parse_int(text: str) -> int | None:
    text = text.strip().replace(",", "").replace("\xa0", "")
    return int(text) if text.isdigit() else None


def _parse_days(text: str) -> int | None:
    clean = text.replace("\xa0", " ").strip()
    m = re.match(r"^(\d+)\s*d$", clean)
    return int(m.group(1)) if m else None


def _extract_week_date(soup) -> str | None:
    """从页面标题提取榜单日期，如 'May 10, 2026' → '2026-05-10'。"""
    for tag in soup.find_all(["h1", "h2"]):
        text = tag.get_text(strip=True)
        m = re.search(r"\b([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})\b", text)
        if m:
            month_name, day, year = m.group(1), m.group(2), m.group(3)
            month_num = _MONTHS.get(month_name.lower())
            if month_num:
                return f"{year}-{month_num}-{int(day):02d}"
    return None
