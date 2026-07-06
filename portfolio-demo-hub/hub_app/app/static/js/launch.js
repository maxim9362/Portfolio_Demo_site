/*
  Demo launch wrapper controller.
  Switches the iframe between demo/admin views, starts fresh demo sessions,
  tracks launch events, and finishes/cleans up demo data when the user exits.
*/

(function () {
  const body = document.body;
  const frame = document.getElementById("demo-frame");
  let demoSessionId = body.dataset.demoSessionId;
  let sessionId = body.dataset.sessionId;
  const projectId = body.dataset.projectId;
  const returnUrl = body.dataset.returnUrl;
  let demoDeletePath = body.dataset.demoDeletePath;
  let activeTab = "demo";
  const peekControls = document.querySelector("[data-launch-peek]");

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

  function setPanelCollapsed(isCollapsed) {
    body.classList.toggle("launch-panel-collapsed", isCollapsed);
    body.classList.toggle("demo-shell-collapsed", isCollapsed);
    body.dataset.collapsed = isCollapsed ? "true" : "false";
    if (peekControls) {
      if (isCollapsed) {
        peekControls.hidden = false;
        peekControls.removeAttribute("hidden");
      } else {
        peekControls.hidden = true;
        peekControls.setAttribute("hidden", "");
      }
    }
  }

  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const hideButton = target?.closest("[data-launch-panel-hide]");
    const showButton = target?.closest("[data-launch-panel-show]");
    if (hideButton) {
      event.preventDefault();
      setPanelCollapsed(true);
      return;
    }
    if (showButton) {
      event.preventDefault();
      setPanelCollapsed(false);
    }
  });

  async function startNewDemoSession() {
    const buttons = document.querySelectorAll("[data-new-chat], [data-new-chat-compact]");
    buttons.forEach((button) => {
      button.disabled = true;
    });
    try {
      await fetch(`/api/demo-session/${encodeURIComponent(demoSessionId)}/finish`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({project_id: projectId}),
        keepalive: true
      }).catch(() => {});

      const response = await fetch(`/api/demo-session/${encodeURIComponent(projectId)}/start`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          session_id: sessionId,
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
      buttons.forEach((button) => {
        button.disabled = false;
      });
    }
  }

  document.querySelectorAll("[data-new-chat], [data-new-chat-compact]").forEach((button) => {
    button.addEventListener("click", startNewDemoSession);
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

  setPanelCollapsed(false);
  openTab("demo");
})();
