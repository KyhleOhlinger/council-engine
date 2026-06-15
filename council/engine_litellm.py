import logging

from litellm import acompletion

from .engine_base import CouncilEngineBase

logger = logging.getLogger("council")


class CouncilDebate(CouncilEngineBase):
    def __init__(self, *args, model: str = "gpt-4o", **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        logger.info("Using LiteLLM model: %s", self.model)

    async def complete(self, prompt: str, *, max_tokens: int | None = None) -> str:
        kwargs = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        response = await acompletion(**kwargs)
        return response.choices[0].message.content
