(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function typeHeadline(node) {
    var text = node.getAttribute("data-typewriter") || node.textContent.trim();
    if (!text || reduceMotion) {
      node.textContent = text;
      node.classList.add("typing-ready");
      return;
    }

    node.textContent = "";
    node.classList.add("typing-active");

    var index = 0;
    var timer = window.setInterval(function () {
      node.textContent = text.slice(0, index + 1);
      index += 1;
      if (index >= text.length) {
        window.clearInterval(timer);
        node.classList.remove("typing-active");
        node.classList.add("typing-ready");
      }
    }, 22);
  }

  function cycleText(node) {
    var items = (node.getAttribute("data-typing-items") || "").split("|").filter(Boolean);
    if (items.length < 2 || reduceMotion) {
      return;
    }

    var index = 0;
    window.setInterval(function () {
      index = (index + 1) % items.length;
      node.classList.add("is-switching");
      window.setTimeout(function () {
        node.textContent = items[index];
        node.classList.remove("is-switching");
      }, 180);
    }, 2100);
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-typewriter]").forEach(typeHeadline);
    document.querySelectorAll("[data-typing-cycle]").forEach(cycleText);
  });
})();
/*
  Hero typing/cycling text helper for the marketing pages.
*/
