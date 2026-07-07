(function () {
  "use strict";
  var MQ = "(max-width: 767.98px)";
  function isMob() {
    try {
      return window.matchMedia(MQ).matches;
    } catch (e) {
      return false;
    }
  }
  function navHeight() {
    var a0 = document.getElementById("A0");
    if (!a0) return 64;
    var bottom = Math.round(a0.getBoundingClientRect().bottom);
    if (bottom >= 24 && bottom <= 220) return bottom;
    try {
      var px = parseFloat(window.getComputedStyle(a0).height);
      if (isFinite(px) && px >= 24 && px <= 220) return Math.round(px);
    } catch (e2) {}
    return 64;
  }
  function syncNav() {
    if (!isMob()) {
      try {
        document.documentElement.style.removeProperty("--nav-height");
      } catch (e) {}
      return;
    }
    var nh = Math.max(24, Math.min(220, navHeight()));
    try {
      document.documentElement.style.setProperty("--nav-height", nh + "px");
    } catch (e3) {}
  }
  function syncPlaceholder() {
    var bar = document.getElementById("pt_p4_mobile_sticky");
    var ph = document.getElementById("pt_p4_sticky_placeholder");
    if (!bar || !ph) return;
    if (!isMob()) {
      ph.style.height = "";
      return;
    }
    var h = Math.round(bar.getBoundingClientRect().height);
    if (h > 0) ph.style.height = h + "px";
  }
  function boot() {
    syncNav();
    syncPlaceholder();
  }
  var resizeT = null;
  function onResize() {
    clearTimeout(resizeT);
    resizeT = setTimeout(function () {
      resizeT = null;
      syncNav();
      syncPlaceholder();
    }, 80);
  }
  window.addEventListener("resize", onResize);
  if (window.ResizeObserver) {
    var bar = document.getElementById("pt_p4_mobile_sticky");
    if (bar) {
      var ro = new ResizeObserver(syncPlaceholder);
      ro.observe(bar);
      var kids = bar.querySelectorAll(":scope > .pt-p4-box");
      for (var i = 0; i < kids.length; i++) ro.observe(kids[i]);
    }
    var navEl = document.getElementById("A0");
    if (navEl) new ResizeObserver(function () { syncNav(); syncPlaceholder(); }).observe(navEl);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
  window.addEventListener("load", boot);
})();
