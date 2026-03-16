from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "configs" / "settings.example.yaml"


@dataclass(frozen=True)
class Settings:
    data_root: Path
    raw_dir: Path
    interim_dir: Path
    processed_dir: Path
    outputs_dir: Path
    maturity_buckets_path: Path
    event_windows_path: Path
    data_sources_path: Path


def _resolve_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def load_settings(path: Path | None = None) -> Settings:
    """Load repository settings from YAML."""

    config_path = path or DEFAULT_SETTINGS_PATH
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    paths = config["paths"]
    files = config["files"]

    return Settings(
        data_root=_resolve_path(paths["data_root"]),
        raw_dir=_resolve_path(paths["raw_dir"]),
        interim_dir=_resolve_path(paths["interim_dir"]),
        processed_dir=_resolve_path(paths["processed_dir"]),
        outputs_dir=_resolve_path(paths["outputs_dir"]),
        maturity_buckets_path=_resolve_path(files["maturity_buckets"]),
        event_windows_path=_resolve_path(files["event_windows"]),
        data_sources_path=_resolve_path(files["data_sources"]),
    )
