from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "serve_top200_minimal_ui_readonly.py"


def test_readonly_preview_uses_handler_without_starting_runtime() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "ConsoleHandler" in source
    assert "ThreadingHTTPServer" in source
    assert "run_server" not in source
    assert "start_demo_market_runtime" not in source
    assert "start_unified_auto_execution_runner" not in source
    assert "strategy orders, Live, or Withdraw" in source


def test_readonly_preview_module_imports_without_serving() -> None:
    spec = importlib.util.spec_from_file_location("top200_readonly_preview", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert callable(module.main)
