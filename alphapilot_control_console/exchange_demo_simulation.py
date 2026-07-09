from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import SAFETY_BOUNDARY
from .state_store import list_exchange_demo_events, now_iso, save_exchange_demo_event
from .strategy_asset_playbook import build_strategy_asset_playbook


CONTROL_CONSOLE_VERSION = "V13.9.5"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_9_5"
DEFAULT_DEMO_BASE_URL = "https://www.okx.com"
ALLOWED_DEMO_BASE_URLS = {"https://www.okx.com", "https://eea.okx.com"}
MAX_DEMO_NOTIONAL_USDT = 1000.0
READ_TIMEOUT_SECONDS = 12


def _env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_text(name: str) -> str:
    return os.environ.get(name, "").strip()


def _demo_base_url() -> tuple[str, str | None]:
    configured = _env_text("ALPHAPILOT_OKX_DEMO_BASE_URL") or DEFAULT_DEMO_BASE_URL
    normalized = configured.rstrip("/")
    if normalized not in ALLOWED_DEMO_BASE_URLS:
        return DEFAULT_DEMO_BASE_URL, f"unsupported_demo_base_url:{normalized}"
    return normalized, None


def _credential_status() -> dict[str, Any]:
    key = _env_text("ALPHAPILOT_OKX_DEMO_API_KEY")
    secret = _env_text("ALPHAPILOT_OKX_DEMO_SECRET_KEY")
    passphrase = _env_text("ALPHAPILOT_OKX_DEMO_PASSPHRASE")
    return {
        "apiKeyConfigured": bool(key),
        "secretKeyConfigured": bool(secret),
        "passphraseConfigured": bool(passphrase),
        "allConfigured": bool(key and secret and passphrase),
    }


def _credential_values() -> dict[str, str]:
    return {
        "api_key": _env_text("ALPHAPILOT_OKX_DEMO_API_KEY"),
        "secret_key": _env_text("ALPHAPILOT_OKX_DEMO_SECRET_KEY"),
        "passphrase": _env_text("ALPHAPILOT_OKX_DEMO_PASSPHRASE"),
    }


def _iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _sign(secret_key: str, timestamp: str, method: str, request_path: str, body: str) -> str:
    message = f"{timestamp}{method.upper()}{request_path}{body}"
    digest = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _compact_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _okx_request(method: str, path: str, query: dict[str, Any] | None = None, body: dict[str, Any] | None = None) -> dict[str, Any]:
    base_url, base_url_warning = _demo_base_url()
    if base_url_warning:
        return {"ok": False, "error": base_url_warning, "code": "local_base_url_blocked"}

    credentials = _credential_values()
    if not all(credentials.values()):
        return {"ok": False, "error": "okx_demo_credentials_missing", "code": "local_credentials_missing"}

    query_string = ""
    if query:
        query_string = "?" + urlencode({key: value for key, value in query.items() if value is not None})
    request_path = f"{path}{query_string}"
    body_text = _compact_json(body or {}) if body else ""
    timestamp = _iso_timestamp()
    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": credentials["api_key"],
        "OK-ACCESS-SIGN": _sign(credentials["secret_key"], timestamp, method, request_path, body_text),
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": credentials["passphrase"],
        "x-simulated-trading": "1",
    }
    request = Request(
        f"{base_url}{request_path}",
        data=body_text.encode("utf-8") if body_text else None,
        headers=headers,
        method=method.upper(),
    )
    try:
        with urlopen(request, timeout=READ_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            return {
                "ok": True,
                "status": response.status,
                "payload": payload,
                "demoHeaderUsed": True,
                "baseUrl": base_url,
            }
    except HTTPError as error:
        raw_error = error.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw_error)
        except json.JSONDecodeError:
            payload = {"message": raw_error[:500]}
        return {
            "ok": False,
            "status": error.code,
            "payload": payload,
            "error": "okx_demo_http_error",
            "demoHeaderUsed": True,
            "baseUrl": base_url,
        }
    except (URLError, TimeoutError, OSError) as error:
        return {
            "ok": False,
            "error": f"okx_demo_network_error:{type(error).__name__}",
            "message": str(error),
            "demoHeaderUsed": True,
            "baseUrl": base_url,
        }


def _pick_default_strategy() -> dict[str, Any]:
    playbook = build_strategy_asset_playbook()
    rows = playbook.get("strategies") if isinstance(playbook.get("strategies"), list) else []
    for row in rows:
        if isinstance(row, dict):
            return row
    return {}


def _private_blockers(order: bool = False) -> list[str]:
    blockers: list[str] = []
    if not _env_enabled("ALPHAPILOT_OKX_DEMO_ENABLED"):
        blockers.append("okx_demo_private_connection_disabled")
    credential_status = _credential_status()
    if not credential_status["allConfigured"]:
        blockers.append("okx_demo_credentials_missing")
    if order and not _env_enabled("ALPHAPILOT_OKX_DEMO_ORDER_ENABLED"):
        blockers.append("okx_demo_order_gate_disabled")
    if SAFETY_BOUNDARY.get("withdrawApiAllowed") is not False:
        blockers.append("withdraw_boundary_unexpected")
    if SAFETY_BOUNDARY.get("liveTradingAllowed") is not False:
        blockers.append("live_trading_boundary_unexpected")
    _, base_url_warning = _demo_base_url()
    if base_url_warning:
        blockers.append(base_url_warning)
    return blockers


def _sanitize_order_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    inst_id = str(payload.get("instId") or "BTC-USDT-SWAP").strip().upper()
    side = str(payload.get("side") or "buy").strip().lower()
    td_mode = str(payload.get("tdMode") or "isolated").strip().lower()
    order_type = str(payload.get("ordType") or "market").strip().lower()
    size = str(payload.get("size") or payload.get("sz") or "").strip()
    px = str(payload.get("px") or payload.get("price") or "").strip()
    manual_confirm = str(payload.get("manualConfirm") or "").strip()
    notional = _safe_float(payload.get("notionalUsdt"), MAX_DEMO_NOTIONAL_USDT)
    return {
        "instId": inst_id,
        "side": side if side in {"buy", "sell"} else "buy",
        "tdMode": td_mode if td_mode in {"isolated", "cross", "cash"} else "isolated",
        "ordType": order_type if order_type in {"market", "limit"} else "market",
        "size": size,
        "px": px,
        "manualConfirm": manual_confirm,
        "notionalUsdt": notional,
    }


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def build_exchange_demo_simulation() -> dict[str, Any]:
    credential_status = _credential_status()
    strategy = _pick_default_strategy()
    private_blockers = _private_blockers()
    order_blockers = _private_blockers(order=True)
    recent_events = list_exchange_demo_events(limit=20)
    base_url, base_url_warning = _demo_base_url()
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            "stage": "exchange_demo_simulation",
            "stageLabel": "交易所 Demo 模拟",
            "exchange": "OKX Demo Trading",
            "baseUrl": base_url,
            "baseUrlWarning": base_url_warning,
            "demoPrivateEnabled": _env_enabled("ALPHAPILOT_OKX_DEMO_ENABLED"),
            "demoOrderEnabled": _env_enabled("ALPHAPILOT_OKX_DEMO_ORDER_ENABLED"),
            "demoCancelEnabled": _env_enabled("ALPHAPILOT_OKX_DEMO_CANCEL_ENABLED"),
            "credentialsConfigured": credential_status["allConfigured"],
            "canRunReadOnlyCheck": not private_blockers,
            "canSubmitDemoOrder": not order_blockers,
            "maxNotionalUsdt": MAX_DEMO_NOTIONAL_USDT,
            "recentEventCount": len(recent_events),
            "nextAction": (
                "先配置 OKX Demo 环境变量并做只读检查；订单能力必须单独开启并人工确认。"
                if private_blockers else "可以先做 OKX Demo 只读检查；订单仍需单独确认。"
            ),
        },
        "modeCards": [
            {
                "modeId": "local_sandbox",
                "label": "本地沙盒",
                "status": "available",
                "description": "用本地虚拟资金持续生成可复盘样本，不连接交易所。",
            },
            {
                "modeId": "local_simulation",
                "label": "本地模拟",
                "status": "available",
                "description": "保存本地模拟票据和虚拟观察，不产生交易所订单。",
            },
            {
                "modeId": "exchange_demo",
                "label": "OKX Demo",
                "status": "locked" if private_blockers else "readonly_ready",
                "description": "连接 OKX Demo Trading。需要模拟账户 API Key 和 x-simulated-trading: 1。",
            },
            {
                "modeId": "live_trading",
                "label": "实盘",
                "status": "disabled",
                "description": "当前版本实盘交易、自动下单和提现权限全部关闭。",
            },
        ],
        "credentialStatus": credential_status,
        "privateBlockers": private_blockers,
        "orderBlockers": order_blockers,
        "defaultTicket": {
            "strategyId": strategy.get("taskId") or strategy.get("strategyId") or "demo_strategy_candidate",
            "readableName": strategy.get("readableName") or strategy.get("plainName") or "本地候选策略",
            "instId": "BTC-USDT-SWAP",
            "side": "buy",
            "tdMode": "isolated",
            "ordType": "market",
            "size": "",
            "notionalUsdt": MAX_DEMO_NOTIONAL_USDT,
        },
        "recentEvents": recent_events,
        "safetyBoundary": {
            **SAFETY_BOUNDARY,
            "okxDemoHeaderRequired": True,
            "okxDemoRawKeyStorageAllowed": False,
            "okxDemoEnvOnlyCredentials": True,
            "okxDemoManualOrderConfirmRequired": True,
            "maxDemoOrderNotionalUsdt": MAX_DEMO_NOTIONAL_USDT,
        },
        "safetyNote": "OKX Demo is separated from local sandbox and live trading. Raw API keys are not stored in the browser or SQLite. Withdraw and live trading remain disabled.",
    }


def run_exchange_demo_readonly_check() -> dict[str, Any]:
    blockers = _private_blockers()
    if blockers:
        event = save_exchange_demo_event({
            "eventType": "readonly_check",
            "status": "blocked",
            "blockers": blockers,
            "liveTrading": False,
        })
        return {
            "ok": False,
            "event": event,
            "exchangeDemoSimulation": build_exchange_demo_simulation(),
            "safetyBoundary": SAFETY_BOUNDARY,
        }

    balance = _okx_request("GET", "/api/v5/account/balance")
    positions = _okx_request("GET", "/api/v5/account/positions", {"instType": "SWAP"})
    ok = bool(balance.get("ok") and positions.get("ok"))
    event = save_exchange_demo_event({
        "eventType": "readonly_check",
        "status": "passed" if ok else "failed",
        "balanceStatus": balance.get("status"),
        "positionStatus": positions.get("status"),
        "okxBalanceCode": (balance.get("payload") or {}).get("code") if isinstance(balance.get("payload"), dict) else None,
        "okxPositionCode": (positions.get("payload") or {}).get("code") if isinstance(positions.get("payload"), dict) else None,
        "demoHeaderUsed": True,
        "liveTrading": False,
    })
    return {
        "ok": ok,
        "event": event,
        "balancePreview": _summarize_okx_payload(balance),
        "positionsPreview": _summarize_okx_payload(positions),
        "exchangeDemoSimulation": build_exchange_demo_simulation(),
        "safetyBoundary": SAFETY_BOUNDARY,
    }


def submit_exchange_demo_order(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    ticket = _sanitize_order_payload(payload)
    blockers = _private_blockers(order=True)
    rejection_reasons = list(blockers)
    if ticket["manualConfirm"] != "OKX_DEMO_ORDER_APPROVED":
        rejection_reasons.append("manual_confirm_required")
    if ticket["notionalUsdt"] <= 0 or ticket["notionalUsdt"] > MAX_DEMO_NOTIONAL_USDT:
        rejection_reasons.append("notional_out_of_demo_cap")
    if not ticket["size"]:
        rejection_reasons.append("explicit_size_required_for_okx_demo_order")
    if ticket["ordType"] == "limit" and not ticket["px"]:
        rejection_reasons.append("limit_price_required")
    if rejection_reasons:
        event = save_exchange_demo_event({
            "eventType": "demo_order",
            "status": "blocked",
            "instId": ticket["instId"],
            "side": ticket["side"],
            "notionalUsdt": ticket["notionalUsdt"],
            "blockers": rejection_reasons,
            "liveTrading": False,
        })
        return {
            "ok": False,
            "event": event,
            "rejectionReasons": rejection_reasons,
            "exchangeDemoSimulation": build_exchange_demo_simulation(),
            "safetyBoundary": SAFETY_BOUNDARY,
        }

    cl_ord_id = f"APD{int(time.time() * 1000)}"
    order_body = {
        "instId": ticket["instId"],
        "tdMode": ticket["tdMode"],
        "side": ticket["side"],
        "ordType": ticket["ordType"],
        "sz": ticket["size"],
        "clOrdId": cl_ord_id[-32:],
    }
    if ticket["ordType"] == "limit":
        order_body["px"] = ticket["px"]
    response = _okx_request("POST", "/api/v5/trade/order", body=order_body)
    ok = bool(response.get("ok") and isinstance(response.get("payload"), dict) and response["payload"].get("code") == "0")
    event = save_exchange_demo_event({
        "eventType": "demo_order",
        "status": "submitted" if ok else "failed",
        "instId": ticket["instId"],
        "side": ticket["side"],
        "tdMode": ticket["tdMode"],
        "ordType": ticket["ordType"],
        "size": ticket["size"],
        "price": ticket["px"] or None,
        "notionalUsdt": ticket["notionalUsdt"],
        "clientOrderId": order_body["clOrdId"],
        "okxCode": (response.get("payload") or {}).get("code") if isinstance(response.get("payload"), dict) else None,
        "okxMessage": (response.get("payload") or {}).get("msg") if isinstance(response.get("payload"), dict) else None,
        "demoHeaderUsed": True,
        "liveTrading": False,
    })
    return {
        "ok": ok,
        "event": event,
        "okxResponsePreview": _summarize_okx_payload(response),
        "exchangeDemoSimulation": build_exchange_demo_simulation(),
        "safetyBoundary": SAFETY_BOUNDARY,
    }


def run_exchange_demo_emergency_drill(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    inst_id = str(payload.get("instId") or "BTC-USDT-SWAP").strip().upper()
    ord_id = str(payload.get("ordId") or "").strip()
    manual_confirm = str(payload.get("manualConfirm") or "").strip()
    blockers = _private_blockers()
    if not _env_enabled("ALPHAPILOT_OKX_DEMO_CANCEL_ENABLED"):
        blockers.append("okx_demo_cancel_gate_disabled")
    if manual_confirm != "OKX_DEMO_EMERGENCY_APPROVED":
        blockers.append("manual_emergency_confirm_required")
    if not ord_id:
        blockers.append("ord_id_required_for_real_demo_cancel")

    if blockers:
        event = save_exchange_demo_event({
            "eventType": "emergency_stop_drill",
            "status": "local_drill_saved",
            "instId": inst_id,
            "ordId": ord_id or None,
            "blockers": blockers,
            "note": "Local emergency drill recorded. No exchange cancel request was sent.",
            "liveTrading": False,
        })
        return {
            "ok": True,
            "event": event,
            "exchangeCancelSent": False,
            "exchangeDemoSimulation": build_exchange_demo_simulation(),
            "safetyBoundary": SAFETY_BOUNDARY,
        }

    response = _okx_request("POST", "/api/v5/trade/cancel-order", body={"instId": inst_id, "ordId": ord_id})
    ok = bool(response.get("ok") and isinstance(response.get("payload"), dict) and response["payload"].get("code") == "0")
    event = save_exchange_demo_event({
        "eventType": "emergency_cancel",
        "status": "submitted" if ok else "failed",
        "instId": inst_id,
        "ordId": ord_id,
        "okxCode": (response.get("payload") or {}).get("code") if isinstance(response.get("payload"), dict) else None,
        "demoHeaderUsed": True,
        "liveTrading": False,
    })
    return {
        "ok": ok,
        "event": event,
        "okxResponsePreview": _summarize_okx_payload(response),
        "exchangeDemoSimulation": build_exchange_demo_simulation(),
        "safetyBoundary": SAFETY_BOUNDARY,
    }


def _summarize_okx_payload(response: dict[str, Any]) -> dict[str, Any]:
    payload = response.get("payload") if isinstance(response.get("payload"), dict) else {}
    data = payload.get("data") if isinstance(payload.get("data"), list) else []
    return {
        "ok": bool(response.get("ok")),
        "status": response.get("status"),
        "code": payload.get("code"),
        "message": payload.get("msg") or response.get("message") or response.get("error"),
        "dataCount": len(data),
        "firstItemKeys": sorted(list(data[0].keys()))[:12] if data and isinstance(data[0], dict) else [],
        "demoHeaderUsed": bool(response.get("demoHeaderUsed")),
    }


if __name__ == "__main__":
    print(json.dumps(build_exchange_demo_simulation(), ensure_ascii=False, indent=2))
