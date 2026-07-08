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

  window.euadoptPtIsPhone = function () {
    return document.documentElement.classList.contains("pt-phone");
  };

  syncPhoneClass();

  var resizeT = null;
  function onResize() {
    clearTimeout(resizeT);
    resizeT = setTimeout(function () {
      resizeT = null;
      syncPhoneClass();
    }, 100);
  }

  window.addEventListener("resize", onResize);
  window.addEventListener("pageshow", syncPhoneClass);
  window.addEventListener("orientationchange", onResize);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", syncPhoneClass);
  }
})();
