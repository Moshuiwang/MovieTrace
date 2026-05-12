from __future__ import annotations

import argparse
import json
import re
import sqlite3
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import unquote
from zoneinfo import ZoneInfo

from movietrace.db.schema import connect_database


CONFIDENCE_ORDER = ("high", "medium", "low", "no_match")


@dataclass(frozen=True)
class BaselineItem:
    id: int
    title: str
    content_type: str | None
    content_granularity: str | None
    season_number: int | None
    episode_number: int | None
    year: int | None
    online_status: str | None


@dataclass(frozen=True)
class ParsedTitle:
    query: str
    season_number: int | None = None
    year: int | None = None
    removed_noise_terms: tuple[str, ...] = ()
    decoded_url_encoding: bool = False


@dataclass(frozen=True)
class ExternalSearchResult:
    source: str
    external_id: str | None
    title: str
    media_type: str | None
    year: int | None
    score: float
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MatchDecision:
    result: ExternalSearchResult | None
    confidence: str
    score: float
    reason: str


@dataclass(frozen=True)
class TitleMatch:
    similarity: float
    matched_field: str
    core_title_matches: bool = False


@dataclass(frozen=True)
class ScoredCandidate:
    score: float
    result: ExternalSearchResult
    title_match: TitleMatch
    confidence: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class EntityMatchingResult:
    total_items: int
    matched_items: int
    confidence_counts: Counter[str]
    api_error_count: int


@dataclass(frozen=True)
class MatchEvaluation:
    item: BaselineItem
    parsed: ParsedTitle
    decision: MatchDecision
    source_decisions: dict[str, MatchDecision]


class EntitySearcher(Protocol):
    def search(
        self, query: str, baseline_item: BaselineItem
    ) -> list[ExternalSearchResult]:
        ...


class MultiSourceSearcher:
    def __init__(self, searchers: list[EntitySearcher]):
        self.searchers = searchers

    def search(
        self, query: str, baseline_item: BaselineItem
    ) -> list[ExternalSearchResult]:
        results: list[ExternalSearchResult] = []
        errors: list[str] = []
        for searcher in self.searchers:
            try:
                results.extend(searcher.search(query, baseline_item))
            except Exception as exc:
                errors.append(f"{type(searcher).__name__}:{type(exc).__name__}")
        if errors and not results:
            raise RuntimeError(";".join(errors))
        return results


def match_baseline_items(
    db_path: str | Path,
    searcher: EntitySearcher,
    report_path: str | Path,
    *,
    limit: int | None = None,
) -> EntityMatchingResult:
    with connect_database(db_path) as conn:
        items = _load_baseline_items(conn, limit=limit)
        conn.execute("delete from match_candidates")

        evaluations: list[MatchEvaluation] = []
        api_error_count = 0
        search_cache: dict[str, list[ExternalSearchResult]] = {}
        for item in items:
            parsed = parse_title(item.title)
            source_decisions: dict[str, MatchDecision] = {}
            try:
                if parsed.query not in search_cache:
                    search_cache[parsed.query] = searcher.search(parsed.query, item)
                search_results = search_cache[parsed.query]
            except Exception as exc:  # Phase 0 report should preserve API failures.
                api_error_count += 1
                decision = MatchDecision(
                    result=None,
                    confidence="no_match",
                    score=0.0,
                    reason=f"api_error={type(exc).__name__}: {exc}",
                )
            else:
                source_decisions = _source_decisions(item, parsed, search_results)
                decision = choose_best_match(item, parsed, search_results)

            evaluations.append(
                MatchEvaluation(
                    item=item,
                    parsed=parsed,
                    decision=decision,
                    source_decisions=source_decisions,
                )
            )
            _write_match_candidate(conn, item, decision)

        conn.commit()

    confidence_counts: Counter[str] = Counter(
        evaluation.decision.confidence for evaluation in evaluations
    )
    _write_report(
        Path(report_path),
        evaluations,
        confidence_counts,
        api_error_count=api_error_count,
    )
    return EntityMatchingResult(
        total_items=len(items),
        matched_items=sum(
            1 for evaluation in evaluations if evaluation.decision.result is not None
        ),
        confidence_counts=confidence_counts,
        api_error_count=api_error_count,
    )


def parse_title(title: str) -> ParsedTitle:
    original = title.strip()
    cleaned = unquote(original)
    decoded_url_encoding = cleaned != original
    season_number: int | None = None
    year: int | None = None
    removed_noise_terms: list[str] = []

    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", cleaned)
    if year_match:
        year = int(year_match.group(1))
        cleaned = (
            cleaned[: year_match.start()] + cleaned[year_match.end() :]
        ).strip()

    season_match = re.search(
        r"(?<![A-Za-z0-9])S(\d{1,2})(?![A-Za-z0-9])",
        cleaned,
        flags=re.IGNORECASE,
    )
    if season_match:
        season_number = int(season_match.group(1))
        cleaned = (
            cleaned[: season_match.start()] + cleaned[season_match.end() :]
        ).strip()

    cleaned, removed_noise_terms = _remove_noise_terms(cleaned)
    query = re.sub(r"\s+", " ", cleaned).strip()
    return ParsedTitle(
        query=query or title.strip(),
        season_number=season_number,
        year=year,
        removed_noise_terms=tuple(removed_noise_terms),
        decoded_url_encoding=decoded_url_encoding,
    )


def choose_best_match(
    item: BaselineItem,
    parsed: ParsedTitle,
    search_results: list[ExternalSearchResult],
) -> MatchDecision:
    if not search_results:
        return MatchDecision(
            result=None,
            confidence="no_match",
            score=0.0,
            reason="no_external_result",
        )

    scored: list[ScoredCandidate] = []
    for result in search_results:
        title_match = _best_title_match(parsed.query, result)
        confidence, reasons = _candidate_confidence_and_reasons(
            parsed, result, title_match
        )
        scored.append(
            ScoredCandidate(
                score=_combined_score(parsed, result, title_match),
                result=result,
                title_match=title_match,
                confidence=confidence,
                reasons=tuple(reasons),
            )
        )
    scored.sort(
        key=lambda candidate: (
            _confidence_rank(candidate.confidence),
            candidate.score,
        ),
        reverse=True,
    )
    return _combine_cross_source_decision(parsed, scored)


def _source_decisions(
    item: BaselineItem,
    parsed: ParsedTitle,
    search_results: list[ExternalSearchResult],
) -> dict[str, MatchDecision]:
    decisions: dict[str, MatchDecision] = {}
    for source in ("tmdb", "omdb"):
        source_results = [
            result for result in search_results if result.source == source
        ]
        decisions[source] = _choose_best_single_source_match(
            item, parsed, source_results
        )
    return decisions


def _choose_best_single_source_match(
    item: BaselineItem,
    parsed: ParsedTitle,
    search_results: list[ExternalSearchResult],
) -> MatchDecision:
    if not search_results:
        return MatchDecision(
            result=None,
            confidence="no_match",
            score=0.0,
            reason="no_external_result",
        )
    scored: list[ScoredCandidate] = []
    for result in search_results:
        title_match = _best_title_match(parsed.query, result)
        confidence, reasons = _candidate_confidence_and_reasons(
            parsed, result, title_match
        )
        scored.append(
            ScoredCandidate(
                score=_combined_score(parsed, result, title_match),
                result=result,
                title_match=title_match,
                confidence=confidence,
                reasons=tuple(reasons),
            )
        )
    scored.sort(
        key=lambda candidate: (
            _confidence_rank(candidate.confidence),
            candidate.score,
        ),
        reverse=True,
    )
    best = scored[0]
    return MatchDecision(
        result=best.result,
        confidence=best.confidence,
        score=best.score,
        reason="; ".join(best.reasons),
    )


def _load_baseline_items(
    conn: sqlite3.Connection, *, limit: int | None
) -> list[BaselineItem]:
    sql = """
        select id, title, content_type, content_granularity, season_number,
               episode_number, year, online_status
        from baseline_items
        order by id
    """
    params: tuple[Any, ...] = ()
    if limit is not None:
        sql += " limit ?"
        params = (limit,)
    return [
        BaselineItem(
            id=row[0],
            title=row[1],
            content_type=row[2],
            content_granularity=row[3],
            season_number=row[4],
            episode_number=row[5],
            year=row[6],
            online_status=row[7],
        )
        for row in conn.execute(sql, params).fetchall()
    ]


def _write_match_candidate(
    conn: sqlite3.Connection,
    item: BaselineItem,
    decision: MatchDecision,
) -> None:
    result = decision.result
    conn.execute(
        """
        insert into match_candidates(
            baseline_item_id, source, external_id, title, media_type, year,
            score, confidence, reason, raw_payload_json
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.id,
            result.source if result else "none",
            result.external_id if result else None,
            result.title if result else item.title,
            result.media_type if result else None,
            result.year if result else None,
            decision.score,
            decision.confidence,
            decision.reason,
            json.dumps(
                result.raw_payload if result else {},
                ensure_ascii=False,
                sort_keys=True,
            ),
        ),
    )


def _write_report(
    report_path: Path,
    evaluations: list[MatchEvaluation],
    confidence_counts: Counter[str],
    *,
    api_error_count: int,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    total = len(evaluations)
    lines = [
        "# MovieTrace 全量实体匹配报告",
        "",
        f"生成时间：{_current_report_time()}",
        "状态：Phase 0 验证产物",
        "数据来源：本地 SQLite `baseline_items`",
        "写入范围：本地 `match_candidates`，不写飞书正式表",
        "",
        "## 1. 结论摘要",
        "",
        f"- 基线记录数：{total}",
        f"- 匹配候选记录数：{sum(1 for e in evaluations if e.decision.result is not None)}",
        f"- API 错误数：{api_error_count}",
        "",
        "| 置信度 | 数量 | 占比 |",
        "| --- | ---: | ---: |",
    ]
    for confidence in CONFIDENCE_ORDER:
        count = confidence_counts.get(confidence, 0)
        lines.append(f"| {confidence} | {count} | {_percent(count, total)} |")

    lines.extend(
        [
        "",
        "## 2. 低置信度和未匹配样本",
            "",
            "| baseline_item_id | 本地标题 | 搜索标题 | 置信度 | 外部标题 | 来源 | 年份 | 依据 |",
            "| ---: | --- | --- | --- | --- | --- | ---: | --- |",
        ]
    )
    risky_rows = [
        evaluation
        for evaluation in evaluations
        if evaluation.decision.confidence in {"low", "no_match"}
    ][:50]
    if risky_rows:
        for evaluation in risky_rows:
            item = evaluation.item
            parsed = evaluation.parsed
            decision = evaluation.decision
            result = decision.result
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(item.id),
                        _md(item.title),
                        _md(parsed.query),
                        decision.confidence,
                        _md(result.title if result else ""),
                        result.source if result else "",
                        str(result.year or "") if result else "",
                        _md(decision.reason),
                    ]
                )
                + " |"
            )
    else:
        lines.append("|  | 未发现 low / no_match 样本 |  |  |  |  |  |  |")

    lines.extend(
        [
            "",
            "## 3. TMDB / OMDb 全量建议与差异",
            "",
            "TMDB ID 与 IMDb ID 属于不同编号体系，不参与冲突判断。差异仅基于标题、类型、年份和来源置信度。",
            "",
            "| baseline_item_id | 本地标题 | 搜索标题 | 最终置信度 | 最终候选 | TMDB ID | IMDb ID | TMDB 建议 | OMDb 建议 | 差异 |",
            "| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for evaluation in evaluations:
        item = evaluation.item
        parsed = evaluation.parsed
        decision = evaluation.decision
        result = decision.result
        tmdb_decision = evaluation.source_decisions.get("tmdb")
        omdb_decision = evaluation.source_decisions.get("omdb")
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.id),
                    _md(item.title),
                    _md(parsed.query),
                    decision.confidence,
                    _md(_decision_summary(decision)),
                    _md(_source_external_id(tmdb_decision)),
                    _md(_source_external_id(omdb_decision)),
                    _md(_decision_summary(tmdb_decision)),
                    _md(_decision_summary(omdb_decision)),
                    _md(_source_difference(tmdb_decision, omdb_decision)),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## 4. 人工复核建议",
            "",
            "- 优先抽样复核 high 匹配，目标准确率 >= 95%。",
            "- 对 low / no_match 样本补充年份、类型或外部 ID 后再重跑。",
            "- 本报告不代表自动写入 canonical_items 的授权。",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _combined_score(
    parsed: ParsedTitle, result: ExternalSearchResult, title_match: TitleMatch
) -> float:
    score = title_match.similarity
    if parsed.season_number is not None and result.media_type == "tv":
        score += 0.08
    if parsed.year is not None and result.year == parsed.year:
        score += 0.30
    if parsed.year is None and _candidate_supports_newer_version_prior(
        parsed, result, title_match
    ):
        score += _newer_version_bonus(result.year)
    source_score = min(max(result.score, 0.0), 100.0) / 1000.0
    return score + source_score


def _candidate_confidence_and_reasons(
    parsed: ParsedTitle,
    result: ExternalSearchResult,
    title_match: TitleMatch,
) -> tuple[str, list[str]]:
    similarity = title_match.similarity
    reasons = [
        f"title_similarity={similarity:.2f}",
        f"matched_field={title_match.matched_field}",
    ]
    if title_match.core_title_matches:
        reasons.append("core_title_matches")
    if parsed.season_number is not None:
        reasons.append(f"parsed_season=S{parsed.season_number:02d}")
    if parsed.year is not None:
        reasons.append(f"parsed_year={parsed.year}")
    if parsed.decoded_url_encoding:
        reasons.append("decoded_url_encoding")
    if parsed.removed_noise_terms:
        reasons.append(
            "removed_noise_terms=" + ",".join(parsed.removed_noise_terms)
        )
    if result.media_type == "tv" and parsed.season_number is not None:
        reasons.append("season_hint_matches_tv")
    if (
        result.media_type == "movie"
        and parsed.season_number is not None
        and similarity >= 0.92
    ):
        reasons.append("data_quality_warning=season_title_matched_movie")
    if parsed.year is not None and result.year == parsed.year:
        reasons.append("year_matches")
    if parsed.year is None and _candidate_supports_newer_version_prior(
        parsed, result, title_match
    ):
        reasons.append("version_disambiguation=newer_entity_preferred")

    if similarity >= 0.92 and (
        parsed.season_number is None or result.media_type == "tv"
    ):
        confidence = "high"
    elif similarity >= 0.78:
        confidence = "medium"
    else:
        confidence = "low"
    return confidence, reasons


def _combine_cross_source_decision(
    parsed: ParsedTitle,
    scored: list[ScoredCandidate],
) -> MatchDecision:
    tmdb = _best_candidate_for_source(scored, "tmdb")
    omdb = _best_candidate_for_source(scored, "omdb")
    best = scored[0]
    reasons = list(best.reasons)

    if tmdb is not None and omdb is not None:
        compatible = _candidates_are_compatible(tmdb, omdb)
        if compatible and (
            _source_is_ok(tmdb.confidence)
            and _source_is_ok(omdb.confidence)
        ):
            selected = _preferred_primary_candidate(tmdb, omdb, best)
            selected_reasons = list(selected.reasons)
            selected_reasons.append("cross_source=tmdb_omdb_consistent")
            selected_reasons.append(_source_summary("tmdb", tmdb))
            selected_reasons.append(_source_summary("omdb", omdb))
            if _season_title_matched_movie(parsed, selected):
                selected_reasons.append("data_quality_warning=season_title_matched_movie")
            return MatchDecision(
                result=selected.result,
                confidence="high",
                score=selected.score,
                reason="; ".join(selected_reasons),
            )
        if _source_is_ok(tmdb.confidence) and _source_is_ok(omdb.confidence):
            selected = _preferred_primary_candidate(tmdb, omdb, best)
            selected_reasons = list(selected.reasons)
            selected_reasons.append("cross_source=tmdb_omdb_conflict")
            selected_reasons.append(_source_summary("tmdb", tmdb))
            selected_reasons.append(_source_summary("omdb", omdb))
            return MatchDecision(
                result=selected.result,
                confidence="medium",
                score=selected.score,
                reason="; ".join(selected_reasons),
            )

    if best.confidence == "high":
        reasons.append(f"cross_source=single_strong_{best.result.source}")
    elif tmdb is not None or omdb is not None:
        if tmdb is not None:
            reasons.append(_source_summary("tmdb", tmdb))
        if omdb is not None:
            reasons.append(_source_summary("omdb", omdb))
    return MatchDecision(
        result=best.result,
        confidence=best.confidence,
        score=best.score,
        reason="; ".join(reasons),
    )


def _best_candidate_for_source(
    scored: list[ScoredCandidate], source: str
) -> ScoredCandidate | None:
    source_candidates = [
        candidate for candidate in scored if candidate.result.source == source
    ]
    if not source_candidates:
        return None
    return max(
        source_candidates,
        key=lambda candidate: (
            _confidence_rank(candidate.confidence),
            candidate.score,
        ),
    )


def _preferred_primary_candidate(
    tmdb: ScoredCandidate,
    omdb: ScoredCandidate,
    fallback: ScoredCandidate,
) -> ScoredCandidate:
    if tmdb.result.external_id:
        return tmdb
    if fallback.result.source not in {"omdb"}:
        return fallback
    return omdb


def _source_is_ok(confidence: str) -> bool:
    return confidence in {"high", "medium"}


def _confidence_rank(confidence: str) -> int:
    return {
        "no_match": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
    }.get(confidence, 0)


def _candidates_are_compatible(
    left: ScoredCandidate, right: ScoredCandidate
) -> bool:
    if left.result.media_type != right.result.media_type:
        return False
    title_similarity = _title_similarity(left.result.title, right.result.title)
    if title_similarity < 0.82:
        return False
    if (
        left.result.year is not None
        and right.result.year is not None
        and abs(left.result.year - right.result.year) > 1
    ):
        return False
    return True


def _season_title_matched_movie(
    parsed: ParsedTitle, candidate: ScoredCandidate
) -> bool:
    return (
        parsed.season_number is not None
        and candidate.result.media_type == "movie"
        and candidate.title_match.similarity >= 0.92
    )


def _source_summary(source: str, candidate: ScoredCandidate) -> str:
    result = candidate.result
    return (
        f"{source}={_summary_value(result.title)}"
        f"|{result.media_type or ''}"
        f"|{result.year or ''}"
        f"|{candidate.confidence}"
    )


def _summary_value(value: str) -> str:
    return value.replace(";", ",").replace("|", "/").strip()


def _candidate_supports_newer_version_prior(
    parsed: ParsedTitle,
    result: ExternalSearchResult,
    title_match: TitleMatch,
) -> bool:
    if result.year is None:
        return False
    if title_match.similarity < 0.92:
        return False
    if parsed.season_number is not None:
        return result.media_type == "tv"
    return result.media_type in {"movie", "tv"}


def _newer_version_bonus(year: int | None) -> float:
    if year is None:
        return 0.0
    if year >= 2020:
        return 0.18
    if year >= 2010:
        return 0.12
    if year >= 2000:
        return 0.06
    return 0.0


def _best_title_match(query: str, result: ExternalSearchResult) -> TitleMatch:
    candidates = [("title", result.title)]
    for field_name in ("original_name", "original_title"):
        value = result.raw_payload.get(field_name)
        if isinstance(value, str) and value.strip():
            candidates.append((field_name, value))

    best = TitleMatch(similarity=0.0, matched_field="title")
    for field_name, value in candidates:
        title_match = _match_title_candidate(query, value, field_name)
        if title_match.similarity > best.similarity:
            best = title_match
    return best


def _match_title_candidate(query: str, candidate: str, field_name: str) -> TitleMatch:
    similarity = _title_similarity(query, candidate)
    query_norm = _normalize_title(query)
    candidate_norm = _normalize_title(candidate)
    core_title_matches = False

    if query_norm and candidate_norm:
        query_ratio = len(query_norm) / max(len(candidate_norm), 1)
        if (
            candidate_norm.endswith(query_norm)
            and query_ratio >= 0.4
            and query_norm != candidate_norm
        ):
            similarity = max(similarity, 0.94)
            core_title_matches = True

    return TitleMatch(
        similarity=similarity,
        matched_field=field_name,
        core_title_matches=core_title_matches,
    )


def _title_similarity(left: str, right: str) -> float:
    left_norm = _normalize_title(left)
    right_norm = _normalize_title(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def _remove_noise_terms(value: str) -> tuple[str, list[str]]:
    cleaned = value.strip()
    removed: list[str] = []
    patterns = [
        ("無英文字幕", r"\s*無英文字幕\s*$"),
        ("无英文字幕", r"\s*无英文字幕\s*$"),
        ("百度网盘", r"\s*百度网盘\s*$"),
        ("interview", r"\s+interview\s*$"),
    ]
    changed = True
    while changed:
        changed = False
        for term, pattern in patterns:
            updated = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
            if updated != cleaned:
                cleaned = updated
                removed.append(term)
                changed = True
    return cleaned, removed


def _normalize_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore")
    text = normalized.decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _percent(count: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{count / total * 100:.1f}%"


def _md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _current_report_time() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).strftime(
        "%Y-%m-%d %H:%M:%S Asia/Shanghai"
    )


def _decision_summary(decision: MatchDecision | None) -> str:
    if decision is None:
        return "no_decision"
    result = decision.result
    if result is None:
        return f"none no_match {decision.reason}"
    return (
        f"{result.title} "
        f"{result.media_type or ''} "
        f"{result.year or ''} "
        f"{decision.confidence}"
    ).strip()


def _source_external_id(decision: MatchDecision | None) -> str:
    if decision is None or decision.result is None:
        return ""
    return decision.result.external_id or ""


def _source_difference(
    tmdb_decision: MatchDecision | None,
    omdb_decision: MatchDecision | None,
) -> str:
    tmdb = tmdb_decision.result if tmdb_decision else None
    omdb = omdb_decision.result if omdb_decision else None
    if tmdb is None and omdb is None:
        return "both_no_match"
    if tmdb is None:
        return "omdb_only"
    if omdb is None:
        return "tmdb_only"

    differences: list[str] = []
    if tmdb.media_type != omdb.media_type:
        differences.append(f"type:{tmdb.media_type}->{omdb.media_type}")
    if tmdb.year is not None and omdb.year is not None:
        year_delta = abs(tmdb.year - omdb.year)
        if year_delta > 1:
            differences.append(f"year_delta={year_delta}")
    if _title_similarity(tmdb.title, omdb.title) < 0.82:
        differences.append("title_diff")
    if not differences:
        return "compatible"
    return ",".join(differences)


def _build_searcher_from_secrets(secrets_path: Path) -> MultiSourceSearcher:
    from movietrace.sources.omdb import OmdbSearchClient
    from movietrace.sources.tmdb import TmdbSearchClient
    from movietrace.sources.trakt import TraktSearchClient

    secrets = json.loads(secrets_path.read_text(encoding="utf-8"))
    searchers: list[EntitySearcher] = []
    tmdb_token = (secrets.get("tmdb") or {}).get("api_read_access_token")
    omdb_api_key = (secrets.get("omdb") or {}).get("api_key")
    trakt_client_id = (secrets.get("trakt") or {}).get("client_id")
    if tmdb_token:
        searchers.append(TmdbSearchClient(tmdb_token))
    if omdb_api_key:
        searchers.append(OmdbSearchClient(omdb_api_key))
    if trakt_client_id:
        searchers.append(TraktSearchClient(trakt_client_id))
    if not searchers:
        raise RuntimeError("No TMDb or Trakt credentials found in secrets file")
    return MultiSourceSearcher(searchers)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 0 full entity matching")
    parser.add_argument("--db", default="data/movietrace.db")
    parser.add_argument("--report", default="reports/full_entity_matching_report.md")
    parser.add_argument(
        "--secrets", default="/tmp/movietrace_phase0_secrets.json"
    )
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    result = match_baseline_items(
        args.db,
        _build_searcher_from_secrets(Path(args.secrets)),
        args.report,
        limit=args.limit,
    )
    print(
        "matched "
        f"{result.matched_items}/{result.total_items}; "
        f"errors={result.api_error_count}; "
        f"confidence={dict(result.confidence_counts)}"
    )


# ---------------------------------------------------------------------------
# P1.5-E: Upstream program matching (A 库 → canonical_items)
# ---------------------------------------------------------------------------


def _strip_season_suffix(name: str) -> str:
    """Remove season suffix like ' S01' or 'S01' from end of name."""
    stripped = re.sub(
        r"\s*S\d{2}\s*$", "", name, flags=re.IGNORECASE
    ).strip()
    return stripped or name


def _extract_season_number(name: str) -> int | None:
    """Extract season number from name, e.g. 'Better Call Saul S01' → 1."""
    m = re.search(
        r"(?<![A-Za-z0-9])S(\d{1,2})(?![A-Za-z0-9])",
        name,
        flags=re.IGNORECASE,
    )
    return int(m.group(1)) if m else None


def _ensure_quality_issues_table(conn: sqlite3.Connection) -> None:
    # If the old V1 baseline_quality_issues table exists with incompatible schema,
    # drop and recreate. Check by looking for the upstream_program_id column.
    existing = conn.execute(
        "select name from sqlite_master where type='table' and name='baseline_quality_issues'"
    ).fetchone()
    if existing:
        cols = {
            r[1]
            for r in conn.execute("pragma table_info(baseline_quality_issues)").fetchall()
        }
        if "upstream_program_id" not in cols:
            conn.execute("drop table baseline_quality_issues")

    conn.execute("""
        create table if not exists baseline_quality_issues (
            id integer primary key autoincrement,
            upstream_program_id integer not null,
            issue_type text not null,
            source_name text,
            confidence text,
            reason text,
            created_at text not null default current_timestamp
        )
    """)


def _record_quality_issue(
    conn: sqlite3.Connection,
    upstream_program_id: int,
    source_name: str,
    issue_type: str,
    confidence: str,
    reason: str,
) -> None:
    conn.execute(
        """insert into baseline_quality_issues(
            upstream_program_id, issue_type, source_name, confidence, reason
        ) values (?, ?, ?, ?, ?)""",
        (upstream_program_id, issue_type, source_name, confidence, reason),
    )


def _make_dummy_baseline_item(
    upstream_id: int, name: str, content_type: str, season_number: int | None
) -> BaselineItem:
    return BaselineItem(
        id=upstream_id,
        title=name,
        content_type=content_type,
        content_granularity="season" if content_type == "tv" else "movie",
        season_number=season_number,
        episode_number=None,
        year=None,
        online_status="1",
    )


def match_upstream_program(
    conn: sqlite3.Connection,
    upstream_program_id: int,
    tmdb_client: object,
) -> dict | None:
    """Match a single upstream_program to TMDb and create canonical_item + external_id.

    Returns a result dict with match details, or None if the program doesn't exist.
    """
    row = conn.execute(
        "select id, name, online_flag from upstream_programs where id = ?",
        (upstream_program_id,),
    ).fetchone()
    if not row:
        return None

    name = row[1]

    season_number = _extract_season_number(name)
    if season_number is not None:
        content_type = "tv"
        content_granularity = "season"
        series_name = _strip_season_suffix(name)
    else:
        content_type = "movie"
        content_granularity = "movie"
        series_name = name
        season_number = None

    parsed = parse_title(series_name)
    item = _make_dummy_baseline_item(
        upstream_program_id, name, content_type, season_number
    )

    search_results: list[ExternalSearchResult] = []
    api_error: str | None = None
    try:
        search_results = tmdb_client.search(parsed.query, item)
    except Exception as exc:
        api_error = f"{type(exc).__name__}: {exc}"

    if api_error or not search_results:
        _ensure_quality_issues_table(conn)
        _record_quality_issue(
            conn,
            upstream_program_id,
            name,
            "entity_matching_api_error" if api_error else "entity_matching_no_results",
            "no_match",
            api_error or "no_external_result",
        )
        return {
            "upstream_program_id": upstream_program_id,
            "name": name,
            "matched": False,
            "confidence": "no_match",
            "error": api_error,
        }

    decision = choose_best_match(item, parsed, search_results)

    if decision.result is None or decision.confidence == "no_match":
        _ensure_quality_issues_table(conn)
        _record_quality_issue(
            conn,
            upstream_program_id,
            name,
            "entity_matching_no_match",
            decision.confidence,
            decision.reason,
        )
        return {
            "upstream_program_id": upstream_program_id,
            "name": name,
            "matched": False,
            "confidence": decision.confidence,
            "reason": decision.reason,
        }

    result = decision.result
    tmdb_id = result.external_id

    if season_number is not None:
        canonical_item_key = f"tmdb:tv:{tmdb_id}:season:{season_number}"
    else:
        canonical_item_key = f"tmdb:movie:{tmdb_id}"

    existing = conn.execute(
        "select id from canonical_items where canonical_item_key = ?",
        (canonical_item_key,),
    ).fetchone()

    if existing:
        canonical_item_id = int(existing[0])
        created = False
    else:
        original_title = (
            result.raw_payload.get("original_name")
            or result.raw_payload.get("original_title")
        )
        conn.execute(
            """insert into canonical_items(
                canonical_item_key, title, original_title, content_type,
                content_granularity, season_number, year
            ) values (?, ?, ?, ?, ?, ?, ?)""",
            (
                canonical_item_key,
                result.title,
                str(original_title) if original_title else None,
                content_type,
                content_granularity,
                season_number,
                result.year,
            ),
        )
        canonical_item_id = int(
            conn.execute("select last_insert_rowid()").fetchone()[0]
        )
        created = True

    conn.execute(
        """insert or ignore into external_ids(
            canonical_item_id, source, external_id, external_granularity
        ) values (?, ?, ?, ?)""",
        (canonical_item_id, "upstream", str(upstream_program_id), content_granularity),
    )
    conn.execute(
        """insert or ignore into external_ids(
            canonical_item_id, source, external_id, external_granularity
        ) values (?, ?, ?, ?)""",
        (
            canonical_item_id,
            "tmdb",
            tmdb_id,
            "series" if content_type == "tv" else "movie",
        ),
    )

    if decision.confidence == "low":
        _ensure_quality_issues_table(conn)
        _record_quality_issue(
            conn,
            upstream_program_id,
            name,
            "entity_matching_low_confidence",
            decision.confidence,
            decision.reason,
        )

    return {
        "upstream_program_id": upstream_program_id,
        "name": name,
        "matched": True,
        "canonical_item_id": canonical_item_id,
        "created": created,
        "confidence": decision.confidence,
        "tmdb_id": tmdb_id,
        "tmdb_title": result.title,
        "tmdb_year": result.year,
        "content_type": content_type,
        "season_number": season_number,
    }


if __name__ == "__main__":
    main()
