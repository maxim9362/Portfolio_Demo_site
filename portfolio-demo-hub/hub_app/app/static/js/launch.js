(function () {
  const body = document.body;
  const frame = document.getElementById("demo-frame");
  const demoSessionId = body.dataset.demoSessionId;
  const sessionId = body.dataset.sessionId;
  const projectId = body.dataset.projectId;
  const returnUrl = body.dataset.returnUrl;
  const demoDeletePath = body.dataset.demoDeletePath;

  function withParams(path) {
    const url = new URL(path, window.location.origin);
    url.searchParams.set("demo_session_id", demoSessionId);
    url.searchParams.set("session_id", sessionId);
    return `${url.pathname}${url.search}`;
  }

  function track(eventType) {
    return fetch("/api/analytics/event", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        event_type: eventType,
        session_id: sessionId,
        demo_session_id: demoSessionId,
        project_id: projectId,
        page_url: window.location.href
      }),
      keepalive: true
    }).catch(() => {});
  }

  function openTab(tab) {
    document.querySelectorAll("[data-launch-tab]").forEach((button) => {
      button.classList.toggle("active", button.dataset.launchTab === tab);
    });

    if (tab === "admin") {
      frame.src = withParams(body.dataset.adminPath);
      track("admin_tab_open");
      return;
    }
    frame.src = withParams(body.dataset.demoPath);
    track("demo_tab_open");
  }

  document.querySelectorAll("[data-launch-tab]").forEach((button) => {
    button.addEventListener("click", () => openTab(button.dataset.launchTab));
  });

  document.querySelector("[data-finish-demo]").addEventListener("click", async () => {
    await fetch(`/api/demo-session/${encodeURIComponent(demoSessionId)}/finish`, {
      method: "POST",
      keepalive: true
    }).catch(() => {});
    if (demoDeletePath) {
      await fetch(demoDeletePath, {
        method: "DELETE",
        keepalive: true
      }).catch(() => {});
    }
    window.location.href = returnUrl;
  });

  openTab("demo");
})();
