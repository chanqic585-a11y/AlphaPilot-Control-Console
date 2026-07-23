(() => {
  "use strict";

  const page = document.documentElement.dataset.previewPage;
  const byId = (id) => document.getElementById(id);
  const value = (input, fallback = "--") => input === null || input === undefined || input === "" ? fallback : String(input);
  const rows = (payload, key) => Array.isArray(payload?.[key]) ? payload[key] : [];
  const escapeHtml = (input) => value(input).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  })[character]);
  const formatUsdt = (input, signed = false) => {
    const number = Number(input);
    if (input === null || input === undefined || !Number.isFinite(number)) return "不可用";
    return `${signed && number > 0 ? "+" : ""}${number.toFixed(2)} USDT`;
  };
  const formatTime = (input) => {
    if (!input) return "--";
    const date = new Date(input);
    return Number.isNaN(date.getTime()) ? String(input) : new Intl.DateTimeFormat("zh-CN", {
      timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
    }).format(date);
  };
  const statusLabel = (status) => ({
    queued: "排队中", running: "运行中", paused: "已暂停", pause_requested: "正在暂停",
    completed: "已完成", failed: "失败", cancelled: "已取消", waiting: "等待闭合 K 线",
    connected_armed: "已连接并 ARM", waiting_for_arm: "等待 ARM", disabled: "关闭",
    armed: "运行中", approved_not_armed: "已批准，未 ARM", waiting_approval: "等待批准",
    can_enter_demo: "可进入 Demo", pending_human_review: "待人工审核", superseded_unapproved: "历史版本",
  })[status] || value(status, "等待");
  const credentialStateLabel = (status) => ({
    ready: "当前凭据已注入",
    provider_credentials_required: "当前凭据未注入",
  })[status] || value(status, "当前状态不可用");
  const historicalSmokeLabel = (status) => ({
    provider_smoke_passed: "历史 Smoke 已通过",
    not_available: "无历史 Smoke 证据",
  })[status] || value(status, "历史状态不可用");

  async function getJson(path) {
    const response = await fetch(path, { headers: { Accept: "application/json" }, cache: "no-store" });
    if (!response.ok) throw new Error(`${response.status} ${path}`);
    return response.json();
  }

  async function postJson(path, payload) {
    const headers = await window.AlphaPilotOperatorWrite.headersFor("POST", path, { Accept: "application/json" });
    const response = await fetch(path, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.message || result.error || `${response.status} ${path}`);
    return result;
  }

  function setPnl(element, input) {
    if (!element) return;
    const number = Number(input);
    element.textContent = formatUsdt(input, true);
    element.classList.toggle("positive", Number.isFinite(number) && number > 0);
    element.classList.toggle("negative", Number.isFinite(number) && number < 0);
  }

  function ensureIssueDialog() {
    let dialog = byId("issueDialog");
    if (dialog) return dialog;
    dialog = document.createElement("dialog");
    dialog.id = "issueDialog";
    dialog.className = "issue-dialog";
    dialog.innerHTML = '<p class="eyebrow">NEEDS ATTENTION</p><h2>需要处理</h2><p id="issueDialogMessage"></p><button id="dismissIssueButton" class="primary-button" type="button">知道了</button>';
    document.body.appendChild(dialog);
    byId("dismissIssueButton").addEventListener("click", () => dialog.close());
    return dialog;
  }

  function showIssue(message, code = "runtime_issue") {
    const banner = byId("issueBanner");
    if (banner) {
      banner.hidden = !message;
      banner.textContent = message || "";
    }
    if (!message) return;
    const fingerprint = `${page}:${code}:${message}`;
    if (window.sessionStorage.getItem("alphapilot-last-issue") === fingerprint) return;
    window.sessionStorage.setItem("alphapilot-last-issue", fingerprint);
    const dialog = ensureIssueDialog();
    byId("issueDialogMessage").textContent = message;
    if (typeof dialog.showModal === "function" && !dialog.open) dialog.showModal();
  }

  function currentFactoryIssue(factory) {
    if (factory.primaryBlocker) return String(factory.primaryBlocker);
    if (factory.resultClass === "system_issue" || factory.status === "failed") {
      const runId = factory.runId ? `（${factory.runId}）` : "";
      return `策略工厂本次运行未完成${runId}。请重新运行；若再次失败，请展开审计详情查看日志。Demo 运行不受影响。`;
    }
    return "";
  }

  function emptyRow(columns, text) {
    return `<tr><td colspan="${columns}" class="empty">${escapeHtml(text)}</td></tr>`;
  }

  function bindCards(container, items, environment) {
    container.querySelectorAll(".strategy-item").forEach((element, index) => {
      const activate = () => openStrategyDrawer(items[index], environment);
      element.addEventListener("click", activate);
      element.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") activate();
      });
    });
  }

  function renderStrategyCard(item) {
    const name = value(item.displayName || item.strategyName || item.name || item.releaseId, "未命名策略");
    const timeframe = Array.isArray(item.timeframes) ? item.timeframes.join(" / ") : value(item.timeframe);
    const scanCount = value(item.scanInstrumentCount, "不可用");
    return `<article class="strategy-item" tabindex="0"><header><h3>${escapeHtml(name)}</h3><span class="strategy-state">${escapeHtml(statusLabel(item.status || item.runtimeStatus))}</span></header><p>${escapeHtml(timeframe)} · 扫描 ${escapeHtml(scanCount)} 个合约</p><p>持仓 ${escapeHtml(value(item.openPositionCount, "0"))} · 浮动 ${escapeHtml(formatUsdt(item.floatingPnl, true))}</p></article>`;
  }

  function policyField(label, name, inputValue, options = {}) {
    const type = options.type || "number";
    const step = options.step || "any";
    return `<label>${escapeHtml(label)}<input name="${escapeHtml(name)}" type="${escapeHtml(type)}" step="${escapeHtml(step)}" value="${escapeHtml(inputValue)}" /></label>`;
  }

  async function renderPolicyEditor(item, environment) {
    const editor = byId("policyEditor");
    if (!editor) return;
    const strategyId = item.strategyId || item.releaseId;
    if (!strategyId) {
      editor.innerHTML = '<p class="empty">该条目没有可绑定的策略身份。</p>';
      return;
    }
    const result = await getJson(`/api/strategy-execution-policies?environment=${encodeURIComponent(environment)}&strategyId=${encodeURIComponent(strategyId)}`);
    const policies = rows(result, "policies");
    const current = [...policies].reverse().find((candidate) => candidate.status === "active") || policies.at(-1);
    if (!current) {
      let releaseHash = item.releaseHash || item.immutableResearchCandidateHash || "";
      if (!releaseHash && item.releaseId) {
        try {
          const release = await getJson(`/api/strategy/releases/${encodeURIComponent(item.releaseId)}`);
          releaseHash = release.releaseHash || "";
        } catch (_) {
          releaseHash = "";
        }
      }
      if (!releaseHash) {
        editor.innerHTML = '<p class="empty">尚无可绑定的冻结 Release Hash，当前不能生成参数版本。</p>';
        return;
      }
      editor.innerHTML = '<p class="empty">尚无参数版本。可从冻结 Release 与当前账户 Risk Profile 生成安全草稿。</p><button id="bootstrapPolicyButton" class="secondary-button" type="button">生成初始参数版本</button>';
      byId("bootstrapPolicyButton").addEventListener("click", async () => {
        const button = byId("bootstrapPolicyButton");
        button.disabled = true;
        try {
          await postJson("/api/strategy-execution-policies/bootstrap", {
            identity: {
              environment,
              strategyId,
              releaseId: item.releaseId || strategyId,
              releaseHash,
              name: item.displayName || item.strategyName || item.name || strategyId,
            },
          });
          await renderPolicyEditor(item, environment);
        } catch (error) {
          button.disabled = false;
          showIssue(`初始参数版本生成失败：${error.message}`, "policy_bootstrap_failed");
        }
      });
      return;
    }
    const policy = current.policy || {};
    editor.innerHTML = `
      <p class="policy-version">v${escapeHtml(current.version)} · ${escapeHtml(current.status)} · ${escapeHtml(current.classification)}</p>
      <form id="policyRevisionForm">
        <div class="settings-grid">
          ${policyField("策略资金 USDT", "allocationUsdt", policy.allocationUsdt)}
          ${policyField("单笔名义上限", "maxOrderNotionalUsdt", policy.maxOrderNotionalUsdt)}
          ${policyField("单笔风险 %", "riskPerTradePercent", policy.riskPerTradePercent)}
          ${policyField("单笔风险 USDT", "riskPerTradeUsdt", policy.riskPerTradeUsdt)}
          ${policyField("最大杠杆", "maxLeverage", policy.maxLeverage, { step: "1" })}
          ${policyField("最大并发持仓", "maxConcurrentPositions", policy.maxConcurrentPositions, { step: "1" })}
          ${policyField("单币最大持仓", "maxPositionsPerSymbol", policy.maxPositionsPerSymbol, { step: "1" })}
          ${policyField("扫描 Top N", "scanTopN", policy.scanTopN, { step: "1" })}
          ${policyField("最低成交额", "minimumQuoteTurnoverUsdt", policy.minimumQuoteTurnoverUsdt)}
          ${policyField("最低深度", "minimumDepthNotionalUsdt", policy.minimumDepthNotionalUsdt)}
          ${policyField("目标延迟秒", "targetSignalToOrderSeconds", policy.targetSignalToOrderSeconds)}
          ${policyField("信号最大年龄秒", "maximumSignalAgeSeconds", policy.maximumSignalAgeSeconds)}
          ${policyField("严重延迟秒", "criticalLatencyFailureSeconds", policy.criticalLatencyFailureSeconds)}
          ${policyField("订单确认超时秒", "orderAckTimeoutSeconds", policy.orderAckTimeoutSeconds)}
          ${policyField("亏损后冷却分钟", "cooldownAfterLossMinutes", policy.cooldownAfterLossMinutes)}
          ${policyField("手续费率", "feeRate", policy.feeRate)}
          ${policyField("滑点率", "slippageRate", policy.slippageRate)}
        </div>
        <label>止损策略 JSON<textarea name="stopPolicy" rows="5">${escapeHtml(JSON.stringify(policy.stopPolicy || {}, null, 2))}</textarea></label>
        <label>止盈策略 JSON<textarea name="exitPolicy" rows="6">${escapeHtml(JSON.stringify(policy.exitPolicy || {}, null, 2))}</textarea></label>
        <button class="primary-button" type="submit">保存为新版本</button>
      </form>
      <div id="policyRevisionResult" class="inline-status"></div>`;
    byId("policyRevisionForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const changes = {};
      for (const name of ["allocationUsdt", "maxOrderNotionalUsdt", "riskPerTradePercent", "riskPerTradeUsdt", "maxLeverage", "maxConcurrentPositions", "maxPositionsPerSymbol", "scanTopN", "minimumQuoteTurnoverUsdt", "minimumDepthNotionalUsdt", "targetSignalToOrderSeconds", "maximumSignalAgeSeconds", "criticalLatencyFailureSeconds", "orderAckTimeoutSeconds", "cooldownAfterLossMinutes", "feeRate", "slippageRate"]) {
        changes[name] = Number(form.get(name));
      }
      try {
        changes.stopPolicy = JSON.parse(String(form.get("stopPolicy") || "{}"));
        changes.exitPolicy = JSON.parse(String(form.get("exitPolicy") || "{}"));
        const created = await postJson(`/api/strategy-execution-policies/${encodeURIComponent(current.policyId)}/revisions`, { changes });
        byId("policyRevisionResult").innerHTML = `<p class="positive">已创建不可变参数版本 v${escapeHtml(created.policy.version)}。创建版本不会自动启用执行。</p><button id="activatePolicyButton" class="secondary-button" type="button">激活此参数版本</button>`;
        byId("activatePolicyButton").addEventListener("click", async () => {
          const needsExact = created.policy.classification !== "lower_risk";
          const confirmation = needsExact ? window.prompt("请输入 ACTIVATE_STRATEGY_EXECUTION_POLICY 精确确认") || "" : "";
          const activated = await postJson(`/api/strategy-execution-policies/${encodeURIComponent(created.policy.policyId)}/activate`, { confirmation, reason: "operator_strategy_policy_activation" });
          byId("policyRevisionResult").innerHTML = `<p class="positive">参数版本已激活。executionEnabled=${escapeHtml(activated.executionEnabled)}</p>`;
        });
      } catch (error) {
        showIssue(`参数版本创建失败：${error.message}`, "policy_revision_failed");
      }
    });
  }

  async function openStrategyDrawer(item, environment) {
    const drawer = byId("strategyDrawer");
    const backdrop = byId("drawerBackdrop");
    if (!drawer || !backdrop) return;
    byId("drawerTitle").textContent = value(item.displayName || item.name || item.releaseId, "策略详情");
    const summary = [
      ["状态", statusLabel(item.status || item.runtimeStatus)],
      ["周期", Array.isArray(item.timeframes) ? item.timeframes.join(" / ") : value(item.timeframe)],
      ["扫描范围", `${value(item.scanInstrumentCount || item.actualInstrumentCount, "不可用")} 个合约`],
      ["最后扫描", formatTime(item.latestScanAt)],
      ["当前持仓", value(item.openPositionCount, "0")],
      ["浮动盈亏", formatUsdt(item.floatingPnl, true)],
    ];
    byId("drawerSummary").innerHTML = summary.map(([key, itemValue]) => `<div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(itemValue)}</dd></div>`).join("");
    drawer.hidden = false;
    backdrop.hidden = false;
    byId("closeDrawer")?.focus();
    try {
      await renderPolicyEditor(item, environment);
    } catch (error) {
      byId("policyEditor").innerHTML = `<p class="empty">参数读取失败：${escapeHtml(error.message)}</p>`;
    }
  }

  function closeStrategyDrawer() {
    byId("strategyDrawer")?.setAttribute("hidden", "");
    byId("drawerBackdrop")?.setAttribute("hidden", "");
  }

  async function refreshStrategy() {
    const [factory, strategy, releases, ai] = await Promise.all([
      getJson("/api/research-factory/summary"),
      getJson("/api/strategy/summary"),
      getJson("/api/strategy/releases"),
      getJson("/api/ai/control"),
    ]);
    const progress = Math.max(0, Math.min(100, Number(factory.progressPercent) || 0));
    byId("factoryStatus").textContent = statusLabel(factory.status);
    byId("factoryProgressBar").style.width = `${progress}%`;
    byId("factoryProgressText").textContent = `${progress}% · ${value(factory.stage, "等待")}`;
    byId("factoryCurrentCandidate").textContent = value(factory.currentCandidate, "等待任务");
    const counts = strategy.resultCounts || {};
    byId("canEnterDemoCount").textContent = value(counts.canEnterDemo, "0");
    byId("needsForwardCount").textContent = value(counts.needsForwardValidation, "0");
    byId("failedCount").textContent = value(counts.failed, "0");
    byId("dataInsufficientCount").textContent = value(counts.dataInsufficient, "0");
    byId("systemIssueCount").textContent = value(counts.systemIssue, "0");
    byId("strategyUpdatedAt").textContent = formatTime(strategy.updatedAt || factory.updatedAt);
    const pilot = strategy.currentPilot || {};
    byId("pilotCampaignStatus").textContent = statusLabel(pilot.status);
    byId("pilotCampaignId").textContent = value(pilot.campaignId);
    byId("pilotCandidateCount").textContent = value(pilot.candidateCount, "0");
    byId("pilotTrialCount").textContent = value(pilot.trialCount, "0");
    byId("pilotStableCount").textContent = value(pilot.stableSelectionCount, "0");
    byId("pilotFormalReadyCount").textContent = value(pilot.formalReadyCandidateCount, "0");
    byId("pilotFormalBlockedCount").textContent = value(pilot.formalBlockedCandidateCount, "0");
    byId("pilotFormalRunCount").textContent = `${value(pilot.formalRunCount, "0")} / ${value(pilot.resultReadCount, "0")}`;
    const currentCredentials = ai.currentCredentialState || {};
    const historicalSmoke = ai.historicalProviderSmoke || {};
    byId("aiCredentialState").textContent = credentialStateLabel(currentCredentials.status);
    byId("aiHistoricalSmokeState").textContent = historicalSmokeLabel(historicalSmoke.status);
    byId("aiHistoricalSmokeTime").textContent = formatTime(historicalSmoke.evidenceFileModifiedAt);
    const allReleaseItems = rows(releases, "releases");
    const projectedHistoricalItems = rows(releases, "historicalReleases");
    const historicalReleaseItems = [
      ...projectedHistoricalItems,
      ...allReleaseItems.filter((item) => String(item.status || "").startsWith("superseded")),
    ];
    const historicalIds = new Set(historicalReleaseItems.map((item) => item.releaseId).filter(Boolean));
    const releaseItems = allReleaseItems.filter((item) => !historicalIds.has(item.releaseId));
    const candidateItems = rows(releases, "candidateReviews");
    const displayItems = [...candidateItems, ...releaseItems];
    byId("releaseCount").textContent = String(displayItems.length);
    byId("releaseList").innerHTML = displayItems.length ? displayItems.map(renderStrategyCard).join("") : '<p class="empty">当前没有候选或 Release。</p>';
    bindCards(byId("releaseList"), displayItems, "okx_demo");
    const current = releaseItems.find((item) => item.status === "can_enter_demo") || releaseItems[0];
    if (current?.releaseId) {
      const forward = await getJson(`/api/strategy/releases/${encodeURIComponent(current.releaseId)}/forward-validation`);
      byId("forwardValidation").innerHTML = `<strong>${escapeHtml(statusLabel(forward.status))}</strong><p>闭合交易 ${escapeHtml(value(forward.closedTradeCount, "0"))} · 运行 ${escapeHtml(value(forward.runningDayCount, "0"))} 天</p><p>${escapeHtml(value(forward.blocker, "没有阻塞"))}</p>`;
    }
    byId("auditSummary").textContent = JSON.stringify({
      factory,
      strategy,
      ai: {
        currentCredentialState: currentCredentials,
        historicalProviderSmoke: historicalSmoke,
      },
      historicalReleaseCount: historicalReleaseItems.length,
    }, null, 2);
    byId("updatedAt").textContent = `更新 ${formatTime(strategy.updatedAt || factory.updatedAt || new Date().toISOString())}`;
    const blocker = currentFactoryIssue(factory);
    if (blocker && factory.status !== "waiting_exact_release_approval") {
      showIssue(value(blocker), "strategy_factory_blocker");
    } else if (candidateItems.length) {
      showIssue(`有 ${candidateItems.length} 条候选策略等待人工审核；系统不会自动批准或 ARM。`, "strategy_factory_candidate_review_required");
    } else {
      showIssue("", "strategy_factory_clear");
    }
  }

  async function startFactoryRun() {
    const button = byId("runFactoryButton");
    button.disabled = true;
    try {
      const payload = {
        operation: byId("factoryOperation").value,
        timeframe: byId("factoryTimeframe").value,
        mode: byId("factoryMode").value,
        maxCandidateCount: Number(byId("factoryCandidateCount").value),
        maxTrialBudget: Number(byId("factoryTrialBudget").value),
      };
      await postJson("/api/research-factory/runs", payload);
      await refreshStrategy();
    } catch (error) {
      showIssue(`策略研究启动失败：${error.message}`, "strategy_factory_start_failed");
    } finally {
      button.disabled = false;
    }
  }

  function renderPositions(payload) {
    const items = rows(payload, "positions");
    byId("positionCount").textContent = String(items.length);
    byId("positionRows").innerHTML = items.length ? items.map((item) => `<tr><td>${escapeHtml(item.instrumentId || item.symbol)}</td><td>${escapeHtml(item.side || item.direction)}</td><td>${escapeHtml(value(item.quantity || item.size))}</td><td>${escapeHtml(value(item.entryPrice))}</td><td>${escapeHtml(formatUsdt(item.unrealizedPnlUsdt, true))}</td></tr>`).join("") : emptyRow(5, "当前没有策略持仓。");
  }

  function renderOrders(payload) {
    const items = rows(payload, "orders").filter((item) => item.errorCode || item.reason || ["failed", "rejected", "unknown"].includes(item.status));
    byId("orderCount").textContent = String(items.length);
    byId("orderRows").innerHTML = items.length ? items.map((item) => `<tr><td>${escapeHtml(formatTime(item.createdAt || item.updatedAt))}</td><td>${escapeHtml(item.instrumentId || item.symbol)}</td><td>${escapeHtml(value(item.status))}</td><td>${escapeHtml(value(item.reason || item.errorCode))}</td></tr>`).join("") : emptyRow(4, "当前没有异常策略订单。");
  }

  async function refreshDemo() {
    const [summary, strategies, positions, orders, universe, reconciliation] = await Promise.all([
      getJson("/api/demo/summary"), getJson("/api/demo/strategies"), getJson("/api/demo/positions"),
      getJson("/api/demo/orders"), getJson("/api/demo/universe"), getJson("/api/demo/reconciliation"),
    ]);
    byId("connectionStatus").textContent = statusLabel(summary.connectionStatus);
    byId("accountEquity").textContent = formatUsdt(summary.equity);
    byId("availableBalance").textContent = formatUsdt(summary.availableBalance);
    byId("equityMeta").textContent = summary.equity === null || summary.equity === undefined ? "不可用 · 未提供账户快照" : `${formatTime(summary.updatedAt)} · 已脱敏账户快照`;
    setPnl(byId("todayPnl"), summary.todayPnl);
    setPnl(byId("floatingPnl"), summary.floatingPnl);
    byId("runningStrategies").textContent = value(summary.runningStrategyCount, "0");
    byId("openPositions").textContent = value(summary.openPositionCount, "0");
    byId("universeStatus").textContent = `TOP200 ${value(universe.actualInstrumentCount, "--")}`;
    const funnel = summary.scanFunnel || universe.funnel || {};
    byId("marketCount").textContent = value(funnel.marketInstrumentCount ?? funnel.publicInstrumentCount);
    byId("demoUniverseCount").textContent = value(funnel.demoInstrumentCount ?? funnel.authenticatedDemoInstrumentCount);
    byId("liquidityCount").textContent = value(funnel.liquidityQualifiedCount ?? funnel.eligibleInstrumentCount);
    byId("deepScreenCount").textContent = value(funnel.deepEvaluatedCount ?? funnel.selectedInstrumentCount);
    byId("signalCount").textContent = value(funnel.matchedSignalCount ?? summary.matchability?.signalCount30d);
    byId("scanUpdatedAt").textContent = summary.updatedAt ? formatTime(summary.updatedAt) : `快照 ${value(universe.utcDate)}`;
    const strategyItems = rows(strategies, "strategies");
    byId("strategyList").innerHTML = strategyItems.length ? strategyItems.map(renderStrategyCard).join("") : '<p class="empty">当前没有 Demo 策略。</p>';
    bindCards(byId("strategyList"), strategyItems, "okx_demo");
    renderPositions(positions);
    renderOrders(orders);
    const issues = Array.isArray(summary.issues) ? summary.issues : [];
    showIssue(issues.length ? value(issues[0].message || issues[0].code) : "", issues[0]?.code || "demo_runtime_issue");
    byId("auditSummary").textContent = JSON.stringify({ releaseId: summary.releaseId || null, releaseHash: summary.releaseHash || null, riskOverlayHash: summary.riskOverlayHash || null, armed: Boolean(summary.armed), reconciliation }, null, 2);
    byId("updatedAt").textContent = `更新 ${formatTime(summary.updatedAt || new Date().toISOString())}`;
  }

  function gate(element, passed, yes, no) {
    if (!element) return;
    element.textContent = passed ? yes : no;
    element.classList.toggle("passed", passed);
  }

  async function refreshLive() {
    const [summary, strategies, positions, orders, readiness] = await Promise.all([
      getJson("/api/live/summary"), getJson("/api/live/strategies"), getJson("/api/live/positions"),
      getJson("/api/live/orders"), getJson("/api/live/canary-readiness"),
    ]);
    const technical = Boolean(readiness.adaptiveLearning?.passed);
    const approved = readiness.execution?.approvalStatus === "approved";
    const armed = readiness.execution?.armStatus === "armed";
    gate(byId("technicalGate"), technical, "已通过", "未通过");
    gate(byId("approvalGateAudit"), approved, "已批准", "未批准");
    gate(byId("armGateAudit"), armed, "已 ARM", "未 ARM");
    byId("connectionStatus").textContent = statusLabel(summary.connectionStatus);
    byId("liveReleaseStatus").textContent = value(readiness.statusLabel || readiness.status, "草稿");
    byId("accountEquity").textContent = formatUsdt(summary.equity);
    byId("availableBalance").textContent = formatUsdt(summary.availableBalance);
    setPnl(byId("todayPnl"), summary.todayPnl);
    setPnl(byId("floatingPnl"), summary.floatingPnl);
    byId("strategyOrders").textContent = value(summary.strategyOrderCount, "0");
    byId("openPositions").textContent = value(summary.openPositionCount, "0");
    const strategyItems = rows(strategies, "strategies");
    byId("strategyList").innerHTML = strategyItems.length ? strategyItems.map(renderStrategyCard).join("") : '<p class="empty">当前没有已批准的实盘策略。</p>';
    bindCards(byId("strategyList"), strategyItems, "okx_live");
    renderPositions(positions);
    renderOrders(orders);
    const blockers = Array.isArray(readiness.adaptiveLearning?.blockers) ? readiness.adaptiveLearning.blockers : [];
    byId("blockerCount").textContent = String(blockers.length);
    byId("blockerList").innerHTML = blockers.length ? blockers.map((item) => `<li>${escapeHtml(item.message || item.code || item)}</li>`).join("") : "<li>当前没有技术阻塞。</li>";
    const unsafe = armed || Boolean(readiness.execution?.withdrawAllowed);
    const issues = Array.isArray(summary.issues) ? summary.issues : [];
    showIssue(unsafe ? "安全状态异常：Live 或 Withdraw 不应在当前阶段开启。" : issues.length ? value(issues[0].message || issues[0].code) : blockers.length ? value(blockers[0].message || blockers[0].code || blockers[0]) : "", unsafe ? "unsafe_live_state" : "live_readiness_blocker");
    byId("auditSummary").textContent = JSON.stringify({ releaseId: readiness.release?.releaseId || null, releaseHash: readiness.audit?.releaseHash || null, modelPolicyHash: readiness.audit?.modelPolicyHash || null, riskOverlayHash: readiness.audit?.riskOverlayHash || null, technicalReadinessPassed: technical, exactApprovalPassed: approved, liveArmed: armed, withdrawEnabled: Boolean(readiness.execution?.withdrawAllowed) }, null, 2);
    byId("updatedAt").textContent = `更新 ${formatTime(summary.updatedAt || readiness.release?.generatedAt || new Date().toISOString())}`;
  }

  async function refresh() {
    const button = byId("refreshButton");
    if (button) button.disabled = true;
    try {
      if (page === "strategy") await refreshStrategy();
      if (page === "demo") await refreshDemo();
      if (page === "live") await refreshLive();
    } catch (error) {
      showIssue(`状态读取失败：${error.message}`, "status_read_failed");
    } finally {
      if (button) button.disabled = false;
    }
  }

  byId("refreshButton")?.addEventListener("click", refresh);
  byId("runFactoryButton")?.addEventListener("click", startFactoryRun);
  byId("closeDrawer")?.addEventListener("click", closeStrategyDrawer);
  byId("drawerBackdrop")?.addEventListener("click", closeStrategyDrawer);
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeStrategyDrawer(); });
  refresh();
  window.setInterval(refresh, page === "strategy" ? 10000 : 15000);
})();
