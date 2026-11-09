"""Generate both sample sets into one output directory.

Run from the repository root:
    python -m training_data_generation.generate_samples --output datasets/tdg_samples
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from training_data_generation.core.io import write_manifest
from training_data_generation.pad_finder.generate import generate_pad_samples
from training_data_generation.search.generate import generate_search_samples


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("datasets/training_data_generation_samples"),
    )
    parser.add_argument("--samples", type=int, default=2, help="samples per task")
    parser.add_argument("--profile", choices=("far", "near"), default="far")
    parser.add_argument("--seed", type=int, default=20261107)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    search = generate_search_samples(
        output,
        samples=args.samples,
        seed=args.seed,
        overwrite=args.overwrite,
        profile=args.profile,
    )
    pad = generate_pad_samples(
        output,
        samples=args.samples,
        seed=args.seed,
        overwrite=args.overwrite,
        profile=args.profile,
    )
    write_manifest(
        output / "manifest.json",
        {
            "description": "Real MuJoCo camera frames with search and pad-finder labels.",
            "profile": args.profile,
            "search": search,
            "pad_finder": pad,
        },
    )
    print(json.dumps({"output": str(output), "search": search, "pad_finder": pad}, indent=2))


if __name__ == "__main__":
    main()
