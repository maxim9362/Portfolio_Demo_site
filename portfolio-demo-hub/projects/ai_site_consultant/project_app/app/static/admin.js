// Этот файл проверяет новые заявки и управляет браузерными уведомлениями.

(() => {
    "use strict";

    const notificationButton = document.querySelector(
        "#enable-notifications"
    );
    const notificationStatus = document.querySelector(
        "#notification-status"
    );
    const refreshButton = document.querySelector("#refresh-leads");
    const newCount = document.querySelector("#new-count");
    const latestLeadKey = "admin_latest_lead_id";
    const notificationsKey = "admin_notifications_enabled";

    document.querySelectorAll("[data-confirm-delete]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const confirmed = window.confirm(
                "Удалить эту заявку? Это действие нельзя отменить."
            );
            if (!confirmed) {
                event.preventDefault();
            }
        });
    });

    if (refreshButton) {
        refreshButton.addEventListener("click", () => window.location.reload());
    }

    const notificationsSupported = "Notification" in window;

    function notificationsEnabled() {
        return (
            notificationsSupported
            && Notification.permission === "granted"
            && localStorage.getItem(notificationsKey) === "true"
        );
    }

    function updateNotificationUi(message = "") {
        if (!notificationButton) {
            return;
        }
        if (!notificationsSupported) {
            notificationButton.disabled = true;
            notificationButton.textContent = "Уведомления недоступны";
            if (notificationStatus) {
                notificationStatus.textContent =
                    "Этот браузер не поддерживает Notification API.";
            }
            return;
        }
        if (notificationsEnabled()) {
            notificationButton.textContent = "Уведомления включены";
            notificationButton.disabled = true;
        }
        if (notificationStatus && message) {
            notificationStatus.textContent = message;
        }
    }

    if (notificationButton) {
        notificationButton.addEventListener("click", async () => {
            if (!notificationsSupported) {
                updateNotificationUi();
                return;
            }
            try {
                const permission = await Notification.requestPermission();
                if (permission === "granted") {
                    localStorage.setItem(notificationsKey, "true");
                    updateNotificationUi("Уведомления включены");
                } else {
                    localStorage.removeItem(notificationsKey);
                    updateNotificationUi(
                        "Браузер не разрешил показывать уведомления."
                    );
                }
            } catch {
                updateNotificationUi(
                    "Не удалось включить уведомления в этом браузере."
                );
            }
        });
    }

    async function checkLatestLead() {
        if (!newCount) {
            return;
        }
        try {
            const response = await fetch("/admin/leads/latest-info", {
                headers: { Accept: "application/json" },
                credentials: "same-origin",
                cache: "no-store",
            });
            if (!response.ok || !response.headers
                .get("content-type")?.includes("application/json")) {
                return;
            }
            const data = await response.json();
            newCount.textContent = String(data.new_count ?? 0);

            const currentId = Number(data.latest_lead_id || 0);
            const previousId = Number(
                localStorage.getItem(latestLeadKey) || 0
            );
            if (!previousId) {
                localStorage.setItem(latestLeadKey, String(currentId));
                return;
            }
            if (currentId > previousId) {
                localStorage.setItem(latestLeadKey, String(currentId));
                refreshButton?.classList.remove("is-hidden");
                if (notificationsEnabled()) {
                    new Notification("Новая заявка", {
                        body: "Появилась новая заявка в админке",
                    });
                }
            }
        } catch {
            if (notificationStatus) {
                notificationStatus.textContent =
                    "Не удалось проверить новые заявки.";
            }
        }
    }

    updateNotificationUi();
    checkLatestLead();
    window.setInterval(checkLatestLead, 12000);
})();
