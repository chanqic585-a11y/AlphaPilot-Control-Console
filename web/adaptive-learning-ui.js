(function () {
  "use strict";

  const POLL_MS = 5000;
  const byId = (id) => document.getElementById(id);

  function setText(id, value) {
    const target = byId(id);
    if (target) target.textContent = String(value ?? "--");
  }

  function setBadge(id, text, state) {
    const target = byId(id);
    if (!target) return;
    target.textContent = text;
    target.classList.toggle("ok", state === "ok");
    target.classList.toggle("warn", state === "warn");
    target.classList.toggle("danger", state === "danger");
    target.classList.toggle("neutral", state === "neutral");
  }

  function render(payload) {
    const ready = payload.status === "observer_ready";
    const mode = payload.modelMode || "observer";
    setBadge("adaptiveStrategyStatus", ready ? "旁路就绪" : "证据未就绪", ready ? "ok" : "warn");
    setText("adaptiveFactorCount", payload.factorCount ?? 0);
    setText("adaptiveFeatureCount", payload.featureCount ?? 0);
    setText("adaptiveStrategyModelMode", mode);

    setBadge("adaptiveDemoMode", mode, ready ? "ok" : "warn");
    setText("adaptiveDemoSnapshotCount", payload.featureSnapshotCount ?? 0);
    setText("adaptiveDemoDecisionCount", payload.modelDecisionCount ?? 0);
    setText("adaptiveDemoSampleCount", payload.learningSampleCount ?? 0);
    setText(
      "adaptiveDemoBoundary",
      ready ? "仅记录，不改变信号、风险或订单。" : "等待因子、Feature Schema 与模型注册表证据。",
    );

    const liveReady = payload.liveDecisionReady === true;
    setBadge("adaptiveLiveReadiness", liveReady ? "模型门已通过" : "未就绪", liveReady ? "ok" : "warn");
    setText(
      "adaptiveLiveNextAction",
      liveReady
        ? "仍需绑定新 Release Hash、风险证据和精确人工批准；当前不会自动 ARM。"
        : "实盘必须绑定 rank_only、veto_only 或 meta_label 模型，并创建新 Release Hash 后精确批准。",
    );
  }

  async function refresh() {
    try {
      const response = await fetch("/api/adaptive-learning?fresh=1", { cache: "no-store" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
      render(payload);
    } catch (error) {
      render({ status: "blocked", modelMode: "observer", liveDecisionReady: false });
      setBadge("adaptiveStrategyStatus", "读取失败", "danger");
      setText("adaptiveDemoBoundary", `状态读取失败：${error.message}`);
    }
  }

  function start() {
    refresh();
    window.setInterval(refresh, POLL_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
