from __future__ import annotations

import json
import os
import time
from typing import Any, Callable

from .config import SAFETY_BOUNDARY
from .credential_runtime import load_okx_demo_credentials, runtime_credential_status
from .exchange_connectors.okx_demo_client import (
    OkxDemoClient,
    OkxDemoError,
    resolve_okx_rest_url,
)
from .exchange_connectors.public_exchange_registry import probe_public_exchanges
from .evolution_demo_service import build_evolution_demo_status
from .state_store import list_exchange_demo_events, now_iso, save_exchange_demo_event
from .usable_strategy_catalog import build_usable_strategy_catalog


CONTROL_CONSOLE_VERSION = "V13.15.2"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_15_2"
DEFAULT_OKX_SITE = "global"
MAX_DEMO_NOTIONAL_USDT = 250.0


def _env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _env_text(name: str) -> str:
    return os.environ.get(name, "").strip()


def _demo_site() -> str:
    return (_env_text("ALPHAPILOT_OKX_SITE") or DEFAULT_OKX_SITE).lower()


def _demo_base_url() -> tuple[str, str | None]:
    site = _demo_site()
    try:
        return resolve_okx_rest_url(site), None
    except ValueError:
        return resolve_okx_rest_url(DEFAULT_OKX_SITE), f"unsupported_okx_site:{site}"


def _credential_status() -> dict[str, Any]:
    return runtime_credential_status()


def _make_demo_client() -> OkxDemoClient:
    site = _demo_site()
    resolve_okx_rest_url(site)
    return OkxDemoClient(load_okx_demo_credentials(), site=site)


def _normalize_client_response(payload: dict[str, Any], *, base_url: str) -> dict[str, Any]:
    raw_code = payload.get("code") if isinstance(payload, dict) else None
    code = "" if raw_code is None else str(raw_code)
    return {
        "ok": code == "0",
        "status": 200,
        "payload": payload if isinstance(payload, dict) else {},
        "demoHeaderUsed": True,
        "baseUrl": base_url,
    }


def _failed_client_response(error: Exception, *, base_url: str) -> dict[str, Any]:
    return {
        "ok": False,
        "status": None,
        "payload": {},
        "error": f"okx_demo_request_failed:{type(error).__name__}",
        "demoHeaderUsed": True,
        "baseUrl": base_url,
    }


def _connectivity_smoke_metadata() -> dict[str, bool | str]:
    return {
        "executionPurpose": "connectivity_smoke_only",
        "strategyEvidenceEligible": False,
        "createsDemoRelease": False,
        "createsLiveCandidate": False,
    }


def _okx_request(
    method: str,
    path: str,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_url, base_url_warning = _demo_base_url()
    if base_url_warning:
        return {"ok": False, "error": base_url_warning, "code": "local_base_url_blocked"}
    try:
        payload = _make_demo_client().request(method, path, query=query, body=body)
        return _normalize_client_response(payload, base_url=base_url)
    except RuntimeError:
        return {
            "ok": False,
            "error": "okx_demo_credentials_missing",
            "code": "local_credentials_missing",
        }
    except (OkxDemoError, PermissionError, ValueError) as error:
        return {
            "ok": False,
            "error": f"okx_demo_request_blocked:{type(error).__name__}",
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
            "accountConfigStatus": None,
            "balanceStatus": None,
            "positionStatus": None,
            "accountConfigCode": None,
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
        next_action = "只读检查已通过；连接烟测仍需单独开关，正式策略自动化仍需不可变 Demo Release。"
    elif status == "blocked":
        next_action = "先补齐 OKX Demo 环境变量和 Demo 私有连接开关。"
    else:
        next_action = "请复核 OKX Demo 返回码、网络连接和模拟账户权限。"
    return {
        "status": status,
        "statusLabel": labels.get(status, status),
        "lastCheckedAt": event.get("createdAt"),
        "accountConfigStatus": event.get("accountConfigStatus"),
        "balanceStatus": event.get("balanceStatus"),
        "positionStatus": event.get("positionStatus"),
        "accountConfigCode": event.get("okxAccountConfigCode"),
        "balanceCode": event.get("okxBalanceCode"),
        "positionCode": event.get("okxPositionCode"),
        "blockers": blockers,
        "nextAction": next_action,
    }


def _build_runbook(
    private_blockers: list[str],
    order_blockers: list[str],
    strategy_automation_ready: bool,
) -> list[dict[str, Any]]:
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
            "label": "连接烟测订单",
            "status": "ready" if not order_blockers else "blocked",
            "description": "烟测必须单独开启订单开关、手动填写 sz，并输入确认口令；结果不计入策略证据。",
        },
        {
            "stepId": "formal_demo_automation",
            "label": "正式策略自动化",
            "status": "ready" if strategy_automation_ready else "locked",
            "description": "只有不可变 Demo Release 通过全部闸门后才能运行；连接烟测不能创建 Release。",
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
    evolution_demo = build_evolution_demo_status()
    evolution_summary = evolution_demo.get("summary") if isinstance(evolution_demo.get("summary"), dict) else {}
    preferred = automation_pipeline.get("preferredCandidate") if isinstance(automation_pipeline.get("preferredCandidate"), dict) else {}
    return {
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "generatedAt": now_iso(),
        "summary": {
            "stage": "exchange_demo_simulation",
            "stageLabel": "交易所 Demo 模拟",
            "exchange": "OKX Demo Trading",
            "site": _demo_site(),
            "baseUrl": base_url,
            "baseUrlWarning": base_url_warning,
            "demoPrivateEnabled": _env_enabled("ALPHAPILOT_OKX_DEMO_ENABLED"),
            "demoOrderEnabled": _env_enabled("ALPHAPILOT_OKX_DEMO_ORDER_ENABLED"),
            "demoCancelEnabled": _env_enabled("ALPHAPILOT_OKX_DEMO_CANCEL_ENABLED"),
            "credentialsConfigured": credential_status["allConfigured"],
            "canRunReadOnlyCheck": not private_blockers,
            "canSubmitDemoOrder": not order_blockers,
            "connectivitySmokeReady": not order_blockers,
            "strategyAutomationReady": bool(evolution_summary.get("ready")),
            "eligibleDemoReleaseCount": int(evolution_summary.get("eligibleReleaseCount") or 0),
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
        "runbook": _build_runbook(
            private_blockers,
            order_blockers,
            bool(evolution_summary.get("ready")),
        ),
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
        "evolutionDemo": evolution_demo,
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
        base_url, _ = _demo_base_url()
        event = save_exchange_demo_event({
            "eventType": "readonly_check",
            "status": "blocked",
            "blockers": blockers,
            "site": _demo_site(),
            "baseUrl": base_url,
            "demoHeaderUsed": False,
            "liveTrading": False,
        })
        return {
            "ok": False,
            "event": event,
            "exchangeDemoSimulation": build_exchange_demo_simulation(),
            "safetyBoundary": SAFETY_BOUNDARY,
        }

    site = _demo_site()
    base_url, _ = _demo_base_url()
    try:
        client = _make_demo_client()
    except (RuntimeError, OkxDemoError, PermissionError, ValueError) as error:
        event = save_exchange_demo_event({
            "eventType": "readonly_check",
            "status": "failed",
            "site": site,
            "baseUrl": base_url,
            "errorCode": f"okx_demo_client_unavailable:{type(error).__name__}",
            "demoHeaderUsed": True,
            "liveTrading": False,
        })
        return {
            "ok": False,
            "event": event,
            "exchangeDemoSimulation": build_exchange_demo_simulation(),
            "safetyBoundary": SAFETY_BOUNDARY,
        }

    def run_check(callback: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        try:
            return _normalize_client_response(callback(), base_url=base_url)
        except (OkxDemoError, PermissionError, ValueError) as error:
            return _failed_client_response(error, base_url=base_url)

    account_config = run_check(client.get_account_config)
    balance = run_check(lambda: client.get_balance("USDT"))
    positions = run_check(lambda: client.get_positions(instrumentType="SWAP"))
    ok = bool(account_config.get("ok") and balance.get("ok") and positions.get("ok"))
    event = save_exchange_demo_event({
        "eventType": "readonly_check",
        "status": "passed" if ok else "failed",
        "site": site,
        "baseUrl": base_url,
        "accountConfigStatus": account_config.get("status"),
        "balanceStatus": balance.get("status"),
        "positionStatus": positions.get("status"),
        "okxAccountConfigCode": (account_config.get("payload") or {}).get("code") if isinstance(account_config.get("payload"), dict) else None,
        "okxBalanceCode": (balance.get("payload") or {}).get("code") if isinstance(balance.get("payload"), dict) else None,
        "okxPositionCode": (positions.get("payload") or {}).get("code") if isinstance(positions.get("payload"), dict) else None,
        "demoHeaderUsed": True,
        "liveTrading": False,
    })
    return {
        "ok": ok,
        "event": event,
        "accountConfigPreview": _summarize_okx_payload(account_config),
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
            **_connectivity_smoke_metadata(),
        })
        return {
            "ok": False,
            "event": event,
            "rejectionReasons": rejection_reasons,
            **_connectivity_smoke_metadata(),
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
        **_connectivity_smoke_metadata(),
    })
    return {
        "ok": ok,
        "event": event,
        **_connectivity_smoke_metadata(),
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
