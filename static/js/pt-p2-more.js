(function () {
  "use strict";
  var grid = document.getElementById("pt_p2_grid");
  var sentinel = document.getElementById("pt_p2_load_sentinel");
  var scrollEl = document.querySelector("#P2 .pt-p2-scroll");
  if (!grid || !sentinel || !scrollEl) return;
  var baseUrl = grid.getAttribute("data-p2-more-url") || "";
  if (!baseUrl) return;
  var loading = false;
  var hasMore = grid.getAttribute("data-p2-has-more") === "1";
  var nextOffset = parseInt(grid.getAttribute("data-p2-offset") || "0", 10) || 0;
  if (!hasMore) return;
  var io = null;
  var fetchAbort = null;
  var tapNavUntil = 0;
  var scrollProbeT = null;
  var lastScrollTop = 0;
  var autoChainCount = 0;
  var maxAutoChain = 2;
  var userScrolledSinceChain = true;

  function isPhone() {
    if (window.euadoptPtIsPhone) return window.euadoptPtIsPhone();
    return Math.min(window.innerWidth || 0, window.innerHeight || 0) <= 767.98;
  }

  function buildPageUrl() {
    var u = new URL(baseUrl, window.location.origin);
    var cur = new URLSearchParams(window.location.search);
    cur.forEach(function (value, key) {
      if (key === "go") return;
      u.searchParams.append(key, value);
    });
    u.searchParams.set("offset", String(nextOffset));
    return u.toString();
  }

  function finish() {
    hasMore = false;
    sentinel.setAttribute("hidden", "");
    if (io) io.disconnect();
  }

  function pickIoRoot() {
    if (isPhone()) return null;
    try {
      var oy = window.getComputedStyle(scrollEl).overflowY;
      if (oy !== "auto" && oy !== "scroll" && oy !== "overlay") return null;
      return scrollEl;
    } catch (e) {
      return null;
    }
  }

  function scrollMargin() {
    return isPhone() ? 420 : 400;
  }

  function currentScrollTop() {
    if (isPhone()) {
      return window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
    }
    return scrollEl.scrollTop;
  }

  function sentinelNearVisibleEdge() {
    if (!sentinel || !sentinel.isConnected || !hasMore) return false;
    var margin = scrollMargin();
    var r = sentinel.getBoundingClientRect();
    var root = pickIoRoot();
    if (root) {
      var b = root.getBoundingClientRect();
      return r.top <= b.bottom + margin && r.bottom >= b.top - margin;
    }
    var vh = window.innerHeight || document.documentElement.clientHeight || 0;
    return r.top <= vh + margin && r.bottom >= -margin;
  }

  function abortFetch() {
    if (fetchAbort) {
      try {
        fetchAbort.abort();
      } catch (eA) {}
      fetchAbort = null;
    }
    loading = false;
  }

  function setupIo() {
    if (io) {
      try {
        io.disconnect();
      } catch (e) {}
      io = null;
    }
    if (!hasMore) return;
    io = new IntersectionObserver(
      function (entries) {
        if (Date.now() < tapNavUntil) return;
        for (var i = 0; i < entries.length; i++) {
          if (entries[i].isIntersecting) loadMore();
        }
      },
      { root: pickIoRoot(), rootMargin: scrollMargin() + "px", threshold: 0 }
    );
    io.observe(sentinel);
  }

  function loadMore() {
    if (loading || !hasMore || Date.now() < tapNavUntil) return;
    if (!userScrolledSinceChain && autoChainCount >= maxAutoChain) return;
    loading = true;
    abortFetch();
    fetchAbort = typeof AbortController !== "undefined" ? new AbortController() : null;
    var fetchOpts = { credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" } };
    if (fetchAbort) fetchOpts.signal = fetchAbort.signal;
    fetch(buildPageUrl(), fetchOpts)
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.ok) throw new Error("p2-more");
        var wrap = document.createElement("div");
        wrap.innerHTML = data.html || "";
        if (window.euadoptInitPetImageRotation) window.euadoptInitPetImageRotation(wrap);
        while (wrap.firstChild) grid.appendChild(wrap.firstChild);
        if (window.euadoptWishlistBindRoot) window.euadoptWishlistBindRoot(grid);
        hasMore = !!data.has_more;
        nextOffset = parseInt(data.next_offset, 10) || nextOffset;
        grid.setAttribute("data-p2-offset", String(nextOffset));
        grid.setAttribute("data-p2-has-more", hasMore ? "1" : "0");
        if (!hasMore) finish();
        return true;
      })
      .catch(function (err) {
        if (err && err.name === "AbortError") return false;
        return false;
      })
      .finally(function () {
        loading = false;
        fetchAbort = null;
      })
      .then(function (ok) {
        if (ok && hasMore) {
          requestAnimationFrame(function () {
            setupIo();
            if (!loading && hasMore && sentinelNearVisibleEdge()) {
              if (autoChainCount < maxAutoChain) {
                autoChainCount++;
                userScrolledSinceChain = false;
                loadMore();
              }
            }
          });
        }
      });
  }

  function scheduleScrollProbe() {
    if (!hasMore || loading || Date.now() < tapNavUntil) return;
    clearTimeout(scrollProbeT);
    scrollProbeT = setTimeout(function () {
      scrollProbeT = null;
      if (!loading && hasMore && sentinelNearVisibleEdge()) loadMore();
    }, 120);
  }

  function onScroll() {
    var st = currentScrollTop();
    if (Math.abs(st - lastScrollTop) > 12) {
      userScrolledSinceChain = true;
      autoChainCount = 0;
    }
    lastScrollTop = st;
    scheduleScrollProbe();
  }

  function onUserTap(ev) {
    try {
      if (ev && ev.target && ev.target.closest && ev.target.closest(".pt-p2-card-link, .pt-p2-ask-plic-btn, .pt-p2-promo-btn, .pt-p2-card-bottom-bar__name")) {
        tapNavUntil = Date.now() + 400;
        autoChainCount = 0;
        userScrolledSinceChain = true;
        abortFetch();
        return true;
      }
    } catch (eTap) {}
    return false;
  }

  setupIo();
  requestAnimationFrame(function () {
    requestAnimationFrame(scheduleScrollProbe);
  });
  grid.addEventListener("touchstart", onUserTap, { passive: true, capture: true });
  grid.addEventListener("mousedown", onUserTap, { capture: true });
  scrollEl.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("pagehide", abortFetch);
  var ioResizeT = null;
  window.addEventListener("resize", function () {
    clearTimeout(scrollProbeT);
    clearTimeout(ioResizeT);
    autoChainCount = 0;
    userScrolledSinceChain = true;
    ioResizeT = setTimeout(function () {
      ioResizeT = null;
      if (hasMore) setupIo();
    }, 350);
  });
  try {
    if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  } catch (eSr) {}
})();
