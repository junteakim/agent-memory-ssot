"""Dummy walkthrough for a generic pressure-vessel shop. No real company."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from memory_ssot import ClaimTag, Fact, GateError, MemoryStore, Tier


def main() -> None:
    root = Path(__file__).resolve().parent / "demo-memory"
    store = MemoryStore.init(root)

    store.write(
        Fact(
            text="The plant has 3 hydrotest bays.",
            tier=Tier.PROFILE,
            tags=[ClaimTag.VERIFIED],
            provenance="shop-walk-2026-08-01",
            human_approved=True,
            date=date(2026, 8, 19),
        )
    )
    store.write(
        Fact(
            text="Bay doors face the yard, not the street.",
            tier=Tier.PROFILE,
            tags=[ClaimTag.VERIFIED],
            provenance="shop-walk-2026-08-01",
            date=date(2026, 8, 19),
        )
    )
    store.write(
        Fact(
            text="RFQ received for a dummy vessel.",
            tier=Tier.LOG,
            tags=[ClaimTag.DOCS],
            provenance="example",
            date=date(2026, 8, 19),
        )
    )

    print("profile:")
    for fact in store.read_profile():
        print(f"  {fact.text}")

    print("search hydrotest:")
    for fact in store.search("hydrotest"):
        print(f"  {fact.text}")

    try:
        store.write(
            Fact(
                text="About 12 welders on the floor.",
                tags=[ClaimTag.SPECULATION],
            )
        )
    except GateError as exc:
        print(f"rejected speculation+number: {exc}")

    try:
        store.write(Fact(text="Quoted price in USD for a dummy job.", tags=[ClaimTag.DOCS]))
    except GateError as exc:
        print(f"rejected money without sign-off: {exc}")

    try:
        store.write(Fact(text="I already sent that email."))
    except GateError as exc:
        print(f"rejected action without sign-off: {exc}")

    cid = store.propose(
        Fact(
            text="Cranes share one runway.",
            tags=[ClaimTag.VERIFIED],
            provenance="inbox",
        )
    )
    print(f"candidate {cid} stays put without approve:", store.promote(cid))
    promoted = store.promote(cid, human_approved=True)
    print("promoted:", promoted.text if promoted else None)
    print("root:", root)


if __name__ == "__main__":
    main()
