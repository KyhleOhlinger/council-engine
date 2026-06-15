"""PAI Council prompt templates.

Standalone extension: packs supply current_state + ideal_state as PAI "topic context"
and target standard. Round prompts follow PAI Council Workflows/Debate.md and Quick.md.
"""

from __future__ import annotations

import re

from .constants import (
    DEBATE_WORDS_MAX,
    DEBATE_WORDS_MIN,
    PAI_CONVERGENCE_MIN,
    QUICK_WORDS_MAX,
    QUICK_WORDS_MIN,
)


def extract_topic(current_state: str) -> str:
    for line in current_state.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    if current_state.strip():
        return current_state.strip().splitlines()[0][:120]
    return "Council Review"


def extract_source_url(current_state: str) -> str | None:
    # Prefer an explicit "URL:" label (with or without markdown bold / link wrapping).
    labelled = re.search(
        r"\bURL\b\s*[:*]*\s*\[?<?(https?://[^\s\])>]+)",
        current_state,
        re.IGNORECASE,
    )
    if labelled:
        return labelled.group(1)
    # Fallback: first markdown link target.
    link = re.search(r"\]\((https?://[^\s)]+)\)", current_state)
    if link:
        return link.group(1)
    return None


_RESPONSE_STYLE = """
Response formatting:
- Do NOT include your name, role, or round number as a heading
- Speak directly in first person; the transcript already labels you
"""


def agent_preamble(agent: dict) -> str:
    traits = agent.get("traits", "")
    traits_line = f"\nTraits: {traits}" if traits else ""
    return f"You are {agent['name']}.{traits_line}\nPersona: {agent['persona']}\n"


def topic_context(topic: str, current_state: str, ideal_state: str) -> str:
    """PAI Topic + full context block (artifact review extension)."""
    return f"""Topic: {topic}

Full topic context:
{current_state}

Target standard (Ideal State):
{ideal_state}
"""


def build_round_1_prompt(agent: dict, topic: str, current_state: str, ideal_state: str) -> str:
    return f"""{agent_preamble(agent)}
COUNCIL DEBATE - ROUND 1: INITIAL POSITIONS

{topic_context(topic, current_state, ideal_state)}

Give your initial position on this topic from your specialized perspective.
- Speak in first person as your character
- Be specific and substantive ({DEBATE_WORDS_MIN}-{DEBATE_WORDS_MAX} words)
- State your key concern, recommendation, or insight
- You'll respond to other council members in Round 2
{_RESPONSE_STYLE}
"""


def build_round_2_prompt(
    agent: dict,
    topic: str,
    current_state: str,
    ideal_state: str,
    round_1_transcript: str,
) -> str:
    return f"""{agent_preamble(agent)}
COUNCIL DEBATE - ROUND 2: RESPONSES & CHALLENGES

{topic_context(topic, current_state, ideal_state)}

Here's what the council said in Round 1:
{round_1_transcript}

Now respond to the other council members:
- Reference specific points they made ("I disagree with [Name]'s point about X...")
- Challenge assumptions or add nuance
- Build on points you agree with
- Maintain your specialized perspective
- {DEBATE_WORDS_MIN}-{DEBATE_WORDS_MAX} words

The value is in genuine intellectual friction -- engage with their actual arguments.
{_RESPONSE_STYLE}
"""


_ROUND_3_STYLE = """
Round 3 response rules (strict):
- Write a brief closing synthesis in plain prose — NOT a full executive report
- Maximum {max_words} words total
- Do NOT use markdown section headings (no ## or ### titles)
- Do NOT output a "Final Recommendation" block, priority tier label, tables, numbered action lists, or MITRE mappings
- Do NOT reproduce blog breakdown, detection tables, actionable items, or organizational relevance sections
- Do NOT include an Appendix or placeholder text such as "included in user context above"
- Cover only: where the council agrees, where you still disagree, and your bottom-line recommendation
"""


def build_round_3_prompt(
    agent: dict,
    topic: str,
    current_state: str,
    ideal_state: str,
    round_1_transcript: str,
    round_2_transcript: str,
) -> str:
    return f"""{agent_preamble(agent)}
COUNCIL DEBATE - ROUND 3: SYNTHESIS

{topic_context(topic, current_state, ideal_state)}

Full debate transcript so far:

### Round 1: Initial Positions
{round_1_transcript}

### Round 2: Responses & Challenges
{round_2_transcript}

Final synthesis from your perspective:
- Where does the council agree?
- Where do you still disagree with others?
- What's your final recommendation given the full discussion?
- {DEBATE_WORDS_MIN}-{DEBATE_WORDS_MAX} words

Be honest about remaining disagreements -- forced consensus is worse than acknowledged tension.
{_ROUND_3_STYLE.format(max_words=DEBATE_WORDS_MAX)}
{_RESPONSE_STYLE}
"""


def build_quick_prompt(agent: dict, topic: str, current_state: str, ideal_state: str) -> str:
    return f"""{agent_preamble(agent)}
QUICK COUNCIL CHECK

{topic_context(topic, current_state, ideal_state)}

Give your immediate take from your specialized perspective:
- Key concern, insight, or recommendation
- {QUICK_WORDS_MIN}-{QUICK_WORDS_MAX} words max
- Be direct and specific

This is a quick sanity check, not a full debate.
{_RESPONSE_STYLE}
"""


def convergence_threshold(expert_count: int) -> int:
    return min(expert_count, PAI_CONVERGENCE_MIN)


def build_council_synthesis_prompt(
    topic: str,
    current_state: str,
    ideal_state: str,
    synthesis_format: str,
    full_transcript: str,
    expert_count: int,
) -> str:
    threshold = convergence_threshold(expert_count)
    return f"""You are the Council Orchestrator. Review the completed multi-agent council debate and produce the final executive synthesis.

{topic_context(topic, current_state, ideal_state)}

Full Debate Transcript:
{full_transcript}

Required Output Format:
{synthesis_format}

Additional synthesis rules:
- Lead with Final Recommendation — assume the reader only reads the first screen
- The Final Recommendation must be a complete executive summary on its own
- Areas of convergence require agreement from at least {threshold} council members
- Remaining disagreements must acknowledge unresolved trade-offs honestly
- The recommended path must be actionable and grounded in the debate transcript
- Do not invent arguments that were not raised in the transcript
- Do not repeat the Final Recommendation verbatim in later sections
- Do NOT reproduce the debate transcript, an Appendix, or round-by-round sections; the transcript is appended separately
- Do NOT quote or paraphrase Round 3 expert responses at length; summarize tensions and decisions only
"""


def build_quick_summary_prompt(
    topic: str,
    current_state: str,
    ideal_state: str,
    perspectives_transcript: str,
) -> str:
    return f"""You are the Council Orchestrator. Summarize the quick council perspectives.

{topic_context(topic, current_state, ideal_state)}

Perspectives:
{perspectives_transcript}

Output exactly this markdown structure:

## Final Recommendation
**Recommendation:** [Proceed / Reconsider / Need full debate]

(2-3 sentences — bottom line for a busy reader. State what to do next and what would trigger a full debate.)

## Quick Analysis
**Consensus:** [Do they generally agree? On what?]
**Concerns:** [Any red flags raised?]

If significant disagreement or complex trade-offs exist, note that a full 3-round council debate is warranted.
"""
