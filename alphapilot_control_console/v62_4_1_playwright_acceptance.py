from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


VIEWPORTS = (
    ("desktop-1440", 1440, 1000),
    ("mobile-390", 390, 844),
    ("mobile-375", 375, 812),
)


def _integer_text(value: object) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _credential_state_label(status: object) -> str:
    return {
        "ready": "当前凭据已注入",
        "provider_credentials_required": "当前凭据未注入",
    }.get(str(status), str(status or "当前状态不可用"))


def _historical_smoke_label(status: object) -> str:
    return {
        "provider_smoke_passed": "历史 Smoke 已通过",
        "not_available": "无历史 Smoke 证据",
    }.get(str(status), str(status or "历史状态不可用"))


def evaluate_browser_snapshot(
    *,
    viewport: str,
    strategy_dom: Mapping[str, object],
    strategy_api: Mapping[str, object],
    demo_dom: Mapping[str, object],
    demo_api: Mapping[str, object],
    ai_dom: Mapping[str, object],
    ai_api: Mapping[str, object],
    console_errors: Sequence[str],
    page_errors: Sequence[str],
    request_failures: Sequence[str],
    horizontal_overflow: bool,
) -> dict[str, object]:
    issues: list[str] = []
    if console_errors:
        issues.append("console_error")
    if page_errors:
        issues.append("page_error")
    if request_failures:
        issues.append("request_failure")
    if horizontal_overflow:
        issues.append("horizontal_overflow")
    if any(str(value).strip() in {"", "--", "读取真实进度"} for value in strategy_dom.values()):
        issues.append("strategy_placeholder_value")

    counts = dict(strategy_api.get("resultCounts") or {})
    for field in (
        "canEnterDemo",
        "needsForwardValidation",
        "failed",
        "dataInsufficient",
        "systemIssue",
    ):
        if _integer_text(strategy_dom.get(field)) != int(counts.get(field, 0) or 0):
            issues.append(f"strategy_count_mismatch:{field}")

    pilot = dict(strategy_api.get("currentPilot") or {})
    expected_candidate_trials = (
        f"{int(pilot.get('candidateCount', 0) or 0)} / "
        f"{int(pilot.get('trialCount', 0) or 0)}"
    )
    if str(strategy_dom.get("campaignId")) != str(pilot.get("campaignId")):
        issues.append("pilot_campaign_mismatch")
    if str(strategy_dom.get("candidateTrials")) != expected_candidate_trials:
        issues.append("pilot_candidate_trial_mismatch")
    if _integer_text(strategy_dom.get("formalReady")) != int(
        pilot.get("formalReadyCandidateCount", 0) or 0
    ):
        issues.append("pilot_formal_ready_mismatch")
    if _integer_text(strategy_dom.get("formalBlocked")) != int(
        pilot.get("formalBlockedCandidateCount", 0) or 0
    ):
        issues.append("pilot_formal_blocked_mismatch")
    if _integer_text(strategy_dom.get("stable")) != int(
        pilot.get("stableSelectionCount", 0) or 0
    ):
        issues.append("pilot_stable_selection_mismatch")

    current_credentials = dict(ai_api.get("currentCredentialState") or {})
    if str(ai_dom.get("credentialState")) != _credential_state_label(
        current_credentials.get("status")
    ):
        issues.append("ai_current_credential_state_mismatch")
    historical_smoke = dict(ai_api.get("historicalProviderSmoke") or {})
    if str(ai_dom.get("historicalSmokeState")) != _historical_smoke_label(
        historical_smoke.get("status")
    ):
        issues.append("ai_historical_smoke_state_mismatch")

    if _integer_text(demo_dom.get("runningStrategyCount")) != int(
        demo_api.get("runningStrategyCount", 0) or 0
    ):
        issues.append("demo_running_strategy_mismatch")
    if _integer_text(demo_dom.get("openPositionCount")) != int(
        demo_api.get("openPositionCount", 0) or 0
    ):
        issues.append("demo_open_position_mismatch")
    return {
        "viewport": viewport,
        "status": "passed" if not issues else "failed",
        "issues": issues,
    }


def _text(page: Any, selector: str) -> str:
    return page.locator(selector).inner_text().strip()


def _get_json(request_context: Any, url: str) -> dict[str, object]:
    response = request_context.get(url)
    if not response.ok:
        raise RuntimeError(f"GET {url} returned HTTP {response.status}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"GET {url} did not return a JSON object")
    return payload


def run_playwright_acceptance(
    *,
    base_url: str,
    output_directory: Path,
    chrome_executable: Path,
) -> dict[str, object]:
    from playwright.sync_api import sync_playwright

    output_directory.mkdir(parents=True, exist_ok=True)
    base_url = base_url.rstrip("/")
    snapshots: list[dict[str, object]] = []
    api_snapshot: dict[str, object] = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(chrome_executable),
            args=["--disable-background-networking"],
        )
        try:
            for viewport_name, width, height in VIEWPORTS:
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                )
                page = context.new_page()
                console_errors: list[str] = []
                page_errors: list[str] = []
                request_failures: list[str] = []
                page.on(
                    "console",
                    lambda message, target=console_errors: (
                        target.append(message.text) if message.type == "error" else None
                    ),
                )
                page.on("pageerror", lambda error, target=page_errors: target.append(str(error)))
                page.on(
                    "requestfailed",
                    lambda request, target=request_failures: target.append(
                        f"{request.method} {request.url}: {request.failure}"
                    ),
                )

                response = page.goto(base_url + "/", wait_until="networkidle", timeout=60_000)
                if response is None or not response.ok:
                    raise RuntimeError("Production route did not return HTTP success")
                page.wait_for_selector("#pilotCampaignId", state="visible", timeout=30_000)
                page.wait_for_function(
                    "() => document.querySelector('#pilotCampaignId')?.textContent?.trim()"
                    " && document.querySelector('#pilotCampaignId').textContent.trim() !== '--'",
                    timeout=30_000,
                )
                strategy_api = _get_json(
                    context.request,
                    base_url + "/api/strategy/summary",
                )
                ai_api = _get_json(context.request, base_url + "/api/ai/control")
                strategy_dom = {
                    "canEnterDemo": _text(page, "#canEnterDemoCount"),
                    "needsForwardValidation": _text(page, "#needsForwardCount"),
                    "failed": _text(page, "#failedCount"),
                    "dataInsufficient": _text(page, "#dataInsufficientCount"),
                    "systemIssue": _text(page, "#systemIssueCount"),
                    "campaignId": _text(page, "#pilotCampaignId"),
                    "candidateTrials": (
                        f"{_text(page, '#pilotCandidateCount')} / "
                        f"{_text(page, '#pilotTrialCount')}"
                    ),
                    "stable": _text(page, "#pilotStableCount"),
                    "formalReady": _text(page, "#pilotFormalReadyCount"),
                    "formalBlocked": _text(page, "#pilotFormalBlockedCount"),
                }
                ai_dom = {
                    "credentialState": _text(page, "#aiCredentialState"),
                    "historicalSmokeState": _text(page, "#aiHistoricalSmokeState"),
                }
                strategy_screenshot = output_directory / f"{viewport_name}-strategy.png"
                page.screenshot(path=str(strategy_screenshot), full_page=True)
                strategy_overflow = bool(
                    page.evaluate(
                        "() => document.documentElement.scrollWidth > window.innerWidth + 1"
                    )
                )

                demo_response = page.goto(
                    base_url + "/ui-preview/demo-v2",
                    wait_until="networkidle",
                    timeout=60_000,
                )
                if demo_response is None or not demo_response.ok:
                    raise RuntimeError("Demo V2 route did not return HTTP success")
                page.wait_for_selector("#connectionStatus", state="visible", timeout=30_000)
                page.wait_for_function(
                    "() => document.querySelector('#connectionStatus')?.textContent?.trim()"
                    " && document.querySelector('#connectionStatus').textContent.trim() !== '读取中'",
                    timeout=30_000,
                )
                demo_api = _get_json(context.request, base_url + "/api/demo/summary")
                demo_dom = {
                    "runningStrategyCount": _text(page, "#runningStrategies"),
                    "openPositionCount": _text(page, "#openPositions"),
                }
                demo_screenshot = output_directory / f"{viewport_name}-demo.png"
                page.screenshot(path=str(demo_screenshot), full_page=True)
                demo_overflow = bool(
                    page.evaluate(
                        "() => document.documentElement.scrollWidth > window.innerWidth + 1"
                    )
                )
                horizontal_overflow = strategy_overflow or demo_overflow
                evaluation = evaluate_browser_snapshot(
                    viewport=viewport_name,
                    strategy_dom=strategy_dom,
                    strategy_api=strategy_api,
                    demo_dom=demo_dom,
                    demo_api=demo_api,
                    ai_dom=ai_dom,
                    ai_api=ai_api,
                    console_errors=console_errors,
                    page_errors=page_errors,
                    request_failures=request_failures,
                    horizontal_overflow=horizontal_overflow,
                )
                snapshots.append(
                    {
                        **evaluation,
                        "viewportPixels": {"width": width, "height": height},
                        "httpStatus": response.status,
                        "strategyDom": strategy_dom,
                        "demoDom": demo_dom,
                        "aiDom": ai_dom,
                        "consoleErrors": console_errors,
                        "pageErrors": page_errors,
                        "requestFailures": request_failures,
                        "horizontalOverflow": horizontal_overflow,
                        "screenshots": {
                            "strategy": strategy_screenshot.name,
                            "demo": demo_screenshot.name,
                        },
                    }
                )
                if not api_snapshot:
                    api_snapshot = {
                        "strategySummary": strategy_api,
                        "demoSummary": demo_api,
                        "aiControl": ai_api,
                    }
                context.close()
        finally:
            browser.close()

    failed = [snapshot for snapshot in snapshots if snapshot["status"] != "passed"]
    report = {
        "schemaVersion": "v62_4_1_playwright_production_route_v1",
        "generatedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "status": "passed" if not failed else "failed",
        "baseUrl": base_url,
        "browser": "system_google_chrome_headless_via_playwright",
        "writeActionsPerformed": False,
        "armAttempted": False,
        "orderAttempted": False,
        "snapshots": snapshots,
        "apiSnapshot": api_snapshot,
    }
    (output_directory / "playwright_acceptance.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# V62.4.1 Playwright Production Route Acceptance",
        "",
        f"- Status: `{report['status']}`",
        f"- Strategy route: `{base_url}/`",
        f"- Demo route: `{base_url}/ui-preview/demo-v2`",
        "- Browser: system Google Chrome controlled by Playwright",
        "- Write / ARM / order actions: `0 / 0 / 0`",
        "",
        "| Viewport | Result | Console errors | Overflow |",
        "|---|---:|---:|---:|",
    ]
    lines.extend(
        f"| `{snapshot['viewport']}` | `{snapshot['status']}` | "
        f"`{len(snapshot['consoleErrors'])}` | `{snapshot['horizontalOverflow']}` |"
        for snapshot in snapshots
    )
    (output_directory / "playwright_acceptance.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    return report


__all__ = ["evaluate_browser_snapshot", "run_playwright_acceptance"]
