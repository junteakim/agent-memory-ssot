"""Core value types for the memory store."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class Tier(StrEnum):
    """Where a fact lives on disk."""

    PROFILE = "profile"
    LOG = "log"
    NOTE = "note"
    DIGEST = "digest"


class ClaimTag(StrEnum):
    """How much trust an agent (or a human) places in a fact."""

    VERIFIED = "VERIFIED"
    DOCS = "DOCS"
    SPECULATION = "SPECULATION"


@dataclass
class Fact:
    """One line of memory. Text is the identity."""

    text: str
    tier: Tier = Tier.PROFILE
    tags: list[ClaimTag] = field(default_factory=list)
    provenance: str = ""
    human_approved: bool = False
    date: date = field(default_factory=date.today)
    id: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.tier, str):
            self.tier = Tier(self.tier)
        normalized: list[ClaimTag] = []
        for tag in self.tags:
            if isinstance(tag, ClaimTag):
                normalized.append(tag)
            else:
                normalized.append(ClaimTag(str(tag).upper()))
        self.tags = normalized
        if isinstance(self.date, str):
            self.date = date.fromisoformat(self.date)
        self.text = self.text.strip()
