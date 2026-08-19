"""Hard gates. Agents invent counts, prices, and "I already sent that". Stop them."""

from __future__ import annotations

import re

from memory_ssot.models import ClaimTag, Fact

ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
ISO_MONTH_RE = re.compile(r"\b\d{4}-\d{2}\b")
HAS_DIGIT_RE = re.compile(r"\d")

# Word-boundary-ish: English tokens plus listed Korean currency/quote words.
_MONEY_EN = r"money|price|cost|krw|usd|invoice|quotation"
MONEY_RE = re.compile(
    rf"(?i)(?<!\w)(?:{_MONEY_EN})(?!\w)|견적|달러|(?<![가-힣A-Za-z])원(?![가-힣A-Za-z])"
)

# "Implies send-mail" includes the lie this library exists to stop.
ACTION_RE = re.compile(
    r"(?i)"
    r"(?:send[\s-]?mails?|send[\s-]?e-?mails?|"
    r"sent[\s-]+(?:that\s+|the\s+|an\s+|a\s+)?(?:e-?mail|mail)|"
    r"emailed|e-mailed|"
    r"git\s+commit|"
    r"(?<!\w)delete(?!\w)|"
    r"(?<!\w)deploy(?!\w)|"
    r"발송)"
)

NUMBER_GATE_MSG = "numbers require VERIFIED or DOCS; do not invent counts"
MONEY_GATE_MSG = "money/price/cost claims require human_approved=True"
ACTION_GATE_MSG = "send-mail / delete / git commit / deploy / 발송 require human_approved=True"
PROMOTE_GATE_MSG = "promote requires human_approved=True"


class GateError(ValueError):
    """A write or promote violated a hard gate."""


def strip_iso_dates(text: str) -> str:
    """Remove ISO dates and YYYY-MM so leftover digits are real claims."""
    without_days = ISO_DATE_RE.sub(" ", text)
    return ISO_MONTH_RE.sub(" ", without_days)


def has_claimed_number(text: str) -> bool:
    """True if text still has a digit after ISO dates / YYYY-MM are removed."""
    return bool(HAS_DIGIT_RE.search(strip_iso_dates(text)))


def has_money_claim(text: str) -> bool:
    return bool(MONEY_RE.search(text))


def has_action_claim(text: str) -> bool:
    return bool(ACTION_RE.search(text))


def _tag_values(fact: Fact) -> set[ClaimTag]:
    return set(fact.tags)


def check_number_gate(fact: Fact) -> None:
    if not has_claimed_number(fact.text):
        return
    tags = _tag_values(fact)
    if ClaimTag.SPECULATION in tags:
        raise GateError(NUMBER_GATE_MSG)
    if ClaimTag.VERIFIED not in tags and ClaimTag.DOCS not in tags:
        raise GateError(NUMBER_GATE_MSG)


def check_money_gate(fact: Fact) -> None:
    if has_money_claim(fact.text) and not fact.human_approved:
        raise GateError(MONEY_GATE_MSG)


def check_action_gate(fact: Fact) -> None:
    if has_action_claim(fact.text) and not fact.human_approved:
        raise GateError(ACTION_GATE_MSG)


def check_write_gates(fact: Fact) -> None:
    """Enforce every gate that applies to a direct write."""
    check_number_gate(fact)
    check_money_gate(fact)
    check_action_gate(fact)


def check_promote_gates(fact: Fact) -> None:
    """Promote is a write: all write gates, plus explicit human sign-off."""
    if not fact.human_approved:
        raise GateError(PROMOTE_GATE_MSG)
    check_write_gates(fact)
