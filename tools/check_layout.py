#!/usr/bin/env python3
"""Read-only check of the repository layout and benchmark-pinned paths."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    "AERODOCK_MuJoCo",
    "px4-mujoco-drone-simulation",
    "landing_training",
    "benchmark",
    "tidewater-game",
    "artifacts",
    "training_runs",
    "packages/datagen/training_data_generation",
    "data/curated",
    "data/generated",
    "experiments/runs",
    "experiments/benchmarks",
    "experiments/evidence",
    "experiments/archive",
    "models",
    "third_party",
    "tools",
    "docs/architecture",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tracked(patterns: list[str]) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", *patterns],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hash",
        action="store_true",
        help="verify every pinned SHA-256 (slower; reads all pinned assets)",
    )
    args = parser.parse_args()

    errors: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).exists():
            errors.append(f"missing required path: {relative}")

    runtime_file = ROOT / "benchmark/environments/runtime.json"
    counts: dict[str, int] = {}
    if not runtime_file.is_file():
        errors.append("missing benchmark/environments/runtime.json")
    else:
        runtime = json.loads(runtime_file.read_text(encoding="utf-8"))
        for group in ("source_files", "assets", "harness_files"):
            items = runtime.get(group, [])
            counts[group] = len(items)
            for item in items:
                relative = item.get("path")
                if not relative:
                    errors.append(f"{group}: entry without a path")
                    continue
                path = ROOT / relative
                if not path.is_file():
                    errors.append(f"{group}: missing {relative}")
                    continue
                expected = item.get("sha256")
                if args.hash and expected and sha256(path) != expected:
                    errors.append(f"{group}: changed {relative}")

    for pattern, label in (
        ("*.pyc", "tracked bytecode"),
        (".venv/*", "tracked virtual environment"),
        ("node_modules/*", "tracked node_modules"),
    ):
        matches = tracked([pattern])
        if matches:
            errors.append(f"{len(matches)} {label} file(s)")

    sys.path.insert(0, str(ROOT))
    try:
        import training_data_generation  # noqa: F401
        shim_paths = {Path(item).resolve() for item in training_data_generation.__path__}
        expected = ROOT / "packages/datagen/training_data_generation"
        if expected.resolve() not in shim_paths:
            errors.append("training_data_generation shim does not point at packages/datagen")
    except Exception as error:  # pragma: no cover - diagnostic path
        errors.append(f"training_data_generation import failed: {error}")

    if errors:
        print("layout check: FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    summary = ", ".join(f"{name}={count}" for name, count in counts.items())
    print("layout check: OK")
    print(f"  pinned receipts: {summary}")
    print("  pinned source and compatibility shim resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
