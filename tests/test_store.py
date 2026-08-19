"""Store integration tests: write, dedup, forget, promote, search, init."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from memory_ssot import ClaimTag, Fact, GateError, MemoryStore, Tier


def _store(tmp_path: Path) -> MemoryStore:
    return MemoryStore.init(tmp_path / "memory")


def test_init_layout(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert (store.root / "profile.md").is_file()
    assert (store.root / "log").is_dir()
    assert (store.root / "candidates.jsonl").is_file()
    assert (store.root / "profile.md").read_text(encoding="utf-8").startswith("# Profile")


def test_happy_write_profile(tmp_path: Path) -> None:
    store = _store(tmp_path)
    fact = store.write(
        Fact(
            text="The plant has 3 hydrotest bays.",
            tier=Tier.PROFILE,
            tags=[ClaimTag.VERIFIED],
            provenance="shop-walk-2026-08-01",
            human_approved=True,
            date=date(2026, 8, 19),
        )
    )
    assert fact.text == "The plant has 3 hydrotest bays."
    profile = store.read_profile()
    assert len(profile) == 1
    assert profile[0].tags == [ClaimTag.VERIFIED]
    assert profile[0].provenance == "shop-walk-2026-08-01"
    raw = (store.root / "profile.md").read_text(encoding="utf-8")
    assert "# Profile" in raw
    assert "[VERIFIED] The plant has 3 hydrotest bays." in raw
    assert "<!-- prov:shop-walk-2026-08-01 -->" in raw
    assert "(2026-08-19)" in raw


def test_write_log_month_file(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.write(
        Fact(
            text="RFQ received for a dummy vessel.",
            tier=Tier.LOG,
            tags=[ClaimTag.DOCS],
            provenance="example",
            date=date(2026, 8, 19),
        )
    )
    rows = store.read_log(2026, 8)
    assert len(rows) == 1
    assert rows[0].text == "RFQ received for a dummy vessel."
    raw = (store.root / "log" / "2026-08.md").read_text(encoding="utf-8")
    assert raw.startswith("# Log 2026-08")
    assert "[DOCS] RFQ received for a dummy vessel." in raw


def test_number_without_tag_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(GateError, match="do not invent counts"):
        store.write(Fact(text="The plant has 3 hydrotest bays."))


def test_speculation_plus_number_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(GateError, match="do not invent counts"):
        store.write(
            Fact(
                text="About 12 welders on the floor.",
                tags=[ClaimTag.SPECULATION],
            )
        )


def test_money_without_approve_rejected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(GateError, match="human_approved"):
        store.write(
            Fact(
                text="Quoted price in USD for a dummy job.",
                tags=[ClaimTag.DOCS],
            )
        )


def test_exact_dedup(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.write(
        Fact(
            text="Bay doors face north.",
            tags=[ClaimTag.VERIFIED],
            provenance="walk-1",
            date=date(2026, 8, 1),
        )
    )
    second = store.write(
        Fact(
            text="  Bay doors face north.  ",
            tags=[ClaimTag.DOCS],
            provenance="walk-2",
        )
    )
    assert second.text == first.text
    assert second.provenance == "walk-1"
    assert len(store.read_profile()) == 1
    # case-sensitive: different casing is a new fact
    store.write(Fact(text="bay doors face north.", tags=[ClaimTag.VERIFIED]))
    assert len(store.read_profile()) == 2


def test_forget_exact_text(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.write(Fact(text="Keep this.", tags=[ClaimTag.VERIFIED]))
    store.write(Fact(text="Drop this.", tags=[ClaimTag.VERIFIED]))
    assert store.forget("Drop this.") is True
    texts = [f.text for f in store.read_profile()]
    assert texts == ["Keep this."]
    assert store.forget("not present") is False
    # case-sensitive: wrong case is a miss
    assert store.forget("keep this.") is False


def test_promote_without_approve_stays_candidate(tmp_path: Path) -> None:
    store = _store(tmp_path)
    cid = store.propose(
        Fact(
            text="Cranes share one runway.",
            tier=Tier.PROFILE,
            tags=[ClaimTag.VERIFIED],
            provenance="inbox",
            human_approved=False,
        )
    )
    assert store.promote(cid) is None
    assert len(store.candidates()) == 1
    assert store.read_profile() == []


def test_promote_with_approve_lands_in_profile(tmp_path: Path) -> None:
    store = _store(tmp_path)
    cid = store.propose(
        Fact(
            text="Cranes share one runway.",
            tier=Tier.PROFILE,
            tags=[ClaimTag.VERIFIED],
            provenance="inbox",
            date=date(2026, 8, 19),
        )
    )
    promoted = store.promote(cid, human_approved=True)
    assert promoted is not None
    assert promoted.text == "Cranes share one runway."
    assert store.candidates() == []
    assert [f.text for f in store.read_profile()] == ["Cranes share one runway."]


def test_date_digits_do_not_trip_number_gate(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.write(
        Fact(
            text="Shop walk on 2026-08-01 noted clean bays.",
            tier=Tier.LOG,
            tags=[ClaimTag.SPECULATION],
            provenance="example",
            date=date(2026, 8, 1),
        )
    )
    rows = store.read_log(2026, 8)
    assert len(rows) == 1


def test_search(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.write(
        Fact(
            text="The plant has 3 hydrotest bays.",
            tags=[ClaimTag.VERIFIED],
            human_approved=True,
        )
    )
    store.write(
        Fact(
            text="Paint booth sits west of the bay line.",
            tags=[ClaimTag.VERIFIED],
        )
    )
    hits = store.search("hydrotest")
    assert [f.text for f in hits] == ["The plant has 3 hydrotest bays."]
    assert store.search("HYDROTEST")  # case-insensitive
    assert store.search("no-such-token") == []


def test_propose_number_still_gated(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(GateError, match="do not invent counts"):
        store.propose(Fact(text="There are 9 unused jigs."))


def test_check_flags_invented_counts(tmp_path: Path) -> None:
    store = _store(tmp_path)
    (store.root / "profile.md").write_text(
        "# Profile\n"
        "- (2026-08-19) [SPECULATION] There are 9 unused jigs.\n",
        encoding="utf-8",
    )
    violations = store.check()
    assert any("do not invent counts" in v for v in violations)
