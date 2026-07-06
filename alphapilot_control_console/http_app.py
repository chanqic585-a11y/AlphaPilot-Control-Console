from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .config import ALLOWED_STRATEGY_STATUSES, SAFETY_BOUNDARY, WEB_DIR
from .exchange_connectors.public_exchange_registry import list_public_exchange_sources, probe_public_exchanges
from .importer import build_mobile_status, import_now, scan_quant_engine
from .mobile_connection import build_mobile_connection_info
from .strategy_slots import list_strategy_slots
from .state_store import list_audit, update_strategy_status


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _safe_int(value: object, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


class ConsoleHandler(BaseHTTPRequestHandler):
    server_version = "AlphaPilotControlConsole/13.6.3"

    def _send_json(self, payload: object, status: int = 200) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"error": "not_found"}, 404)
            return
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            self._send_json({
                "ok": True,
                "version": "V13.6.3",
                "source": "alphapilot_control_console_v13_6_3",
                "safetyBoundary": SAFETY_BOUNDARY,
            })
            return
        if path == "/api/strategies":
            self._send_json({"strategies": scan_quant_engine()["strategies"]})
            return
        if path == "/api/reports":
            self._send_json({"reports": scan_quant_engine()["reports"]})
            return
        if path == "/api/mobile/status":
            self._send_json(build_mobile_status(scan_quant_engine()))
            return
        if path == "/api/mobile/connection-info":
            self._send_json(build_mobile_connection_info(str(self.server.server_address[0]), int(self.server.server_address[1])))
            return
        if path == "/api/audit":
            self._send_json({"events": list_audit()})
            return
        if path == "/api/exchanges":
            self._send_json(list_public_exchange_sources())
            return
        if path == "/api/strategy-slots":
            self._send_json(list_strategy_slots())
            return
        if path in {"/", "/index.html"}:
            self._send_static(WEB_DIR / "index.html")
            return
        static_path = (WEB_DIR / path.lstrip("/")).resolve()
        if WEB_DIR.resolve() in static_path.parents:
            self._send_static(static_path)
            return
        self._send_json({"error": "not_found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/import":
            self._send_json(import_now())
            return
        if parsed.path == "/api/strategy-status":
            payload = self._read_body_json()
            strategy_id = str(payload.get("strategyId") or "").strip()
            status = str(payload.get("status") or "").strip()
            note = str(payload.get("note") or "").strip()
            if not strategy_id:
                self._send_json({"error": "strategyId_required"}, 400)
                return
            if status not in ALLOWED_STRATEGY_STATUSES:
                self._send_json({"error": "unsupported_status", "allowed": sorted(ALLOWED_STRATEGY_STATUSES)}, 400)
                return
            updated = update_strategy_status(strategy_id, status, note)
            self._send_json({"updated": updated, "safetyBoundary": SAFETY_BOUNDARY})
            return
        if parsed.path == "/api/exchanges/probe-public":
            payload = self._read_body_json()
            exchanges = payload.get("exchanges")
            if not isinstance(exchanges, list):
                exchanges = None
            symbol = str(payload.get("symbol") or "").strip() or "BTC/USDT:USDT"
            timeframe = str(payload.get("timeframe") or "").strip() or "1h"
            limit = _safe_int(payload.get("limit") or 2, 2)
            self._send_json(probe_public_exchanges(exchanges=exchanges, symbol=symbol, timeframe=timeframe, limit=limit))
            return
        self._send_json({"error": "not_found"}, 404)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def run_server(host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), ConsoleHandler)
    print(f"AlphaPilot Control Console running at http://{host}:{port}")
    print("Research control only. No Trade API, no API keys, no orders, no auto trading.")
    server.serve_forever()


def smoke() -> None:
    payload = scan_quant_engine()
    assert payload["safetyBoundary"]["tradeApiAllowed"] is False
    assert payload["safetyBoundary"]["orderCreationAllowed"] is False
    assert isinstance(payload["strategies"], list)
    print(json.dumps({
        "ok": True,
        "strategyCount": len(payload["strategies"]),
        "reportCount": len(payload["reports"]),
        "mobileBridgeReady": True,
    }, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.smoke:
        smoke()
        return
    run_server(args.host, args.port)


if __name__ == "__main__":
    main()
