"""Console-only CLI for OKX Demo credential vault enrollment."""

from __future__ import annotations

import argparse
import json

from .demo_credential_enrollment import enroll_demo_credentials


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("enroll",))
    args = parser.parse_args(argv)
    if args.action != "enroll":
        return 2
    result = enroll_demo_credentials()
    print(
        json.dumps(
            {
                "ok": bool(result.get("ok")),
                "status": str(result.get("status") or "rejected"),
                "category": str(result.get("category") or "validated"),
            },
            separators=(",", ":"),
        )
    )
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
