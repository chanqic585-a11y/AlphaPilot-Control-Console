from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alphapilot_control_console.live_environment_contract import (
    LIVE_ENVIRONMENT_CONTRACT_PATH,
    LIVE_PRIVATE_READ_AUDIT_PATH,
    run_live_private_read_audit,
    write_live_environment_contract,
)


def main() -> int:
    contract = write_live_environment_contract(LIVE_ENVIRONMENT_CONTRACT_PATH)
    audit = run_live_private_read_audit(output_path=LIVE_PRIVATE_READ_AUDIT_PATH)
    print(json.dumps({"contract": contract, "privateReadAudit": audit}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
