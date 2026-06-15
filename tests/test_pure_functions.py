"""Unit tests for deterministic, API-free helpers."""

from __future__ import annotations

from datetime import date

import pytest

from council.compose import parse_experts_response
from council.output import slugify_topic
from council.prompts import convergence_threshold, extract_source_url, extract_topic
from council.transcript import (
    RunContext,
    assemble_debate_output,
    assemble_escalated_output,
    assemble_quick_output,
    format_round_section,
    strip_expert_report_bloat,
    strip_model_appendix,
)

RUN_DATE = date(2026, 6, 15)
EXPERTS = [
    {"name": "The Skeptic", "traits": "adversarial", "persona": "p"},
    {"name": "The Builder", "traits": "pragmatic", "persona": "p"},
]


# --- slugify_topic ---------------------------------------------------------

def test_slugify_strips_prefix_and_punctuation():
    assert slugify_topic("DRAFT BLOG POST: Why VPNs Are Dead!") == "why-vpns-are-dead"


def test_slugify_empty_falls_back():
    assert slugify_topic("!!!") == "council-review"


def test_slugify_respects_max_length():
    assert len(slugify_topic("word " * 100, max_length=20)) <= 20


# --- extract_topic ---------------------------------------------------------

def test_extract_topic_uses_first_heading():
    assert extract_topic("# My Title\n\nbody") == "My Title"


def test_extract_topic_without_heading_uses_first_line():
    assert extract_topic("just a line\nsecond") == "just a line"


def test_extract_topic_empty():
    assert extract_topic("   ") == "Council Review"


# --- extract_source_url ----------------------------------------------------

def test_extract_source_url_bold_label():
    assert extract_source_url("**URL:** https://example.com/a") == "https://example.com/a"


def test_extract_source_url_plain_label():
    assert extract_source_url("URL: https://example.com/b") == "https://example.com/b"


def test_extract_source_url_markdown_link_fallback():
    assert extract_source_url("see [post](https://example.com/c) here") == "https://example.com/c"


def test_extract_source_url_none():
    assert extract_source_url("no link at all") is None


# --- convergence_threshold -------------------------------------------------

@pytest.mark.parametrize("count,expected", [(1, 1), (2, 2), (3, 3), (5, 3)])
def test_convergence_threshold(count, expected):
    assert convergence_threshold(count) == expected


# --- parse_experts_response ------------------------------------------------

def test_parse_experts_plain_json():
    raw = '[{"name": "A", "persona": "p"}]'
    assert parse_experts_response(raw) == [{"name": "A", "persona": "p"}]


def test_parse_experts_fenced_json():
    raw = '```json\n[{"name": "A", "persona": "p"}]\n```'
    assert parse_experts_response(raw)[0]["name"] == "A"


def test_parse_experts_rejects_missing_keys():
    with pytest.raises(ValueError):
        parse_experts_response('[{"name": "A"}]')


def test_parse_experts_rejects_non_array():
    with pytest.raises(ValueError):
        parse_experts_response("not json")


# --- strip_model_appendix --------------------------------------------------

def test_strip_model_appendix_removes_appendix_heading():
    text = "## Final Recommendation\n\nDo X.\n\n## Appendix: Council Debate Transcript\n\nnoise"
    assert strip_model_appendix(text) == "## Final Recommendation\n\nDo X."


def test_strip_model_appendix_removes_round_heading():
    text = "## Final Recommendation\n\nDo X.\n\n### Round 1: Initial Positions\n\nnoise"
    assert strip_model_appendix(text) == "## Final Recommendation\n\nDo X."


def test_strip_model_appendix_keeps_clean_text():
    text = "## Final Recommendation\n\nDo X."
    assert strip_model_appendix(text) == text


# --- transcript sanitization ----------------------------------------------

def test_format_round_section_strips_duplicate_role_heading():
    responses = [(EXPERTS[0], "**The Skeptic — Round 1**\n\nReal content.")]
    section = format_round_section(1, responses)
    assert "**The Skeptic — Round 1**" not in section
    assert "Real content." in section


def test_format_round_section_strips_round_3_verdict_bloat():
    bloated = (
        "We agree on inventory gating and disagree on Method 4 urgency.\n\n"
        "## Final Recommendation\n\n"
        "**Priority:** MONITOR\n\n"
        "### Actionable Items\n\n1. Do inventory"
    )
    section = format_round_section(3, [(EXPERTS[0], bloated)])
    assert "We agree on inventory gating" in section
    assert "## Final Recommendation" not in section
    assert "Actionable Items" not in section


def test_strip_expert_report_bloat_removes_placeholder_appendix():
    text = (
        "Concise synthesis here.\n\n"
        "## Appendix: Full Debate Transcript\n\n"
        "*(Included in user context above)*"
    )
    assert "Concise synthesis here." in strip_expert_report_bloat(text)
    assert "Appendix" not in strip_expert_report_bloat(text)


def test_strip_expert_report_bloat_keeps_plain_prose():
    text = (
        "**Council agreement:** Inventory first.\n\n"
        "**Where I still disagree:** Lab gating.\n\n"
        "My bottom line: monitor until inventory completes."
    )
    assert strip_expert_report_bloat(text) == text


# --- document assembly ordering -------------------------------------------

def test_debate_output_is_bluf_first_with_front_matter():
    doc = assemble_debate_output(
        "Topic",
        RUN_DATE,
        EXPERTS,
        ["### Round 1: Initial Positions\n\n**The Skeptic:** hi"],
        "## Final Recommendation\n\nProceed.",
        context=RunContext(
            pack_name="security",
            pack_description="Security triage",
            scenario_path="config/scenario.md",
            source_url="https://e.com",
            engine="cursor",
            model="composer-2.5",
        ),
    )["document"]
    assert doc.startswith("---\n")
    assert "pack: \"security\"" in doc
    assert 'pack_description: "Security triage"' in doc
    assert 'scenario: "config/scenario.md"' in doc
    assert 'source_url: "https://e.com"' in doc
    assert '  - name: "The Skeptic"' in doc
    assert "    traits: \"adversarial\"" in doc
    assert "# Council Verdict" not in doc
    assert doc.index("## Final Recommendation") < doc.index("## Appendix")


def test_quick_output_orders_and_lists_members_in_front_matter():
    doc = assemble_quick_output(
        "Topic",
        RUN_DATE,
        EXPERTS,
        "### Perspectives\n\n**The Skeptic:** hi",
        "## Final Recommendation\n\nProceed.",
    )["document"]
    assert '  - name: "The Skeptic"' in doc
    assert "# Council Verdict" not in doc
    assert doc.index("## Final Recommendation") < doc.index("## Appendix")


def test_escalated_output_single_front_matter_block():
    doc = assemble_escalated_output(
        "Topic",
        RUN_DATE,
        EXPERTS,
        ["### Round 1: Initial Positions\n\n**The Skeptic:** hi"],
        "## Final Recommendation\n\nFull debate verdict.",
        "## Final Recommendation\n\nQuick verdict.",
        "### Perspectives\n\n**The Skeptic:** quick take",
        context=RunContext(pack_name="security"),
    )["document"]
    assert doc.startswith("---\n")
    assert "# Council Verdict" not in doc
    assert "escalated: true" in doc
    assert doc.count('pack: "security"') == 1
    assert "Superseded Quick Triage" in doc
