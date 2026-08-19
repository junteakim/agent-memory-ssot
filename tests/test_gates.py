"""Gate unit tests — the product."""

from __future__ import annotations

from datetime import date

import pytest

from memory_ssot import ClaimTag, Fact, GateError, Tier
from memory_ssot.gates import (
    NUMBER_GATE_MSG,
    check_number_gate,
    check_write_gates,
    has_action_claim,
    has_claimed_number,
    has_money_claim,
)


def _fact(text: str, **kwargs) -> Fact:
    kwargs.setdefault("tier", Tier.PROFILE)
    kwargs.setdefault("tags", [])
    return Fact(text=text, **kwargs)


def test_date_digits_are_not_claimed_numbers() -> None:
    assert not has_claimed_number("Walkthrough completed on 2026-08-01.")
    assert not has_claimed_number("Logged in 2026-08.")
    assert has_claimed_number("The plant has 3 hydrotest bays.")


def test_number_without_tag_rejected() -> None:
    with pytest.raises(GateError, match=NUMBER_GATE_MSG):
        check_number_gate(_fact("The plant has 3 hydrotest bays."))


def test_speculation_plus_number_rejected() -> None:
    with pytest.raises(GateError, match=NUMBER_GATE_MSG):
        check_number_gate(
            _fact(
                "About 12 welders on the floor.",
                tags=[ClaimTag.SPECULATION],
            )
        )


def test_verified_number_ok() -> None:
    check_number_gate(
        _fact("The plant has 3 hydrotest bays.", tags=[ClaimTag.VERIFIED])
    )


def test_docs_number_ok() -> None:
    check_number_gate(_fact("Drawing lists 2 nozzles.", tags=[ClaimTag.DOCS]))


def test_money_without_approve_rejected() -> None:
    with pytest.raises(GateError, match="human_approved"):
        check_write_gates(_fact("Quoted price in USD for a dummy job."))


def test_money_korean_requires_approve() -> None:
    with pytest.raises(GateError, match="human_approved"):
        check_write_gates(_fact("견적 초안을 작성했다."))
    with pytest.raises(GateError, match="human_approved"):
        check_write_gates(_fact("단가는 원 단위로 적는다."))


def test_money_with_approve_ok() -> None:
    check_write_gates(
        _fact(
            "Invoice language is USD on the dummy form.",
            tags=[ClaimTag.DOCS],
            human_approved=True,
        )
    )


def test_action_without_approve_rejected() -> None:
    with pytest.raises(GateError, match="human_approved"):
        check_write_gates(_fact("I already sent that email."))
    with pytest.raises(GateError, match="human_approved"):
        check_write_gates(_fact("발송 완료로 기록한다."))
    with pytest.raises(GateError, match="human_approved"):
        check_write_gates(_fact("Ready to git commit the memory files."))


def test_action_with_approve_ok() -> None:
    check_write_gates(_fact("I already sent that email.", human_approved=True))


def test_money_helpers() -> None:
    assert has_money_claim("The quotation is not ready.")
    assert has_money_claim("KRW is listed on the dummy form.")
    assert not has_money_claim("The shop paints support brackets.")
    assert not has_money_claim("지원 요청을 남긴다.")  # 원 inside 지원


def test_action_helpers() -> None:
    assert has_action_claim("Please send-mail the dummy notice.")
    assert has_action_claim("Do not deploy from an agent.")
    assert has_action_claim("delete the scratch file")
    assert not has_action_claim("The shop uses a mailing address for drawings.")


def test_iso_date_on_fact_does_not_need_number_tag() -> None:
    fact = _fact(
        "Shop walk on 2026-08-01 noted clean bays.",
        tags=[ClaimTag.SPECULATION],
        date=date(2026, 8, 1),
    )
    check_number_gate(fact)
