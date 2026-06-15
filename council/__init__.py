"""Council Engine — standalone PAI Council implementation."""

from .engine_base import CouncilEngineBase

__all__ = ["CouncilEngineBase", "CursorCouncilDebate", "LiteLLMCouncilDebate", "create_engine"]


def __getattr__(name: str):
    if name == "CursorCouncilDebate":
        from .engine_cursor import CouncilDebate

        return CouncilDebate
    if name == "LiteLLMCouncilDebate":
        from .engine_litellm import CouncilDebate

        return CouncilDebate
    if name == "create_engine":
        from .engines import create_engine

        return create_engine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
