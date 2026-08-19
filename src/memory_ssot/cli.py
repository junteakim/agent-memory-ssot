"""memory-ssot command-line interface."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from memory_ssot.gates import GateError
from memory_ssot.models import ClaimTag, Fact, Tier
from memory_ssot.parse import format_line
from memory_ssot.store import MemoryStore


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except GateError as exc:
        print(f"gate: {exc}", file=sys.stderr)
        return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memory-ssot",
        description="File-backed SSOT memory for coding agents. Never invent numbers.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="create profile.md, log/, candidates.jsonl")
    p_init.add_argument("dir")
    p_init.set_defaults(func=cmd_init)

    p_write = sub.add_parser("write", help="append a fact (or --candidate inbox)")
    p_write.add_argument("--text", required=True)
    p_write.add_argument("--tier", choices=["profile", "log", "note"], default="profile")
    p_write.add_argument("--tag", action="append", default=[], help="VERIFIED, DOCS, SPECULATION")
    p_write.add_argument("--prov", default="")
    p_write.add_argument("--approve", action="store_true")
    p_write.add_argument("--candidate", action="store_true")
    p_write.add_argument("--root", default=".")
    p_write.add_argument("--date", default=None, help="YYYY-MM-DD (default: today)")
    p_write.set_defaults(func=cmd_write)

    p_read = sub.add_parser("read", help="print profile or a monthly log")
    g = p_read.add_mutually_exclusive_group(required=True)
    g.add_argument("--profile", action="store_true")
    g.add_argument("--log", metavar="YYYY-MM")
    p_read.add_argument("--root", default=".")
    p_read.set_defaults(func=cmd_read)

    p_search = sub.add_parser("search", help="substring search across files")
    p_search.add_argument("q")
    p_search.add_argument("--root", default=".")
    p_search.set_defaults(func=cmd_search)

    p_forget = sub.add_parser("forget", help="delete by exact text")
    p_forget.add_argument("--text", required=True)
    p_forget.add_argument("--root", default=".")
    p_forget.set_defaults(func=cmd_forget)

    p_promote = sub.add_parser("promote", help="candidate -> profile/log")
    p_promote.add_argument("--id", required=True)
    p_promote.add_argument("--approve", action="store_true")
    p_promote.add_argument("--root", default=".")
    p_promote.set_defaults(func=cmd_promote)

    p_check = sub.add_parser("check", help="validate files and print gate violations")
    p_check.add_argument("dir")
    p_check.set_defaults(func=cmd_check)

    return parser


def cmd_init(args: argparse.Namespace) -> int:
    store = MemoryStore.init(args.dir)
    print(store.root.resolve())
    return 0


def cmd_write(args: argparse.Namespace) -> int:
    tags = [ClaimTag(t.upper()) for t in args.tag]
    fact_date = date.fromisoformat(args.date) if args.date else date.today()
    fact = Fact(
        text=args.text,
        tier=Tier(args.tier),
        tags=tags,
        provenance=args.prov,
        human_approved=args.approve,
        date=fact_date,
    )
    store = MemoryStore(args.root)
    written = store.write(fact, candidate=args.candidate)
    if args.candidate:
        print(written.id or "")
    else:
        print(format_line(written))
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    store = MemoryStore(args.root)
    if args.profile:
        for fact in store.read_profile():
            print(format_line(fact))
        return 0
    ym = args.log
    if not _looks_like_ym(ym):
        print("log month must be YYYY-MM", file=sys.stderr)
        return 2
    year_s, month_s = ym.split("-")
    for fact in store.read_log(int(year_s), int(month_s)):
        print(format_line(fact))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    store = MemoryStore(args.root)
    for fact in store.search(args.q):
        print(format_line(fact))
    return 0


def cmd_forget(args: argparse.Namespace) -> int:
    store = MemoryStore(args.root)
    ok = store.forget(args.text)
    print("forgot" if ok else "not-found")
    return 0 if ok else 1


def cmd_promote(args: argparse.Namespace) -> int:
    store = MemoryStore(args.root)
    fact = store.promote(args.id, human_approved=True if args.approve else None)
    if fact is None:
        print("stayed-candidate")
        return 1
    print(format_line(fact))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.dir)
    store = MemoryStore(root)
    violations = store.check()
    if not violations:
        print("ok")
        return 0
    for item in violations:
        print(item)
    return 1


def _looks_like_ym(value: str) -> bool:
    if len(value) != 7 or value[4] != "-":
        return False
    y, m = value.split("-")
    return y.isdigit() and m.isdigit() and 1 <= int(m) <= 12


if __name__ == "__main__":
    sys.exit(main())
