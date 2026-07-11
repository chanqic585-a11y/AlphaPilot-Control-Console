(function attachIssueGuidance(globalScope) {
  "use strict";

  const ACK_PREFIX = "ALPHAPILOT_ISSUE_ACK_V1";

  function normalizedBlockers(issue) {
    return [...new Set(Array.isArray(issue?.blockers) ? issue.blockers.filter(Boolean).map(String) : [])].sort();
  }

  function issueFingerprint(issue = {}) {
    const acknowledgementIdentity = issue.acknowledgementId || normalizedBlockers(issue).join("|");
    return [
      issue.pageId || "unknown_page",
      issue.strategyId || "global",
      issue.stage || "unknown_stage",
      acknowledgementIdentity,
      issue.version || "1",
    ].join("::");
  }

  function storageCandidates() {
    const candidates = [];
    for (const name of ["localStorage", "sessionStorage"]) {
      try {
        const storage = globalScope[name];
        if (storage && typeof storage.getItem === "function" && typeof storage.setItem === "function") {
          candidates.push(storage);
        }
      } catch (_error) {
        // Privacy modes may reject storage access; the in-memory fallback remains available.
      }
    }
    return candidates;
  }

  function createController(options = {}) {
    const documentRef = options.documentRef || globalScope.document;
    const dialog = documentRef?.getElementById("issueGuidanceDialog") || null;
    const issues = new Map();
    const memoryAcknowledged = new Set();
    const stores = storageCandidates();
    let currentIssueKey = null;

    function acknowledgementKey(fingerprint) {
      return `${ACK_PREFIX}::${fingerprint}`;
    }

    function isAcknowledged(issue) {
      const fingerprint = issue.fingerprint || issueFingerprint(issue);
      if (memoryAcknowledged.has(fingerprint)) return true;
      return stores.some((storage) => {
        try {
          return storage.getItem(acknowledgementKey(fingerprint)) === "1";
        } catch (_error) {
          return false;
        }
      });
    }

    function acknowledge(issue) {
      if (!issue) return;
      const fingerprint = issue.fingerprint || issueFingerprint(issue);
      memoryAcknowledged.add(fingerprint);
      for (const storage of stores) {
        try {
          storage.setItem(acknowledgementKey(fingerprint), "1");
          return;
        } catch (_error) {
          // Try the next storage implementation before retaining memory-only state.
        }
      }
    }

    function setText(id, value) {
      const target = documentRef?.getElementById(id);
      if (target) target.textContent = value || "--";
    }

    function setList(id, rows) {
      const target = documentRef?.getElementById(id);
      if (!target) return;
      target.replaceChildren();
      const values = Array.isArray(rows) && rows.length ? rows : ["等待系统补充已完成步骤。"];
      for (const value of values) {
        const item = documentRef.createElement("li");
        item.textContent = String(value);
        target.appendChild(item);
      }
    }

    function render(issue) {
      setText("issueGuidanceTitle", issue.title || "需要处理的问题");
      setText("issueGuidanceStage", issue.stageLabel || issue.stage || "当前阶段");
      setText("issueGuidanceSummary", issue.summary || "当前流程存在阻塞。");
      setList("issueGuidanceCompletedList", issue.completed);
      setText("issueGuidanceNextAction", issue.nextAction || "请按当前页面提示继续。");
      setText("issueGuidanceSafety", issue.safety || "该操作不会越过现有安全闸门。");
    }

    function register(issue) {
      if (!issue || !issue.pageId) return null;
      const fingerprint = issueFingerprint(issue);
      const key = issue.key || fingerprint;
      issues.set(key, { ...issue, key, fingerprint, blockers: normalizedBlockers(issue) });
      return key;
    }

    function replacePageIssues(pageId, pageIssues = []) {
      for (const [key, issue] of issues.entries()) {
        if (issue.pageId === pageId) issues.delete(key);
      }
      return pageIssues.map(register).filter(Boolean);
    }

    function open(issueKey, options = {}) {
      const issue = issues.get(issueKey);
      if (!issue || !dialog) return false;
      if (!options.manual && isAcknowledged(issue)) return false;
      if (dialog.open) return false;
      currentIssueKey = issueKey;
      render(issue);
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
      return true;
    }

    function presentHighestPriority(pageId) {
      const candidates = [...issues.values()]
        .filter((issue) => issue.pageId === pageId && !isAcknowledged(issue))
        .sort((left, right) => Number(right.priority || 0) - Number(left.priority || 0));
      return candidates.length ? open(candidates[0].key) : false;
    }

    function acknowledgeCurrent() {
      const issue = currentIssueKey ? issues.get(currentIssueKey) : null;
      acknowledge(issue);
      currentIssueKey = null;
    }

    dialog?.addEventListener("close", acknowledgeCurrent);
    documentRef?.getElementById("issueGuidanceAcknowledgeButton")?.addEventListener("click", (event) => {
      event.preventDefault();
      acknowledgeCurrent();
      if (typeof dialog.close === "function") dialog.close("acknowledged");
      else dialog.removeAttribute("open");
    });
    documentRef?.getElementById("issueGuidanceCloseButton")?.addEventListener("click", () => {
      if (typeof dialog.close === "function") dialog.close();
      else {
        acknowledgeCurrent();
        dialog.removeAttribute("open");
      }
    });

    return {
      register,
      replacePageIssues,
      presentHighestPriority,
      open: (issueKey) => open(issueKey, { manual: true }),
      acknowledgeCurrent,
      issueFingerprint,
    };
  }

  globalScope.AlphaPilotIssueGuidance = { ACK_PREFIX, createController, issueFingerprint };
})(typeof window !== "undefined" ? window : globalThis);
