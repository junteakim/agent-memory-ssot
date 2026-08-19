"""File-backed memory store. profile.md, log/YYYY-MM.md, candidates.jsonl."""

from __future__ import annotations

import json
import uuid
from datetime import date
from pathlib import Path

from memory_ssot.gates import (
    GateError,
    check_number_gate,
    check_promote_gates,
    check_write_gates,
    has_action_claim,
    has_claimed_number,
    has_money_claim,
)
from memory_ssot.models import ClaimTag, Fact, Tier
from memory_ssot.parse import format_line, parse_line, parse_markdown

_CANDIDATES = "candidates.jsonl"
_PROFILE = "profile.md"
_NOTES = "notes.md"
_LOG_DIR = "log"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _tier_for_storage(tier: Tier) -> Tier:
    if tier is Tier.DIGEST:
        return Tier.PROFILE
    return tier


class MemoryStore:
    """Single source of truth rooted at a directory of markdown files."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    @classmethod
    def init(cls, root: str | Path) -> MemoryStore:
        store = cls(root)
        store.ensure_layout()
        return store

    def ensure_layout(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / _LOG_DIR).mkdir(exist_ok=True)
        profile = self.root / _PROFILE
        if not profile.exists():
            profile.write_text("# Profile\n", encoding="utf-8")
        notes = self.root / _NOTES
        if not notes.exists():
            notes.write_text("# Notes\n", encoding="utf-8")
        candidates = self.root / _CANDIDATES
        if not candidates.exists():
            candidates.write_text("", encoding="utf-8")

    def write(self, fact: Fact, *, candidate: bool = False) -> Fact:
        """Write a fact. Exact-text match (trim, case-sensitive) is a no-op.

        If ``candidate=True``, land in the inbox instead of profile/log.
        """
        fact = _copy_fact(fact)
        if candidate:
            return self._propose(fact)
        check_write_gates(fact)
        existing = self._find_exact(fact.text)
        if existing is not None:
            return existing
        self.ensure_layout()
        self._append_fact(fact)
        return fact

    def propose(self, fact: Fact) -> str:
        """Add an unpromoted fact to the inbox. Returns the candidate id."""
        written = self._propose(_copy_fact(fact))
        return written.id or ""

    def _propose(self, fact: Fact) -> Fact:
        check_number_gate(fact)
        existing = self._find_exact(fact.text)
        if existing is not None:
            return existing
        for cand in self.candidates():
            if cand.text == fact.text:
                return cand
        self.ensure_layout()
        fact.id = fact.id or _new_id()
        with (self.root / _CANDIDATES).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_fact_to_json(fact), ensure_ascii=False) + "\n")
        return fact

    def read_profile(self) -> list[Fact]:
        return self._read_file(self.root / _PROFILE, Tier.PROFILE)

    def read_notes(self) -> list[Fact]:
        return self._read_file(self.root / _NOTES, Tier.NOTE)

    def read_log(self, year: int, month: int) -> list[Fact]:
        return self._read_file(self._log_path(year, month), Tier.LOG)

    def search(self, query: str) -> list[Fact]:
        needle = query.lower()
        found: list[Fact] = []
        seen: set[str] = set()
        for fact in self._iter_all():
            if needle in fact.text.lower() and fact.text not in seen:
                seen.add(fact.text)
                found.append(fact)
        return found

    def forget(self, text: str) -> bool:
        target = text.strip()
        removed = False
        removed = self._forget_in_file(self.root / _PROFILE, Tier.PROFILE, target) or removed
        removed = self._forget_in_file(self.root / _NOTES, Tier.NOTE, target) or removed
        log_dir = self.root / _LOG_DIR
        if log_dir.is_dir():
            for path in sorted(log_dir.glob("*.md")):
                removed = self._forget_in_file(path, Tier.LOG, target) or removed
        kept: list[Fact] = []
        for cand in self.candidates():
            if cand.text == target:
                removed = True
            else:
                kept.append(cand)
        if removed:
            self._write_candidates(kept)
        return removed

    def promote(self, candidate_id: str, *, human_approved: bool | None = None) -> Fact | None:
        """Move a candidate to profile/log. Without human approval it stays put."""
        remaining: list[Fact] = []
        target: Fact | None = None
        for cand in self.candidates():
            if cand.id == candidate_id:
                target = cand
            else:
                remaining.append(cand)
        if target is None:
            return None
        if human_approved is not None:
            target.human_approved = human_approved
        if not target.human_approved:
            return None
        try:
            check_promote_gates(target)
        except GateError:
            return None
        existing = self._find_committed(target.text)
        if existing is not None:
            self._write_candidates(remaining)
            return existing
        self.ensure_layout()
        target.tier = _tier_for_storage(target.tier)
        self._append_fact(target)
        self._write_candidates(remaining)
        return target

    def candidates(self) -> list[Fact]:
        path = self.root / _CANDIDATES
        if not path.is_file():
            return []
        out: list[Fact] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            out.append(_fact_from_json(json.loads(line)))
        return out

    def check(self) -> list[str]:
        """Validate on-disk files. Return human-readable violation strings."""
        violations: list[str] = []
        for path, tier in self._iter_markdown_paths():
            raw = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(raw.splitlines(), start=1):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if not stripped.startswith("-"):
                    continue
                fact = parse_line(stripped, default_tier=tier)
                loc = f"{path.relative_to(self.root)}:{lineno}"
                if fact is None:
                    violations.append(f"{loc}: unparseable fact line")
                    continue
                if has_claimed_number(fact.text):
                    tags = set(fact.tags)
                    if ClaimTag.SPECULATION in tags or (
                        ClaimTag.VERIFIED not in tags and ClaimTag.DOCS not in tags
                    ):
                        violations.append(
                            f"{loc}: numbers require VERIFIED or DOCS; do not invent counts"
                        )
                # Files are the approved SSOT; still flag money/action so a human sees them.
                if has_money_claim(fact.text):
                    violations.append(
                        f"{loc}: money/price/cost language present (confirm a human signed off)"
                    )
                if has_action_claim(fact.text):
                    violations.append(
                        f"{loc}: action language present (confirm a human signed off)"
                    )
        return violations

    def _iter_markdown_paths(self) -> list[tuple[Path, Tier]]:
        paths: list[tuple[Path, Tier]] = []
        profile = self.root / _PROFILE
        if profile.is_file():
            paths.append((profile, Tier.PROFILE))
        notes = self.root / _NOTES
        if notes.is_file():
            paths.append((notes, Tier.NOTE))
        log_dir = self.root / _LOG_DIR
        if log_dir.is_dir():
            for path in sorted(log_dir.glob("*.md")):
                paths.append((path, Tier.LOG))
        return paths

    def _iter_all(self) -> list[Fact]:
        facts: list[Fact] = []
        facts.extend(self.read_profile())
        facts.extend(self.read_notes())
        facts.extend(self._iter_logs())
        facts.extend(self.candidates())
        return facts

    def _find_exact(self, text: str) -> Fact | None:
        target = text.strip()
        for fact in self._iter_all():
            if fact.text == target:
                return fact
        return None

    def _find_committed(self, text: str) -> Fact | None:
        """Exact text already on disk (not the candidate inbox)."""
        target = text.strip()
        for fact in (
            *self.read_profile(),
            *self.read_notes(),
            *self._iter_logs(),
        ):
            if fact.text == target:
                return fact
        return None

    def _iter_logs(self) -> list[Fact]:
        facts: list[Fact] = []
        log_dir = self.root / _LOG_DIR
        if log_dir.is_dir():
            for path in sorted(log_dir.glob("*.md")):
                facts.extend(self._read_file(path, Tier.LOG))
        return facts

    def _read_file(self, path: Path, tier: Tier) -> list[Fact]:
        if not path.is_file():
            return []
        return parse_markdown(path.read_text(encoding="utf-8"), default_tier=tier)

    def _append_fact(self, fact: Fact) -> None:
        path = self._path_for(fact)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(self._title_for(path, fact) + "\n", encoding="utf-8")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(format_line(fact) + "\n")

    def _path_for(self, fact: Fact) -> Path:
        tier = _tier_for_storage(fact.tier)
        if tier is Tier.PROFILE:
            return self.root / _PROFILE
        if tier is Tier.NOTE:
            return self.root / _NOTES
        return self._log_path(fact.date.year, fact.date.month)

    def _log_path(self, year: int, month: int) -> Path:
        return self.root / _LOG_DIR / f"{year:04d}-{month:02d}.md"

    def _title_for(self, path: Path, fact: Fact) -> str:
        tier = _tier_for_storage(fact.tier)
        if tier is Tier.PROFILE:
            return "# Profile"
        if tier is Tier.NOTE:
            return "# Notes"
        return f"# Log {fact.date.year:04d}-{fact.date.month:02d}"

    def _forget_in_file(self, path: Path, tier: Tier, text: str) -> bool:
        if not path.is_file():
            return False
        original = path.read_text(encoding="utf-8")
        kept_lines: list[str] = []
        removed = False
        for line in original.splitlines():
            fact = parse_line(line.strip(), default_tier=tier)
            if fact is not None and fact.text == text:
                removed = True
                continue
            kept_lines.append(line)
        if not removed:
            return False
        # Drop trailing blank lines, keep a final newline.
        while kept_lines and kept_lines[-1] == "":
            kept_lines.pop()
        path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")
        return True

    def _write_candidates(self, facts: list[Fact]) -> None:
        self.ensure_layout()
        lines = [json.dumps(_fact_to_json(f), ensure_ascii=False) for f in facts]
        body = "\n".join(lines)
        if body:
            body += "\n"
        (self.root / _CANDIDATES).write_text(body, encoding="utf-8")


def _copy_fact(fact: Fact) -> Fact:
    return Fact(
        text=fact.text,
        tier=fact.tier,
        tags=list(fact.tags),
        provenance=fact.provenance,
        human_approved=fact.human_approved,
        date=fact.date,
        id=fact.id,
    )


def _fact_to_json(fact: Fact) -> dict[str, object]:
    return {
        "id": fact.id,
        "text": fact.text,
        "tier": fact.tier.value,
        "tags": [t.value for t in fact.tags],
        "provenance": fact.provenance,
        "human_approved": fact.human_approved,
        "date": fact.date.isoformat(),
    }


def _fact_from_json(payload: dict[str, object]) -> Fact:
    raw_date = payload.get("date") or date.today().isoformat()
    return Fact(
        text=str(payload.get("text") or ""),
        tier=Tier(str(payload.get("tier") or "profile")),
        tags=[ClaimTag(t) for t in (payload.get("tags") or [])],  # type: ignore[arg-type]
        provenance=str(payload.get("provenance") or ""),
        human_approved=bool(payload.get("human_approved")),
        date=date.fromisoformat(str(raw_date)),
        id=str(payload["id"]) if payload.get("id") else None,
    )
