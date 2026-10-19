"""Human approval gate for out/brief.md + out/data.csv before export."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APPROVAL_FILENAME = ".approval.json"
REQUIRED_ARTIFACTS = ("brief.md", "data.csv")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_paths(out_dir: Path, out_cfg: dict[str, Any] | None = None) -> dict[str, Path]:
    cfg = out_cfg or {}
    return {
        "brief": out_dir / (cfg.get("brief") or "brief.md"),
        "csv": out_dir / (cfg.get("csv") or "data.csv"),
    }


def approval_path(out_dir: Path) -> Path:
    return out_dir / APPROVAL_FILENAME


def require_artifacts(paths: dict[str, Path]) -> None:
    missing = [str(p) for p in paths.values() if not p.is_file() or p.stat().st_size == 0]
    if missing:
        raise SystemExit(
            "Cannot approve — missing or empty artifacts:\n  - "
            + "\n  - ".join(missing)
            + "\nRun `python src/cli.py --demo` (or --live) first."
        )


def build_approval_record(paths: dict[str, Path]) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for key, path in paths.items():
        files[key] = {
            "path": path.name,
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
    return {
        "approved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": files,
        "note": "Human approved brief.md + data.csv for Gumroad free-tier export (no API upload).",
    }


def write_approval(out_dir: Path, record: dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = approval_path(out_dir)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def load_approval(out_dir: Path) -> dict[str, Any]:
    path = approval_path(out_dir)
    if not path.is_file():
        raise SystemExit(
            f"No approval found at {path}\n"
            "Review out/brief.md and out/data.csv, then run:\n"
            "  python src/cli.py approve --yes"
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Corrupt approval file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Approval file must be a JSON object: {path}")
    return data


def verify_approval(out_dir: Path, out_cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load approval and ensure artifacts still match recorded checksums."""
    paths = artifact_paths(out_dir, out_cfg)
    require_artifacts(paths)
    record = load_approval(out_dir)
    files = record.get("files") or {}
    mismatches: list[str] = []
    for key, path in paths.items():
        entry = files.get(key) or {}
        expected = entry.get("sha256")
        actual = _sha256(path)
        if not expected or expected != actual:
            mismatches.append(f"{path.name} (re-approve after editing)")
    if mismatches:
        raise SystemExit(
            "Approval is stale — artifacts changed since approve:\n  - "
            + "\n  - ".join(mismatches)
            + "\nRun `python src/cli.py approve --yes` again."
        )
    return record


def prompt_confirm(paths: dict[str, Path]) -> bool:
    print("Review these artifacts before approving for Gumroad export:")
    for path in paths.values():
        print(f"  - {path} ({path.stat().st_size} bytes)")
    try:
        answer = input("Approve for export? [y/N] ").strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def approve(
    out_dir: Path,
    *,
    yes: bool = False,
    out_cfg: dict[str, Any] | None = None,
) -> Path:
    paths = artifact_paths(out_dir, out_cfg)
    require_artifacts(paths)
    if not yes and not prompt_confirm(paths):
        raise SystemExit("Approval cancelled.")
    record = build_approval_record(paths)
    path = write_approval(out_dir, record)
    print(f"Approved at {record['approved_at']}")
    print(f"Wrote {path}")
    print("Next: python src/cli.py export")
    return path
