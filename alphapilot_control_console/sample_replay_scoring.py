from __future__ import annotations

from typing import Any


SCORING_VERSION = "V13.7.47"


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


def _add_label(labels: list[dict[str, Any]], code: str, label: str, severity: str, evidence: str) -> None:
    labels.append({
        "code": code,
        "label": label,
        "severity": severity,
        "evidence": evidence,
    })


def _outcome_quality(outcome_r: float, path_outcome_r: float | None) -> tuple[int, str]:
    reference = path_outcome_r if path_outcome_r is not None else outcome_r
    if reference >= 2:
        return 24, "target_like_path"
    if reference >= 1:
        return 18, "positive_path"
    if reference >= 0:
        return 12, "flat_positive_path"
    if reference > -1:
        return 7, "controlled_loss_path"
    return 2, "stop_like_loss_path"


def score_replay_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Score an estimated local replay sample for review, not execution."""
    outcome_r = _safe_float(sample.get("outcomeR"), 0.0)
    path_outcome_value = sample.get("pathOutcomeR")
    path_outcome_r = None if path_outcome_value in (None, "") else _safe_float(path_outcome_value)
    mfe_r = _safe_float(sample.get("mfeR"), 0.0)
    mae_r = _safe_float(sample.get("maeR"), 0.0)
    fee_r = _safe_float(sample.get("feeEstimateR"), 0.0)
    slippage_r = _safe_float(sample.get("slippageEstimateR"), 0.0)
    holding_minutes = _safe_int(sample.get("holdingTimeMinutes"), 0)
    quality = str(sample.get("sampleQuality") or "")
    instrumentation_status = str(sample.get("instrumentationStatus") or "")
    actual_fill = bool(sample.get("actualExchangeFill"))
    labels: list[dict[str, Any]] = []

    score = 40
    outcome_points, outcome_bucket = _outcome_quality(outcome_r, path_outcome_r)
    score += outcome_points

    if instrumentation_status == "estimated":
        score += 8
        _add_label(
            labels,
            "estimated_path_only",
            "估算路径",
            "info",
            "样本路径来自本地 public OHLCV cache，不是真实成交。",
        )
    elif actual_fill:
        score += 15
        _add_label(labels, "actual_fill_path", "真实成交路径", "info", "样本包含真实成交路径字段。")
    else:
        score -= 12
        _add_label(labels, "path_missing", "路径字段不足", "warning", "样本缺少可复盘路径字段。")

    if outcome_r >= 2:
        _add_label(labels, "target_hit", "目标兑现", "positive", f"样本结果 {outcome_r:.2f}R。")
    elif outcome_r <= -1:
        _add_label(labels, "stop_loss_like", "止损型亏损", "danger", f"样本结果 {outcome_r:.2f}R。")
    elif outcome_r > 0:
        _add_label(labels, "small_win", "小幅盈利", "info", f"样本结果 {outcome_r:.2f}R。")
    else:
        _add_label(labels, "flat_or_small_loss", "小亏或持平", "warning", f"样本结果 {outcome_r:.2f}R。")

    if mfe_r >= 2 and outcome_r < 1:
        score -= 12
        _add_label(
            labels,
            "profit_not_captured",
            "利润未兑现",
            "warning",
            f"MFE 达到 {mfe_r:.2f}R，但最终结果只有 {outcome_r:.2f}R。",
        )
    elif mfe_r >= 2:
        score += 10
        _add_label(labels, "strong_favorable_path", "有利波动充分", "positive", f"MFE {mfe_r:.2f}R。")
    elif mfe_r < 0.8 and outcome_r <= 0:
        score -= 10
        _add_label(labels, "weak_favorable_path", "有利波动不足", "warning", f"MFE 只有 {mfe_r:.2f}R。")

    if mae_r <= -2:
        score -= 14
        _add_label(labels, "deep_adverse_excursion", "回撤过深", "danger", f"MAE {mae_r:.2f}R。")
    elif mae_r <= -1:
        score -= 8
        _add_label(labels, "stop_area_touched", "接近止损区", "warning", f"MAE {mae_r:.2f}R。")
    elif mae_r > -0.5:
        score += 8
        _add_label(labels, "clean_entry_path", "入场路径较干净", "positive", f"MAE {mae_r:.2f}R。")

    cost_r = fee_r + slippage_r
    if cost_r >= 0.2:
        score -= 8
        _add_label(labels, "cost_drag_high", "成本拖累", "warning", f"费用和滑点约 {cost_r:.2f}R。")
    elif cost_r > 0:
        _add_label(labels, "cost_tracked", "成本已计入", "info", f"费用和滑点约 {cost_r:.2f}R。")

    if holding_minutes >= 1440:
        score -= 5
        _add_label(labels, "holding_too_long", "持有过久", "warning", f"估算持有 {holding_minutes} 分钟。")
    elif 0 < holding_minutes <= 240:
        score += 4
        _add_label(labels, "compact_holding_window", "持有窗口较紧凑", "info", f"估算持有 {holding_minutes} 分钟。")

    if quality == "estimated_path_ready":
        _add_label(labels, "reviewable_estimated_sample", "可复盘估算样本", "info", "样本可用于本地复盘，但不能当作真实成交。")

    score = max(0, min(100, score))
    if score >= 75:
        rating = "strong_review_sample"
        rating_label = "高质量复盘样本"
    elif score >= 60:
        rating = "usable_review_sample"
        rating_label = "可用复盘样本"
    elif score >= 40:
        rating = "weak_review_sample"
        rating_label = "弱复盘样本"
    else:
        rating = "poor_review_sample"
        rating_label = "低质量复盘样本"

    positives = sum(1 for item in labels if item.get("severity") == "positive")
    warnings = sum(1 for item in labels if item.get("severity") == "warning")
    dangers = sum(1 for item in labels if item.get("severity") == "danger")
    primary = next((item for item in labels if item.get("severity") == "danger"), None)
    if primary is None:
        primary = next((item for item in labels if item.get("severity") == "warning"), None)
    if primary is None and labels:
        primary = labels[0]

    if primary:
        summary = f"{rating_label}：{primary['label']}。"
    else:
        summary = f"{rating_label}：暂无明显弱点标签。"

    return {
        "scoringVersion": SCORING_VERSION,
        "reviewScore": score,
        "reviewRating": rating,
        "reviewRatingLabel": rating_label,
        "outcomeBucket": outcome_bucket,
        "primaryWeaknessCode": primary.get("code") if primary else None,
        "primaryWeaknessLabel": primary.get("label") if primary else None,
        "weaknessLabels": labels,
        "positiveLabelCount": positives,
        "warningLabelCount": warnings,
        "dangerLabelCount": dangers,
        "reviewSummary": summary,
        "reviewSafetyNote": "复盘评分只解释本地估算样本，不是交易建议，不会创建订单。",
    }


def summarize_replay_scores(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        return {
            "averageReviewScore": 0,
            "strongReviewSampleCount": 0,
            "usableReviewSampleCount": 0,
            "weakReviewSampleCount": 0,
            "poorReviewSampleCount": 0,
            "topWeaknessLabels": [],
        }
    scores = [_safe_float(sample.get("reviewScore"), 0.0) for sample in samples]
    ratings = [str(sample.get("reviewRating") or "") for sample in samples]
    label_counts: dict[str, dict[str, Any]] = {}
    for sample in samples:
        for label in sample.get("weaknessLabels") or []:
            if not isinstance(label, dict):
                continue
            severity = str(label.get("severity") or "info")
            if severity not in {"warning", "danger"}:
                continue
            code = str(label.get("code") or "")
            if not code:
                continue
            row = label_counts.setdefault(code, {
                "code": code,
                "label": label.get("label") or code,
                "severity": severity,
                "count": 0,
            })
            row["count"] += 1
    top_labels = sorted(label_counts.values(), key=lambda item: (-int(item["count"]), str(item["code"])))[:8]
    return {
        "averageReviewScore": round(sum(scores) / len(scores), 2),
        "strongReviewSampleCount": ratings.count("strong_review_sample"),
        "usableReviewSampleCount": ratings.count("usable_review_sample"),
        "weakReviewSampleCount": ratings.count("weak_review_sample"),
        "poorReviewSampleCount": ratings.count("poor_review_sample"),
        "topWeaknessLabels": top_labels,
    }
