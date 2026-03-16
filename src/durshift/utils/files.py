from __future__ import annotations

from pathlib import Path


def ensure_parent_dir(path: str | Path) -> Path:
    """Create the parent directory for the provided file path."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path
