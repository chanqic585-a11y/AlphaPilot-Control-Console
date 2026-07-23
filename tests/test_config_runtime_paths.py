from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_data_dir_can_be_bound_to_the_active_runtime_store(tmp_path: Path) -> None:
    active_data = (tmp_path / "active-data").resolve()
    environment = dict(os.environ)
    environment["ALPHAPILOT_DATA_DIR"] = str(active_data)

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from alphapilot_control_console.config import DATA_DIR; "
                "print(DATA_DIR)"
            ),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert Path(completed.stdout.strip()).resolve() == active_data
