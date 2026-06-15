"""Shared PAI Council orchestration logic for all LLM backends."""

from __future__ import annotations

import asyncio
import re
import warnings
from abc import ABC, abstractmethod
from datetime import date

from .constants import (
    DEBATE_MAX_TOKENS,
    MAX_EXPERTS,
    MIN_EXPERTS,
    QUICK_MAX_TOKENS,
    SYNTHESIS_MAX_TOKENS,
)
from .output import fill_run_variables
from .prompts import (
    build_council_synthesis_prompt,
    build_quick_prompt,
    build_quick_summary_prompt,
    build_round_1_prompt,
    build_round_2_prompt,
    build_round_3_prompt,
    extract_topic,
)
from .transcript import (
    assemble_debate_output,
    assemble_quick_output,
    format_debate_header,
    format_quick_header,
    format_quick_perspectives,
    format_round_section,
    round_label,
)

_ESCALATION_PATTERNS = (
    r"need full debate",
    r"full (?:3[- ]round )?council debate",
    r"full debate is warranted",
    r"warrant(?:s|ed)?\s+a\s+full",
)


def _should_escalate(quick_summary: str) -> bool:
    text = quick_summary.lower()
    return any(re.search(p, text) for p in _ESCALATION_PATTERNS)


def _escalation_notice() -> str:
    return (
        "This topic has enough complexity for a full council debate. "
        "Re-run with `--workflow debate` for a 3-round structured discussion."
    )


class CouncilEngineBase(ABC):
    def __init__(
        self,
        current_state: str,
        ideal_state: str,
        synthesis_format: str,
        experts: list[dict],
        workflow: str = "debate",
        topic: str | None = None,
        run_date: date | None = None,
        auto_escalate: bool = False,
        validate_experts: bool = True,
    ):
        if validate_experts:
            self._validate_experts(experts)
        self.topic = topic or extract_topic(current_state)
        self.run_date = run_date or date.today()
        self.current_state = current_state
        self.ideal_state = ideal_state
        self.synthesis_format = fill_run_variables(synthesis_format, self.topic, self.run_date)
        self.experts = experts
        self.workflow = workflow
        self.auto_escalate = auto_escalate
        self.round_sections: list[str] = []

    @staticmethod
    def _validate_experts(experts: list[dict]) -> None:
        if not experts:
            raise ValueError("At least one expert is required.")
        count = len(experts)
        if count < MIN_EXPERTS:
            warnings.warn(
                f"PAI Council recommends {MIN_EXPERTS}-{MAX_EXPERTS} experts; "
                f"you have {count}. Consider adding experts or using --compose.",
                stacklevel=2,
            )
        elif count > MAX_EXPERTS:
            warnings.warn(
                f"PAI Council recommends at most {MAX_EXPERTS} experts; "
                f"you have {count}. More agents may dilute debate quality.",
                stacklevel=2,
            )
        for expert in experts:
            if "name" not in expert or "persona" not in expert:
                raise ValueError("Each expert must include 'name' and 'persona'.")

    @abstractmethod
    async def complete(self, prompt: str, *, max_tokens: int | None = None) -> str:
        """Send a prompt to the configured LLM backend and return text."""

    async def run(self) -> dict[str, str]:
        if self.workflow == "quick":
            return await self._run_quick()
        return await self._run_debate()

    async def _run_debate(self) -> dict[str, str]:
        print(f"Starting Council Debate ({len(self.experts)} members, 3 rounds)...")
        header = format_debate_header(self.topic, self.experts, self.run_date)
        print(header)

        for round_num in (1, 2, 3):
            self.round_sections.append(await self._run_round(round_num))

        print("Synthesizing Council Verdict...")
        synthesis = await self._synthesize_debate()
        return assemble_debate_output(header, self.round_sections, synthesis)

    async def _run_quick(self) -> dict[str, str]:
        print(f"Starting Quick Council ({len(self.experts)} members, 1 round)...")
        header = format_quick_header(self.topic, self.experts, self.run_date)
        print(header)

        responses = await self._gather(
            self._build_quick_prompt,
            max_tokens=QUICK_MAX_TOKENS,
        )
        perspectives = format_quick_perspectives(list(zip(self.experts, responses, strict=True)))

        print("Synthesizing Quick Summary...")
        summary = await self._synthesize_quick(perspectives)
        result = assemble_quick_output(header, perspectives, summary)

        if _should_escalate(summary):
            print(f"\n⚠️  {_escalation_notice()}")
            if self.auto_escalate:
                print("Auto-escalating to full DEBATE workflow...\n")
                self.round_sections.clear()
                debate_result = await self._run_debate()
                debate_result["document"] = (
                    f"{result['document']}\n\n---\n\n## Escalation\n\n"
                    f"{_escalation_notice()}\n\n{debate_result['document']}"
                )
                return debate_result

        return result

    async def _run_round(self, round_num: int) -> str:
        print(f"Executing {round_label(round_num)}...")
        responses = await self._gather(
            lambda agent: self._build_round_prompt(agent, round_num),
            max_tokens=DEBATE_MAX_TOKENS,
        )
        return format_round_section(
            round_num,
            list(zip(self.experts, responses, strict=True)),
        )

    async def _gather(self, prompt_builder, *, max_tokens: int) -> list[str]:
        tasks = [self.complete(prompt_builder(a), max_tokens=max_tokens) for a in self.experts]
        return await asyncio.gather(*tasks)

    def _build_round_prompt(self, agent: dict, round_num: int) -> str:
        ctx = (self.topic, self.current_state, self.ideal_state)
        if round_num == 1:
            return build_round_1_prompt(agent, *ctx)
        if round_num == 2:
            return build_round_2_prompt(agent, *ctx, self.round_sections[0])
        if round_num == 3:
            return build_round_3_prompt(agent, *ctx, self.round_sections[0], self.round_sections[1])
        raise ValueError(f"Unsupported round: {round_num}")

    def _build_quick_prompt(self, agent: dict) -> str:
        return build_quick_prompt(agent, self.topic, self.current_state, self.ideal_state)

    async def _synthesize_debate(self) -> str:
        prompt = build_council_synthesis_prompt(
            self.topic,
            self.current_state,
            self.ideal_state,
            self.synthesis_format,
            "\n\n".join(self.round_sections),
            len(self.experts),
        )
        return await self.complete(prompt, max_tokens=SYNTHESIS_MAX_TOKENS)

    async def _synthesize_quick(self, perspectives: str) -> str:
        prompt = build_quick_summary_prompt(
            self.topic, self.current_state, self.ideal_state, perspectives
        )
        return await self.complete(prompt, max_tokens=SYNTHESIS_MAX_TOKENS)
