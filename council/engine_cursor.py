import asyncio
import os

from cursor_sdk import Agent, AgentOptions, LocalAgentOptions

from .engine_base import CouncilEngineBase


class CouncilDebate(CouncilEngineBase):
    def __init__(
        self,
        current_state,
        ideal_state,
        synthesis_format,
        experts,
        workflow="debate",
        topic=None,
        run_date=None,
        auto_escalate=False,
        model="composer-2.5",
        validate_experts=True,
    ):
        super().__init__(
            current_state,
            ideal_state,
            synthesis_format,
            experts,
            workflow=workflow,
            topic=topic,
            run_date=run_date,
            auto_escalate=auto_escalate,
            validate_experts=validate_experts,
        )
        self.api_key = os.environ.get("CURSOR_API_KEY")
        self.cwd = os.getcwd()
        self.model = model

        if not self.api_key:
            raise ValueError("Missing CURSOR_API_KEY environment variable.")

        print(f"Using Cursor SDK model: {self.model}")

    def _call_agent_sync(self, prompt: str) -> str:
        result = Agent.prompt(
            prompt,
            AgentOptions(
                api_key=self.api_key,
                model=self.model,
                local=LocalAgentOptions(cwd=self.cwd),
            ),
        )
        if result.status == "error":
            raise RuntimeError(f"Cursor agent run failed: {result.id}")
        return result.result or ""

    async def complete(self, prompt: str, *, max_tokens: int | None = None) -> str:
        del max_tokens  # Cursor SDK selects limits server-side for one-shot prompts
        return await asyncio.to_thread(self._call_agent_sync, prompt)
