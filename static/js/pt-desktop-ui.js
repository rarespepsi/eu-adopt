(function () {
  "use strict";
  var MQ = "(max-width: 767.98px)";
  var filtersForm = document.getElementById("filtre-animale");
  var mobileFiltersBtns = document.querySelectorAll("#PW .js-pt-mobile-filters");
  var modal = document.getElementById("ptMatchModal");
  var backdrop = document.getElementById("ptMatchModalBackdrop");
  var closeBtn = document.getElementById("ptMatchModalClose");
  var form = document.getElementById("ptMatchMiniForm");
  var matchBtns = document.querySelectorAll("#PW .pt-p4-btn-match");
  var filterSelects = filtersForm ? filtersForm.querySelectorAll("select") : [];
  var filtersApplied = false;

  function isMobile() {
    try {
      return window.matchMedia(MQ).matches;
    } catch (e) {
      return false;
    }
  }

  function hasAppliedFiltersInUrl() {
    try {
      var url = new URL(window.location.href);
      return ["species", "judet", "marime", "varsta", "varsta_band", "sex", "traits"].some(function (k) {
        return url.searchParams.getAll(k).some(function (v) {
          return !!(v || "").trim();
        });
      });
    } catch (e2) {
      return false;
    }
  }

  function setMobileFiltersBtnState(active) {
    filtersApplied = !!active;
    Array.prototype.forEach.call(mobileFiltersBtns, function (btn) {
      if (!btn) return;
      if (filtersApplied) {
        btn.textContent = "Resetează filtre";
        btn.classList.add("pt-filters-btn--active");
      } else {
        btn.textContent = "Filtre";
        btn.classList.remove("pt-filters-btn--active");
      }
    });
  }

  function countCheckedTraitsInForm() {
    if (!form) return 0;
    var n = 0;
    Array.prototype.forEach.call(form.querySelectorAll('input[type="checkbox"]'), function (inp) {
      if (inp.checked) n++;
    });
    return n;
  }

  function readSelectedTraits() {
    try {
      var raw = window.localStorage.getItem("ptMatchTraits");
      if (!raw) return [];
      var parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  }

  var defaultMatchText = matchBtns.length ? (matchBtns[0].textContent || "").trim() : "";
  var defaultMatchTitle = matchBtns.length ? matchBtns[0].getAttribute("title") || "" : "";
  var isActive = readSelectedTraits().length > 0;

  function setMatchBtnActive(active) {
    Array.prototype.forEach.call(matchBtns, function (matchBtn) {
      if (!matchBtn) return;
      if (active) {
        matchBtn.textContent = "Renunță la potrivire";
        matchBtn.setAttribute("title", "Apasă pentru a renunța la potrivire și a reseta bifele");
        matchBtn.setAttribute("aria-label", "Renunță la potrivire");
        matchBtn.classList.add("pt-match-btn--active");
      } else {
        matchBtn.textContent = defaultMatchText || "Găsește-mi perechea";
        if (defaultMatchTitle) matchBtn.setAttribute("title", defaultMatchTitle);
        else matchBtn.removeAttribute("title");
        matchBtn.setAttribute("aria-label", defaultMatchText || "Găsește-mi perechea");
        matchBtn.classList.remove("pt-match-btn--active");
      }
    });
  }

  function syncMatchBtnFromTraits() {
    setMatchBtnActive(isActive || countCheckedTraitsInForm() > 0);
  }

  function openModal() {
    if (isMobile() || !modal) return;
    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    try {
      var raw = window.localStorage.getItem("ptMatchTraits");
      var selected = raw ? JSON.parse(raw) || [] : [];
      var selectedSet = new Set(selected);
      modal.querySelectorAll('input[type="checkbox"]').forEach(function (inp) {
        inp.checked = selectedSet.has(inp.name);
      });
    } catch (e) {}
    syncMatchBtnFromTraits();
  }

  function closeModal() {
    if (!modal) return;
    modal.hidden = true;
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  setMobileFiltersBtnState(hasAppliedFiltersInUrl());
  syncMatchBtnFromTraits();

  if (filtersForm) {
    filterSelects.forEach(function (sel) {
      sel.addEventListener("change", function () {
        if (!isMobile()) filtersForm.submit();
      });
    });
  }

  Array.prototype.forEach.call(matchBtns, function (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      if (isActive) {
        try {
          window.localStorage.removeItem("ptMatchTraits");
        } catch (err) {}
        isActive = false;
        setMatchBtnActive(false);
        closeModal();
        window.location.href = window.location.pathname + (window.location.search || "");
        return;
      }
      if (countCheckedTraitsInForm() > 0) {
        Array.prototype.forEach.call(form ? form.querySelectorAll('input[type="checkbox"]') : [], function (inp) {
          inp.checked = false;
        });
        syncMatchBtnFromTraits();
        closeModal();
        return;
      }
      openModal();
    });
  });

  Array.prototype.forEach.call(mobileFiltersBtns, function (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      if (!isMobile()) return;
      if (filtersApplied && filtersForm && filtersForm.action) {
        window.location.href = filtersForm.action;
        return;
      }
      if (filtersForm && filtersForm.action) window.location.href = filtersForm.action;
    });
  });

  if (backdrop) backdrop.addEventListener("click", closeModal);
  if (closeBtn) closeBtn.addEventListener("click", closeModal);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && modal && !modal.hidden) closeModal();
  });

  if (form) {
    form.addEventListener("change", function (ev) {
      if (ev.target && ev.target.matches && ev.target.matches('input[type="checkbox"]')) syncMatchBtnFromTraits();
    });
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      try {
        var selected = [];
        form.querySelectorAll('input[type="checkbox"]').forEach(function (inp) {
          if (inp.checked) selected.push(inp.name);
        });
        window.localStorage.setItem("ptMatchTraits", JSON.stringify(selected));
        var url = new URL(window.location.href);
        url.searchParams.delete("traits");
        selected.forEach(function (t) {
          url.searchParams.append("traits", t);
        });
        window.location.href = url.toString();
      } catch (err) {}
    });
  }

  (function () {
    try {
      var url = new URL(window.location.href);
      if (url.searchParams.has("traits")) {
        url.searchParams.delete("traits");
        window.history.replaceState({}, document.title, url.pathname + (url.search ? url.search : ""));
      }
    } catch (e) {}
  })();

  function normalizeSexOptions(selectEl) {
    if (!selectEl) return;
    Array.prototype.forEach.call(selectEl.querySelectorAll("option"), function (opt) {
      var v = (opt.value || "").toLowerCase();
      if (v === "m") opt.textContent = "MASCUL";
      if (v === "f") opt.textContent = "FEMELA";
    });
  }

  function shrinkSelectFontToFit(selectEl) {
    if (!selectEl) return;
    var base = parseFloat(getComputedStyle(selectEl).fontSize) || 14;
    var min = 10;
    selectEl.style.fontSize = base + "px";
    for (var i = 0; i < 14; i++) {
      if ((selectEl.scrollWidth || 0) <= (selectEl.clientWidth || 0) + 2) break;
      base = Math.max(min, base - 0.5);
      selectEl.style.fontSize = base + "px";
      if (base <= min) break;
    }
  }

  function initSexSelect() {
    var sel = document.getElementById("id_sex_pt");
    if (!sel) return;
    normalizeSexOptions(sel);
    shrinkSelectFontToFit(sel);
  }

  function observeSexSelect() {
    var sel = document.getElementById("id_sex_pt");
    if (!sel || !window.MutationObserver) return;
    new MutationObserver(function () {
      normalizeSexOptions(sel);
      shrinkSelectFontToFit(sel);
    }).observe(sel, { childList: true, subtree: true });
  }

  var sexResizeT = null;
  function scheduleInitSexSelect() {
    clearTimeout(sexResizeT);
    sexResizeT = setTimeout(function () {
      sexResizeT = null;
      requestAnimationFrame(initSexSelect);
    }, 220);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initSexSelect();
      observeSexSelect();
    });
  } else {
    initSexSelect();
    observeSexSelect();
  }
  window.addEventListener("resize", scheduleInitSexSelect);
})();
