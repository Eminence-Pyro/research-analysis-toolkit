"""
tests/parsers/test_schema_validator.py

Unit tests for research_engine/parsers/schema_validator.py

Covers:
  - validate_config() happy path for all four schema types
  - validate_config() catches missing required fields
  - validate_config() catches wrong types
  - validate_study_dir() returns one result per config file
  - assert_valid_study_dir() passes on a valid directory
  - assert_valid_study_dir() raises ConfigValidationError on bad configs
  - Graceful handling of missing schema files (no crash)
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from research_engine.parsers.schema_validator import (
    validate_config,
    validate_study_dir,
    assert_valid_study_dir,
    ConfigValidationError,
    ValidationResult,
)

# ── Fixtures ──────────────────────────────────────────────────

STUDY_DIR = Path(__file__).parent.parent.parent / "studies" / "immunization_aba"


@pytest.fixture()
def temp_study(tmp_path):
    """Copy the real immunization_aba study to a temp directory."""
    target = tmp_path / "study"
    shutil.copytree(STUDY_DIR, target)
    return target


# ── Happy-path tests ──────────────────────────────────────────

def test_validate_config_study_valid():
    data = json.loads((STUDY_DIR / "config.json").read_text())
    result = validate_config(data, "study", "config.json")
    assert result.valid, f"Expected valid. Errors: {result.errors}"
    assert result.errors == []


def test_validate_config_questionnaire_valid():
    data = json.loads((STUDY_DIR / "questionnaire.json").read_text())
    result = validate_config(data, "questionnaire", "questionnaire.json")
    assert result.valid, f"Expected valid. Errors: {result.errors}"


def test_validate_config_demographics_valid():
    data = json.loads((STUDY_DIR / "demographics.json").read_text())
    result = validate_config(data, "demographics", "demographics.json")
    assert result.valid, f"Expected valid. Errors: {result.errors}"


def test_validate_config_observation_valid():
    data = json.loads((STUDY_DIR / "observation.json").read_text())
    result = validate_config(data, "observation", "observation.json")
    assert result.valid, f"Expected valid. Errors: {result.errors}"


# ── Failure-mode tests ────────────────────────────────────────

def test_validate_config_study_missing_required_field():
    data = json.loads((STUDY_DIR / "config.json").read_text())
    del data["facilities"]
    result = validate_config(data, "study", "config.json")
    assert not result.valid
    assert any("facilities" in e for e in result.errors)


def test_validate_config_study_wrong_type_for_target_n():
    data = json.loads((STUDY_DIR / "config.json").read_text())
    data["target_n"] = "one-hundred-and-twenty"
    result = validate_config(data, "study", "config.json")
    assert not result.valid
    assert any("target_n" in e for e in result.errors)


def test_validate_config_study_target_n_below_minimum():
    data = json.loads((STUDY_DIR / "config.json").read_text())
    data["target_n"] = 0
    result = validate_config(data, "study", "config.json")
    assert not result.valid


def test_validate_config_questionnaire_empty_sections():
    data = json.loads((STUDY_DIR / "questionnaire.json").read_text())
    data["sections"] = {}
    result = validate_config(data, "questionnaire", "questionnaire.json")
    assert not result.valid


def test_validate_config_observation_missing_key():
    data = json.loads((STUDY_DIR / "observation.json").read_text())
    # Remove required 'key' field from first checklist item
    del data["checklist"][0]["key"]
    result = validate_config(data, "observation", "observation.json")
    assert not result.valid


def test_validate_config_bad_schema_name():
    """Unknown schema name returns a failed ValidationResult, not an exception."""
    result = validate_config({}, "nonexistent_schema", "test.json")
    assert not result.valid
    assert result.errors


# ── validate_study_dir tests ──────────────────────────────────

def test_validate_study_dir_all_pass():
    results = validate_study_dir(STUDY_DIR)
    assert "config.json" in results
    assert "questionnaire.json" in results
    assert "demographics.json" in results
    for fname, r in results.items():
        assert r.valid, f"{fname} failed: {r.errors}"


def test_validate_study_dir_returns_validation_results():
    results = validate_study_dir(STUDY_DIR)
    for r in results.values():
        assert isinstance(r, ValidationResult)


def test_validate_study_dir_bad_config(temp_study):
    config = json.loads((temp_study / "config.json").read_text())
    config["target_n"] = "bad"
    (temp_study / "config.json").write_text(json.dumps(config))

    results = validate_study_dir(temp_study)
    assert not results["config.json"].valid


def test_validate_study_dir_invalid_json(temp_study):
    (temp_study / "config.json").write_text("{ this is not json }")
    results = validate_study_dir(temp_study)
    assert not results["config.json"].valid
    assert any("Invalid JSON" in e for e in results["config.json"].errors)


def test_validate_study_dir_missing_required_file(temp_study):
    (temp_study / "config.json").unlink()
    results = validate_study_dir(temp_study)
    assert not results["config.json"].valid
    assert any("not found" in e for e in results["config.json"].errors)


# ── assert_valid_study_dir tests ──────────────────────────────

def test_assert_valid_study_dir_passes():
    """Should not raise on the real immunization_aba study."""
    assert_valid_study_dir(STUDY_DIR)  # no exception = pass


def test_assert_valid_study_dir_raises_on_bad_config(temp_study):
    config = json.loads((temp_study / "config.json").read_text())
    del config["title"]
    del config["facilities"]
    (temp_study / "config.json").write_text(json.dumps(config))

    with pytest.raises(ConfigValidationError) as exc_info:
        assert_valid_study_dir(temp_study)

    msg = str(exc_info.value)
    assert "config.json" in msg
    assert "facilities" in msg or "title" in msg


def test_assert_valid_study_dir_error_message_is_readable(temp_study):
    config = json.loads((temp_study / "config.json").read_text())
    config["target_n"] = -5
    (temp_study / "config.json").write_text(json.dumps(config))

    with pytest.raises(ConfigValidationError) as exc_info:
        assert_valid_study_dir(temp_study)

    msg = str(exc_info.value)
    # Should be human-readable — contains the file and field name
    assert "config.json" in msg
    assert "target_n" in msg
