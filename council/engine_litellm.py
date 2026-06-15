from litellm import acompletion

from .engine_base import CouncilEngineBase


class CouncilDebate(CouncilEngineBase):
    def __init__(
        self,
        current_state,
        ideal_state,
        synthesis_format,
        experts,
        model="gpt-4o",
        workflow="debate",
        topic=None,
        run_date=None,
        auto_escalate=False,
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
        self.model = model
        print(f"Using LiteLLM model: {self.model}")

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
