# agent-memory-ssot

A file-backed memory layer for coding agents.

Facts live in markdown you can read in git. The files are the source of truth.
A write that asserts a quantity, a commercial term, or an irreversible action
has to carry a source tag or a human sign-off. There is no "summarize and save" helper.

Neo4j is out of scope for v0.1. This is file-first.

## 이게 뭐냐

에이전트 기억을 마크다운 파일로 고정하는 라이브러리입니다.
`profile.md`와 `log/YYYY-MM.md`가 원본이고, 출처가 없거나 사람이 확인하지 않은
단정은 기록되지 않습니다.

## Install

```bash
pip install -e .
# or, once published:
# pip install memory-ssot
```

Requires Python 3.11+.

## Example

```python
from pathlib import Path
from memory_ssot import MemoryStore, Fact, Tier, ClaimTag, GateError

store = MemoryStore.init(Path("memory"))

store.write(Fact(
    text="The plant has 3 hydrotest bays.",
    tier=Tier.PROFILE,
    tags=[ClaimTag.VERIFIED],
    provenance="shop-walk-2026-08-01",
    human_approved=True,
))

print(store.read_profile())
print(store.search("hydrotest"))

try:
    store.write(Fact(text="About 12 welders on the floor.", tags=[ClaimTag.SPECULATION]))
except GateError as exc:
    print(exc)
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
| `[VERIFIED]` | A human or a live source stood behind this. Required (or DOCS) for a quantity claim. |
| `[DOCS]` | Copied from a document you can point at via `provenance`. |
| `[SPECULATION]` | Soft memory. Cannot sit on the same line as a quantity claim. |

ISO dates (`2026-08-19`) and `YYYY-MM` are ignored by the quantity check, so a dated episode is not treated as a measurement.

## Write rules

Enforced on every `write` / `promote` in `memory_ssot/gates.py`:

1. **Quantity** — leftover digits after date-strip need `VERIFIED` or `DOCS`. Speculation plus a quantity is rejected.
2. **Commercial language** — terms like quotation, invoice, KRW, USD, 견적 need `human_approved=True`.
3. **Irreversible action** — send, delete, git commit, deploy, 발송 need `human_approved=True`.
4. **Dedup** — exact text (trim, case-sensitive) is a no-op and returns the existing fact.
5. **Forget** — exact text only.
6. **Promote** — candidate to profile/log only if `human_approved=True`. Otherwise it stays in the inbox.
7. **No fabrication helper** — there is no API that summarizes a chat and writes it down.

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
- It will not measure the shop for you. Bring a source, or omit the claim.
- Dummy examples only in this repo (a generic pressure-vessel shop). Bring your own facts.

## License

MIT. Copyright 2026 Juntae Kim.
