"use strict";

const fs = require("fs");
const http = require("http");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..");
const WEB = path.join(ROOT, "web");
const outputArg = process.argv.indexOf("--output");
const OUTPUT = path.resolve(outputArg >= 0 ? process.argv[outputArg + 1] : path.join(ROOT, "reports", "ui-preview-v2"));

const strategy = {
  "/api/research-factory/summary": {
    status: "running",
    progressPercent: 64,
    stage: "正式回测与证据归档",
    currentCandidate: "1h 趋势回撤组合 v3",
    updatedAt: "2026-07-22T04:30:00Z",
  },
  "/api/strategy/summary": {
    resultCounts: {
      canEnterDemo: 2,
      needsForwardValidation: 3,
      failed: 11,
      dataInsufficient: 1,
      systemIssue: 0,
    },
    updatedAt: "2026-07-22T04:30:00Z",
  },
  "/api/strategy/releases": {
    releases: [{
      releaseId: "candidate-release-preview",
      strategyId: "candidate-strategy-preview",
      displayName: "1h 趋势回撤组合 v3",
      status: "can_enter_demo",
      timeframes: ["1h"],
      scanInstrumentCount: 200,
      openPositionCount: 0,
      todayPnl: null,
    }],
    candidateReviews: [{
      candidateReviewId: "candidate-review-preview",
      candidateId: "candidate-review-strategy-preview",
      strategyId: "candidate-review-strategy-preview",
      displayName: "15m 波动收缩突破候选 v1",
      status: "pending_human_review",
      timeframe: "15m",
      scanInstrumentCount: 200,
      openPositionCount: 0,
      todayPnl: null,
      approvalRequestActionable: true,
      automaticApprovalAllowed: false,
      approved: false,
      demoArm: false,
      orderCount: 0,
    }],
  },
  "/api/strategy/releases/candidate-release-preview/forward-validation": {
    status: "running",
    closedTradeCount: 18,
    runningDayCount: 12,
    blocker: "继续收集冻结后闭合交易证据",
  },
};

const demo = {
  "/api/demo/summary": {
    connectionStatus: "Demo 已连接",
    equity: 1000,
    availableBalance: 925.4,
    equitySource: "OKX Demo 账户快照",
    todayPnl: 6.82,
    floatingPnl: 1.35,
    runningStrategyCount: 1,
    openPositionCount: 1,
    releaseId: "preview-top200-portfolio",
    releaseHash: "preview_release_hash",
    riskOverlayHash: "preview_risk_hash",
    armed: true,
    issues: [],
    matchability: { signalCount30d: 14 },
    updatedAt: "2026-07-22T04:30:00Z",
  },
  "/api/demo/strategies": {
    strategies: [{
      releaseId: "preview-top200-portfolio",
      name: "趋势、回撤与波动组合",
      status: "等待收线",
      timeframes: ["1h", "1d"],
      scanInstrumentCount: 200,
      latestScanAt: "2026-07-22T04:00:00Z",
      openPositionCount: 1,
      todayPnl: 6.82,
    }],
  },
  "/api/demo/positions": {
    positions: [{ instrumentId: "ETH-USDT-SWAP", side: "多", quantity: "0.02", entryPrice: "3512.4", unrealizedPnlUsdt: 1.35 }],
  },
  "/api/demo/orders": { orders: [] },
  "/api/demo/universe": {
    actualInstrumentCount: 200,
    utcDate: "2026-07-22",
    funnel: {
      publicInstrumentCount: 405,
      authenticatedDemoInstrumentCount: 392,
      eligibleInstrumentCount: 327,
      selectedInstrumentCount: 200,
    },
  },
  "/api/demo/reconciliation": { status: "reconciled", unknownOrderCount: 0, nonzeroPositionCount: 1 },
};

const live = {
  status: "blocked_not_ready",
  statusLabel: "技术证据未就绪",
  release: { releaseId: "draft-live-release", generatedAt: "2026-07-22T04:30:00Z" },
  risk: {
    allocatedCapitalUSDT: 1000,
    riskPerTradeUSDT: 2.5,
    maximumConcurrentPositions: 1,
    maximumLeverage: 1,
  },
  adaptiveLearning: {
    passed: false,
    modelMode: "observer",
    blockers: ["真实 Factor Bench 尚未完成", "Live 可用模型仍未冻结"],
  },
  execution: {
    approvalStatus: "not_run",
    armStatus: "not_run",
    withdrawAllowed: false,
  },
  orders: { count: 0 },
  positions: { count: 0 },
  issues: [{ message: "自适应学习实盘证据尚未完成，Live 保持关闭。" }],
  audit: { releaseHash: "draft_release_hash", riskOverlayHash: "draft_risk_hash" },
  readOnly: true,
};

const liveProjection = {
  "/api/live/summary": {
    connectionStatus: "disabled",
    equity: null,
    availableBalance: null,
    todayPnl: null,
    floatingPnl: null,
    strategyOrderCount: 0,
    openPositionCount: 0,
    issues: [{ code: "adaptive_learning_not_ready", message: "自适应学习实盘证据尚未完成，Live 保持关闭。" }],
    updatedAt: "2026-07-22T04:30:00Z",
  },
  "/api/live/strategies": { strategies: [] },
  "/api/live/positions": { positions: [] },
  "/api/live/orders": { orders: [] },
};

function contentType(file) {
  if (file.endsWith(".html")) return "text/html; charset=utf-8";
  if (file.endsWith(".css")) return "text/css; charset=utf-8";
  if (file.endsWith(".js")) return "application/javascript; charset=utf-8";
  return "application/octet-stream";
}

function responseJson(response, payload) {
  const body = Buffer.from(JSON.stringify(payload));
  response.writeHead(200, { "Content-Type": "application/json; charset=utf-8", "Content-Length": body.length });
  response.end(body);
}

function serveStatic(response, name) {
  const file = path.join(WEB, name);
  const body = fs.readFileSync(file);
  response.writeHead(200, { "Content-Type": contentType(file), "Content-Length": body.length });
  response.end(body);
}

async function render() {
  fs.mkdirSync(OUTPUT, { recursive: true });
  const server = http.createServer((request, response) => {
    const requestPath = new URL(request.url, "http://127.0.0.1").pathname;
    if (strategy[requestPath]) return responseJson(response, strategy[requestPath]);
    if (demo[requestPath]) return responseJson(response, demo[requestPath]);
    if (liveProjection[requestPath]) return responseJson(response, liveProjection[requestPath]);
    if (requestPath === "/api/live/canary-readiness") return responseJson(response, live);
    if (requestPath === "/ui-preview/strategy-v2") return serveStatic(response, "preview-strategy-v2.html");
    if (requestPath === "/ui-preview/demo-v2") return serveStatic(response, "preview-demo-v2.html");
    if (requestPath === "/ui-preview/live-v2") return serveStatic(response, "preview-live-v2.html");
    if (requestPath === "/ui-preview-v2.css") return serveStatic(response, "ui-preview-v2.css");
    if (requestPath === "/ui-preview-v2.js") return serveStatic(response, "ui-preview-v2.js");
    response.writeHead(404);
    response.end("not found");
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  process.stdout.write(`UI fixture server ready on ${port}.\n`);
  const executablePath = process.env.ALPHAPILOT_BROWSER_EXECUTABLE || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
  const browser = await chromium.launch({ headless: true, executablePath, timeout: 15000 });
  process.stdout.write("Browser ready.\n");
  const checks = [];
  try {
    for (const item of [
      { page: "strategy", viewport: { width: 1440, height: 1000 }, file: "strategy_v2_desktop.png" },
      { page: "strategy", viewport: { width: 390, height: 844 }, file: "strategy_v2_mobile_390.png" },
      { page: "demo", viewport: { width: 1440, height: 1000 }, file: "demo_v2_desktop.png" },
      { page: "demo", viewport: { width: 390, height: 844 }, file: "demo_v2_mobile_390.png" },
      { page: "live", viewport: { width: 1440, height: 1000 }, file: "live_v2_desktop.png" },
      { page: "live", viewport: { width: 390, height: 844 }, file: "live_v2_mobile_390.png" },
    ]) {
      process.stdout.write(`Rendering ${item.file}.\n`);
      const context = await browser.newContext({ viewport: item.viewport, deviceScaleFactor: 1 });
      const page = await context.newPage();
      const errors = [];
      page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
      page.on("pageerror", (error) => errors.push(error.message));
      await page.goto(`http://127.0.0.1:${port}/ui-preview/${item.page}-v2`, {
        waitUntil: "domcontentloaded",
        timeout: 15000,
      });
      await page.waitForFunction(
        () => document.querySelector("#updatedAt")?.textContent?.startsWith("更新"),
        undefined,
        { timeout: 10000 },
      );
      let reviewReminderShown = null;
      if (item.page === "strategy") {
        const reminder = page.locator("#issueDialog");
        await reminder.waitFor({ state: "visible", timeout: 5000 });
        reviewReminderShown = await reminder.isVisible();
        if (reviewReminderShown) await page.locator("#dismissIssueButton").click();
      }
      const dimensions = await page.evaluate(() => ({
        viewportWidth: window.innerWidth,
        documentWidth: document.documentElement.scrollWidth,
        bodyWidth: document.body.scrollWidth,
      }));
      await page.screenshot({ path: path.join(OUTPUT, item.file), fullPage: true });
      process.stdout.write(`Rendered ${item.file}.\n`);
      checks.push({
        page: item.page,
        screenshot: item.file,
        viewport: item.viewport,
        reviewReminderShown,
        horizontalOverflow: dimensions.documentWidth > dimensions.viewportWidth || dimensions.bodyWidth > dimensions.viewportWidth,
        browserErrors: errors,
      });
      await context.close();
    }
  } finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
  const acceptance = {
    schemaVersion: "ui_preview_v2_acceptance_v1",
    status: checks.every((item) => (
      !item.horizontalOverflow
      && item.browserErrors.length === 0
      && (item.page !== "strategy" || item.reviewReminderShown === true)
    )) ? "passed" : "failed",
    fixtureData: true,
    fixturePurpose: "layout_and_browser_acceptance_only",
    productionRoutesUseReadOnlyLedgerProjection: true,
    writeActions: 0,
    checks,
  };
  fs.writeFileSync(path.join(OUTPUT, "ui_acceptance.json"), `${JSON.stringify(acceptance, null, 2)}\n`, "utf8");
  if (acceptance.status !== "passed") process.exitCode = 1;
  process.stdout.write(`${JSON.stringify(acceptance)}\n`);
}

render().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exitCode = 1;
});
