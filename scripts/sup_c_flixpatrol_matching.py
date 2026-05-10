from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from movietrace.pipeline.entity_matching import (
    BaselineItem,
    ExternalSearchResult,
    parse_title,
    _title_similarity,
)
from movietrace.sources.tmdb import TmdbSearchClient

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
PARSED_ITEMS_FILE = PROJECT_ROOT / "data" / "flixpatrol_parsed_items.json"
RESULTS_FILE      = PROJECT_ROOT / "data" / "sup_c_match_results.json"
SECRETS_FILE      = Path("/tmp/movietrace_phase0_secrets.json")
REQUEST_INTERVAL  = 1.0


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
    if similarity >= 0.85:
        base = "high"
    elif similarity >= 0.60:
        base = "medium"
    elif similarity >= 0.40:
        base = "low"
    else:
        return "no_match"

    if tmdb_year is not None and flixpatrol_year is not None:
        if abs(tmdb_year - flixpatrol_year) <= 1:
            if base == "low":
                return "medium"
            if base == "medium":
                return "high"
    return base


def _deduplicate_flixpatrol_items(items: list[dict]) -> list[dict]:
    seen: dict[tuple, dict] = {}
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


def _match_single(item: dict, client: TmdbSearchClient) -> MatchResult:
    title = item["title"]
    content_type = item["content_type"]
    platforms = item["platforms"]

    parsed = parse_title(title)
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
    try:
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


def _load_bearer_token() -> str:
    # 优先读 secrets 文件（项目标准方式）
    if SECRETS_FILE.exists():
        secrets = json.loads(SECRETS_FILE.read_text(encoding="utf-8"))
        token = (secrets.get("tmdb") or {}).get("api_read_access_token", "").strip()
        if token:
            return token
    # 备选：环境变量
    token = os.environ.get("TMDB_BEARER_TOKEN", "").strip()
    if token:
        return token
    return ""


def run_matching(bearer_token: str) -> list[MatchResult]:
    if not PARSED_ITEMS_FILE.exists():
        logger.error("找不到输入文件: %s", PARSED_ITEMS_FILE)
        return []
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

    bearer_token = _load_bearer_token()
    if not bearer_token:
        print("ERROR: 未找到 TMDB_BEARER_TOKEN（secrets 文件或环境变量均未设置）", file=sys.stderr)
        sys.exit(1)

    results = run_matching(bearer_token)

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(
        json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("结果已写入 %s", RESULTS_FILE)

    total = len(results)
    by_conf = {c: sum(1 for r in results if r.confidence == c)
               for c in ("high", "medium", "low", "no_match")}
    matched = by_conf["high"] + by_conf["medium"]
    rate_str = f"{matched/total*100:.1f}%" if total > 0 else "N/A"
    print(f"\n=== SUP-C 匹配摘要 ===", file=sys.stderr)
    print(f"总计: {total}", file=sys.stderr)
    print(f"high: {by_conf['high']}  medium: {by_conf['medium']}  low: {by_conf['low']}  no_match: {by_conf['no_match']}", file=sys.stderr)
    print(f"高/中置信度匹配率: {matched}/{total} = {rate_str}", file=sys.stderr)


if __name__ == "__main__":
    main()
