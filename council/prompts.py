"""PAI Council prompt templates.

Standalone extension: packs supply current_state + ideal_state as PAI "topic context"
and target standard. Round prompts follow PAI Council Workflows/Debate.md and Quick.md.
"""

from __future__ import annotations

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
- Areas of convergence require agreement from at least {threshold} council members
- Remaining disagreements must acknowledge unresolved trade-offs honestly
- The recommended path must be actionable and grounded in the debate transcript
- Do not invent arguments that were not raised in the transcript
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

### Quick Summary

**Consensus:** [Do they generally agree? On what?]
**Concerns:** [Any red flags raised?]
**Recommendation:** [Proceed / Reconsider / Need full debate]

If significant disagreement or complex trade-offs exist, note that a full 3-round council debate is warranted.
"""
