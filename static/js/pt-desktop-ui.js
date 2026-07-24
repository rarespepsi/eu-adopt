(function () {
  "use strict";
  var touchDevice =
    ("matchMedia" in window && window.matchMedia("(hover: none), (pointer: coarse)").matches) ||
    "ontouchstart" in window;
  if (touchDevice) return;
  var filtersForm = document.getElementById("filtre-animale");
  var mobileFiltersCloseBtn = document.getElementById("ptMobileFiltersClose");
  var mobileFiltersOkBtn = document.getElementById("ptMobileFiltersOk");
  var mobileFiltersBtns = document.querySelectorAll("#PW .js-pt-mobile-filters");
  var p4Cell = document.getElementById("P4");
  var modal = document.getElementById("ptMatchModal");
  var backdrop = document.getElementById("ptMatchModalBackdrop");
  var closeBtn = document.getElementById("ptMatchModalClose");
  var form = document.getElementById("ptMatchMiniForm");
  var matchBtns = document.querySelectorAll("#PW .pt-p4-btn-match");
  var filterSelects = filtersForm ? filtersForm.querySelectorAll("select") : [];
  var filtersApplied = false;

  function isPhone() {
    if (!touchDevice) return false;
    if (!("matchMedia" in window)) return true;
    return window.matchMedia("(orientation: portrait)").matches;
  }

  function hasAppliedFiltersInUrl() {
    try {
      var url = new URL(window.location.href);
      return ["species", "country", "judet", "marime", "varsta", "varsta_band", "sex", "traits"].some(function (k) {
        return url.searchParams.getAll(k).some(function (v) {
          return !!(v || "").trim();
        });
      });
    } catch (e2) {
      return false;
    }
  }

  function getSpeciesLabel() {
    var root = document.getElementById("PW");
    var eu = root && root.getAttribute("data-pt-eu") === "1";
    var sf = document.getElementById("pt_filter_species_field");
    var v = (sf && sf.value ? sf.value : "").trim().toLowerCase();
    if (eu) {
      if (v === "dog") return root.getAttribute("data-pt-lbl-filters-dog") || "Dog filters";
      if (v === "cat") return root.getAttribute("data-pt-lbl-filters-cat") || "Cat filters";
      if (v === "other") return root.getAttribute("data-pt-lbl-filters-other") || "Other filters";
      return root.getAttribute("data-pt-lbl-filters") || "Filters";
    }
    if (v === "dog") return "Filtre caini";
    if (v === "cat") return "Filtre pisici";
    if (v === "other") return "Filtre altele";
    return "Filtre";
  }

  function filtersBaseLabel() {
    var root = document.getElementById("PW");
    if (root && root.getAttribute("data-pt-eu") === "1") {
      return root.getAttribute("data-pt-lbl-filters") || "Filters";
    }
    return "Filtre";
  }

  function setMobileFiltersBtnState(active) {
    filtersApplied = !!active;
    var label = getSpeciesLabel();
    var base = filtersBaseLabel();
    Array.prototype.forEach.call(mobileFiltersBtns, function (btn) {
      if (!btn) return;
      if (filtersApplied || label !== base) {
        btn.textContent = label;
        btn.classList.add("pt-filters-btn--active");
      } else {
        btn.textContent = label;
        btn.classList.remove("pt-filters-btn--active");
      }
    });
  }

  function closeMobileFilters() {
    if (!p4Cell) return;
    p4Cell.classList.remove("pt-mobile-filters-open");
  }

  function openMobileFilters() {
    if (!p4Cell || !isPhone()) return;
    p4Cell.classList.add("pt-mobile-filters-open");
    var box = p4Cell.querySelector(".pt-p4-box-filters");
    if (box && box.scrollIntoView) {
      try {
        box.scrollIntoView({ behavior: "smooth", block: "nearest" });
      } catch (e) {}
    }
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
    if (!modal) return;
    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    if (!isPhone()) document.body.style.overflow = "hidden";
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
        if (isPhone()) return;
        filtersForm.submit();
      });
    });
  }

  function syncSpeciesTabsFromField() {
    var sf = document.getElementById("pt_filter_species_field");
    var list = document.getElementById("pt_animal_filter_tabs");
    if (!sf || !list) return;
    var v = (sf.value || "").trim().toLowerCase();
    var want = v === "dog" || v === "cat" || v === "other" ? v : "";
    var links = list.querySelectorAll("a[data-pt-species]");
    Array.prototype.forEach.call(links, function (a) {
      var sp = (a.getAttribute("data-pt-species") || "").trim().toLowerCase();
      if (want === "") a.classList.toggle("active", sp === "");
      else a.classList.toggle("active", sp === want);
    });
    setMobileFiltersBtnState(hasAppliedFiltersInUrl());
  }

  (function () {
    var tabList = document.getElementById("pt_animal_filter_tabs");
    if (!tabList) return;
    tabList.addEventListener("click", function (e) {
      var a = e.target.closest("a[data-pt-species]");
      if (!a || !tabList.contains(a)) return;
      if (!isPhone() || !p4Cell || !p4Cell.classList.contains("pt-mobile-filters-open")) return;
      e.preventDefault();
      var sf = document.getElementById("pt_filter_species_field");
      if (sf) sf.value = a.getAttribute("data-pt-species") || "";
      syncSpeciesTabsFromField();
    });
    var resetA = filtersForm ? filtersForm.querySelector("a.p3-reset-link") : null;
    if (resetA) {
      resetA.addEventListener("click", function (e) {
        if (!isPhone() || !p4Cell || !p4Cell.classList.contains("pt-mobile-filters-open")) return;
        e.preventDefault();
        Array.prototype.forEach.call(filterSelects, function (sel) {
          sel.selectedIndex = 0;
        });
        var sf = document.getElementById("pt_filter_species_field");
        if (sf) sf.value = "";
        syncSpeciesTabsFromField();
      });
    }
  })();

  Array.prototype.forEach.call(matchBtns, function (btn) {
    btn.addEventListener("click", function (e) {
      if (!isPhone()) return;
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
      if (!isPhone()) return;
      if (filtersApplied) {
        window.location.href = filtersForm ? filtersForm.action || window.location.pathname : window.location.pathname;
        return;
      }
      if (p4Cell && p4Cell.classList.contains("pt-mobile-filters-open")) {
        closeMobileFilters();
        return;
      }
      openMobileFilters();
    });
  });

  if (mobileFiltersCloseBtn) {
    mobileFiltersCloseBtn.addEventListener("click", function () {
      closeMobileFilters();
    });
  }
  if (mobileFiltersOkBtn) {
    mobileFiltersOkBtn.addEventListener("click", function () {
      if (filtersForm) filtersForm.submit();
    });
  }

  if (backdrop) backdrop.addEventListener("click", closeModal);
  if (closeBtn) closeBtn.addEventListener("click", closeModal);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      if (p4Cell && p4Cell.classList.contains("pt-mobile-filters-open")) {
        closeMobileFilters();
        return;
      }
      if (modal && !modal.hidden) closeModal();
    }
  });

  window.addEventListener("resize", function () {
    if (!isPhone()) closeMobileFilters();
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
