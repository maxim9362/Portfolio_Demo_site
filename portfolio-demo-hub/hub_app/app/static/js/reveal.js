(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var selectors = [
    ".section",
    ".page-hero",
    ".project-hero",
    ".project-card",
    ".feature-card",
    ".steps article",
    ".detail-content > section",
    ".cta-band",
    ".contact-form",
    ".contact-copy",
    ".video-placeholder",
    ".video-frame",
    ".offer-grid article"
  ];

  function collectRevealNodes() {
    selectors.forEach(function (selector) {
      document.querySelectorAll(selector).forEach(function (node) {
        node.classList.add("reveal");
      });
    });
  }

  function showAll(nodes) {
    nodes.forEach(function (node) {
      node.classList.add("is-visible");
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    collectRevealNodes();
    var nodes = Array.prototype.slice.call(document.querySelectorAll(".reveal"));

    if (reduceMotion || !("IntersectionObserver" in window)) {
      showAll(nodes);
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) {
          return;
        }
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, {
      rootMargin: "0px 0px -8% 0px",
      threshold: 0.12
    });

    nodes.forEach(function (node, index) {
      node.style.transitionDelay = Math.min(index % 6, 5) * 70 + "ms";
      observer.observe(node);
    });
  });
})();
