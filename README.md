# agent-memory-ssot

Coding agents invent headcount, invent prices, and then write "I already sent that email."
This library is a **file-backed Single Source of Truth** so they stop doing that.

Facts live in markdown you can read in git. Writes go through hard gates: no invented
numbers, no money/action claims without a human, no silent overwrite of the same line.

Neo4j is out of scope for v0.1. This is file-first.

## 이게 뭐냐

에이전트가 사람 수, 금액, "메일 이미 보냄"을 지어내지 못하게 하는 파일 기반 기억층입니다.
`profile.md`와 `log/YYYY-MM.md`가 원본이고, 숫자는 세거나 생략하고, 돈/발송은 사람 승인 없이는 못 적습니다.

## Install

```bash
pip install -e .
# or, once published:
# pip install memory-ssot
```

Requires Python 3.11+.

## 20-line example

```python
from pathlib import Path
from memory_ssot import MemoryStore, Fact, Tier, ClaimTag, GateError

store = MemoryStore.init(Path("memory"))

store.write(Fact(
    text="The plant has 3 hydrotest bays.",
    tier=Tier.PROFILE,
    tags=[ClaimTag.VERIFIED],
    provenance="shop-walk-2026-08-01",
    human_approved=True,  # required: the text contains a number
))

print(store.read_profile())
print(store.search("hydrotest"))

try:
    store.write(Fact(text="About 12 welders on the floor.", tags=[ClaimTag.SPECULATION]))
except GateError as exc:
    print(exc)  # numbers require VERIFIED or DOCS; do not invent counts
```

## File format

`memory/profile.md`:

```markdown
# Profile
- (2026-08-19) [VERIFIED] The plant has 3 hydrotest bays. <!-- prov:shop-walk-2026-08-01 -->
```

`memory/log/2026-08.md`:

```markdown
# Log 2026-08
- (2026-08-19) [DOCS] RFQ received for a dummy vessel. <!-- prov:example -->
```

Unpromoted facts sit in `memory/candidates.jsonl` until a human approves `promote`.

## Claim tags

| Tag | Meaning |
| --- | --- |
| `[VERIFIED]` | A human or a live count stood behind this. Required (or DOCS) if the text has a digit. |
| `[DOCS]` | Copied from a document you can point at via `provenance`. Also satisfies the number gate. |
| `[SPECULATION]` | Soft memory. **Illegal** on the same line as a number. |

ISO dates (`2026-08-19`) and `YYYY-MM` in the text are stripped before the number gate runs, so a dated episode is not a count claim.

## Gates (the product)

Enforced on every `write` / `promote` in `memory_ssot/gates.py`:

1. **Number** — leftover digits after date-strip require `VERIFIED` or `DOCS`. Speculation + a number is rejected. Message: `numbers require VERIFIED or DOCS; do not invent counts`.
2. **Money** — `money` / `price` / `cost` / `KRW` / `USD` / `invoice` / `quotation` / `견적` / `원` / `달러` require `human_approved=True`.
3. **Action** — send-mail, delete, git commit, deploy, `발송` require `human_approved=True`.
4. **Dedup** — exact text (trim, case-sensitive) is a no-op and returns the existing fact.
5. **Forget** — exact text only.
6. **Promote** — candidate → profile/log only if `human_approved=True`. Otherwise it stays in the inbox.
7. **No fabrication helper** — there is no "summarize and write" API.

## API

```python
from memory_ssot import MemoryStore, Fact, Tier, ClaimTag, GateError

store = MemoryStore(root)  # root/profile.md and root/log/YYYY-MM.md

store.write(fact) -> Fact
store.write(fact, candidate=True) -> Fact   # inbox
store.propose(fact) -> str                  # candidate id
store.read_profile() -> list[Fact]
store.read_log(year=2026, month=8) -> list[Fact]
store.search("hydrotest") -> list[Fact]
store.forget("exact fact text") -> bool
store.promote(candidate_id)                 # no-op without approval
store.promote(candidate_id, human_approved=True)
store.candidates()                          # inbox
store.check() -> list[str]                  # on-disk gate violations
```

## CLI

```bash
memory-ssot init ./memory
memory-ssot write --root ./memory --text "The plant has 3 hydrotest bays." \
    --tier profile --tag VERIFIED --prov shop-walk-2026-08-01 --approve
memory-ssot read --root ./memory --profile
memory-ssot read --root ./memory --log 2026-08
memory-ssot search --root ./memory hydrotest
memory-ssot forget --root ./memory --text "The plant has 3 hydrotest bays."
memory-ssot write --root ./memory --text "Cranes share one runway." --tag VERIFIED --candidate
memory-ssot promote --root ./memory --id <id> --approve
memory-ssot check ./memory
```

## What this is not

- Not a graph database. Not a vector store. Not an LLM wrapper.
- It will not count people for you. Live-count or omit.
- Dummy examples only in this repo (a generic pressure-vessel shop). Bring your own facts.

## License

MIT. Copyright 2026 Juntae Kim.
