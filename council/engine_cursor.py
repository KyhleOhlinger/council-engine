import asyncio
import logging
import os

from cursor_sdk import Agent, AgentOptions, LocalAgentOptions

from .engine_base import CouncilEngineBase

logger = logging.getLogger("council")


class CouncilDebate(CouncilEngineBase):
    def __init__(self, *args, model: str = "composer-2.5", **kwargs):
        super().__init__(*args, **kwargs)
        # Security: read the key from the environment; never accept it as an argument
        # or log it. Missing key fails fast rather than silently degrading.
        self.api_key = os.environ.get("CURSOR_API_KEY")
        if not self.api_key:
            raise ValueError("Missing CURSOR_API_KEY environment variable.")
        self.cwd = os.getcwd()
        self.model = model
        logger.info("Using Cursor SDK model: %s", self.model)

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
