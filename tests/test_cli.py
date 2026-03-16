from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_module_cli_builds_operation_panel(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    input_path = repo_root / "data" / "examples" / "sample_buybacks.csv"
    output_path = tmp_path / "panel.csv"

    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "durshift.cli",
            "build-operation-panel",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert output_path.exists()
    assert str(output_path) in result.stdout
