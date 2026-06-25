"""Tests for council pack scenario resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from council.packs import load_pack, resolve_scenario, resolve_scenario_path


@pytest.fixture
def security_council_pack(tmp_path: Path, monkeypatch):
    pack_root = tmp_path / "config" / "councils" / "security-council"
    scenarios = pack_root / "scenarios"
    scenarios.mkdir(parents=True)
    (scenarios / "bindplane-integration.md").write_text("# Bindplane\n", encoding="utf-8")
    (scenarios / "detection-engineering-with-ai.md").write_text("# Detection AI\n", encoding="utf-8")
    (pack_root / "ideal_state.md").write_text("ideal", encoding="utf-8")
    (pack_root / "synthesis_format.md").write_text("format", encoding="utf-8")
    (pack_root / "experts.json").write_text("[]", encoding="utf-8")
    (pack_root / "council.json").write_text(
        json.dumps(
            {
                "name": "security-council",
                "description": "test",
                "ideal_state": "ideal_state.md",
                "synthesis_format": "synthesis_format.md",
                "experts": "experts.json",
                "default_scenario": "scenarios/bindplane-integration.md",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    return load_pack("security-council")


def test_resolve_scenario_by_slug(security_council_pack):
    path = resolve_scenario(security_council_pack, None, "detection-engineering-with-ai")
    assert path.name == "detection-engineering-with-ai.md"
    assert path.read_text(encoding="utf-8").startswith("# Detection AI")


def test_resolve_current_by_slug_without_md_suffix(security_council_pack):
    path = resolve_scenario(security_council_pack, "bindplane-integration", None)
    assert path.name == "bindplane-integration.md"


def test_resolve_scenario_case_insensitive(security_council_pack):
    path = resolve_scenario_path(security_council_pack, "Bindplane-Integration")
    assert path.name == "bindplane-integration.md"


def test_resolve_scenario_rejects_both_current_and_scenario(security_council_pack):
    with pytest.raises(ValueError, match="only one"):
        resolve_scenario(security_council_pack, "bindplane-integration", "detection-engineering-with-ai")


def test_resolve_scenario_unknown_lists_available(security_council_pack):
    with pytest.raises(FileNotFoundError, match="missing-scenario"):
        resolve_scenario_path(security_council_pack, "missing-scenario")
    with pytest.raises(FileNotFoundError, match="bindplane-integration"):
        resolve_scenario_path(security_council_pack, "missing-scenario")


def test_resolve_scenario_explicit_relative_path(security_council_pack, tmp_path: Path):
    path = resolve_scenario_path(
        security_council_pack,
        "config/councils/security-council/scenarios/detection-engineering-with-ai.md",
    )
    assert path.name == "detection-engineering-with-ai.md"
