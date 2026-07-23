"""Static checks for provider and execution-path dependency boundaries."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable


_PROVIDER_MODULE_PREFIXES = (
    "openai",
    "deepseek",
    "google.genai",
    "google.generativeai",
    "anthropic",
)
_EXECUTION_FILE_FRAGMENTS = (
    "order",
    "risk",
    "position",
    "reconciliation",
    "approval",
    "arm",
    "kill_switch",
    "auto_execution",
    "execution_runtime",
)


def _python_files(root: Path) -> Iterable[Path]:
    yield from sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _imports(path: Path) -> list[tuple[str, int]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.module, node.lineno))
    return imports


def find_direct_provider_imports(package_root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in _python_files(package_root):
        relative = path.relative_to(package_root)
        if relative.parts[:2] == ("ai_orchestration", "provider_adapters"):
            continue
        for module, line in _imports(path):
            if any(module == prefix or module.startswith(prefix + ".") for prefix in _PROVIDER_MODULE_PREFIXES):
                findings.append({"path": relative.as_posix(), "line": line, "module": module})
    return findings


def find_execution_path_ai_imports(package_root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in _python_files(package_root):
        name = path.stem.lower()
        if not any(fragment in name for fragment in _EXECUTION_FILE_FRAGMENTS):
            continue
        for module, line in _imports(path):
            if module == "ai_orchestration" or "ai_orchestration" in module.split("."):
                findings.append(
                    {
                        "path": path.relative_to(package_root).as_posix(),
                        "line": line,
                        "module": module,
                    }
                )
    return findings
