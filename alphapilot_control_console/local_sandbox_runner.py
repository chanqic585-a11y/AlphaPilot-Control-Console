from __future__ import annotations

import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DEFAULT_QUANT_ENGINE_PATH, SAFETY_BOUNDARY, get_quant_engine_path
from .sample_path_instrumentation import build_estimated_path_fields
from .state_store import add_paper_observation_log, list_paper_observation_logs, now_iso, save_local_sandbox_run
from .usable_strategy_catalog import (
    USABLE_STRATEGY_CATALOG_REPORT,
    build_usable_sandbox_task_pack,
)


CONTROL_CONSOLE_VERSION = "V13.8"
CONTROL_CONSOLE_SOURCE = "alphapilot_control_console_v13_8"
SAMPLE_KEY_SCHEMA_VERSION = "V13.7.34"
VIRTUAL_CAPITAL_PER_STRATEGY = 1000.0
RISK_UNIT_PERCENT = 1.0
TASK_PACK_REPORT = "v13_7_41_usable_sandbox_task_pack"
REFERENCE_CHECKLIST = {
    "referenceOnly": True,
    "recordedReferences": [
        "yydhYYDH/alpha101",
        "ryckli/CryptoAgentPro.beta",
        "QuantFans/quantdigger",
    ],
    "safeSandboxUse": [
        "factor_research_context",
        "paper_testnet_live_mode_separation",
        "risk_gateway_before_execution",
        "human_confirmation_gate",
        "audit_first_observation_logs",
    ],
    "notImplementedHere": [
        "api_key_storage",
        "trade_order_endpoint",
        "emergency_close_execution",
        "testnet_order_execution",
        "automatic_trading",
    ],
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed == parsed else fallback


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_pair_tokens(pair: str) -> list[str]:
    cleaned = pair.strip().upper()
    if not cleaned:
        return []
    full = cleaned.replace("/", "_").replace(":", "_").replace("-", "_")
    base = cleaned.split("/")[0].strip()
    tokens = [full]
    if base:
        tokens.extend([f"{base}_USDT_USDT", f"{base}_USDT"])
    return list(dict.fromkeys(tokens))


def _find_local_public_ohlcv_cache(quant_path: Path, pair: str, timeframe: str) -> dict[str, Any]:
    data_root = quant_path / "user_data" / "data"
    if not data_root.exists():
        return {
            "available": False,
            "source": "missing_local_public_ohlcv_cache",
            "reason": "quant_engine_user_data_data_missing",
        }
    timeframe_token = str(timeframe or "").strip().lower()
    tokens = _normalize_pair_tokens(pair)
    if not tokens or not timeframe_token:
        return {
            "available": False,
            "source": "missing_local_public_ohlcv_cache",
            "reason": "pair_or_timeframe_missing",
        }
    for path in data_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".feather", ".json", ".csv"}:
            continue
        name = path.name.upper()
        if timeframe_token not in path.name.lower():
            continue
        if any(token in name for token in tokens):
            stat = path.stat()
            return {
                "available": True,
                "source": "local_public_ohlcv_cache",
                "pathHint": str(path.relative_to(data_root)),
                "fileSize": stat.st_size,
                "modifiedAt": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            }
    return {
        "available": False,
        "source": "missing_local_public_ohlcv_cache",
        "reason": "pair_timeframe_cache_not_found",
    }


def _task_existing_log_count(task_id: str) -> int:
    rows = list_paper_observation_logs(task_id)
    return len(rows) if isinstance(rows, list) else 0


def _digest_payload(value: Any) -> str:
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    except TypeError:
        encoded = str(value).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _sample_key(task_id: str, pair: str, timeframe: str, cache: dict[str, Any], pair_metrics: dict[str, Any]) -> str:
    data_mode = "local_public_ohlcv_cache" if cache.get("available") else "task_pack_metrics_only"
    payload = {
        "version": SAMPLE_KEY_SCHEMA_VERSION,
        "taskId": task_id,
        "pair": pair,
        "timeframe": timeframe,
        "dataMode": data_mode,
        "pathHint": cache.get("pathHint"),
        "fileSize": cache.get("fileSize"),
        "modifiedAt": cache.get("modifiedAt"),
        "metricsDigest": _digest_payload(pair_metrics),
    }
    return f"local_sandbox_sample::{_digest_payload(payload)}"


def _utc_date_key(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d")


def _has_closed_outcome(log: dict[str, Any]) -> bool:
    return log.get("outcomeR") is not None or bool(str(log.get("outcome") or "").strip())


def _find_duplicate_closed_sample(
    task_id: str,
    sample_key: str,
    pair: str,
    timeframe: str,
    cache: dict[str, Any],
    data_mode: str,
) -> dict[str, Any] | None:
    rows = list_paper_observation_logs(task_id)
    if not isinstance(rows, list):
        return None
    today_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path_hint = cache.get("pathHint")
    for row in reversed(rows):
        if not isinstance(row, dict) or not _has_closed_outcome(row):
            continue
        if row.get("sampleKey") == sample_key:
            return row
        legacy_same_window = (
            row.get("sampleKey") is None
            and str(row.get("pair") or "") == pair
            and str(row.get("timeframe") or "") == timeframe
            and str(row.get("dataMode") or "") == data_mode
            and row.get("dataSourcePathHint") == path_hint
            and _utc_date_key(row.get("createdAt")) == today_key
        )
        if legacy_same_window:
            return row
    return None


def _select_replay_pair(task: dict[str, Any]) -> tuple[dict[str, Any], str]:
    recommended = task.get("recommendedPairs") if isinstance(task.get("recommendedPairs"), list) else []
    avoid_rows = task.get("avoidUntilReviewedPairs") if isinstance(task.get("avoidUntilReviewedPairs"), list) else []
    avoid_pairs = {
        str(row.get("pair") or "").strip()
        for row in avoid_rows
        if isinstance(row, dict)
    }
    for row in recommended:
        if not isinstance(row, dict):
            continue
        pair = str(row.get("pair") or "").strip()
        if pair and pair not in avoid_pairs:
            return row, pair
    for row in recommended:
        if isinstance(row, dict) and str(row.get("pair") or "").strip():
            return row, str(row.get("pair")).strip()
    return {}, ""


def _deterministic_outcome_r(task: dict[str, Any], pair_metrics: dict[str, Any], sequence: int) -> tuple[float, str]:
    historical = task.get("historicalMetrics") if isinstance(task.get("historicalMetrics"), dict) else {}
    win_rate = _safe_float(pair_metrics.get("winRatePct"), _safe_float(historical.get("winRatePct"), 45.0))
    rank = _safe_int(task.get("rank"), 1)
    bucket = (sequence * 37 + rank * 17) % 100
    if bucket < max(0.0, min(100.0, win_rate)):
        return 2.0, "virtual_target_hit"
    return -1.0, "virtual_stop_hit"


def _build_artifact(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifactId": task.get("taskId"),
        "strategyId": task.get("strategyId"),
        "title": task.get("title") or task.get("candidateId") or task.get("taskId"),
        "displayName": task.get("title") or task.get("candidateId") or task.get("taskId"),
        "version": CONTROL_CONSOLE_VERSION,
        "sourceFile": task.get("sourceReport"),
        "readinessTier": task.get("status") or "planned_paper_observation",
        "metrics": task.get("historicalMetrics") if isinstance(task.get("historicalMetrics"), dict) else {},
    }


def _build_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"local_sandbox_v13_7_34::{stamp}"


def run_local_sandbox(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    quant_path = Path(str(payload.get("quantEnginePath") or get_quant_engine_path() or DEFAULT_QUANT_ENGINE_PATH)).expanduser().resolve()
    task_pack = build_usable_sandbox_task_pack(quant_path)
    tasks = task_pack.get("paperObservationTasks") if isinstance(task_pack.get("paperObservationTasks"), list) else []
    default_max_tasks = min(len(tasks) or 1, 20)
    max_tasks = max(1, min(_safe_int(payload.get("maxTasks"), default_max_tasks), 20))
    run_id = _build_run_id()
    rows: list[dict[str, Any]] = []
    generated = 0
    closed_samples = 0
    data_gap_count = 0
    skipped_duplicates = 0
    total_virtual_equity = 0.0
    total_virtual_capital = 0.0

    for task in tasks[:max_tasks]:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("taskId") or "").strip()
        if not task_id:
            continue
        pair_metrics, pair = _select_replay_pair(task)
        timeframe = str(task.get("timeframe") or "1d").strip()
        cache = _find_local_public_ohlcv_cache(quant_path, pair, timeframe) if pair else {
            "available": False,
            "source": "missing_local_public_ohlcv_cache",
            "reason": "no_recommended_pair",
        }
        existing_count = _task_existing_log_count(task_id)
        sequence = existing_count + 1
        artifact = _build_artifact(task)
        total_virtual_capital += VIRTUAL_CAPITAL_PER_STRATEGY

        if cache.get("available") or pair_metrics:
            data_mode = "local_public_ohlcv_cache" if cache.get("available") else "task_pack_metrics_only"
            sample_key = _sample_key(task_id, pair, timeframe, cache, pair_metrics)
            duplicate = _find_duplicate_closed_sample(task_id, sample_key, pair, timeframe, cache, data_mode)
            if duplicate:
                skipped_duplicates += 1
                total_virtual_equity += VIRTUAL_CAPITAL_PER_STRATEGY
                rows.append({
                    "taskId": task_id,
                    "strategyId": task.get("strategyId"),
                    "title": task.get("title"),
                    "pair": pair,
                    "timeframe": timeframe,
                    "logId": None,
                    "duplicateOfLogId": duplicate.get("logId"),
                    "sampleKey": sample_key,
                    "outcomeR": None,
                    "virtualCapital": VIRTUAL_CAPITAL_PER_STRATEGY,
                    "virtualEquity": VIRTUAL_CAPITAL_PER_STRATEGY,
                    "dataStatus": "duplicate_sample_skipped",
                    "dataMode": data_mode,
                    "dataSourcePathHint": cache.get("pathHint"),
                })
                continue
            outcome_r, outcome_reason = _deterministic_outcome_r(task, pair_metrics, sequence)
            equity = VIRTUAL_CAPITAL_PER_STRATEGY * (1 + ((outcome_r * RISK_UNIT_PERCENT) / 100))
            total_virtual_equity += equity
            note = (
                f"本地沙盒自动观察：{pair or 'unknown'} {timeframe} 使用本地 public OHLCV/历史任务包生成虚拟闭合样本；"
                f"结果 {outcome_r:+.2f}R。仅用于复盘，不是交易信号。"
            )
            base_extra_fields = {
                "runId": run_id,
                "autoGenerated": True,
                "sandboxMode": "historical_replay_virtual",
                "sampleKey": sample_key,
                "dataMode": data_mode,
                "dataStatus": "cache_available" if cache.get("available") else "cache_missing_metrics_available",
                "dataSourcePathHint": cache.get("pathHint"),
                "dataSourceFileSize": cache.get("fileSize"),
                "dataSourceModifiedAt": cache.get("modifiedAt"),
                "pair": pair,
                "timeframe": timeframe,
                "virtualCapital": VIRTUAL_CAPITAL_PER_STRATEGY,
                "virtualEquity": round(equity, 2),
                "outcomeR": outcome_r,
                "outcomeReason": outcome_reason,
                "riskUnitPercent": RISK_UNIT_PERCENT,
                "referenceChecklist": REFERENCE_CHECKLIST,
                "safetyNote": "Local sandbox virtual observation only. No exchange order is created.",
            }
            instrumented_extra_fields = {
                **base_extra_fields,
                **build_estimated_path_fields(base_extra_fields, task=task, quant_path=quant_path),
            }
            log = add_paper_observation_log(
                artifact_id=task_id,
                log_type="rule_matched",
                note=note,
                signal_observed=True,
                rule_matched=True,
                outcome=f"{outcome_r:+.2f}R",
                artifact=artifact,
                extra_fields=instrumented_extra_fields,
            )
            generated += 1
            closed_samples += 1
            rows.append({
                "taskId": task_id,
                "strategyId": task.get("strategyId"),
                "title": task.get("title"),
                "pair": pair,
                "timeframe": timeframe,
                "logId": log.get("logId"),
                "outcomeR": outcome_r,
                "virtualCapital": VIRTUAL_CAPITAL_PER_STRATEGY,
                "virtualEquity": round(equity, 2),
                "sampleKey": sample_key,
                "dataMode": data_mode,
                "dataStatus": "cache_available" if cache.get("available") else "cache_missing_metrics_available",
                "dataSourcePathHint": cache.get("pathHint"),
                "instrumentationStatus": log.get("instrumentationStatus"),
                "instrumentationMode": log.get("instrumentationMode"),
                "actualExchangeFill": log.get("actualExchangeFill"),
                "direction": log.get("direction"),
                "entryPrice": log.get("entryPrice"),
                "exitPrice": log.get("exitPrice"),
                "pathOutcomeR": log.get("pathOutcomeR"),
                "mfeR": log.get("mfeR"),
                "maeR": log.get("maeR"),
                "feeEstimateR": log.get("feeEstimateR"),
                "slippageEstimateR": log.get("slippageEstimateR"),
                "holdingTimeMinutes": log.get("holdingTimeMinutes"),
            })
        else:
            data_gap_count += 1
            total_virtual_equity += VIRTUAL_CAPITAL_PER_STRATEGY
            note = (
                f"本地沙盒数据不足：{task.get('title') or task_id} 缺少推荐币种或本地 public OHLCV cache。"
                "已记录缺口，不生成虚拟闭合样本。"
            )
            log = add_paper_observation_log(
                artifact_id=task_id,
                log_type="no_signal",
                note=note,
                signal_observed=False,
                rule_matched=False,
                outcome="",
                artifact=artifact,
                extra_fields={
                    "runId": run_id,
                    "autoGenerated": True,
                    "sandboxMode": "historical_replay_virtual",
                    "dataMode": "data_gap",
                    "dataStatus": "insufficient_data",
                    "dataGapReason": cache.get("reason") or "unknown",
                    "pair": pair,
                    "timeframe": timeframe,
                    "virtualCapital": VIRTUAL_CAPITAL_PER_STRATEGY,
                    "virtualEquity": VIRTUAL_CAPITAL_PER_STRATEGY,
                    "riskUnitPercent": RISK_UNIT_PERCENT,
                    "referenceChecklist": REFERENCE_CHECKLIST,
                    "safetyNote": "Local sandbox virtual observation only. No exchange order is created.",
                },
            )
            generated += 1
            rows.append({
                "taskId": task_id,
                "strategyId": task.get("strategyId"),
                "title": task.get("title"),
                "pair": pair,
                "timeframe": timeframe,
                "logId": log.get("logId"),
                "outcomeR": None,
                "virtualCapital": VIRTUAL_CAPITAL_PER_STRATEGY,
                "virtualEquity": VIRTUAL_CAPITAL_PER_STRATEGY,
                "dataStatus": "insufficient_data",
                "dataGapReason": cache.get("reason") or "unknown",
            })

    run = {
        "runId": run_id,
        "version": CONTROL_CONSOLE_VERSION,
        "source": CONTROL_CONSOLE_SOURCE,
        "createdAt": now_iso(),
        "taskCount": len(rows),
        "generatedLogCount": generated,
        "closedSampleCount": closed_samples,
        "dataGapCount": data_gap_count,
        "skippedDuplicateCount": skipped_duplicates,
        "virtualCapitalPerStrategy": VIRTUAL_CAPITAL_PER_STRATEGY,
        "totalVirtualCapital": round(total_virtual_capital, 2),
        "totalVirtualEquity": round(total_virtual_equity, 2),
        "totalVirtualPnl": round(total_virtual_equity - total_virtual_capital, 2),
        "riskUnitPercent": RISK_UNIT_PERCENT,
        "rows": rows,
        "quantEnginePath": str(quant_path),
        "taskPackReport": TASK_PACK_REPORT,
        "usableStrategyCatalogReport": USABLE_STRATEGY_CATALOG_REPORT,
        "taskPackSummary": task_pack.get("summary") if isinstance(task_pack.get("summary"), dict) else {},
        "referenceChecklist": REFERENCE_CHECKLIST,
        "safetyBoundary": SAFETY_BOUNDARY,
        "safetyNote": "Local sandbox replay uses virtual capital only; no Trade API, API key, account read, order, Dry-run, or auto trading.",
    }
    return save_local_sandbox_run(run)
