from __future__ import annotations

import sys
from pathlib import Path

import yaml

REQUIRED_PATHS = [
    "README.md",
    "LICENSE",
    "configs/settings.example.yaml",
    "configs/maturity_buckets.yaml",
    "configs/event_windows.yaml",
    "configs/data_sources.yaml",
    "data/examples/sample_buybacks.csv",
    "scripts/run_pipeline.sh",
    "src/durshift/cli.py",
    "tests/test_duration.py",
]


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    missing = [path for path in REQUIRED_PATHS if not (repo_root / path).exists()]
    if missing:
        print("Missing required seed files:")
        for path in missing:
            print(f" - {path}")
        return 1

    config_path = repo_root / "configs" / "settings.example.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    if "paths" not in config or "files" not in config:
        print("settings.example.yaml is missing required top-level keys.")
        return 1

    print("DurShift seed looks structurally complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
