(function () {
  "use strict";
  var PHONE_MAX = 767.98;

  function isPhoneViewport() {
    var w = window.innerWidth || document.documentElement.clientWidth || 0;
    var h = window.innerHeight || document.documentElement.clientHeight || 0;
    return Math.min(w, h) <= PHONE_MAX;
  }

  function recoverUi() {
    document.body.style.overflow = "";
    document.body.classList.remove("pt-mob-filters-above-nav");
    try {
      if (window.__a0CloseMobileNav) window.__a0CloseMobileNav();
    } catch (e) {}
  }

  function syncPhoneClass() {
    var phone = isPhoneViewport();
    document.documentElement.classList.toggle("pt-phone", phone);
    if (phone) recoverUi();
  }

  function fixHeaderGap() {
    if (!document.documentElement.classList.contains("pt-phone")) return;
    if (window.__ptUserBusyUntil && Date.now() < window.__ptUserBusyUntil) return;
    var p1 = document.getElementById("P1");
    var p4 = document.getElementById("P4");
    if (!p1 || !p4) return;
    var st = window.pageYOffset || document.documentElement.scrollTop || 0;
    if (st > 500) return;
    var p1Top = p1.getBoundingClientRect().top;
    var p4Top = p4.getBoundingClientRect().top;
    if (st < 80 && (p1Top > 100 || p4Top > 220)) {
      window.scrollTo(0, 0);
    }
  }

  window.euadoptPtIsPhone = function () {
    return document.documentElement.classList.contains("pt-phone");
  };

  syncPhoneClass();

  var resizeT = null;
  var scrollFixT = null;
  function onResize() {
    clearTimeout(resizeT);
    resizeT = setTimeout(function () {
      resizeT = null;
      syncPhoneClass();
      fixHeaderGap();
    }, 100);
  }

  function onScrollEnd() {
    clearTimeout(scrollFixT);
    scrollFixT = setTimeout(function () {
      scrollFixT = null;
      fixHeaderGap();
    }, 120);
  }

  window.addEventListener("resize", onResize);
  window.addEventListener("scroll", onScrollEnd, { passive: true });
  window.addEventListener("pageshow", function () {
    syncPhoneClass();
    fixHeaderGap();
  });
  window.addEventListener("orientationchange", onResize);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      syncPhoneClass();
      fixHeaderGap();
    });
  } else {
    fixHeaderGap();
  }
})();
