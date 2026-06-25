"""Council pack loading and resolution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

COUNCILS_ROOT = Path("config/councils")


@dataclass(frozen=True)
class CouncilPack:
    name: str
    description: str
    root: Path
    ideal_state: Path
    synthesis_format: Path
    experts: Path
    council_members: Path | None
    default_scenario: Path | None
    output_dir: Path

    @property
    def scenarios_dir(self) -> Path:
        return self.root / "scenarios"

    def list_scenarios(self) -> list[str]:
        if not self.scenarios_dir.exists():
            return []
        return sorted(path.stem for path in self.scenarios_dir.glob("*.md"))

    def read_compose_guide(self) -> str | None:
        if self.council_members and self.council_members.exists():
            return self.council_members.read_text(encoding="utf-8")
        return None


def _is_explicit_path(value: str) -> bool:
    """True when the user supplied a path, not a bare scenario slug."""
    candidate = Path(value)
    return candidate.is_absolute() or len(candidate.parts) > 1


def _find_scenario_in_pack(pack: CouncilPack, name: str) -> Path | None:
    """Resolve a scenario slug to a file under the pack scenarios/ directory."""
    stem = Path(name).stem.lower()
    scenarios_dir = pack.scenarios_dir
    if not scenarios_dir.exists():
        return None

    for path in scenarios_dir.glob("*.md"):
        if path.stem.lower() == stem:
            return path
    return None


def resolve_scenario_path(pack: CouncilPack, value: str) -> Path:
    """Resolve --scenario or --current to a concrete scenario file."""
    if _is_explicit_path(value):
        path = Path(value)
        if not path.suffix:
            path = path.with_suffix(".md")
        if path.exists():
            return path
        raise FileNotFoundError(f"Scenario not found: {path}")

    path = _find_scenario_in_pack(pack, value)
    if path is not None:
        return path

    available = pack.list_scenarios()
    hint = f" Available: {', '.join(available)}" if available else ""
    raise FileNotFoundError(f"Scenario not found: {pack.scenarios_dir / Path(value).stem}.md.{hint}")


def list_packs() -> list[str]:
    if not COUNCILS_ROOT.exists():
        return []
    return sorted(
        p.name for p in COUNCILS_ROOT.iterdir() if p.is_dir() and (p / "council.json").exists()
    )


def load_pack(name: str) -> CouncilPack:
    pack_root = COUNCILS_ROOT / name
    manifest_path = pack_root / "council.json"
    if not manifest_path.exists():
        raise ValueError(f"Unknown council pack '{name}'. Available: {', '.join(list_packs())}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    council_members = None
    if manifest.get("council_members"):
        council_members = pack_root / manifest["council_members"]

    default_scenario = None
    if manifest.get("default_scenario"):
        default_scenario = pack_root / manifest["default_scenario"]

    return CouncilPack(
        name=manifest.get("name", name),
        description=manifest.get("description", ""),
        root=pack_root,
        ideal_state=pack_root / manifest["ideal_state"],
        synthesis_format=pack_root / manifest["synthesis_format"],
        experts=pack_root / manifest["experts"],
        council_members=council_members,
        default_scenario=default_scenario,
        output_dir=Path("output") / name,
    )


def resolve_scenario(pack: CouncilPack, current: str | None, scenario: str | None) -> Path:
    if current and scenario and current != scenario:
        raise ValueError(
            f"Provide only one of --current or --scenario, not both "
            f"(got --current {current!r} and --scenario {scenario!r})."
        )

    if scenario:
        return resolve_scenario_path(pack, scenario)
    if current:
        return resolve_scenario_path(pack, current)
    if pack.default_scenario and pack.default_scenario.exists():
        return pack.default_scenario
    raise ValueError(f"Provide --current or --scenario for pack '{pack.name}'.")
