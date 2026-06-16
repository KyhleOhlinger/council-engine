# Council Engine

<img width="1376" height="768" alt="council-engine-image" src="https://github.com/user-attachments/assets/91e28695-a9f9-41c2-bef8-79046533182d" />


A standalone Python library and CLI implementing the [PAI Council](https://github.com/danielmiessler/Personal_AI_Infrastructure/tree/main/Packs/Council) workflow — multi-agent collaborative debate with genuine intellectual friction.

Use it from the terminal, or import it into a larger Python application.

**Requirements:** Python 3.11+. Use `python3` (not `python`) on macOS.

## What it does

Council Engine runs structured multi-agent debates against a document or scenario:

1. **Round 1** — each expert states an initial position
2. **Round 2** — experts cite and challenge each other by name
3. **Round 3** — each expert synthesizes agreement, tension, and recommendation (brief prose only)
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

### Standalone extensions

PAI uses **topic + freeform context**. This engine adds an **artifact review model** via packs:

- **Current state** — the artifact under review (maps to PAI "full topic context")
- **Ideal state** — the target standard the artifact must meet

The same engine code can review security blog posts, trade theses, architecture docs, etc. by swapping packs — no Python changes required.

Additional standalone features beyond PAI:

- **Pack-based domain config** — `current_state` + `ideal_state` per council
- **Dual backends** — LiteLLM and Cursor SDK (`--engine litellm | cursor`)
- **YAML front matter** — run metadata in a single machine-readable block at the top of each verdict
- **Final Recommendation** — executive summary leads the verdict (replaces PAI's BLUF-style opening)
- **Dated output files** — `output/<pack>/YYYY-MM-DD-<slug>-final_verdict.md`
- **Appendix sanitization** — strips duplicate transcript sections and Round 3 verdict bloat from expert responses

## Project structure

```
config/
├── _shared/synthesis_format_pai.md     # PAI default synthesis template
└── councils/                           # Domain packs (the only thing that varies)
    └── security/                       # Tracked example pack (others are local/gitignored)
council/                                # Domain-agnostic engine (importable package)
├── engine_base.py                      # Shared DEBATE/QUICK orchestration
├── engines.py                          # Backend factory (litellm | cursor)
├── engine_litellm.py                   # LiteLLM backend
├── engine_cursor.py                    # Cursor SDK backend
├── packs.py                            # Pack loading
├── compose.py                          # ComposeAgent equivalent
├── prompts.py                          # Round prompts
├── transcript.py                       # Output assembly, YAML front matter, sanitization
├── output.py                           # Path helpers
├── constants.py                        # Token limits, expert count bounds
└── cli.py                              # CLI entry point
tests/
└── test_pure_functions.py              # Unit tests for deterministic helpers
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

**Dev dependencies** (tests):

```bash
pip install -e ".[dev]"
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

> **Cursor note:** The Cursor SDK ignores `max_tokens` on one-shot prompts; token limits apply to the LiteLLM backend only.

## CLI usage

Run from the **project root** so pack paths (`config/councils/...`) resolve correctly.

```bash
# Security pack (default scenario: vpn-blog-post)
python3 -m council.cli --council security --engine cursor

# Specific scenario
python3 -m council.cli --council security --scenario vpn-blog-post --engine cursor

# Auto-compose domain experts at runtime (PAI ComposeAgent equivalent)
python3 -m council.cli --council security --compose --engine cursor

# Quick check with auto-escalation to full debate
python3 -m council.cli --council security --workflow quick --auto-escalate --engine cursor

# LiteLLM backend (requires provider API key)
python3 -m council.cli --council security --engine litellm --model gpt-4o
```

Equivalent using the installed script (if on `PATH`):

```bash
council --council security --scenario vpn-blog-post --engine cursor
```

### Terminal output

The CLI shows council progress (pack, engine, rounds, synthesis) via normal stdout and `council` logger messages at `INFO`. HTTP client libraries (`httpx`, `httpcore`, `litellm`, etc.) are capped at `WARNING` so request-level noise does not flood the terminal.

Warnings still surface for issues like expert count outside 4–6 or when a QUICK run recommends escalation without `--auto-escalate`.

### Output

Pack runs write dated markdown verdicts to:

```
output/<pack-name>/YYYY-MM-DD-<topic-slug>-final_verdict.md
```

If that path already exists, the engine appends `-2`, `-3`, etc.

Example: `output/security/2026-06-15-why-you-need-to-stop-using-vpns-in-2026-final_verdict.md`

Override with `--output` or `--output-dir`.

#### Verdict document structure

Each verdict is a single markdown file with this layout:

```
---
date: "2026-06-15"
topic: "..."
workflow: debate
pack: "security"
pack_description: "..."
scenario: "config/councils/security/scenarios/vpn-blog-post.md"
engine: "cursor"
model: "composer-2.5"
council_members:
  - name: "The Skeptic"
    traits: "adversarial, meticulous"
  - name: "The Builder"
    traits: "pragmatic, systematic"
---

## Final Recommendation
(Executive summary — priority tier, what to do now, what to defer, escalation conditions)

---

## Analysis & Recommendations
(Structured synthesis per pack's synthesis_format.md)

---

## Appendix: Council Debate Transcript
(Full Round 1–3 expert responses)
```

All run metadata lives in the YAML block. The body starts directly with **Final Recommendation** — there is no duplicate markdown metadata section.

**Optional front-matter fields** are omitted when not set: `pack`, `pack_description`, `scenario`, `engine`, `model`, `escalated`, and `source_url`. Most councils do not need `source_url` — it is only included when a pack's scenario contains a link (e.g. blog-triage packs that review external posts). The CLI auto-extracts it via `extract_source_url()` when a `URL:` label or markdown link is present in the scenario; otherwise the field is left out entirely.

For QUICK runs, the appendix is titled `## Appendix: Council Perspectives`. Escalated runs (`--auto-escalate`) add `escalated: true` to the front matter and preserve the superseded quick triage in the appendix.

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

## Tests

```bash
python3 -m pytest tests/ -q
```

Tests cover slug generation, URL extraction, transcript sanitization, appendix stripping, and document assembly order — no API calls required.

## Using as a module

Council Engine is a library first. The CLI is a thin wrapper around the same async API.

### Core API

```python
import asyncio

from council.engines import create_engine
from council.transcript import RunContext

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
        run_context=RunContext(
            pack_name="security",
            pack_description="Security artifact review",
            scenario_path="config/councils/security/scenarios/vpn-blog-post.md",
            engine="cursor",
            model="composer-2.5",
        ),
    )
    return await engine.run()

result = asyncio.run(main())
# result["document"]   — full markdown output (YAML + synthesis + appendix)
# result["transcript"] — appendix section only
# result["synthesis"]  — Final Recommendation + analysis (no appendix)
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
from council.transcript import RunContext

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
from council.transcript import RunContext

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
        run_context=RunContext(
            pack_name=pack.name,
            pack_description=pack.description,
            scenario_path=str(scenario),
            engine="cursor",
            model="composer-2.5",
        ),
    )
    return await engine.run()

asyncio.run(run_security_council())
```

### Example: compose experts at runtime

Equivalent to PAI's ComposeAgent step and the CLI's `--compose` flag:

```python
import asyncio

from council.compose import compose_council
from council.engine_base import CouncilEngineBase
from council.engines import create_engine
from council.packs import load_pack, resolve_scenario

async def run_with_compose():
    pack = load_pack("security")
    scenario = resolve_scenario(pack, current=None, scenario="vpn-blog-post")

    engine = create_engine(
        "cursor",
        current_state=scenario.read_text(),
        ideal_state=pack.ideal_state.read_text(),
        synthesis_format=pack.synthesis_format.read_text(),
        experts=[],
        workflow="debate",
    )
    engine.experts = await compose_council(
        topic="VPN blog post review",
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
- **Progress logging** — the engine logs round progress via the `council` logger at `INFO`. HTTP client loggers are silenced to `WARNING` in the CLI; configure loggers yourself when embedding.
- **Lazy backends** — `create_engine("cursor", ...)` never loads LiteLLM. `LiteLLMCouncilDebate` only imports litellm when explicitly accessed.
- **Expert schema** — each expert requires `name` and `persona`; `traits` is optional but recommended for transcript formatting and YAML front matter.

## Adding a pack

1. Copy `config/councils/security/` → `config/councils/<name>/`
2. Edit `council.json`, `experts.json`, `ideal_state.md`, `synthesis_format.md`, `council_members.md`
3. Add scenarios to `scenarios/`
4. Run: `python3 -m council.cli --council <name> --engine cursor`

No Python changes required.

> **Git note:** Only `config/councils/security/` is tracked in git. Other packs under `config/councils/` are gitignored by default so you can keep local domain councils without committing them. Generated verdicts under `output/` are also gitignored (except `output/.gitkeep`).

## Pack files

| File | PAI equivalent | Purpose |
|------|----------------|---------|
| `council.json` | — | Manifest wiring paths together |
| `experts.json` | ComposeAgent output | Council personas |
| `council_members.md` | CouncilMembers.md | Composition guidance for `--compose` / `compose_council()` |
| `ideal_state.md` | — | Target standard (standalone extension) |
| `synthesis_format.md` | OutputFormat.md | Verdict structure (lead with `## Final Recommendation`) |
| `scenarios/*.md` | Topic context | Artifact under review per run |

Some packs (e.g. blog triage) include a `URL:` line or markdown link in scenarios so the CLI can populate optional `source_url` front matter. That is a pack convention, not an engine requirement.

## Source

Inspired by [danielmiessler/Personal_AI_Infrastructure Packs/Council](https://github.com/danielmiessler/Personal_AI_Infrastructure/tree/main/Packs/Council).
