from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
WEB_DIR = PROJECT_ROOT / "web"

DEFAULT_WORKSPACE = Path("D:/Codex-Workspace")
DEFAULT_QUANT_ENGINE_PATH = DEFAULT_WORKSPACE / "AlphaPilot-Quant-Engine"

ALLOWED_STRATEGY_STATUSES = {
    "research_only",
    "local_paper_ready",
    "forward_testing",
    "dry_run_candidate",
    "disabled",
}

SAFETY_BOUNDARY = {
    "apiKeysAllowed": False,
    "tradeApiAllowed": False,
    "withdrawApiAllowed": False,
    "realAccountReadsAllowed": False,
    "realPositionReadsAllowed": False,
    "orderCreationAllowed": False,
    "exchangeDryRunAllowed": False,
    "liveTradingAllowed": False,
    "automaticTradingAllowed": False,
}


def get_quant_engine_path() -> Path:
    configured = os.environ.get("ALPHAPILOT_QUANT_ENGINE_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_QUANT_ENGINE_PATH


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
