// Этот файл управляет мобильным меню и открывает AI-чат по кнопкам лендинга.

const menuToggle = document.querySelector(".menu-toggle");
const siteNavigation = document.querySelector(".site-nav");
const chatTriggers = document.querySelectorAll(".chat-trigger");

function closeMenu() {
    siteNavigation.classList.remove("is-open");
    menuToggle.setAttribute("aria-expanded", "false");
}

menuToggle.addEventListener("click", () => {
    const willOpen = !siteNavigation.classList.contains("is-open");
    siteNavigation.classList.toggle("is-open", willOpen);
    menuToggle.setAttribute("aria-expanded", String(willOpen));
});

siteNavigation.addEventListener("click", (event) => {
    if (event.target.closest("a")) {
        closeMenu();
    }
});

chatTriggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
        window.dispatchEvent(new CustomEvent("uaisc:open", {
            detail: {
                message: trigger.dataset.chatMessage || "",
            },
        }));
    });
});
