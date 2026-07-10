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
from .exchange_connectors.public_exchange_registry import probe_public_exchanges
from .state_store import list_exchange_demo_events, now_iso, save_exchange_demo_event
from .usable_strategy_catalog import build_usable_strategy_catalog
from .evolution_demo_service import build_evolution_demo_status


CONTROL_CONSOLE_VERSION = "V13.10.0"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_10_0"
DEFAULT_DEMO_BASE_URL = "https://openapi.okx.com"
ALLOWED_DEMO_BASE_URLS = {"https://openapi.okx.com"}
MAX_DEMO_NOTIONAL_USDT = 250.0
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
    return {
        "taskId": "manual_okx_demo_observation",
        "readableName": "手动 OKX Demo 观察票据",
    }


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


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _okx_inst_id_from_pair(pair: str) -> str:
    value = (pair or "BTC/USDT:USDT").upper().replace(":USDT", "").strip()
    if "/" in value:
        base, quote = value.split("/", 1)
    elif value.endswith("USDT"):
        base, quote = value[:-4], "USDT"
    else:
        base, quote = value, "USDT"
    return f"{base}-{quote}-SWAP"


def _demo_side_from_direction(direction: str) -> str:
    return "sell" if str(direction or "").lower() == "short" else "buy"


def _build_strategy_candidates(limit: int = 12) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    catalog = build_usable_strategy_catalog()
    strategies = catalog.get("strategies") if isinstance(catalog.get("strategies"), list) else []
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for strategy in sorted(strategies, key=lambda item: _safe_float(item.get("score")), reverse=True):
        pairs = strategy.get("selectedPairs") if isinstance(strategy.get("selectedPairs"), list) else []
        if not pairs:
            pairs = ["BTC/USDT:USDT"]
        direction = str(strategy.get("direction") or "long")
        for pair in pairs[:3]:
            inst_id = _okx_inst_id_from_pair(str(pair))
            key = (str(strategy.get("strategyId") or strategy.get("taskId") or ""), inst_id)
            if key in seen:
                continue
            seen.add(key)
            metrics = strategy.get("testMetrics") if isinstance(strategy.get("testMetrics"), dict) else strategy.get("metrics") or {}
            rows.append({
                "candidateId": f"demo::{strategy.get('strategyId') or strategy.get('taskId') or len(rows)}::{inst_id}",
                "strategyId": strategy.get("strategyId") or strategy.get("taskId"),
                "strategyName": strategy.get("name") or strategy.get("shortName") or "本地候选策略",
                "family": strategy.get("family") or "--",
                "frequencyLabel": strategy.get("frequencyLabel") or strategy.get("timeframe") or "--",
                "symbol": str(pair),
                "instId": inst_id,
                "side": _demo_side_from_direction(direction),
                "direction": direction,
                "timeframe": strategy.get("timeframe") or "--",
                "score": _safe_float(strategy.get("score")),
                "targetR": _safe_float(strategy.get("targetR"), 2.0),
                "winRatePct": _safe_float(metrics.get("winRatePct")),
                "profitFactor": _safe_float(metrics.get("profitFactor")),
                "tradeCount": _safe_int(metrics.get("tradeCount")),
                "marketDataStatus": "not_scanned",
                "screeningStatus": "strategy_loaded",
                "reason": "来自本地可用策略库；需公共行情扫描后再考虑 Demo 票据。",
                "manualOrderRequired": True,
            })
            if len(rows) >= limit:
                break
        if len(rows) >= limit:
            break
    summary = catalog.get("summary") if isinstance(catalog.get("summary"), dict) else {}
    return rows, {
        "strategyCount": _safe_int(summary.get("totalUsableStrategies"), len(strategies)),
        "sandboxReadyCount": _safe_int(summary.get("sandboxReadyCount")),
        "candidateCount": len(rows),
        "catalogSource": summary.get("sourceReports") or [],
    }


def _build_automation_pipeline(scan_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    candidates, catalog_summary = _build_strategy_candidates()
    market_probe_count = 0
    ok_market_count = 0
    probe_by_inst: dict[str, dict[str, Any]] = {}
    if isinstance(scan_payload, dict):
        for item in scan_payload.get("scans", []) if isinstance(scan_payload.get("scans"), list) else []:
            inst_id = item.get("instId")
            probe = item.get("publicProbe") if isinstance(item.get("publicProbe"), dict) else {}
            results = probe.get("results") if isinstance(probe.get("results"), list) else []
            okx = next((result for result in results if result.get("exchange") == "okx"), None)
            if inst_id:
                probe_by_inst[str(inst_id)] = okx or {}
            market_probe_count += 1
            if okx and okx.get("ok"):
                ok_market_count += 1
    for candidate in candidates:
        probe = probe_by_inst.get(candidate["instId"])
        if probe:
            candidate["marketDataStatus"] = "public_ok" if probe.get("ok") else "public_gap"
            candidate["screeningStatus"] = "market_ready" if probe.get("ok") else "market_gap"
            candidate["marketLatencyMs"] = probe.get("latencyMs")
            candidate["missingPublicFields"] = probe.get("missingPublicFields") or []
            candidate["reason"] = (
                "本地策略通过候选筛选，OKX 公共行情可用；仍需人工确认 Demo 票据。"
                if probe.get("ok")
                else "本地策略通过候选筛选，但公共行情字段不完整，暂不填入票据。"
            )
    preferred = next((item for item in candidates if item.get("screeningStatus") == "market_ready"), None) or (candidates[0] if candidates else None)
    return {
        "status": "scanned" if scan_payload else "strategy_loaded",
        "summary": {
            **catalog_summary,
            "publicProbeCount": market_probe_count,
            "publicOkCount": ok_market_count,
            "preferredCandidateId": preferred.get("candidateId") if preferred else None,
            "preferredInstId": preferred.get("instId") if preferred else None,
            "manualOrderRequired": True,
            "autoOrderAllowed": False,
            "nextAction": (
                "公共行情扫描完成；可以把首选候选填入 Demo 票据，但仍需人工确认和订单闸门。"
                if scan_payload else "先点击扫描 Demo 候选，使用 OKX 公共行情确认候选币种是否可观察。"
            ),
        },
        "candidates": candidates,
        "preferredCandidate": preferred,
        "flow": [
            {"stepId": "load_strategies", "label": "加载可用策略", "status": "ready", "count": catalog_summary.get("strategyCount")},
            {"stepId": "public_market_scan", "label": "接入公共实时行情", "status": "ready" if scan_payload else "waiting"},
            {"stepId": "auto_screen_symbols", "label": "自动筛选候选币种", "status": "ready" if candidates else "blocked", "count": len(candidates)},
            {"stepId": "manual_demo_ticket", "label": "填入 Demo 票据", "status": "manual_required"},
            {"stepId": "gated_order", "label": "订单闸门", "status": "blocked", "description": "仍需 Demo 开关、订单开关、sz 和人工确认。"},
        ],
    }


def _latest_readonly_event(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    for event in events:
        if event.get("eventType") == "readonly_check":
            return event
    return None


def _build_readonly_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    event = _latest_readonly_event(events)
    if not event:
        return {
            "status": "not_run",
            "statusLabel": "尚未检查",
            "lastCheckedAt": None,
            "balanceStatus": None,
            "positionStatus": None,
            "balanceCode": None,
            "positionCode": None,
            "blockers": [],
            "nextAction": "先用 OKX Demo 启动脚本启动控制台，再点击只读检查。",
        }
    blockers = event.get("blockers") if isinstance(event.get("blockers"), list) else []
    status = str(event.get("status") or "unknown")
    labels = {
        "passed": "只读检查通过",
        "failed": "只读检查失败",
        "blocked": "只读检查被阻塞",
        "unknown": "状态未知",
    }
    if status == "passed":
        next_action = "只读检查已通过；若要做 Demo 订单演练，仍需单独开启订单开关并人工确认。"
    elif status == "blocked":
        next_action = "先补齐 OKX Demo 环境变量和 Demo 私有连接开关。"
    else:
        next_action = "请复核 OKX Demo 返回码、网络连接和模拟账户权限。"
    return {
        "status": status,
        "statusLabel": labels.get(status, status),
        "lastCheckedAt": event.get("createdAt"),
        "balanceStatus": event.get("balanceStatus"),
        "positionStatus": event.get("positionStatus"),
        "balanceCode": event.get("okxBalanceCode"),
        "positionCode": event.get("okxPositionCode"),
        "blockers": blockers,
        "nextAction": next_action,
    }


def _build_runbook(private_blockers: list[str], order_blockers: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "stepId": "create_okx_demo_key",
            "label": "准备 OKX Demo API Key",
            "status": "manual_required",
            "description": "只使用 OKX Demo Trading 模拟账户密钥，不使用实盘密钥，不勾选提现权限。",
        },
        {
            "stepId": "start_with_env_launcher",
            "label": "用启动器注入临时环境变量",
            "status": "ready" if "okx_demo_credentials_missing" not in private_blockers else "waiting_credentials",
            "description": "运行 scripts/start_okx_demo_console.ps1；脚本只把密钥放在当前进程环境变量里，不写入文件。",
        },
        {
            "stepId": "run_readonly_check",
            "label": "只读检查",
            "status": "ready" if not private_blockers else "blocked",
            "description": "点击 OKX Demo 页面里的只读检查，验证模拟余额和模拟持仓接口。",
        },
        {
            "stepId": "manual_demo_order",
            "label": "人工 Demo 订单演练",
            "status": "ready" if not order_blockers else "blocked",
            "description": "订单演练必须单独开启订单开关、手动填写 sz，并输入 OKX_DEMO_ORDER_APPROVED。",
        },
        {
            "stepId": "future_live_gate",
            "label": "未来实盘闸门",
            "status": "disabled",
            "description": "实盘、自动交易、Withdraw API 仍关闭，未来必须单独设计和验收。",
        },
    ]


def build_exchange_demo_simulation() -> dict[str, Any]:
    credential_status = _credential_status()
    strategy = _pick_default_strategy()
    private_blockers = _private_blockers()
    order_blockers = _private_blockers(order=True)
    recent_events = list_exchange_demo_events(limit=20)
    base_url, base_url_warning = _demo_base_url()
    readonly_summary = _build_readonly_summary(recent_events)
    automation_pipeline = _build_automation_pipeline()
    preferred = automation_pipeline.get("preferredCandidate") if isinstance(automation_pipeline.get("preferredCandidate"), dict) else {}
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
        "readonlySummary": readonly_summary,
        "privateBlockers": private_blockers,
        "orderBlockers": order_blockers,
        "runbook": _build_runbook(private_blockers, order_blockers),
        "launcher": {
            "script": "scripts/start_okx_demo_console.ps1",
            "readOnlyCommand": "powershell -ExecutionPolicy Bypass -File scripts\\start_okx_demo_console.ps1",
            "orderCommand": "powershell -ExecutionPolicy Bypass -File scripts\\start_okx_demo_console.ps1 -EnableOrder",
            "mobileCommand": "powershell -ExecutionPolicy Bypass -File scripts\\start_okx_demo_console.ps1 -Mobile",
            "storesRawKeys": False,
            "envOnly": True,
        },
        "defaultTicket": {
            "strategyId": preferred.get("strategyId") or strategy.get("taskId") or strategy.get("strategyId") or "demo_strategy_candidate",
            "readableName": preferred.get("strategyName") or strategy.get("readableName") or strategy.get("plainName") or "本地候选策略",
            "instId": preferred.get("instId") or "BTC-USDT-SWAP",
            "side": preferred.get("side") or "buy",
            "tdMode": "isolated",
            "ordType": "market",
            "size": "",
            "notionalUsdt": MAX_DEMO_NOTIONAL_USDT,
        },
        "automationPipeline": automation_pipeline,
        "evolutionDemo": build_evolution_demo_status(),
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


def scan_exchange_demo_candidates(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    raw_limit = _safe_int(payload.get("limit"), 5)
    limit = max(1, min(raw_limit, 8))
    candidates, _ = _build_strategy_candidates(limit=limit)
    scans: list[dict[str, Any]] = []
    for candidate in candidates:
        probe = probe_public_exchanges(
            exchanges=["okx"],
            symbol=str(candidate.get("symbol") or "BTC/USDT:USDT"),
            timeframe=str(candidate.get("timeframe") or "1h"),
            limit=2,
        )
        scans.append({
            "candidateId": candidate.get("candidateId"),
            "strategyId": candidate.get("strategyId"),
            "strategyName": candidate.get("strategyName"),
            "symbol": candidate.get("symbol"),
            "instId": candidate.get("instId"),
            "side": candidate.get("side"),
            "publicProbe": probe,
        })
    scan_payload = {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "publicOnly": True,
        "usesApiKey": False,
        "createsOrder": False,
        "scans": scans,
    }
    pipeline = _build_automation_pipeline(scan_payload)
    preferred = pipeline.get("preferredCandidate") if isinstance(pipeline.get("preferredCandidate"), dict) else {}
    event = save_exchange_demo_event({
        "eventType": "demo_candidate_scan",
        "status": "completed",
        "instId": preferred.get("instId"),
        "side": preferred.get("side"),
        "notionalUsdt": MAX_DEMO_NOTIONAL_USDT,
        "candidateCount": len(candidates),
        "publicProbeCount": pipeline.get("summary", {}).get("publicProbeCount"),
        "publicOkCount": pipeline.get("summary", {}).get("publicOkCount"),
        "liveTrading": False,
        "apiKeyUsed": False,
        "ordersCreated": False,
    })
    return {
        "ok": True,
        "event": event,
        "automationPipeline": pipeline,
        "exchangeDemoSimulation": {
            **build_exchange_demo_simulation(),
            "automationPipeline": pipeline,
        },
        "safetyBoundary": SAFETY_BOUNDARY,
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
