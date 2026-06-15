"""Compose council experts from topic context (PAI ComposeAgent equivalent)."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable
from typing import Protocol

from .constants import COMPOSE_MAX_TOKENS, DEFAULT_PERSPECTIVE_SLOTS, OPTIMAL_EXPERTS


class CompleteFn(Protocol):
    def __call__(self, prompt: str, *, max_tokens: int | None = None) -> Awaitable[str]: ...


def build_compose_prompt(
    topic: str,
    current_state: str,
    ideal_state: str,
    expert_count: int = OPTIMAL_EXPERTS,
    compose_guide: str | None = None,
) -> str:
    slots = "\n".join(
        f"- **{s['slot']}** ({s['traits']}): {s['purpose']}"
        for s in DEFAULT_PERSPECTIVE_SLOTS
    )
    guide = ""
    if compose_guide:
        guide = f"\nDomain-specific composition guidance:\n{compose_guide}\n"

    return f"""You are the Council Composer. Create {expert_count} unique council experts for a structured debate.

Topic: {topic}

Full topic context:
{current_state}

Target standard (Ideal State):
{ideal_state}
{guide}
Use these PAI perspective slots as inspiration — tailor traits and personas to THIS topic:
{slots}

Rules:
- Each expert must have a unique name (never generic labels like Architect or Designer)
- Each expert must have topic-specific traits and a distinct analytical voice
- Personas must create genuine intellectual friction on this topic
- Return ONLY valid JSON: an array of {expert_count} objects with keys: name, traits, persona
"""


def parse_experts_response(raw: str) -> list[dict]:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("Composer did not return a JSON array of experts.")
    experts = json.loads(text[start : end + 1])
    if not isinstance(experts, list) or not experts:
        raise ValueError("Composer returned an empty expert list.")
    for expert in experts:
        if "name" not in expert or "persona" not in expert:
            raise ValueError("Each composed expert needs 'name' and 'persona'.")
    return experts


async def compose_council(
    topic: str,
    current_state: str,
    ideal_state: str,
    complete: CompleteFn,
    expert_count: int = OPTIMAL_EXPERTS,
    compose_guide: str | None = None,
) -> list[dict]:
    prompt = build_compose_prompt(
        topic, current_state, ideal_state, expert_count, compose_guide
    )
    raw = await complete(prompt, max_tokens=COMPOSE_MAX_TOKENS)
    return parse_experts_response(raw)
