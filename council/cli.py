import argparse
import asyncio
import json
import logging
from datetime import date
from pathlib import Path

from .compose import compose_council
from .constants import DEFAULT_SYNTHESIS_FORMAT, OPTIMAL_EXPERTS
from .engine_base import CouncilEngineBase
from .engines import create_engine
from .output import resolve_output_path
from .packs import CouncilPack, list_packs, load_pack, resolve_scenario
from .prompts import extract_source_url, extract_topic
from .transcript import RunContext

SHARED_FORMAT = Path(DEFAULT_SYNTHESIS_FORMAT)

_NOISY_LOGGERS = (
    "httpx",
    "httpcore",
    "litellm",
    "openai",
    "urllib3",
    "hpack",
    "cursor",
)


def configure_logging() -> None:
    """Show council progress; silence HTTP client request noise only."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("council").setLevel(logging.INFO)
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


def resolve_paths(args) -> tuple[CouncilPack | None, dict]:
    pack = load_pack(args.council) if args.council else None
    if pack:
        print(f"📦 Council pack: {pack.name} — {pack.description}")
        current = resolve_scenario(pack, args.current, args.scenario)
    elif args.current:
        current = Path(args.current)
        if not current.exists():
            raise FileNotFoundError(f"Not found: {current}")
    else:
        raise ValueError("Provide --council or --current.")

    ideal = Path(args.ideal) if args.ideal else (pack.ideal_state if pack else None)
    fmt = Path(args.format) if args.format else (pack.synthesis_format if pack else SHARED_FORMAT)
    experts = Path(args.experts) if args.experts else (pack.experts if pack else None)
    output_dir = str(pack.output_dir) if pack and args.output_dir == "output" else args.output_dir

    if ideal is None:
        raise ValueError("Provide --ideal or use --council.")
    if experts is None and not args.compose:
        raise ValueError("Provide --experts, --compose, or use --council.")

    return pack, {
        "current": current,
        "ideal": ideal,
        "format": fmt,
        "experts": experts,
        "output_dir": output_dir,
        "compose_guide": pack.read_compose_guide() if pack else None,
    }


async def run(args, paths: dict, engine_kwargs: dict) -> dict[str, str]:
    engine_kwargs["validate_experts"] = not (args.compose and not engine_kwargs["experts"])

    print(f"🔌 Routing to {'Cursor SDK' if args.engine == 'cursor' else 'LiteLLM'} Engine...")
    debate = create_engine(args.engine, workflow=args.workflow, **engine_kwargs)

    if args.compose:
        print(f"🧩 Composing {OPTIMAL_EXPERTS} experts...")
        debate.experts = await compose_council(
            engine_kwargs["topic"],
            engine_kwargs["current_state"],
            engine_kwargs["ideal_state"],
            debate.complete,
            compose_guide=paths.get("compose_guide"),
        )
        CouncilEngineBase._validate_experts(debate.experts)
        for e in debate.experts:
            print(f"   • {e['name']} ({e.get('traits', '')})")

    return await debate.run()


def main():
    configure_logging()
    packs = list_packs()
    parser = argparse.ArgumentParser(description="PAI Council — multi-agent collaborative debate.")
    parser.add_argument("--council", choices=packs, help=f"Pack: {', '.join(packs)}")
    parser.add_argument("--current", help="Artifact under review (path or scenario name)")
    parser.add_argument("--scenario", help="Scenario in pack scenarios/ folder")
    parser.add_argument("--ideal", help="ideal_state.md (overrides pack)")
    parser.add_argument("--format", help="synthesis_format.md (overrides pack)")
    parser.add_argument("--experts", help="experts.json (overrides pack)")
    parser.add_argument("--compose", action="store_true", help="Auto-compose experts (PAI ComposeAgent)")
    parser.add_argument("--workflow", choices=["debate", "quick"], default="debate")
    parser.add_argument("--auto-escalate", action="store_true", help="QUICK → DEBATE if recommended")
    parser.add_argument("--topic", help="Topic title (default: first heading in scenario)")
    parser.add_argument("--output", help="Override output file path")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--engine", choices=["litellm", "cursor"], default="litellm")
    parser.add_argument("--model", help="Model override")
    args = parser.parse_args()

    if not args.council and not args.current:
        parser.error("Provide --council or --current.")
    if not args.experts and not args.compose and not args.council:
        parser.error("Provide --experts, --compose, or --council.")

    pack, paths = resolve_paths(args)
    current_state = paths["current"].read_text(encoding="utf-8")
    ideal_state = paths["ideal"].read_text(encoding="utf-8")
    synthesis_format = paths["format"].read_text(encoding="utf-8")
    experts = []
    if paths["experts"]:
        experts = json.loads(paths["experts"].read_text(encoding="utf-8"))

    topic = args.topic or extract_topic(current_state)
    run_date = date.today()
    output_path = resolve_output_path(topic, paths["output_dir"], args.output, run_date)
    model = args.model or ("composer-2.5" if args.engine == "cursor" else "gpt-4o")

    print(f"📅 Date: {run_date.isoformat()}\n📋 Topic: {topic}\n📄 Output: {output_path}")

    engine_kwargs = {
        "current_state": current_state,
        "ideal_state": ideal_state,
        "synthesis_format": synthesis_format,
        "experts": experts,
        "topic": topic,
        "run_date": run_date,
        "auto_escalate": args.auto_escalate,
        "model": model,
        "run_context": RunContext(
            pack_name=pack.name if pack else None,
            pack_description=pack.description if pack else None,
            scenario_path=str(paths["current"]),
            source_url=extract_source_url(current_state),
            engine=args.engine,
            model=model,
        ),
    }

    results = asyncio.run(run(args, paths, engine_kwargs))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(results["document"], encoding="utf-8")
    print(f"\n✅ Council complete. Results written to {output_path}")


if __name__ == "__main__":
    main()
