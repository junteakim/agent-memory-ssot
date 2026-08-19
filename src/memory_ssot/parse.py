"""Human-readable markdown lines. Round-trip only; never invent text."""

from __future__ import annotations

import re
from datetime import date

from memory_ssot.models import ClaimTag, Fact, Tier

# - (2026-08-19) [VERIFIED] [DOCS] The plant has 3 hydrotest bays. <!-- prov:shop-walk -->
LINE_RE = re.compile(
    r"^\-\s+"
    r"\((?P<date>\d{4}-\d{2}-\d{2})\)\s+"
    r"(?P<tags>(?:\[[A-Za-z]+\]\s*)*)"
    r"(?P<text>.+?)"
    r"(?:\s+<!--\s*prov:(?P<prov>.*?)\s*-->)?\s*$"
)
TAG_RE = re.compile(r"\[([A-Za-z]+)\]")


def format_line(fact: Fact) -> str:
    tags = "".join(f"[{tag.value}] " for tag in fact.tags)
    prov = f" <!-- prov:{fact.provenance} -->" if fact.provenance else ""
    return f"- ({fact.date.isoformat()}) {tags}{fact.text}{prov}"


def parse_line(line: str, *, default_tier: Tier) -> Fact | None:
    stripped = line.strip()
    if not stripped.startswith("-"):
        return None
    match = LINE_RE.match(stripped)
    if not match:
        return None
    tags: list[ClaimTag] = []
    for raw in TAG_RE.findall(match.group("tags") or ""):
        try:
            tags.append(ClaimTag(raw.upper()))
        except ValueError:
            continue
    prov = (match.group("prov") or "").strip()
    return Fact(
        text=match.group("text").strip(),
        tier=default_tier,
        tags=tags,
        provenance=prov,
        date=date.fromisoformat(match.group("date")),
    )


def parse_markdown(text: str, *, default_tier: Tier) -> list[Fact]:
    facts: list[Fact] = []
    for line in text.splitlines():
        fact = parse_line(line, default_tier=default_tier)
        if fact is not None:
            facts.append(fact)
    return facts


def render_markdown(title: str, facts: list[Fact]) -> str:
    lines = [title.rstrip(), ""]
    for fact in facts:
        lines.append(format_line(fact))
    if facts:
        lines.append("")
    return "\n".join(lines)
