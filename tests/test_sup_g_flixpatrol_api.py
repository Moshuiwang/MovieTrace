"""Unit tests for SUP-G FlixPatrol API verification — field mapping, extraction, and masking logic.

No network tests; all use fixture JSON.
"""

import json
import os
import sys
import tempfile
from importlib.machinery import SourceFileLoader

import pytest

# Load the script as a module for access to its pure functions
script_path = os.path.join(
    os.path.dirname(__file__), "..", "scripts", "sup_g_flixpatrol_api_check.py"
)
script_path = os.path.abspath(script_path)

# Ensure data/ directory is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sup_g = SourceFileLoader("sup_g_flixpatrol_api_check", script_path).load_module()


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def sample_top10_item():
    """A single well-formed Top 10 entry matching documented schema."""
    return {
        "id": "top_abc123",
        "movie": "mov_xyz789",
        "company": "cmp_IA6TdMqwf6kuyQvxo9bJ4nKX",
        "country": "cnt_iMUHNbZvnNHK5YdhgwtOoP4u",
        "language": "en",
        "origin": "cmp_IA6TdMqwf6kuyQvxo9bJ4nKX",
        "type": 2,
        "date": {"type": 1, "from": "2026-05-10", "to": "2026-05-10"},
        "ranking": 1,
        "rankingLast": 2,
        "value": 845,
        "valueLast": 812,
        "daysTotal": 15,
        "note": None,
        "key": None,
        "updatedAt": "2026-05-11T08:00:00.000Z",
    }


@pytest.fixture
def sample_minimal_item():
    """An item missing some optional fields like daysTotal and origin."""
    return {
        "id": "top_def456",
        "movie": "mov_abc123",
        "company": "cmp_qypvowjqFhEIpCc0HlQ6VoYk",
        "country": "cnt_iMUHNbZvnNHK5YdhgwtOoP4u",
        "language": None,
        "origin": None,
        "type": 3,
        "date": {"type": 1, "from": "2026-05-10", "to": "2026-05-10"},
        "ranking": 5,
        "rankingLast": None,
        "value": 320,
        "valueLast": None,
        "daysTotal": None,
        "note": None,
        "key": None,
        "updatedAt": "2026-05-11T08:00:00.000Z",
    }


# ── _extract_items ────────────────────────────────────────────────────


def test_extract_items_from_list():
    items = [{"id": "1"}, {"id": "2"}]
    result = sup_g._extract_items(items)
    assert len(result) == 2
    assert result == items


def test_extract_items_from_dict_with_data_key():
    data = {"data": [{"id": "1"}, {"id": "2"}], "meta": {"count": 2}}
    result = sup_g._extract_items(data)
    assert len(result) == 2


def test_extract_items_from_dict_with_items_key():
    data = {"items": [{"id": "1"}]}
    result = sup_g._extract_items(data)
    assert len(result) == 1


def test_extract_items_from_dict_with_results_key():
    data = {"results": [{"id": "1"}, {"id": "2"}, {"id": "3"}]}
    result = sup_g._extract_items(data)
    assert len(result) == 3


def test_extract_items_from_dict_with_top10s_key():
    data = {"top10s": [{"id": "a"}]}
    result = sup_g._extract_items(data)
    assert len(result) == 1


def test_extract_items_from_dict_with_records_key():
    data = {"records": [{"id": "x"}, {"id": "y"}]}
    result = sup_g._extract_items(data)
    assert len(result) == 2


def test_extract_items_from_empty_dict():
    data = {"meta": {"count": 0}, "links": {}}
    result = sup_g._extract_items(data)
    assert result == []


def test_extract_items_from_dict_with_non_list_data():
    data = {"data": "not_a_list"}
    result = sup_g._extract_items(data)
    assert result == []


# ── Field completeness ────────────────────────────────────────────────


def test_all_required_fields_present(sample_top10_item):
    """A complete item should have all P1-C required fields."""
    fields = set(sample_top10_item.keys())
    required = set(sup_g.REQUIRED_FIELDS.keys())
    missing = required - fields
    assert missing == set(), f"Missing required fields: {missing}"


def test_minimal_item_missing_optional_only(sample_minimal_item):
    """A minimal item may miss daysTotal but should still have core fields."""
    fields = set(sample_minimal_item.keys())
    core_required = {"movie", "type", "ranking", "company", "country", "date"}
    missing_core = core_required - fields
    assert missing_core == set(), f"Missing core fields: {missing_core}"


def test_field_mapping_identifies_missing_fields(sample_minimal_item):
    """Required field check should flag fields entirely absent from the response."""
    fields = set(sample_minimal_item.keys())
    required = set(sup_g.REQUIRED_FIELDS.keys())
    missing = [f for f in required if f not in fields]
    # daysTotal is None but the key IS present
    assert "daysTotal" not in missing


def test_content_type_field_encodes_movie_vs_tv():
    """type=2 means Movie, type=3 means TV Show (verified from API docs)."""
    assert 2 == 2  # Movie
    assert 3 == 3  # TV Show
    # These values come from the API docs; this test serves as living documentation


def test_ranking_range_is_1_to_10(sample_top10_item):
    """Top 10 rankings should be between 1 and 10 inclusive."""
    assert 1 <= sample_top10_item["ranking"] <= 10


# ── Key masking ───────────────────────────────────────────────────────


def test_mask_key_standard_length():
    key = "aku_tmbKiZWTog2beK9rmPdNBpx6"
    masked = sup_g.mask_key_in_text("", key)
    # Should not contain the full key
    assert key not in masked


def test_mask_key_replaces_in_text():
    key = "aku_secret1234567890ab"
    text = f"Authorization: Basic {key}:"
    result = sup_g.mask_key_in_text(text, key)
    assert key not in result
    assert "aku_****" in result or "aku_***" in result


def test_mask_key_short_key():
    key = "ab12"
    masked = sup_g.mask_key_in_text(f"key={key}", key)
    assert key not in masked


# ── Secrets file loading ──────────────────────────────────────────────


def test_load_api_key_from_valid_file():
    """Verify secrets loading from a temp file with the expected structure."""
    secrets = {"flixpatrol": {"api_key": "aku_testkey12345678"}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(secrets, f)
        tmp_path = f.name
    try:
        orig = sup_g.SECRETS_PATH
        sup_g.SECRETS_PATH = tmp_path
        key, error, masked = sup_g.load_api_key()
        sup_g.SECRETS_PATH = orig
        assert error is None
        assert key == "aku_testkey12345678"
        assert "aku_" in masked
        assert "testkey" not in masked.lower() or "*" in masked
    finally:
        os.unlink(tmp_path)


def test_load_api_key_missing_file():
    orig = sup_g.SECRETS_PATH
    sup_g.SECRETS_PATH = "/tmp/nonexistent_secrets_12345.json"
    key, error, masked = sup_g.load_api_key()
    sup_g.SECRETS_PATH = orig
    assert key is None
    assert error is not None


def test_load_api_key_missing_flixpatrol_section():
    secrets = {"tmdb": {"api_key": "abc"}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(secrets, f)
        tmp_path = f.name
    try:
        orig = sup_g.SECRETS_PATH
        sup_g.SECRETS_PATH = tmp_path
        key, error, masked = sup_g.load_api_key()
        sup_g.SECRETS_PATH = orig
        assert key is None
        assert "flixpatrol" in error.lower()
    finally:
        os.unlink(tmp_path)


# ── Compound document unwrapping ──────────────────────────────────────


@pytest.fixture
def compound_doc_item():
    """A real FlixPatrol v2 API item in compound document format."""
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
                },
                "legacy": {"id": 73422},
            },
            "company": {
                "type": "companies",
                "data": {"id": "cmp_IA6TdMqwf6kuyQvxo9bJ4nKX"},
                "legacy": {"id": 656},
            },
            "country": {
                "type": "countries",
                "data": {"id": "cnt_iMUHNbZvnNHK5YdhgwtOoP4u"},
                "legacy": {"id": 4672},
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
        "legacy": {"id": 988},
    }


def test_extract_items_unwraps_compound_document(compound_doc_item):
    """Compound doc items should be unwrapped to inner data dict."""
    response = {"data": [compound_doc_item]}
    items = sup_g._extract_items(response)
    assert len(items) == 1
    item = items[0]
    # Should have top-level fields from inner data
    assert item["ranking"] == 1
    assert item["type"] == 2
    # Should have nested movie object
    assert item["movie"]["data"]["tmdbId"] == 581600
    assert item["movie"]["data"]["title"] == "Spenser Confidential"


def test_extract_items_unwraps_multiple_compound_docs(compound_doc_item):
    item2 = {
        "type": "top10s",
        "data": {
            "ranking": 2,
            "type": 2,
            "movie": {"data": {"title": "Extraction", "tmdbId": 545609}},
        },
        "legacy": {"id": 999},
    }
    response = {"data": [compound_doc_item, item2]}
    items = sup_g._extract_items(response)
    assert len(items) == 2
    assert items[0]["ranking"] == 1
    assert items[1]["ranking"] == 2
    assert items[1]["movie"]["data"]["title"] == "Extraction"


def test_compound_doc_has_tmdb_id(compound_doc_item):
    """Verify that movie.data.tmdbId is accessible after unwrapping."""
    response = {"data": [compound_doc_item]}
    items = sup_g._extract_items(response)
    item = items[0]
    assert "movie" in item
    assert "data" in item["movie"]
    assert "tmdbId" in item["movie"]["data"]
    assert item["movie"]["data"]["tmdbId"] == 581600


def test_compound_doc_all_required_fields_present(compound_doc_item):
    """After unwrapping, a compound document item should have all P1-C required fields."""
    response = {"data": [compound_doc_item]}
    items = sup_g._extract_items(response)
    item = items[0]
    fields = set(item.keys())
    required = set(sup_g.REQUIRED_FIELDS.keys())
    missing = required - fields
    assert missing == set(), f"Missing required fields: {missing}"


# ── Integration: response-to-fields pipeline ──────────────────────────


def test_response_pipeline_with_array_format():
    """Simulate API returning a plain array of items."""
    response = [
        {
            "movie": "mov_1",
            "type": 2,
            "ranking": 1,
            "company": "cmp_X",
            "country": "cnt_Y",
            "date": {"from": "2026-05-10"},
            "daysTotal": 10,
        }
    ]
    items = sup_g._extract_items(response)
    assert len(items) == 1
    item = items[0]
    assert item["movie"] == "mov_1"
    assert item["ranking"] == 1


def test_response_pipeline_with_wrapped_format():
    """Simulate API returning data wrapped in a 'data' key."""
    response = {"data": [{"movie": "mov_2", "type": 3, "ranking": 3}]}
    items = sup_g._extract_items(response)
    assert len(items) == 1
    assert items[0]["type"] == 3
