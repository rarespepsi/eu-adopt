(function () {
  "use strict";

  function isLandscapeTouch() {
    if (!("matchMedia" in window)) return false;
    var touch =
      window.matchMedia("(hover: none), (pointer: coarse)").matches || "ontouchstart" in window;
    return touch && window.matchMedia("(orientation: landscape) and (max-height: 34em)").matches;
  }

  if (!isLandscapeTouch()) return;

  function syncP2RowHeight() {
    var scroll = document.querySelector("#PW .pt-p2-scroll");
    if (!scroll) return;
    var h = scroll.getBoundingClientRect().height;
    if (h > 0) {
      document.body.style.setProperty("--p2-row-h", Math.max(64, Math.floor((h - 4) / 2)) + "px");
    }
  }

  function syncLandChromeHeights() {
    var nav = document.getElementById("A0");
    var banner = document.getElementById("population-org-banner");
    var nh = nav ? Math.round(nav.getBoundingClientRect().height) : 64;
    document.body.style.setProperty("--nav-height", nh + "px");
    var bh = 0;
    if (banner && !banner.classList.contains("is-pop-collapsed")) {
      var br = banner.getBoundingClientRect();
      if (br.height > 0) bh = Math.round(br.height);
    }
    document.body.style.setProperty("--pt-land-banner", bh + "px");
    syncP2RowHeight();
  }

  function lockLandPageScroll() {
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";
  }

  syncLandChromeHeights();
  lockLandPageScroll();
  window.addEventListener("resize", syncLandChromeHeights);
  window.addEventListener("orientationchange", function () {
    setTimeout(function () {
      syncLandChromeHeights();
      syncP2RowHeight();
    }, 120);
  });
  if (typeof ResizeObserver !== "undefined") {
    var p2Scroll = document.querySelector("#PW .pt-p2-scroll");
    if (p2Scroll) {
      var ro = new ResizeObserver(function () {
        syncP2RowHeight();
      });
      ro.observe(p2Scroll);
    }
  }

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

  function clearStuckUiState() {
    document.body.style.overflow = "";
    document.documentElement.style.overflow = "";
    if (modal && modal.hidden) {
      modal.setAttribute("aria-hidden", "true");
    }
  }

  clearStuckUiState();
  lockLandPageScroll();
  window.addEventListener("pageshow", function () {
    clearStuckUiState();
    lockLandPageScroll();
    syncLandChromeHeights();
  });

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
      btn.textContent = label;
      btn.classList.toggle("pt-filters-btn--active", filtersApplied || label !== base);
    });
  }

  function closeMobileFilters() {
    if (!p4Cell) return;
    p4Cell.classList.remove("pt-mobile-filters-open");
    document.body.classList.remove("pt-land-filters-open");
  }

  function openMobileFilters() {
    if (!p4Cell) return;
    p4Cell.classList.add("pt-mobile-filters-open");
    document.body.classList.add("pt-land-filters-open");
    syncLandChromeHeights();
    syncSpeciesTabsFromField();
  }

  function submitFilters() {
    if (!filtersForm) return;
    var keepOpen = filtersForm.querySelector('input[name="pt_filters_open"]');
    if (!keepOpen) {
      keepOpen = document.createElement("input");
      keepOpen.type = "hidden";
      keepOpen.name = "pt_filters_open";
      filtersForm.appendChild(keepOpen);
    }
    keepOpen.value = "1";
    filtersForm.submit();
  }

  function reopenFiltersIfRequested() {
    try {
      var url = new URL(window.location.href);
      if (url.searchParams.get("pt_filters_open") !== "1") return;
      openMobileFilters();
      url.searchParams.delete("pt_filters_open");
      var qs = url.searchParams.toString();
      window.history.replaceState({}, document.title, url.pathname + (qs ? "?" + qs : ""));
    } catch (e) {}
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

  function closeModal() {
    if (!modal) return;
    modal.hidden = true;
    modal.setAttribute("aria-hidden", "true");
    lockLandPageScroll();
  }

  function openModal() {
    if (!modal) return;
    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    lockLandPageScroll();
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

  setMobileFiltersBtnState(hasAppliedFiltersInUrl());
  syncMatchBtnFromTraits();
  reopenFiltersIfRequested();

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
      if (!p4Cell || !p4Cell.classList.contains("pt-mobile-filters-open")) return;
      e.preventDefault();
      var sf = document.getElementById("pt_filter_species_field");
      if (sf) sf.value = a.getAttribute("data-pt-species") || "";
      syncSpeciesTabsFromField();
      submitFilters();
    });
    var resetA = filtersForm ? filtersForm.querySelector("a.p3-reset-link") : null;
    if (resetA) {
      resetA.addEventListener("click", function (e) {
        if (!p4Cell || !p4Cell.classList.contains("pt-mobile-filters-open")) return;
        e.preventDefault();
        window.location.href = resetA.getAttribute("href") || (filtersForm ? filtersForm.action : window.location.pathname);
      });
    }
  })();

  if (filtersForm) {
    filterSelects.forEach(function (sel) {
      sel.addEventListener("change", function () {
        if (!p4Cell || !p4Cell.classList.contains("pt-mobile-filters-open")) return;
        submitFilters();
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
      if (p4Cell && p4Cell.classList.contains("pt-mobile-filters-open")) {
        closeMobileFilters();
        return;
      }
      openMobileFilters();
    });
  });

  if (mobileFiltersCloseBtn) {
    mobileFiltersCloseBtn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      closeMobileFilters();
    });
  }
  if (mobileFiltersOkBtn) {
    mobileFiltersOkBtn.addEventListener("click", function () {
      if (filtersForm) filtersForm.submit();
    });
  }
  if (closeBtn) {
    closeBtn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      closeModal();
    });
  }
  if (backdrop) {
    backdrop.addEventListener("click", function (e) {
      e.preventDefault();
      closeModal();
    });
  }

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
})();
