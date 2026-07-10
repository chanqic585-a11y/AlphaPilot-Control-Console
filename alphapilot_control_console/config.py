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
    "demo_eligible",
    "demo_active",
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
    "demoRuntimeCredentialsAllowed": True,
    "demoTradeApiAllowed": True,
    "demoOrderCreationAllowed": True,
    "automaticDemoExecutionAllowed": True,
    "demoOnly": True,
    "rawCredentialStorageAllowed": False,
}

DEFAULT_EXCHANGE_PROBE_SYMBOL = "BTC/USDT:USDT"
DEFAULT_EXCHANGE_PROBE_TIMEFRAME = "1h"
DEFAULT_EXCHANGE_PROBE_LIMIT = 2

PUBLIC_EXCHANGE_IDS = ("okx", "binance", "bybit")

DEFAULT_STRATEGY_SLOTS = [
    {
        "slotId": "active_candidate",
        "label": "Active Local Paper Candidate",
        "role": "active_candidate",
        "expectedStrategyId": "v13_5_21_local_paper_refresh_candidate",
        "status": "waiting_for_import",
    },
    {
        "slotId": "observer_alpha191",
        "label": "Alpha191 Observer",
        "role": "observer",
        "expectedStrategyId": "v13_5_23_alpha191_crypto_subset_observer",
        "status": "waiting_for_import",
    },
    {
        "slotId": "backup_1",
        "label": "Backup Strategy Slot 1",
        "role": "backup",
        "expectedStrategyId": None,
        "status": "empty",
    },
    {
        "slotId": "backup_2",
        "label": "Backup Strategy Slot 2",
        "role": "backup",
        "expectedStrategyId": None,
        "status": "empty",
    },
    {
        "slotId": "backup_3",
        "label": "Backup Strategy Slot 3",
        "role": "backup",
        "expectedStrategyId": None,
        "status": "empty",
    },
]


def get_quant_engine_path() -> Path:
    configured = os.environ.get("ALPHAPILOT_QUANT_ENGINE_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return DEFAULT_QUANT_ENGINE_PATH


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
