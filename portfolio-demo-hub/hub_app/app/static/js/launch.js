(function () {
  const body = document.body;
  const frame = document.getElementById("demo-frame");
  let demoSessionId = body.dataset.demoSessionId;
  let sessionId = body.dataset.sessionId;
  const projectId = body.dataset.projectId;
  const returnUrl = body.dataset.returnUrl;
  let demoDeletePath = body.dataset.demoDeletePath;
  let activeTab = "demo";

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

  function clearEmbeddedDemoStorage() {
    const prefixes = [
      "uaisc_session_id:",
      `uaisc_session_id:${window.location.origin}`,
      `uaisc_session_id:${window.location.origin}${body.dataset.demoPath.replace(/\/$/, "")}`,
      `uaisc_session_id:${window.location.origin}${body.dataset.demoPath}`,
    ];

    for (const storage of [window.localStorage, window.sessionStorage]) {
      try {
        Object.keys(storage).forEach((key) => {
          if (prefixes.some((prefix) => key.startsWith(prefix))) {
            storage.removeItem(key);
          }
        });
      } catch (storageError) {
        console.warn("Demo storage cleanup failed.", storageError);
      }
    }
  }

  function openTab(tab) {
    activeTab = tab;
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

  document.querySelector("[data-new-chat]")?.addEventListener("click", async () => {
    const button = document.querySelector("[data-new-chat]");
    button.disabled = true;
    try {
      await fetch(`/api/demo-session/${encodeURIComponent(demoSessionId)}/finish`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({project_id: projectId}),
        keepalive: true
      }).catch(() => {});

      const newSessionPart = globalThis.crypto?.randomUUID
        ? globalThis.crypto.randomUUID()
        : String(Date.now());
      const response = await fetch(`/api/demo-session/${encodeURIComponent(projectId)}/start`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          session_id: `session_${newSessionPart}`,
          previous_demo_session_id: demoSessionId,
          page_url: window.location.href
        })
      });
      const payload = await response.json();
      sessionId = payload.session_id;
      demoSessionId = payload.demo_session_id;
      demoDeletePath = `${body.dataset.demoPath}demo-session/${demoSessionId}`;
      body.dataset.sessionId = sessionId;
      body.dataset.demoSessionId = demoSessionId;
      body.dataset.demoDeletePath = demoDeletePath;
      clearEmbeddedDemoStorage();
      openTab("demo");
      track("demo_tab_open");
    } finally {
      button.disabled = false;
    }
  });

  document.querySelector("[data-finish-demo]").addEventListener("click", async () => {
    await fetch(`/api/demo-session/${encodeURIComponent(demoSessionId)}/finish`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({project_id: projectId}),
      keepalive: true
    }).catch(() => {});
    window.location.href = returnUrl;
  });

  openTab("demo");
})();
