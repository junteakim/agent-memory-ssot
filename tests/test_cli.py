"""CLI smoke tests via memory_ssot.cli.main."""

from __future__ import annotations

from pathlib import Path

from memory_ssot.cli import main


def test_cli_init_write_read_search_forget(tmp_path: Path, capsys) -> None:
    root = tmp_path / "mem"
    assert main(["init", str(root)]) == 0

    assert (
        main(
            [
                "write",
                "--root",
                str(root),
                "--text",
                "The plant has 3 hydrotest bays.",
                "--tier",
                "profile",
                "--tag",
                "VERIFIED",
                "--prov",
                "shop-walk-2026-08-01",
                "--approve",
                "--date",
                "2026-08-19",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "The plant has 3 hydrotest bays." in out

    assert main(["read", "--root", str(root), "--profile"]) == 0
    out = capsys.readouterr().out
    assert "[VERIFIED] The plant has 3 hydrotest bays." in out

    assert main(["search", "--root", str(root), "hydrotest"]) == 0
    assert "hydrotest" in capsys.readouterr().out

    assert main(["forget", "--root", str(root), "--text", "The plant has 3 hydrotest bays."]) == 0
    assert "forgot" in capsys.readouterr().out
    assert main(["read", "--root", str(root), "--profile"]) == 0
    assert "hydrotest" not in capsys.readouterr().out


def test_cli_write_number_rejected(tmp_path: Path, capsys) -> None:
    root = tmp_path / "mem"
    main(["init", str(root)])
    capsys.readouterr()
    rc = main(["write", "--root", str(root), "--text", "Headcount is 40 people."])
    assert rc == 2
    err = capsys.readouterr().err
    assert "do not invent counts" in err


def test_cli_promote_flow(tmp_path: Path, capsys) -> None:
    root = tmp_path / "mem"
    main(["init", str(root)])
    capsys.readouterr()
    rc = main(
        [
            "write",
            "--root",
            str(root),
            "--text",
            "Cranes share one runway.",
            "--tag",
            "VERIFIED",
            "--candidate",
        ]
    )
    assert rc == 0
    cid = capsys.readouterr().out.strip()
    assert cid

    rc = main(["promote", "--root", str(root), "--id", cid])
    assert rc == 1
    assert "stayed-candidate" in capsys.readouterr().out

    rc = main(["promote", "--root", str(root), "--id", cid, "--approve"])
    assert rc == 0
    assert "Cranes share one runway." in capsys.readouterr().out

    main(["read", "--root", str(root), "--profile"])
    assert "Cranes share one runway." in capsys.readouterr().out


def test_cli_check_ok_and_fail(tmp_path: Path, capsys) -> None:
    root = tmp_path / "mem"
    main(["init", str(root)])
    capsys.readouterr()
    assert main(["check", str(root)]) == 0
    assert capsys.readouterr().out.strip() == "ok"

    (root / "profile.md").write_text(
        "# Profile\n- (2026-08-19) There are 9 unused jigs.\n",
        encoding="utf-8",
    )
    assert main(["check", str(root)]) == 1
    assert "do not invent counts" in capsys.readouterr().out


def test_cli_read_log(tmp_path: Path, capsys) -> None:
    root = tmp_path / "mem"
    main(["init", str(root)])
    main(
        [
            "write",
            "--root",
            str(root),
            "--text",
            "RFQ received for a dummy vessel.",
            "--tier",
            "log",
            "--tag",
            "DOCS",
            "--prov",
            "example",
            "--date",
            "2026-08-19",
        ]
    )
    capsys.readouterr()
    assert main(["read", "--root", str(root), "--log", "2026-08"]) == 0
    out = capsys.readouterr().out
    assert "RFQ received for a dummy vessel." in out
