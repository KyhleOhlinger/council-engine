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

    def scenario_path(self, scenario: str) -> Path:
        candidate = Path(scenario)
        if candidate.is_absolute() or candidate.exists():
            return candidate
        return self.root / "scenarios" / scenario

    def read_compose_guide(self) -> str | None:
        if self.council_members and self.council_members.exists():
            return self.council_members.read_text(encoding="utf-8")
        return None


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
    if scenario:
        path = pack.scenario_path(scenario)
        if not path.suffix:
            path = path.with_suffix(".md")
        if not path.exists():
            raise FileNotFoundError(f"Scenario not found: {path}")
        return path
    if current:
        path = Path(current)
        if path.exists():
            return path
        relative = pack.scenario_path(current)
        if relative.exists():
            return relative
        raise FileNotFoundError(f"Current state file not found: {path}")
    if pack.default_scenario and pack.default_scenario.exists():
        return pack.default_scenario
    raise ValueError(f"Provide --current or --scenario for pack '{pack.name}'.")
