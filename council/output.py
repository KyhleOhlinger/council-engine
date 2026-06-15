"""Output path helpers for council verdict files."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path("output")


def fill_run_variables(text: str, topic: str, run_date: date | None = None) -> str:
    day = (run_date or date.today()).isoformat()
    for old, new in (("[date]", day), ("[topic]", topic), ("{{date}}", day), ("{{topic}}", topic)):
        text = text.replace(old, new)
    return text


def slugify_topic(topic: str, max_length: int = 80) -> str:
    slug = re.sub(
        r"^(draft|ideal state artifact|synopsis|trade thesis)\s*[^:]*:\s*",
        "",
        topic.strip(),
        flags=re.IGNORECASE,
    )
    slug = re.sub(r"[^\w\s-]", "", slug.lower())
    slug = re.sub(r"[\s_]+", "-", slug.strip())
    return re.sub(r"-+", "-", slug).strip("-")[:max_length] or "council-review"


def resolve_output_path(
    topic: str,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    explicit_output: str | None = None,
    on_date: date | None = None,
) -> Path:
    if explicit_output:
        return Path(explicit_output)

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    day = (on_date or date.today()).isoformat()
    path = directory / f"{day}-{slugify_topic(topic)}-final_verdict.md"

    if not path.exists():
        return path

    stem = path.stem
    for counter in range(2, 100):
        candidate = directory / f"{stem}-{counter}.md"
        if not candidate.exists():
            return candidate
    return path
