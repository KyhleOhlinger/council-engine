"""Transcript formatting aligned with PAI Council OutputFormat.md."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

ROUND_LABELS = {
    1: "Round 1: Initial Positions",
    2: "Round 2: Responses & Challenges",
    3: "Round 3: Synthesis",
}


@dataclass
class RunContext:
    pack_name: str | None = None
    pack_description: str | None = None
    scenario_path: str | None = None
    source_url: str | None = None  # optional; e.g. blog-triage packs with linked scenarios
    engine: str | None = None
    model: str | None = None


def round_label(round_num: int) -> str:
    return ROUND_LABELS.get(round_num, f"Round {round_num}")


def format_agent_label(agent: dict, include_traits: bool = True) -> str:
    name = agent["name"]
    traits = agent.get("traits", "")
    if include_traits and traits:
        return f"**{name} ({traits}):**"
    return f"**{name}:**"


def _normalize_heading(text: str) -> str:
    return re.sub(r"\*+", "", text).strip().lower()


_SYNTHESIS_SECTION_HEADINGS = (
    "final recommendation",
    "priority tier",
    "blog post breakdown",
    "blog summary",
    "points of convergence",
    "remaining disagreements",
    "organizational relevance",
    "actionable items",
    "actionable next steps",
    "detection opportunities",
    "why this may not matter",
    "council agreement",
    "justification for",
    "uncertainty requiring validation",
    "mitre mapping",
    "executive synthesis",
    "validation before engineering",
)


def _is_duplicate_synthesis_heading(heading: str) -> bool:
    normalized = _normalize_heading(heading)
    if normalized.startswith("appendix") or "debate transcript" in normalized:
        return True
    if re.match(r"round\s*\d+\s*[:\-]", normalized):
        return True
    return any(
        normalized.startswith(prefix) or normalized == prefix
        for prefix in _SYNTHESIS_SECTION_HEADINGS
    )


def strip_expert_report_bloat(content: str) -> str:
    """Trim expert Round 3 text that re-emits a full executive verdict."""
    lines = content.splitlines()
    cut_at = len(lines)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^\*\([^)]*(?:included|provided|above|source material)[^)]*\)\*$", stripped, re.I):
            cut_at = index
            break
        heading_match = re.match(r"^#{1,6}\s+(.*)$", stripped)
        if heading_match and _is_duplicate_synthesis_heading(heading_match.group(1)):
            cut_at = index
            break
        if re.match(
            r"^\*\*(?:Final [Rr]ecommendation|Priority [Tt]ier|Blog Summary|Executive [Ss]ynthesis|MITRE [Mm]apping)[^*]*\*\*:?\s*$",
            stripped,
        ):
            cut_at = index
            break
    return "\n".join(lines[:cut_at]).rstrip()


def _sanitize_agent_response(agent: dict, content: str) -> str:
    """Strip duplicate name/round headings the model often prepends."""
    name = re.escape(agent["name"])
    patterns = (
        rf"^\*\*{name}[^*]*\*\*\s*$",
        rf"^\*\*[^*]+ — Round \d+\*\*\s*$",
        rf"^{name}\s*—\s*Round \d+\s*$",
        rf"^\*\*{name}\s*—\s*Round \d+\*\*\s*$",
        r"^\*\*Initial position\*\*\s*$",
        r"^\*\*Final [Rr]ecommendation[^*]*\*\*:?\s*$",
        r"^\*\*Final [Rr]ecommendation \(preview\)[^*]*\*\*:?\s*$",
        r"^- \*\*Priority:\*\*.*$",
    )
    lines = content.strip().splitlines()
    while lines:
        line = lines[0].strip()
        if not line:
            lines.pop(0)
            continue
        if any(re.match(pattern, line, re.IGNORECASE) for pattern in patterns):
            lines.pop(0)
            continue
        break
    return "\n".join(lines).strip()


def strip_model_appendix(synthesis: str) -> str:
    """Drop any transcript/appendix section the orchestrator emitted itself.

    The synthesis model occasionally reproduces an "Appendix" or round-by-round
    block; the real transcript is appended separately, so cut from the first such
    heading to the end to avoid duplicate sections.
    """
    lines = synthesis.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^#{1,6}\s+(.*)$", line)
        if not match:
            continue
        heading = match.group(1).strip().lower()
        if (
            heading.startswith("appendix")
            or "debate transcript" in heading
            or re.match(r"round\s*\d+\s*[:\-]", heading)
        ):
            return "\n".join(lines[:index]).rstrip()
    return synthesis.rstrip()


def format_round_section(round_num: int, agent_responses: list[tuple[dict, str]]) -> str:
    lines = [f"### {round_label(round_num)}", ""]
    include_traits = round_num == 1
    for agent, content in agent_responses:
        lines.append(format_agent_label(agent, include_traits=include_traits))
        cleaned = _sanitize_agent_response(agent, content)
        if round_num == 3:
            cleaned = strip_expert_report_bloat(cleaned)
        lines.append(cleaned)
        lines.append("")
    return "\n".join(lines).rstrip()


def _yaml_scalar(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def format_front_matter(
    topic: str,
    run_date: date | None,
    *,
    workflow: str,
    experts: list[dict] | None = None,
    context: RunContext | None = None,
    escalated: bool = False,
) -> str:
    day = (run_date or date.today()).isoformat()
    ctx = context or RunContext()
    fields: list[str] = [
        f"date: {_yaml_scalar(day)}",
        f"topic: {_yaml_scalar(topic)}",
        f"workflow: {workflow}",
    ]
    if escalated:
        fields.append("escalated: true")
    if ctx.pack_name:
        fields.append(f"pack: {_yaml_scalar(ctx.pack_name)}")
    if ctx.pack_description:
        fields.append(f"pack_description: {_yaml_scalar(ctx.pack_description)}")
    if ctx.scenario_path:
        fields.append(f"scenario: {_yaml_scalar(ctx.scenario_path)}")
    if ctx.source_url:
        fields.append(f"source_url: {_yaml_scalar(ctx.source_url)}")
    if ctx.engine:
        fields.append(f"engine: {_yaml_scalar(ctx.engine)}")
    if ctx.model:
        fields.append(f"model: {_yaml_scalar(ctx.model)}")
    if experts:
        fields.append("council_members:")
        for expert in experts:
            fields.append(f"  - name: {_yaml_scalar(expert['name'])}")
            if expert.get("traits"):
                fields.append(f"    traits: {_yaml_scalar(expert['traits'])}")
    body = "\n".join(fields)
    return f"---\n{body}\n---\n"


def format_quick_perspectives(agent_responses: list[tuple[dict, str]]) -> str:
    lines = ["### Perspectives", ""]
    for agent, content in agent_responses:
        lines.append(format_agent_label(agent, include_traits=True))
        lines.append(_sanitize_agent_response(agent, content))
        lines.append("")
    return "\n".join(lines).rstrip()


def format_transcript_appendix(
    sections: list[str],
    *,
    workflow: str = "debate",
) -> str:
    title = (
        "## Appendix: Council Debate Transcript"
        if workflow == "debate"
        else "## Appendix: Council Perspectives"
    )
    body = "\n\n".join(sections).strip()
    if body:
        return f"{title}\n\n{body}"
    return title


def _assemble(
    front_matter: str,
    analysis: str,
    appendix: str,
    *,
    preamble: str = "",
) -> dict[str, str]:
    body = analysis
    if preamble:
        body = f"{preamble}\n\n{body}"
    document = f"{front_matter}\n{body}\n\n---\n\n{appendix}\n"
    return {
        "document": document,
        "transcript": appendix,
        "synthesis": analysis,
    }


def assemble_debate_output(
    topic: str,
    run_date: date | None,
    experts: list[dict],
    round_sections: list[str],
    synthesis: str,
    *,
    context: RunContext | None = None,
) -> dict[str, str]:
    front_matter = format_front_matter(
        topic, run_date, workflow="debate", experts=experts, context=context
    )
    analysis = strip_model_appendix(synthesis.strip())
    appendix = format_transcript_appendix(round_sections, workflow="debate")
    return _assemble(front_matter, analysis, appendix)


def assemble_quick_output(
    topic: str,
    run_date: date | None,
    experts: list[dict],
    perspectives: str,
    summary: str,
    *,
    context: RunContext | None = None,
) -> dict[str, str]:
    front_matter = format_front_matter(
        topic, run_date, workflow="quick", experts=experts, context=context
    )
    analysis = strip_model_appendix(summary.strip())
    appendix = format_transcript_appendix([perspectives], workflow="quick")
    return _assemble(front_matter, analysis, appendix)


def assemble_escalated_output(
    topic: str,
    run_date: date | None,
    experts: list[dict],
    round_sections: list[str],
    debate_synthesis: str,
    quick_summary: str,
    quick_perspectives: str,
    *,
    context: RunContext | None = None,
) -> dict[str, str]:
    """Single-document output for a QUICK check that auto-escalated to DEBATE.

    The full debate verdict is primary; the superseded quick triage and both
    transcripts are preserved in the appendix under one metadata block.
    """
    front_matter = format_front_matter(
        topic, run_date, workflow="debate", experts=experts, context=context, escalated=True
    )
    analysis = strip_model_appendix(debate_synthesis.strip())
    note = (
        "> Escalated from a QUICK check after the initial perspectives flagged "
        "enough complexity to warrant a full 3-round debate."
    )
    debate_appendix = format_transcript_appendix(round_sections, workflow="debate")
    quick_block = (
        "## Appendix: Superseded Quick Triage\n\n"
        f"{strip_model_appendix(quick_summary.strip())}\n\n"
        f"{quick_perspectives}"
    )
    appendix = f"{debate_appendix}\n\n---\n\n{quick_block}"
    return _assemble(front_matter, analysis, appendix, preamble=note)
