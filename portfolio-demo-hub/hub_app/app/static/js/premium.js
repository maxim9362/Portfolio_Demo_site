(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function attachTilt(node, strength) {
    if (!node || reduceMotion) {
      return;
    }

    node.addEventListener("pointermove", function (event) {
      var rect = node.getBoundingClientRect();
      var x = (event.clientX - rect.left) / rect.width - 0.5;
      var y = (event.clientY - rect.top) / rect.height - 0.5;
      var rotateX = clamp(y * -strength, -strength, strength);
      var rotateY = clamp(x * strength, -strength, strength);
      node.style.transform = "perspective(900px) rotateX(" + rotateX + "deg) rotateY(" + rotateY + "deg) translateY(-2px)";
    });

    node.addEventListener("pointerleave", function () {
      node.style.transform = "";
    });
  }

  function initMobileMenu() {
    var toggle = document.querySelector(".mobile-menu-toggle");
    var nav = document.querySelector(".main-nav");
    var backdrop = document.querySelector(".mobile-nav-backdrop");
    var closeNodes = document.querySelectorAll("[data-menu-close]");

    if (!toggle || !nav || !backdrop) {
      return;
    }

    function openMenu() {
      backdrop.hidden = false;
      document.body.classList.add("nav-open");
      toggle.setAttribute("aria-expanded", "true");
    }

    function closeMenu() {
      document.body.classList.remove("nav-open");
      toggle.setAttribute("aria-expanded", "false");
      window.setTimeout(function () {
        if (!document.body.classList.contains("nav-open")) {
          backdrop.hidden = true;
        }
      }, 260);
    }

    toggle.addEventListener("click", function () {
      if (document.body.classList.contains("nav-open")) {
        closeMenu();
        return;
      }
      openMenu();
    });

    closeNodes.forEach(function (node) {
      node.addEventListener("click", closeMenu);
    });

    nav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", closeMenu);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeMenu();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initMobileMenu();

    attachTilt(document.querySelector(".hero-console"), 4);

    document.querySelectorAll(".product-card").forEach(function (card) {
      attachTilt(card, 2.4);
    });
  });
})();
/*
  Small premium UI effects for the public site.
  Keeps visual polish client-side without changing backend behavior.
*/
