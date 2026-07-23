(function () {
  "use strict";

  let sessionPromise = null;

  function routeConfirmation(method, path) {
    const parsed = new URL(path, window.location.origin);
    return `CONFIRM ${String(method || "POST").toUpperCase()} ${parsed.pathname}`;
  }

  async function loadSession() {
    if (!sessionPromise) {
      sessionPromise = fetch("/api/operator-session", {
        headers: { Accept: "application/json" },
        cache: "no-store",
      }).then(async (response) => {
        const payload = await response.json().catch(() => ({}));
        if (!response.ok || !payload.writeToken || !payload.csrfToken) {
          throw new Error(payload.error || "operator_session_unavailable");
        }
        return payload;
      }).catch((error) => {
        sessionPromise = null;
        throw error;
      });
    }
    return sessionPromise;
  }

  async function headersFor(method, path, baseHeaders = {}) {
    const session = await loadSession();
    return {
      ...baseHeaders,
      Accept: baseHeaders.Accept || "application/json",
      "Content-Type": "application/json",
      "X-AlphaPilot-Write-Token": session.writeToken,
      "X-AlphaPilot-CSRF": session.csrfToken,
      "X-AlphaPilot-Confirmation": routeConfirmation(method, path),
    };
  }

  window.AlphaPilotOperatorWrite = Object.freeze({ headersFor, routeConfirmation });
})();
