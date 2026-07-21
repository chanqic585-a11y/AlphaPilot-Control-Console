from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alphapilot_control_console.v54_v60_evidence import build_v54_v60_evidence


DEFAULT_QUANT_ROOT = Path(r"D:\Codex-Workspace\AlphaPilot-Quant-Engine")
DEFAULT_DOCS_ROOT = Path(r"D:\Codex-Workspace\AlphaPilot-Docs")
DEFAULT_OUTPUT_ROOT = Path(r"D:\Codex-Workspace\deliveries")


def _git(git_executable: str, root: Path, *arguments: str) -> str:
    result = subprocess.run(
        [git_executable, *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _repository_snapshot(git_executable: str, root: Path) -> dict[str, Any]:
    head = _git(git_executable, root, "rev-parse", "HEAD")
    status = _git(git_executable, root, "status", "--porcelain")
    branch = _git(git_executable, root, "branch", "--show-current")
    pointing_tags = [
        item for item in _git(git_executable, root, "tag", "--points-at", "HEAD").splitlines() if item
    ]
    try:
        upstream = _git(git_executable, root, "rev-parse", "@{upstream}")
    except subprocess.CalledProcessError:
        upstream = None
    try:
        remote_url = _git(git_executable, root, "remote", "get-url", "origin")
    except subprocess.CalledProcessError:
        remote_url = None
    return {
        "root": str(root),
        "remoteUrl": remote_url,
        "branch": branch,
        "headCommit": head,
        "upstreamCommit": upstream,
        "pointingTags": pointing_tags,
        "pushStatus": "verified" if upstream == head else "not_verified",
        "worktreeClean": not bool(status),
    }


def _read_json(path: Path | None, default: dict[str, Any]) -> dict[str, Any]:
    if path is None:
        return default
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the verified V54-V60 total evidence ZIP")
    parser.add_argument("--console-root", type=Path, default=ROOT)
    parser.add_argument("--quant-root", type=Path, default=DEFAULT_QUANT_ROOT)
    parser.add_argument("--docs-root", type=Path, default=DEFAULT_DOCS_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--git", default="git")
    parser.add_argument("--repository-snapshots", type=Path)
    parser.add_argument("--test-summary", type=Path)
    args = parser.parse_args()

    repository_snapshots = _read_json(
        args.repository_snapshots,
        {
            "Console": _repository_snapshot(args.git, args.console_root),
            "Quant": _repository_snapshot(args.git, args.quant_root),
            "Docs": _repository_snapshot(args.git, args.docs_root),
        },
    )
    test_summary = _read_json(args.test_summary, {"status": "not_supplied"})
    result = build_v54_v60_evidence(
        console_root=args.console_root,
        quant_root=args.quant_root,
        docs_root=args.docs_root,
        output_root=args.output_root,
        repository_snapshots=repository_snapshots,
        test_summary=test_summary,
    )
    print(
        json.dumps(
            {
                "zipPath": str(result["zipPath"]),
                "sha256Path": str(result["sha256Path"]),
                "sha256": result["sha256"],
                "artifactCount": result["artifactCount"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
