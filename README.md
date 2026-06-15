# Council Engine

A standalone Python library and CLI implementing the [PAI Council](https://github.com/danielmiessler/Personal_AI_Infrastructure/tree/main/Packs/Council) workflow — multi-agent collaborative debate with genuine intellectual friction.

Use it from the terminal, or import it into a larger Python application.

**Requirements:** Python 3.11+. Use `python3` (not `python`) on macOS.

## What it does

Council Engine runs structured multi-agent debates against a document or scenario:

1. **Round 1** — each expert states an initial position
2. **Round 2** — experts cite and challenge each other by name
3. **Round 3** — each expert synthesizes agreement, tension, and recommendation
4. **Council Synthesis** — an orchestrator pass produces a final verdict

Two workflows are supported:

| Workflow | Rounds | Use case |
|----------|--------|----------|
| `debate` | 3 + synthesis | Important decisions, full transcript |
| `quick` | 1 + summary | Fast sanity check; optional auto-escalation to `debate` |

## PAI ideology

From [PAI Council](https://github.com/danielmiessler/Personal_AI_Infrastructure/tree/main/Packs/Council):

| PAI principle | This engine |
|---------------|-------------|
| **Collaborative-adversarial** — debate to find the best path | Round 2+ requires experts to engage each other's arguments |
| **Intellectual friction** — value is in interaction, not polling | 3-round arc: positions → engagement → synthesis |
| **Custom-composed agents** — never generic Architect/Designer types | `experts.json` per pack or runtime composition via `compose_council()` |
| **4–6 tailored experts** outperform 12 generic ones | Validates count; warns if outside 4–6 |
| **Honest disagreement** — forced consensus is worse than tension | Round 3 + synthesis preserve remaining disagreements |
| **DEBATE** (parallel within rounds) | Sequential rounds, parallel experts per round |
| **QUICK** (30–50 word perspectives) | `workflow="quick"` with optional `auto_escalate=True` |
| **Council Synthesis** (3+ convergence) | Separate orchestrator step using `synthesis_format.md` |

### Standalone extension

PAI uses **topic + freeform context**. This engine adds an **artifact review model** via packs:

- **Current state** — the artifact under review (maps to PAI "full topic context")
- **Ideal state** — the target standard the artifact must meet

The same engine code can review security blog posts, trade theses, architecture docs, etc. by swapping packs — no Python changes required.

## Project structure

```
config/
├── _shared/synthesis_format_pai.md     # PAI default synthesis template
└── councils/                           # Domain packs (the only thing that varies)
    ├── security/
    └── finance-trader/
council/                                # Domain-agnostic engine (importable package)
├── engine_base.py                      # Shared DEBATE/QUICK orchestration
├── engines.py                          # Backend factory (litellm | cursor)
├── engine_litellm.py                   # LiteLLM backend
├── engine_cursor.py                    # Cursor SDK backend
├── packs.py                            # Pack loading
├── compose.py                          # ComposeAgent equivalent
├── prompts.py                          # Round prompts
├── transcript.py                       # Output formatting
├── output.py                           # Path helpers
└── cli.py                              # CLI entry point
output/<pack-name>/                     # Generated verdicts (gitignored)
```

## Install

**Recommended** — virtual environment:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e .
```

**Without a venv** — install into your user Python:

```bash
pip3 install -e .
```

This installs the `council` package and registers the `council` CLI command. If the `council` script is not found, use `python3 -m council.cli` instead, or add your Python user `bin` directory to `PATH`.

### API keys

Set the key for whichever backend you use:

```bash
# Cursor SDK
export CURSOR_API_KEY="your-key-here"

# LiteLLM (example: OpenAI)
export OPENAI_API_KEY="your-key-here"
```

| Backend | `--engine` value | Default model | Requirement |
|---------|------------------|---------------|-------------|
| LiteLLM | `litellm` (default) | `gpt-4o` | Provider API key for your model |
| Cursor SDK | `cursor` | `composer-2.5` | `CURSOR_API_KEY` environment variable |

Backends are loaded **lazily** — using `--engine cursor` does not import LiteLLM at startup. This lets the Cursor backend run even if LiteLLM dependencies are not installed or broken in your environment.

> **Apple Silicon note:** If `--engine litellm` fails with a `pydantic_core` architecture error on system Python, use a venv (`python3 -m venv .venv`) or run with `--engine cursor`.

## CLI usage

Run from the **project root** so pack paths (`config/councils/...`) resolve correctly.

```bash
# Security pack (default scenario: vpn-blog-post)
python3 -m council.cli --council security --engine cursor

# Finance trader pack
python3 -m council.cli --council finance-trader --engine cursor

# Specific scenario
python3 -m council.cli --council security --scenario vpn-blog-post --engine cursor

# Auto-compose domain experts at runtime (PAI ComposeAgent equivalent)
python3 -m council.cli --council finance-trader --compose --engine cursor

# Quick check with auto-escalation to full debate
python3 -m council.cli --council security --workflow quick --auto-escalate --engine cursor

# LiteLLM backend (requires provider API key)
python3 -m council.cli --council security --engine litellm --model gpt-4o
```

Equivalent using the installed script (if on `PATH`):

```bash
council --council security --scenario vpn-blog-post --engine cursor
```

### Output

Pack runs write dated markdown verdicts to:

```
output/<pack-name>/YYYY-MM-DD-<topic-slug>-final_verdict.md
```

Example: `output/security/2026-06-15-why-you-need-to-stop-using-vpns-in-2026-final_verdict.md`

Override with `--output` or `--output-dir`.

### Manual paths (without a pack)

You can still pass files directly instead of using `--council`:

```bash
python3 -m council.cli \
  --current path/to/draft.md \
  --ideal path/to/ideal_state.md \
  --format path/to/synthesis_format.md \
  --experts path/to/experts.json \
  --engine cursor
```

## Using as a module

Council Engine is a library first. The CLI is a thin wrapper around the same async API.

### Core API

```python
import asyncio

from council.engines import create_engine

async def main():
    engine = create_engine(
        "cursor",                         # or "litellm"
        current_state="...",              # artifact under review
        ideal_state="...",                # target standard
        synthesis_format="...",           # verdict markdown template
        experts=[{"name": "...", "persona": "...", "traits": "..."}],
        workflow="debate",                # or "quick"
        topic="Optional topic title",
        auto_escalate=False,
        model="composer-2.5",             # cursor default; litellm default is gpt-4o
    )
    return await engine.run()

result = asyncio.run(main())
# result["document"]   — full markdown output
# result["transcript"] — header + round sections
# result["synthesis"]  — final synthesis block
```

`run()` is **async**. Use `asyncio.run()` from a script, or call it directly inside an existing event loop (FastAPI, etc.).

### Public exports

```python
from council import CouncilEngineBase
from council.engines import create_engine          # preferred entry point
from council.packs import load_pack, list_packs, resolve_scenario
from council.compose import compose_council
from council.output import resolve_output_path
from council.prompts import extract_topic

# Backend classes load lazily (only when imported):
from council import CursorCouncilDebate, LiteLLMCouncilDebate
```

Prefer `create_engine("cursor", ...)` or `create_engine("litellm", ...)` — backends are only imported when selected.

### Example: pass content directly

```python
import asyncio
from pathlib import Path

from council.engines import create_engine

async def review_draft():
    engine = create_engine(
        "cursor",
        current_state=Path("draft.md").read_text(),
        ideal_state=Path("ideal_state.md").read_text(),
        synthesis_format=Path("synthesis_format.md").read_text(),
        experts=[
            {
                "name": "The Skeptic",
                "traits": "adversarial, meticulous",
                "persona": "You challenge assumptions and find flaws others overlook.",
            },
            # ... 3–5 more experts (4–6 recommended)
        ],
        workflow="debate",
    )
    result = await engine.run()
    return result["document"]

asyncio.run(review_draft())
```

### Example: load a council pack

Pack paths are resolved relative to the **current working directory**. Run from the project root, or pass absolute paths for scenario files.

```python
import asyncio
import json

from council.engines import create_engine
from council.packs import load_pack, resolve_scenario

async def run_security_council():
    pack = load_pack("security")
    scenario = resolve_scenario(pack, current=None, scenario="vpn-blog-post")

    engine = create_engine(
        "cursor",
        current_state=scenario.read_text(),
        ideal_state=pack.ideal_state.read_text(),
        synthesis_format=pack.synthesis_format.read_text(),
        experts=json.loads(pack.experts.read_text()),
        workflow="debate",
    )
    return await engine.run()

asyncio.run(run_security_council())
```

### Example: compose experts at runtime

Equivalent to PAI's ComposeAgent step and the CLI's `--compose` flag:

```python
import asyncio
import json

from council.compose import compose_council
from council.engine_base import CouncilEngineBase
from council.engines import create_engine
from council.packs import load_pack, resolve_scenario

async def run_with_compose():
    pack = load_pack("finance-trader")
    scenario = resolve_scenario(pack, current=None, scenario=None)

    engine = create_engine(
        "cursor",
        current_state=scenario.read_text(),
        ideal_state=pack.ideal_state.read_text(),
        synthesis_format=pack.synthesis_format.read_text(),
        experts=[],
        workflow="debate",
    )
    engine.experts = await compose_council(
        topic="NVDA earnings trade thesis",
        current_state=scenario.read_text(),
        ideal_state=pack.ideal_state.read_text(),
        complete=engine.complete,
        compose_guide=pack.read_compose_guide(),
    )
    CouncilEngineBase._validate_experts(engine.experts)
    return await engine.run()

asyncio.run(run_with_compose())
```

### Embedding notes

- **No file output required** — the CLI writes `result["document"]` to disk; a host app can store it anywhere or return it over an API.
- **Progress logging** — the engine prints round progress to stdout. Redirect or wrap if you need silent operation in production.
- **Lazy backends** — `create_engine("cursor", ...)` never loads LiteLLM. `LiteLLMCouncilDebate` only imports litellm when explicitly accessed.
- **Expert schema** — each expert requires `name` and `persona`; `traits` is optional but recommended for transcript formatting.

## Adding a pack

1. Copy `config/councils/security/` → `config/councils/<name>/`
2. Edit `council.json`, `experts.json`, `ideal_state.md`, `synthesis_format.md`, `council_members.md`
3. Add scenarios to `scenarios/`
4. Run: `python3 -m council.cli --council <name> --engine cursor`

No Python changes required.

## Pack files

| File | PAI equivalent | Purpose |
|------|----------------|---------|
| `council.json` | — | Manifest wiring paths together |
| `experts.json` | ComposeAgent output | Council personas |
| `council_members.md` | CouncilMembers.md | Composition guidance for `--compose` / `compose_council()` |
| `ideal_state.md` | — | Target standard (standalone extension) |
| `synthesis_format.md` | OutputFormat.md | Verdict structure |
| `scenarios/*.md` | Topic context | Artifact under review per run |

## Source

Inspired by [danielmiessler/Personal_AI_Infrastructure Packs/Council](https://github.com/danielmiessler/Personal_AI_Infrastructure/tree/main/Packs/Council).
