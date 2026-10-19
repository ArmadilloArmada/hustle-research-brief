"""CLI entry: collect pricing/RSS rows → out/data.csv + out/brief.md."""

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

from collect import CSV_FIELDS, collect
from draft import draft_brief

ROOT = _SRC.parent


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"Config must be a mapping: {path}")
    return data


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a SaaS pricing snapshot research brief (CSV + Markdown).",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=ROOT / "config.yaml",
        help="Path to config.yaml (default: ./config.yaml)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Force demo fixtures (offline dry-run)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Force live fetches (overrides config demo: true)",
    )
    args = parser.parse_args(argv)

    config_path = args.config if args.config.is_absolute() else (Path.cwd() / args.config)
    if not config_path.exists():
        example = ROOT / "config.example.yaml"
        raise SystemExit(
            f"Missing config: {config_path}\n"
            f"Copy {example} to config.yaml and edit sources."
        )

    config = load_config(config_path)
    if args.demo and args.live:
        raise SystemExit("Use only one of --demo or --live")
    if args.demo:
        config["demo"] = True
    if args.live:
        config["demo"] = False

    out_cfg = config.get("output") or {}
    out_dir = Path(out_cfg.get("dir") or "out")
    if not out_dir.is_absolute():
        out_dir = Path.cwd() / out_dir
    csv_path = out_dir / (out_cfg.get("csv") or "data.csv")
    brief_path = out_dir / (out_cfg.get("brief") or "brief.md")

    print(f"Config: {config_path}")
    print(f"Mode: {'demo' if config.get('demo') else 'live'}")
    rows = collect(config)
    write_csv(csv_path, rows)
    brief = draft_brief(config, rows)
    write_brief(brief_path, brief)

    print(f"Wrote {len(rows)} rows → {csv_path}")
    print(f"Wrote brief → {brief_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
