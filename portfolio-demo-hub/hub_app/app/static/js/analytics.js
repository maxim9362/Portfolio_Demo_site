(function () {
  const SESSION_KEY = "portfolio_demo_hub_session_id";

  function getSessionId() {
    let sessionId = localStorage.getItem(SESSION_KEY);
    if (!sessionId) {
      sessionId = `session_${crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36)}`;
      localStorage.setItem(SESSION_KEY, sessionId);
    }
    return sessionId;
  }

  function projectId() {
    return document.body.dataset.projectId || null;
  }

  function payload(eventType, extra) {
    return {
      event_type: eventType,
      session_id: getSessionId(),
      project_id: projectId(),
      page_url: window.location.href,
      metadata: extra || {}
    };
  }

  async function postJson(url, data) {
    try {
      await fetch(url, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data),
        keepalive: true
      });
    } catch (error) {
      console.debug("analytics failed", error);
    }
  }

  function track(eventType, extra) {
    return postJson("/api/analytics/event", payload(eventType, extra));
  }

  function heartbeat() {
    return postJson("/api/analytics/heartbeat", {
      session_id: getSessionId(),
      demo_session_id: document.body.dataset.demoSessionId || null,
      project_id: projectId(),
      page_url: window.location.href
    });
  }

  function sendSessionEnd() {
    const data = JSON.stringify(payload("session_end", {}));
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/api/analytics/event", new Blob([data], {type: "application/json"}));
      return;
    }
    postJson("/api/analytics/event", JSON.parse(data));
  }

  window.PortfolioAnalytics = {getSessionId, track, heartbeat};

  document.addEventListener("DOMContentLoaded", () => {
    track("page_view", {});
    heartbeat();
    window.setInterval(heartbeat, 15000);

    document.querySelectorAll("[data-track-event]").forEach((node) => {
      node.addEventListener("click", () => {
        track(node.dataset.trackEvent, {
          text: node.textContent.trim(),
          href: node.getAttribute("href") || null
        });
      });
    });

    document.querySelectorAll("[data-demo-link]").forEach((link) => {
      link.addEventListener("click", () => {
        const sessionId = getSessionId();
        if (sessionId) {
          link.href = `/launch/${encodeURIComponent(link.dataset.projectId)}?session_id=${encodeURIComponent(sessionId)}`;
        }
      });
    });
  });

  window.addEventListener("pagehide", sendSessionEnd);
})();
