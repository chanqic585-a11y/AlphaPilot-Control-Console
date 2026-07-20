from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer

from alphapilot_control_console.http_app import ConsoleHandler


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve the frozen TOP200 Strategy and Demo projections without starting any runtime."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8877)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), ConsoleHandler)
    print(f"TOP200 minimal UI read-only preview at http://{args.host}:{args.port}")
    print("Projection-only: no credentials, ARM, market runtime, strategy orders, Live, or Withdraw.")
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
