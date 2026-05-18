from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from movietrace.sources.flixpatrol_api import (
    FlixPatrolClient,
    TYPE_INT_TO_STR,
    PLATFORM_COMPANY_IDS,
    FP_COUNTRIES,
    COMPANY_TO_PLATFORM,
    load_api_key,
    unwrap_item,
    _extract_http_status,
)
from movietrace.sources.http import FatalApiError

# ── compound document fixture ───────────────────────────────────────────


@pytest.fixture
def compound_doc_item():
    """Real FlixPatrol v2 API item in compound document format (from SUP-G fixture)."""
    return {
        "type": "top10s",
        "data": {
            "id": "tpt_ye7U2UzROTNVv5JZ7Hu4m8MY",
            "movie": {
                "type": "titles",
                "data": {
                    "id": "ttl_BdMTpjUaQxLHk84AY3ldN2X0",
                    "title": "Spenser Confidential",
                    "tmdbId": 581600,
                    "imdbId": "8629748",
                },
            },
            "company": {
                "type": "companies",
                "data": {
                    "id": "cmp_IA6TdMqwf6kuyQvxo9bJ4nKX",
                    "name": "Netflix",
                },
            },
            "country": {
                "type": "countries",
                "data": {
                    "id": "cnt_iMUHNbZvnNHK5YdhgwtOoP4u",
                    "name": "United States",
                },
            },
            "type": 2,
            "date": {"type": 1, "from": "2020-03-20", "to": "2020-03-20"},
            "ranking": 1,
            "rankingLast": 0,
            "value": 10,
            "valueLast": 0,
            "daysTotal": None,
            "updatedAt": "2022-07-27T16:55:02",
        },
    }


@pytest.fixture
def compound_doc_item_tv():
    """Compound document item for TV show (type=3)."""
    return {
        "type": "top10s",
        "data": {
            "movie": {
                "data": {
                    "title": "Stranger Things",
                    "tmdbId": 66732,
                    "imdbId": "4574334",
                }
            },
            "company": {
                "data": {"id": "cmp_IA6TdMqwf6kuyQvxo9bJ4nKX", "name": "Netflix"}
            },
            "country": {
                "data": {
                    "id": "cnt_iMUHNbZvnNHK5YdhgwtOoP4u",
                    "name": "United States",
                }
            },
            "type": 3,
            "date": {"type": 1, "from": "2026-05-10", "to": "2026-05-10"},
            "ranking": 3,
            "rankingLast": 1,
            "value": 8,
            "valueLast": 10,
            "daysTotal": 45,
        },
    }


@pytest.fixture
def minimal_compound_item():
    """Item with minimal fields — some optional fields absent."""
    return {
        "type": "top10s",
        "data": {
            "movie": {
                "data": {"title": "Unknown Film"}
            },
            "company": {"data": {}},
            "country": {"data": {}},
            "type": 2,
            "date": {"type": 1, "from": "2026-05-09", "to": "2026-05-09"},
            "ranking": 10,
        },
    }


# ── unwrap_item tests ───────────────────────────────────────────────────


class TestUnwrapItem:
    def test_unwraps_compound_document(self, compound_doc_item):
        result = unwrap_item(compound_doc_item)
        assert result["fp_id"] == "tpt_ye7U2UzROTNVv5JZ7Hu4m8MY"
        assert result["title"] == "Spenser Confidential"
        assert result["content_type"] == "movie"
        assert result["ranking"] == 1
        assert result["ranking_last"] == 0
        assert result["value"] == 10
        assert result["days_total"] is None
        assert result["platform"] == "netflix"
        assert result["country"] == "united-states"
        assert result["snapshot_date"] == "2020-03-20"
        assert result["tmdb_id"] == 581600
        assert result["imdb_id"] == 8629748
        assert result["updated_at"] == "2022-07-27T16:55:02"

    def test_unwraps_tv_show(self, compound_doc_item_tv):
        result = unwrap_item(compound_doc_item_tv)
        assert result["content_type"] == "tv_show"
        assert result["ranking"] == 3
        assert result["title"] == "Stranger Things"
        assert result["tmdb_id"] == 66732
        assert result["imdb_id"] == 4574334

    def test_unwraps_minimal_item(self, minimal_compound_item):
        result = unwrap_item(minimal_compound_item)
        assert result["title"] == "Unknown Film"
        assert result["content_type"] == "movie"
        assert result["ranking"] == 10
        assert result["tmdb_id"] is None
        assert result["imdb_id"] is None
        assert result["ranking_last"] is None
        assert result["value"] is None
        assert result["snapshot_date"] == "2026-05-09"

    def test_platform_from_company_id(self):
        item = {
            "type": "top10s",
            "data": {
                "movie": {"data": {"title": "Test"}},
                "company": {"data": {"id": "cmp_qypvowjqFhEIpCc0HlQ6VoYk"}},
                "country": {"data": {}},
                "type": 2,
                "date": {"type": 1, "from": "2026-05-10", "to": "2026-05-10"},
                "ranking": 1,
            },
        }
        result = unwrap_item(item)
        assert result["platform"] == "prime-video"

    def test_platform_from_company_id_hbo_max(self):
        item = {
            "type": "top10s",
            "data": {
                "movie": {"data": {"title": "Test"}},
                "company": {"data": {"id": "cmp_6UhCvnTeRkgZUtcNGslX9bJL"}},
                "country": {"data": {}},
                "type": 2,
                "date": {"type": 1, "from": "2026-05-10", "to": "2026-05-10"},
                "ranking": 1,
            },
        }
        result = unwrap_item(item)
        assert result["platform"] == "hbo-max"

    def test_imdb_id_as_none_when_missing(self):
        item = {
            "type": "top10s",
            "data": {
                "movie": {"data": {"title": "No IMDB", "tmdbId": 123}},
                "company": {"data": {}},
                "country": {"data": {}},
                "type": 2,
                "date": {"type": 1, "from": "2026-05-10", "to": "2026-05-10"},
                "ranking": 1,
            },
        }
        result = unwrap_item(item)
        assert result["tmdb_id"] == 123
        assert result["imdb_id"] is None

    def test_country_name_normalized(self):
        item = {
            "type": "top10s",
            "data": {
                "movie": {"data": {"title": "Test"}},
                "company": {"data": {}},
                "country": {"data": {"name": "United States"}},
                "type": 2,
                "date": {"type": 1, "from": "2026-05-10", "to": "2026-05-10"},
                "ranking": 1,
            },
        }
        result = unwrap_item(item)
        assert result["country"] == "united-states"

    def test_days_total_as_integer(self):
        item = {
            "type": "top10s",
            "data": {
                "movie": {"data": {"title": "Test"}},
                "company": {"data": {}},
                "country": {"data": {}},
                "type": 2,
                "date": {"type": 1, "from": "2026-05-10", "to": "2026-05-10"},
                "ranking": 1,
                "daysTotal": 15,
            },
        }
        result = unwrap_item(item)
        assert result["days_total"] == 15

    def test_ranking_last_as_zero_not_none(self):
        item = {
            "type": "top10s",
            "data": {
                "movie": {"data": {"title": "Test"}},
                "company": {"data": {}},
                "country": {"data": {}},
                "type": 2,
                "date": {"type": 1, "from": "2026-05-10", "to": "2026-05-10"},
                "ranking": 1,
                "rankingLast": 0,
            },
        }
        result = unwrap_item(item)
        assert result["ranking_last"] == 0


# ── Field mapping tests ─────────────────────────────────────────────────


class TestFieldMapping:
    def test_type_int_to_str_movie(self):
        assert TYPE_INT_TO_STR[2] == "movie"

    def test_type_int_to_str_tv(self):
        assert TYPE_INT_TO_STR[3] == "tv_show"

    def test_unknown_type_returns_none(self):
        assert TYPE_INT_TO_STR.get(999) is None

    def test_platform_ids_are_6(self):
        assert len(PLATFORM_COMPANY_IDS) == 6

    def test_company_to_platform_reverse_map(self):
        assert COMPANY_TO_PLATFORM["cmp_IA6TdMqwf6kuyQvxo9bJ4nKX"] == "netflix"
        assert COMPANY_TO_PLATFORM["cmp_qypvowjqFhEIpCc0HlQ6VoYk"] == "prime-video"
        assert COMPANY_TO_PLATFORM["cmp_oGtsgdpOrjIu3XzTEnWPt87Y"] == "disney-plus"
        assert COMPANY_TO_PLATFORM["cmp_VvmYc7OphiUds0Hgjbz5MESn"] == "apple-tv-plus"
        assert COMPANY_TO_PLATFORM["cmp_6UhCvnTeRkgZUtcNGslX9bJL"] == "hbo-max"
        assert COMPANY_TO_PLATFORM["cmp_riMmDaNhomIc4J2dWGQPKbkZ"] == "paramount-plus"


# ── load_api_key tests ──────────────────────────────────────────────────


class TestLoadApiKey:
    def test_loads_from_valid_file(self):
        secrets = {"flixpatrol": {"api_key": "aku_testkey12345678"}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(secrets, f)
            tmp_path = f.name
        try:
            key = load_api_key(tmp_path)
            assert key == "aku_testkey12345678"
        finally:
            os.unlink(tmp_path)

    def test_raises_on_missing_file(self):
        with pytest.raises(RuntimeError, match="Secrets file not found"):
            load_api_key("/tmp/nonexistent_abc_12345.json")

    def test_raises_on_invalid_json(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("not valid json{{{")
            tmp_path = f.name
        try:
            with pytest.raises(RuntimeError, match="not valid JSON"):
                load_api_key(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_raises_when_flixpatrol_key_missing(self):
        secrets = {"tmdb": {"api_key": "abc"}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(secrets, f)
            tmp_path = f.name
        try:
            with pytest.raises(RuntimeError, match="API key not found"):
                load_api_key(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_raises_when_api_key_is_empty_string(self):
        secrets = {"flixpatrol": {"api_key": ""}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(secrets, f)
            tmp_path = f.name
        try:
            with pytest.raises(RuntimeError, match="API key not found"):
                load_api_key(tmp_path)
        finally:
            os.unlink(tmp_path)


# ── Client tests ────────────────────────────────────────────────────────


class TestFlixPatrolClient:
    def test_client_initialization(self):
        client = FlixPatrolClient("aku_test123")
        assert client.timeout == 60
        assert client._api_key == "aku_test123"

    def test_client_custom_timeout(self):
        client = FlixPatrolClient("aku_test123", timeout=30)
        assert client.timeout == 30

    def test_masked_key_short(self):
        client = FlixPatrolClient("ab")
        assert client._masked_key == "***"

    def test_masked_key_normal(self):
        client = FlixPatrolClient("aku_tmbKiZWTog2beK9rmPdNBpx6")
        assert client._masked_key == "aku_***"

    def test_auth_header_format(self):
        client = FlixPatrolClient("testkey")
        header = client._auth_header()
        assert header.startswith("Basic ")

    def test_fetch_top10_auth_error_401(self):
        """401 should raise FatalApiError immediately (circuit breaker)."""
        client = FlixPatrolClient("bad_key")
        with patch("movietrace.sources.flixpatrol_api.get_json") as mock_get:
            mock_get.side_effect = FatalApiError(401, "HTTP Error 401: Unauthorized")
            with pytest.raises(FatalApiError) as ctx:
                client.fetch_top10(
                    company="cmp_IA6TdMqwf6kuyQvxo9bJ4nKX",
                    country=FP_COUNTRIES["united-states"],
                    content_type=2,
                )
            assert ctx.value.status_code == 401

    def test_fetch_top10_auth_error_403(self):
        """403 should raise FatalApiError immediately (circuit breaker)."""
        client = FlixPatrolClient("bad_key")
        with patch("movietrace.sources.flixpatrol_api.get_json") as mock_get:
            mock_get.side_effect = FatalApiError(403, "HTTP Error 403: Forbidden")
            with pytest.raises(FatalApiError) as ctx:
                client.fetch_top10(
                    company="cmp_IA6TdMqwf6kuyQvxo9bJ4nKX",
                    country=FP_COUNTRIES["united-states"],
                    content_type=2,
                )
            assert ctx.value.status_code == 403

    def test_fetch_top10_rate_limit_429_retry_ok(self, compound_doc_item):
        """429 should retry once and succeed."""
        client = FlixPatrolClient("test_key")
        with patch("movietrace.sources.flixpatrol_api.get_json") as mock_get:
            mock_get.side_effect = [
                Exception("HTTP Error 429: Too Many Requests"),
                {"data": [compound_doc_item]},
            ]
            with patch("movietrace.sources.flixpatrol_api.time.sleep") as mock_sleep:
                results = client.fetch_top10(
                    company="cmp_IA6TdMqwf6kuyQvxo9bJ4nKX",
                    country=FP_COUNTRIES["united-states"],
                    content_type=2,
                )
            mock_sleep.assert_called_once_with(5)
            assert len(results) == 1
            assert results[0]["title"] == "Spenser Confidential"

    def test_fetch_top10_rate_limit_429_both_fail(self):
        """429 on both attempts should return empty list."""
        client = FlixPatrolClient("test_key")
        with patch("movietrace.sources.flixpatrol_api.get_json") as mock_get:
            mock_get.side_effect = [
                Exception("HTTP Error 429: Too Many Requests"),
                Exception("HTTP Error 429: Too Many Requests"),
            ]
            with patch("movietrace.sources.flixpatrol_api.time.sleep"):
                results = client.fetch_top10(
                    company="cmp_IA6TdMqwf6kuyQvxo9bJ4nKX",
                    country=FP_COUNTRIES["united-states"],
                    content_type=2,
                )
            assert results == []

    def test_fetch_top10_5xx_returns_empty(self):
        """5xx errors should log and return empty list."""
        client = FlixPatrolClient("test_key")
        with patch("movietrace.sources.flixpatrol_api.get_json") as mock_get:
            mock_get.side_effect = Exception("HTTP Error 502: Bad Gateway")
            results = client.fetch_top10(
                company="cmp_IA6TdMqwf6kuyQvxo9bJ4nKX",
                country=FP_COUNTRIES["united-states"],
                content_type=2,
            )
            assert results == []

    def test_fetch_top10_network_timeout_returns_empty(self):
        """Network timeout should log and return empty list."""
        client = FlixPatrolClient("test_key")
        with patch("movietrace.sources.flixpatrol_api.get_json") as mock_get:
            mock_get.side_effect = TimeoutError("timed out")
            results = client.fetch_top10(
                company="cmp_IA6TdMqwf6kuyQvxo9bJ4nX",
                country=FP_COUNTRIES["united-states"],
                content_type=2,
            )
            assert results == []

    def test_fetch_all_platforms_returns_stats_and_results(self, compound_doc_item):
        """fetch_all_platforms returns stats dict with results key (P1.8-H)."""
        client = FlixPatrolClient("test_key")
        with patch("movietrace.sources.flixpatrol_api.get_json") as mock_get:
            mock_get.return_value = {"data": [compound_doc_item]}
            with patch("movietrace.sources.flixpatrol_api.time.sleep"):
                result = client.fetch_all_platforms(date_from="2026-05-10")
        assert isinstance(result, dict)
        assert "results" in result
        assert "planned_calls" in result
        assert "actual_calls" in result
        # Default: 4 countries × 6 platforms × 1 TV type = 24
        assert result["planned_calls"] == 24
        assert len(result["results"]) == 24
        # Check country is in keys
        sample_key = list(result["results"].keys())[0]
        parts = sample_key.split("/")
        assert len(parts) == 3  # country/platform/type
        assert result["tv_calls"] == 24
        assert result["movie_calls"] == 0

    def test_fetch_all_platforms_with_movies(self, compound_doc_item):
        """With fetch_movies=True, plan = 4×6×2 = 48."""
        client = FlixPatrolClient("test_key")
        with patch("movietrace.sources.flixpatrol_api.get_json") as mock_get:
            mock_get.return_value = {"data": [compound_doc_item]}
            with patch("movietrace.sources.flixpatrol_api.time.sleep"):
                result = client.fetch_all_platforms(date_from="2026-05-10", fetch_movies=True)
        assert result["planned_calls"] == 48
        assert result["tv_calls"] == 24
        assert result["movie_calls"] == 24

    def test_fetch_all_platforms_circuit_breaker_stops_after_first_fatal(self):
        """First 401 should stop all remaining FP requests (circuit breaker)."""
        client = FlixPatrolClient("bad_key")
        with patch("movietrace.sources.flixpatrol_api.get_json") as mock_get:
            mock_get.side_effect = FatalApiError(402, "HTTP Error 402: Payment Required")
            with patch("movietrace.sources.flixpatrol_api.time.sleep"):
                result = client.fetch_all_platforms(date_from="2026-05-14")
        # Should have stopped after first call, not 24
        assert result["actual_calls"] == 0
        assert result["planned_calls"] == 24
        assert result.get("circuit_breaker") is True
        assert "402" in result.get("error", "")
        # get_json should have been called only once
        assert mock_get.call_count == 1

    def test_fetch_top10_uses_closed_single_day_window_when_date_from_given(self, compound_doc_item):
        """A single-day fetch should not pull later snapshot dates."""
        client = FlixPatrolClient("test_key")
        with patch("movietrace.sources.flixpatrol_api.get_json") as mock_get:
            mock_get.return_value = {"data": [compound_doc_item]}
            client.fetch_top10(
                company=PLATFORM_COMPANY_IDS["netflix"],
                country=FP_COUNTRIES["united-states"],
                content_type=2,
                date_from="2026-05-13",
            )

        params = mock_get.call_args.kwargs["params"]
        assert params["date[from][gte]"] == "2026-05-13"
        assert params["date[from][lte]"] == "2026-05-13"


# ── _extract_http_status tests ──────────────────────────────────────────


class TestExtractHttpStatus:
    def test_401(self):
        assert _extract_http_status("HTTP Error 401: Unauthorized") == 401

    def test_403(self):
        assert _extract_http_status("HTTP Error 403: Forbidden") == 403

    def test_429(self):
        assert _extract_http_status("HTTP Error 429: Too Many Requests") == 429

    def test_502(self):
        assert _extract_http_status("HTTP Error 502: Bad Gateway") == 502

    def test_no_match(self):
        assert _extract_http_status("Connection refused") is None


# ── Dedup / DB tests ────────────────────────────────────────────────────


@pytest.fixture
def db_conn():
    """In-memory SQLite with migration 002 applied."""
    conn = sqlite3.connect(":memory:")
    conn.execute("pragma foreign_keys = on")
    migration_sql = (
        Path(__file__).parent.parent
        / "src/movietrace/db/migrations/002_flixpatrol_top10.sql"
    ).read_text()
    conn.executescript(migration_sql)
    conn.commit()
    return conn


class TestDedup:
    def test_same_fp_id_same_date_fails(self, db_conn):
        """Inserting same fp_id + snapshot_date twice should fail due to unique index."""
        db_conn.execute(
            """insert into flixpatrol_top10
               (fp_id, title, content_type, platform, country, snapshot_date,
                ranking, raw_payload_json)
               values (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("fp_001", "Test Movie", "movie", "netflix", "united-states",
             "2026-05-10", 1, "{}"),
        )
        db_conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """insert into flixpatrol_top10
                   (fp_id, title, content_type, platform, country, snapshot_date,
                    ranking, raw_payload_json)
                   values (?, ?, ?, ?, ?, ?, ?, ?)""",
                ("fp_001", "Test Movie", "movie", "netflix", "united-states",
                 "2026-05-10", 1, "{}"),
            )
            db_conn.commit()

    def test_same_fp_id_different_date_ok(self, db_conn):
        """Same fp_id with different snapshot_date should succeed."""
        db_conn.execute(
            """insert into flixpatrol_top10
               (fp_id, title, content_type, platform, country, snapshot_date,
                ranking, raw_payload_json)
               values (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("fp_001", "Test Movie", "movie", "netflix", "united-states",
             "2026-05-09", 1, "{}"),
        )
        db_conn.commit()
        db_conn.execute(
            """insert into flixpatrol_top10
               (fp_id, title, content_type, platform, country, snapshot_date,
                ranking, raw_payload_json)
               values (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("fp_001", "Test Movie", "movie", "netflix", "united-states",
             "2026-05-10", 2, "{}"),
        )
        db_conn.commit()

    def test_different_fp_id_same_date_ok(self, db_conn):
        """Different fp_id with same snapshot_date should succeed."""
        db_conn.execute(
            """insert into flixpatrol_top10
               (fp_id, title, content_type, platform, country, snapshot_date,
                ranking, raw_payload_json)
               values (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("fp_001", "Movie A", "movie", "netflix", "united-states",
             "2026-05-10", 1, "{}"),
        )
        db_conn.commit()
        db_conn.execute(
            """insert into flixpatrol_top10
               (fp_id, title, content_type, platform, country, snapshot_date,
                ranking, raw_payload_json)
               values (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("fp_002", "Movie B", "movie", "netflix", "united-states",
             "2026-05-10", 2, "{}"),
        )
        db_conn.commit()

    def test_ranking_check_constraint(self, db_conn):
        """ranking must be between 1 and 10."""
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """insert into flixpatrol_top10
                   (fp_id, title, content_type, platform, country, snapshot_date,
                    ranking, raw_payload_json)
                   values (?, ?, ?, ?, ?, ?, ?, ?)""",
                ("fp_001", "Test", "movie", "netflix", "united-states",
                 "2026-05-10", 0, "{}"),
            )
            db_conn.commit()

        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                """insert into flixpatrol_top10
                   (fp_id, title, content_type, platform, country, snapshot_date,
                    ranking, raw_payload_json)
                   values (?, ?, ?, ?, ?, ?, ?, ?)""",
                ("fp_002", "Test", "movie", "netflix", "united-states",
                 "2026-05-10", 11, "{}"),
            )
            db_conn.commit()

    def test_tmdb_id_null_allowed(self, db_conn):
        """tmdb_id can be NULL."""
        db_conn.execute(
            """insert into flixpatrol_top10
               (fp_id, title, content_type, platform, country, snapshot_date,
                ranking, tmdb_id, raw_payload_json)
               values (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("fp_001", "No TMDB", "movie", "netflix", "united-states",
             "2026-05-10", 5, None, "{}"),
        )
        db_conn.commit()
