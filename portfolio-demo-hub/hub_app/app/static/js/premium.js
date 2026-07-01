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

  document.addEventListener("DOMContentLoaded", function () {
    attachTilt(document.querySelector(".hero-console"), 4);

    document.querySelectorAll(".product-card").forEach(function (card) {
      attachTilt(card, 2.4);
    });
  });
})();
