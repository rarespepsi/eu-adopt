(function () {
  "use strict";
  var PHONE_MAX = 767.98;

  function isPhoneViewport() {
    var w = window.innerWidth || document.documentElement.clientWidth || 0;
    return w <= PHONE_MAX;
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
    return;
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
