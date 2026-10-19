"""CLI: collect → human approve → export pack for Gumroad free-tier upload."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import yaml

from approve import approve as do_approve
from collect import CSV_FIELDS, collect
from draft import draft_brief
from export import export_pack

ROOT = _SRC.parent


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"Config must be a mapping: {path}")
    return data


def resolve_config_path(raw: Path) -> Path:
    path = raw if raw.is_absolute() else (Path.cwd() / raw)
    if not path.exists():
        example = ROOT / "config.example.yaml"
        raise SystemExit(
            f"Missing config: {path}\n"
            f"Copy {example} to config.yaml and edit sources."
        )
    return path


def resolve_out_dir(config: dict[str, Any]) -> Path:
    out_cfg = config.get("output") or {}
    out_dir = Path(out_cfg.get("dir") or "out")
    if not out_dir.is_absolute():
        out_dir = Path.cwd() / out_dir
    return out_dir


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})


def write_brief(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def apply_mode_flags(config: dict[str, Any], demo: bool, live: bool) -> None:
    if demo and live:
        raise SystemExit("Use only one of --demo or --live")
    if demo:
        config["demo"] = True
    if live:
        config["demo"] = False


def cmd_run(args: argparse.Namespace) -> int:
    config_path = resolve_config_path(args.config)
    config = load_config(config_path)
    apply_mode_flags(config, args.demo, args.live)

    out_cfg = config.get("output") or {}
    out_dir = resolve_out_dir(config)
    csv_path = out_dir / (out_cfg.get("csv") or "data.csv")
    brief_path = out_dir / (out_cfg.get("brief") or "brief.md")

    # New collect invalidates prior approval.
    approval = out_dir / ".approval.json"
    if approval.exists():
        approval.unlink()

    print(f"Config: {config_path}")
    print(f"Mode: {'demo' if config.get('demo') else 'live'}")
    rows = collect(config)
    write_csv(csv_path, rows)
    brief = draft_brief(config, rows)
    write_brief(brief_path, brief)

    print(f"Wrote {len(rows)} rows → {csv_path}")
    print(f"Wrote brief → {brief_path}")
    print("Next: review artifacts, then `python src/cli.py approve --yes`")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    config_path = resolve_config_path(args.config)
    config = load_config(config_path)
    out_dir = resolve_out_dir(config)
    out_cfg = config.get("output") or {}
    do_approve(out_dir, yes=args.yes, out_cfg=out_cfg)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    config_path = resolve_config_path(args.config)
    config = load_config(config_path)
    out_dir = resolve_out_dir(config)
    results = export_pack(config, out_dir, fmt=args.format, clean=not args.keep_old)
    print("Export ready for Gumroad free-tier upload (manual — no API):")
    for kind, path in results.items():
        print(f"  {kind}: {path}")
    print("Upload the .zip (or folder contents) in the Gumroad product UI.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "SaaS pricing snapshot research brief: collect → approve → export "
            "for Gumroad free-tier digital download (no API upload)."
        ),
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=ROOT / "config.yaml",
        help="Path to config.yaml (default: ./config.yaml)",
    )

    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Collect sources and draft out/brief.md + out/data.csv")
    run_p.add_argument("--demo", action="store_true", help="Force demo fixtures (offline dry-run)")
    run_p.add_argument("--live", action="store_true", help="Force live fetches")
    run_p.set_defaults(func=cmd_run)

    ap = sub.add_parser("approve", help="Human-approve out/brief.md + out/data.csv")
    ap.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Approve without interactive prompt (after you reviewed the files)",
    )
    ap.set_defaults(func=cmd_approve)

    ex = sub.add_parser(
        "export",
        help="Pack approved artifacts into out/export/ (zip and/or folder)",
    )
    ex.add_argument(
        "--format",
        choices=("both", "zip", "folder"),
        default="both",
        help="Export zip, folder, or both (default: both)",
    )
    ex.add_argument(
        "--keep-old",
        action="store_true",
        help="Do not clear previous packs under out/export/",
    )
    ex.set_defaults(func=cmd_export)

    # Backward-compatible top-level --demo/--live → run
    parser.add_argument("--demo", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--live", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()

    # Bare flags without subcommand: `python src/cli.py --demo`
    if not argv or argv[0].startswith("-"):
        args = parser.parse_args(argv)
        args.command = "run"
        args.func = cmd_run
        if not hasattr(args, "demo"):
            args.demo = False
        if not hasattr(args, "live"):
            args.live = False
        return int(args.func(args))

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
