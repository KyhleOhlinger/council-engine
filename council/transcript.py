"""Transcript formatting aligned with PAI Council OutputFormat.md."""

from __future__ import annotations

from datetime import date

ROUND_LABELS = {
    1: "Round 1: Initial Positions",
    2: "Round 2: Responses & Challenges",
    3: "Round 3: Synthesis",
}


def round_label(round_num: int) -> str:
    return ROUND_LABELS.get(round_num, f"Round {round_num}")


def format_agent_label(agent: dict, include_traits: bool = True) -> str:
    name = agent["name"]
    traits = agent.get("traits", "")
    if include_traits and traits:
        return f"**{name} ({traits}):**"
    return f"**{name}:**"


def format_round_section(round_num: int, agent_responses: list[tuple[dict, str]]) -> str:
    lines = [f"### {round_label(round_num)}", ""]
    include_traits = round_num == 1
    for agent, content in agent_responses:
        lines.append(format_agent_label(agent, include_traits=include_traits))
        lines.append(content.strip())
        lines.append("")
    return "\n".join(lines).rstrip()


def format_run_metadata(topic: str, run_date: date | None = None) -> str:
    day = (run_date or date.today()).isoformat()
    return f"**Date:** {day}\n**Topic:** {topic}\n"


def format_debate_header(topic: str, experts: list[dict], run_date: date | None = None) -> str:
    members = "\n".join(
        f"- {e['name']} ({e['traits']})" if e.get("traits") else f"- {e['name']}"
        for e in experts
    )
    return (
        f"## Council Debate: {topic}\n\n"
        f"{format_run_metadata(topic, run_date)}\n"
        f"**Council Members:**\n{members}\n"
        f"**Rounds:** 3 (Positions -> Responses -> Synthesis)\n"
    )


def format_quick_header(topic: str, experts: list[dict], run_date: date | None = None) -> str:
    names = ", ".join(expert["name"] for expert in experts)
    return (
        f"## Quick Council: {topic}\n\n"
        f"{format_run_metadata(topic, run_date)}\n"
        f"**Council Members:** {names}\n"
        f"**Mode:** Single round (fast perspectives)\n"
    )


def format_quick_perspectives(agent_responses: list[tuple[dict, str]]) -> str:
    lines = ["### Perspectives", ""]
    for agent, content in agent_responses:
        lines.append(format_agent_label(agent, include_traits=True))
        lines.append(content.strip())
        lines.append("")
    return "\n".join(lines).rstrip()


def assemble_debate_output(header: str, round_sections: list[str], synthesis: str) -> dict[str, str]:
    transcript = header + "\n\n" + "\n\n".join(round_sections)
    synthesis_block = f"### Council Synthesis\n\n{synthesis.strip()}"
    return {
        "document": f"{transcript}\n\n{synthesis_block}\n",
        "transcript": transcript,
        "synthesis": synthesis_block,
    }


def assemble_quick_output(header: str, perspectives: str, summary: str) -> dict[str, str]:
    document = f"{header}\n\n{perspectives}\n\n{summary.strip()}\n"
    return {
        "document": document,
        "transcript": f"{header}\n\n{perspectives}",
        "synthesis": summary.strip(),
    }
