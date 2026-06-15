"""LLM backend factory."""

from __future__ import annotations

from importlib import import_module

_BACKENDS = {"cursor": "engine_cursor", "litellm": "engine_litellm"}


def create_engine(backend: str, **kwargs):
    module_name = _BACKENDS.get(backend)
    if not module_name:
        raise ValueError(f"Unknown engine '{backend}'. Choose: {', '.join(_BACKENDS)}")
    module = import_module(f"council.{module_name}")
    return module.CouncilDebate(**kwargs)
