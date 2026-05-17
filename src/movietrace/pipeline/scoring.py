from __future__ import annotations

import logging
import math
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger("movietrace.pipeline.scoring")

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = str(_PROJECT_ROOT / "config/scoring_weights.yaml")

DEFAULT_WEIGHTS: dict = {
    "weights": {
        "flixpatrol": 0.10,
        "tmdb_popularity": 0.15,
        "trakt": 0.15,
        "tmdb_rating": 0.15,
        "imdb_rating": 0.15,
        "platform_weight": 0.15,
        "content_type": 0.05,
        "freshness": 0.05,
        "language": 0.05,
    },
    "priority_thresholds": {"P0": 85, "P1": 70, "P2": 50},
    "platform_weight": {
        "netflix": 1.0,
        "prime-video": 1.0,
        "disney-plus": 0.9,
        "hbo-max": 0.85,
        "apple-tv-plus": 0.8,
        "hulu": 0.8,
        "paramount-plus": 0.8,
    },
    "freshness": {"full_score_days": 90, "half_score_days": 180},
}

SOAP_GENRE_ID = 10766  # TMDb genre: Soap; 命中即降权 P3(P1.24)


def load_weights_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        _write_default_config(config_path, DEFAULT_WEIGHTS)
        return dict(DEFAULT_WEIGHTS)
    try:
        import yaml
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        return cfg if cfg else dict(DEFAULT_WEIGHTS)
    except ImportError:
        logger.warning("pyyaml not available, using default weights")
        return dict(DEFAULT_WEIGHTS)
    except Exception as exc:
        logger.warning("Failed to load config %s: %s — using defaults", path, exc)
        return dict(DEFAULT_WEIGHTS)


def _write_default_config(path: Path, cfg: dict) -> None:
    try:
        import yaml
        with open(path, "w") as f:
            yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=False)
    except ImportError:
        pass


# ── Individual factor functions ────────────────────────────────────────


def compute_flixpatrol_score(fp_items: list[dict]) -> float:
    """Compute FlixPatrol heat score from one or more FP items (0-100).

    Uses best (lowest) ranking across platforms, plus days_in_top10 bonus.
    """
    if not fp_items:
        return 0.0

    best_rank = min(
        (item.get("ranking") for item in fp_items if item.get("ranking") is not None),
        default=10,
    )
    rank_score = max(0, 100 - (best_rank - 1) * 10)

    max_days = max(
        (item.get("days_total") or 0 for item in fp_items), default=0,
    )
    days_bonus = min(max_days, 30) / 30 * 20

    return min(100, rank_score + days_bonus)


def compute_tmdb_popularity_score(ext_data: dict | None) -> float:
    """Compute TMDb popularity score from cached external data (0-100).

    Returns 0 when data is unavailable.
    """
    if not ext_data or not ext_data.get("tmdb_popularity"):
        return 0.0
    pop = float(ext_data["tmdb_popularity"])
    return min(100, (pop / 1000) * 100)


def compute_trakt_score(ext_data: dict | None) -> float:
    """Compute Trakt community heat score (0-100).

    Returns 0 when data is unavailable.
    """
    if not ext_data or not ext_data.get("trakt_watchers"):
        return 0.0
    watchers = float(ext_data["trakt_watchers"])
    return min(100, (watchers / 5000) * 100)


def compute_tmdb_rating_score(ext_data: dict | None) -> float:
    """Compute TMDb rating score: vote_average × log10(vote_count+1), normalized 0-100.

    Returns 0 when data is unavailable.
    """
    if not ext_data:
        return 0.0
    vote_avg = ext_data.get("tmdb_vote_average")
    vote_count = ext_data.get("tmdb_vote_count")
    if vote_avg is None or vote_count is None:
        return 0.0
    try:
        raw = float(vote_avg) * math.log10(int(vote_count) + 1)
    except (ValueError, TypeError):
        return 0.0
    return min(100, (raw / 30) * 100)


def compute_imdb_rating_score(ext_data: dict | None) -> tuple[float, str | None]:
    """Compute IMDb rating score: rating × log10(votes+1), normalized 0-100.

    Returns (score, source) where source is None (no data), 'omdb', or 'tmdb_fallback'.
    """
    if not ext_data:
        return 0.0, None
    rating = ext_data.get("imdb_rating")
    votes = ext_data.get("imdb_votes")
    if rating is not None and votes is not None:
        try:
            raw = float(rating) * math.log10(int(votes) + 1)
        except (ValueError, TypeError):
            return 0.0, None
        return min(100, (raw / 40) * 100), "omdb"

    # P1.8-G: TMDb fallback when OMDb rating unavailable
    tmdb_rating = ext_data.get("tmdb_vote_average")
    tmdb_votes = ext_data.get("tmdb_vote_count")
    if tmdb_rating is not None and tmdb_votes is not None:
        try:
            raw = float(tmdb_rating) * math.log10(int(tmdb_votes) + 1)
        except (ValueError, TypeError):
            return 0.0, None
        return min(100, (raw / 40) * 100), "tmdb_fallback"

    return 0.0, None


def compute_platform_weight_score(platform: str, cfg: dict) -> float:
    """Compute platform weight score (0-100)."""
    pw = cfg.get("platform_weight", {})
    weight = pw.get(platform, pw.get("unknown", 0.8))
    return float(weight) * 100


def compute_content_type_score(content_type: str) -> float:
    """Content type bias: tv_show=100, movie=80."""
    return 100.0 if content_type == "tv_show" else 80.0


def compute_freshness_score(release_date_str: str | None, cfg: dict) -> float:
    """Compute freshness score based on days since release (0-100).

    90 days → 100, 180 days → 50, older → 0.
    """
    if not release_date_str:
        return 0.0
    try:
        rd = date.fromisoformat(release_date_str[:10])
    except (ValueError, TypeError):
        return 0.0

    days_ago = (date.today() - rd).days
    if days_ago < 0:
        return 100.0  # future release (unlikely but handle)

    fresh_cfg = cfg.get("freshness", {})
    full = fresh_cfg.get("full_score_days", 90)
    half = fresh_cfg.get("half_score_days", 180)

    if days_ago <= full:
        return 100.0
    if days_ago <= half:
        return 50.0
    return 0.0


def compute_language_score(language: str | None, fp_ranking: int | None) -> float:
    """Language relevance score (0-100).

    English=100, non-English but high FP ranking=80, other=50.
    """
    if language and language.lower() in ("en", "english"):
        return 100.0
    if fp_ranking and fp_ranking <= 5:
        return 80.0
    return 50.0


# ── Composite scoring ──────────────────────────────────────────────────


def compute_hot_score(candidate: dict, cfg: dict) -> tuple[float, dict]:
    """Compute weighted hot_score (0-100) and return score_breakdown dict."""
    w = cfg.get("weights", DEFAULT_WEIGHTS["weights"])

    fp_score = compute_flixpatrol_score(candidate.get("fp_items", []))
    tmdb_pop = compute_tmdb_popularity_score(candidate.get("ext_data"))
    trakt_s = compute_trakt_score(candidate.get("ext_data"))
    tmdb_rating = compute_tmdb_rating_score(candidate.get("ext_data"))
    imdb_rating, imdb_source = compute_imdb_rating_score(candidate.get("ext_data"))
    platform_s = compute_platform_weight_score(
        candidate.get("platform", "hulu"), cfg
    )
    content_s = compute_content_type_score(candidate.get("content_type", "movie"))
    freshness_s = compute_freshness_score(candidate.get("release_date"), cfg)
    language_s = compute_language_score(
        candidate.get("language"),
        candidate.get("ranking"),
    )

    hot = (
        fp_score * w.get("flixpatrol", 0.30)
        + tmdb_pop * w.get("tmdb_popularity", 0.15)
        + trakt_s * w.get("trakt", 0.10)
        + tmdb_rating * w.get("tmdb_rating", 0.10)
        + imdb_rating * w.get("imdb_rating", 0.10)
        + platform_s * w.get("platform_weight", 0.10)
        + content_s * w.get("content_type", 0.05)
        + freshness_s * w.get("freshness", 0.05)
        + language_s * w.get("language", 0.05)
    )

    hot = round(min(100, max(0, hot)), 1)

    breakdown = {
        "flixpatrol_score": round(fp_score, 1),
        "tmdb_popularity_score": round(tmdb_pop, 1) if tmdb_pop else None,
        "trakt_score": round(trakt_s, 1) if trakt_s else None,
        "tmdb_rating_score": round(tmdb_rating, 1) if tmdb_rating else None,
        "imdb_rating_score": round(imdb_rating, 1) if imdb_rating else None,
        "imdb_rating_source": imdb_source,
        "platform_weight_score": round(platform_s, 1),
        "content_type_score": round(content_s, 1),
        "freshness_score": round(freshness_s, 1),
        "language_score": round(language_s, 1),
    }

    return hot, breakdown


def map_priority(hot_score: float, thresholds: dict | None = None) -> str:
    """Map hot_score to P0/P1/P2/P3 threshold.

    ≥85→P0, ≥70→P1, ≥50→P2, other→P3.
    """
    if thresholds is None:
        thresholds = DEFAULT_WEIGHTS["priority_thresholds"]
    if hot_score >= thresholds.get("P0", 85):
        return "P0"
    if hot_score >= thresholds.get("P1", 70):
        return "P1"
    if hot_score >= thresholds.get("P2", 50):
        return "P2"
    return "P3"
