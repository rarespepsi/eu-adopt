(function () {
  "use strict";
  var ROT_TICK_MS = 5000;
  var rotRegistry = [];
  var rotTimer = null;
  function rotTick() {
    if (document.hidden) return;
    for (var i = rotRegistry.length - 1; i >= 0; i--) {
      var r = rotRegistry[i];
      if (!r.img || !r.img.isConnected) {
        rotRegistry.splice(i, 1);
        continue;
      }
      r.idx = (r.idx + 1) % r.list.length;
      r.img.setAttribute("src", r.list[r.idx]);
    }
    if (!rotRegistry.length && rotTimer != null) {
      clearInterval(rotTimer);
      rotTimer = null;
    }
  }
  function ensureRotTimer() {
    if (rotTimer != null || !rotRegistry.length) return;
    rotTimer = setInterval(rotTick, ROT_TICK_MS);
  }
  function skipRotation() {
    try {
      return window.matchMedia("(max-width: 767.98px)").matches;
    } catch (e) {
      return false;
    }
  }
  function initPetImageRotation(root) {
    if (skipRotation()) return;
    var el = root || document.getElementById("pt_p2_grid") || document;
    var all = el.querySelectorAll ? el.querySelectorAll("img.pet-rotating-image") : [];
    if (!all || !all.length) return;
    Array.prototype.forEach.call(all, function (img) {
      if (img.dataset.rotInit === "1") return;
      var list = [img.getAttribute("src") || "", img.getAttribute("data-rot-src-2") || "", img.getAttribute("data-rot-src-3") || ""].filter(Boolean);
      if (list.length <= 1) {
        img.dataset.rotInit = "1";
        return;
      }
      img.dataset.rotInit = "1";
      rotRegistry.push({ img: img, list: list, idx: 0 });
    });
    ensureRotTimer();
  }
  window.euadoptInitPetImageRotation = initPetImageRotation;
  window.addEventListener("pagehide", function () {
    if (rotTimer != null) {
      clearInterval(rotTimer);
      rotTimer = null;
    }
    rotRegistry.length = 0;
  });
  function boot() {
    initPetImageRotation(document.getElementById("pt_p2_grid"));
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
