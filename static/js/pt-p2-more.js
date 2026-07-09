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
  var lastScrollAt = 0;
  var autoChainCount = 0;
  var maxAutoChain = 2;
  var userScrolledSinceChain = true;
  var phoneUserScrolledDown = false;
  var userBusyUntil = 0;
  var touchDevice =
    ("matchMedia" in window && window.matchMedia("(hover: none), (pointer: coarse)").matches) ||
    "ontouchstart" in window;
  var phoneMode = (window.innerWidth || document.documentElement.clientWidth || 0) <= 767.98;
  var landscapeTouchPhone = false;
  try {
    landscapeTouchPhone =
      touchDevice &&
      window.matchMedia("(orientation: landscape) and (max-height: 34em)").matches;
  } catch (eLand) {
    landscapeTouchPhone = false;
  }

  // Portrait touch: lot inițial fără auto-load. Landscape touch: scroll P2 + p2-more activ.
  if ((phoneMode || touchDevice) && !landscapeTouchPhone) {
    sentinel.setAttribute("hidden", "");
    return;
  }

  function isPhone() {
    if (window.euadoptPtIsPhone) return window.euadoptPtIsPhone();
    return (window.innerWidth || document.documentElement.clientWidth || 0) <= 767.98;
  }

  function markUserBusy(ms) {
    var until = Date.now() + ms;
    if (until > userBusyUntil) userBusyUntil = until;
    if (until > tapNavUntil) tapNavUntil = until;
    window.__ptUserBusyUntil = userBusyUntil;
    abortFetch();
    clearTimeout(scrollProbeT);
    scrollProbeT = null;
    if (io) {
      try {
        io.disconnect();
      } catch (e) {}
      io = null;
    }
  }

  function phoneCanLoad() {
    if (!phoneUserScrolledDown) return false;
    if (Date.now() < userBusyUntil) return false;
    if (Date.now() < tapNavUntil) return false;
    if (Date.now() - lastScrollAt < 700) return false;
    return true;
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
    return isPhone() ? 24 : 400;
  }

  function maxAutoChainAllowed() {
    return isPhone() ? 0 : maxAutoChain;
  }

  function currentScrollTop() {
    if (isPhone()) {
      return window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
    }
    return scrollEl.scrollTop;
  }

  function sentinelNearVisibleEdge() {
    if (!sentinel || !sentinel.isConnected || !hasMore) return false;
    if (isPhone() && !phoneCanLoad()) return false;
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
    if (isPhone()) return;
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

  function appendChunk(html) {
    var wrap = document.createElement("div");
    wrap.innerHTML = html || "";
    if (window.euadoptInitPetImageRotation) window.euadoptInitPetImageRotation(wrap);
    while (wrap.firstChild) grid.appendChild(wrap.firstChild);
    if (window.euadoptWishlistBindRoot) window.euadoptWishlistBindRoot(grid);
  }

  function loadMore() {
    if (loading || !hasMore || Date.now() < tapNavUntil) return;
    if (isPhone() && !phoneCanLoad()) return;
    var chainMax = maxAutoChainAllowed();
    if (!userScrolledSinceChain && autoChainCount >= chainMax) return;
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
        if (isPhone() && Date.now() < userBusyUntil) throw new Error("aborted-user");
        var html = data.html || "";
        if (isPhone()) {
          return new Promise(function (resolve) {
            requestAnimationFrame(function () {
              if (Date.now() < userBusyUntil) {
                resolve(false);
                return;
              }
              appendChunk(html);
              resolve(data);
            });
          });
        }
        appendChunk(html);
        return data;
      })
      .then(function (data) {
        if (!data) return false;
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
        if (!ok || !hasMore || isPhone()) return;
        requestAnimationFrame(function () {
          setupIo();
          if (!loading && hasMore && sentinelNearVisibleEdge()) {
            if (autoChainCount < maxAutoChainAllowed()) {
              autoChainCount++;
              userScrolledSinceChain = false;
              loadMore();
            }
          }
        });
      });
  }

  function scheduleScrollProbe() {
    if (!hasMore || loading) return;
    if (isPhone() && !phoneUserScrolledDown) return;
    clearTimeout(scrollProbeT);
    var wait = isPhone() ? 750 : 180;
    scrollProbeT = setTimeout(function () {
      scrollProbeT = null;
      if (!loading && hasMore && sentinelNearVisibleEdge()) loadMore();
    }, wait);
  }

  function onScroll() {
    lastScrollAt = Date.now();
    var st = currentScrollTop();
    if (isPhone() && st > 220) phoneUserScrolledDown = true;
    if (Math.abs(st - lastScrollTop) > 12) {
      userScrolledSinceChain = true;
      autoChainCount = 0;
    }
    lastScrollTop = st;
    scheduleScrollProbe();
  }

  if (isPhone()) {
    document.addEventListener(
      "touchstart",
      function () {
        markUserBusy(2800);
      },
      { passive: true }
    );
    document.addEventListener(
      "pointerdown",
      function () {
        markUserBusy(2800);
      },
      { passive: true }
    );
    window.addEventListener("scroll", onScroll, { passive: true });
  } else {
    scrollEl.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("scroll", onScroll, { passive: true });
    setupIo();
    requestAnimationFrame(function () {
      requestAnimationFrame(scheduleScrollProbe);
    });
  }

  window.addEventListener("pagehide", abortFetch);
  var ioResizeT = null;
  window.addEventListener("resize", function () {
    clearTimeout(scrollProbeT);
    clearTimeout(ioResizeT);
    autoChainCount = 0;
    userScrolledSinceChain = true;
    ioResizeT = setTimeout(function () {
      ioResizeT = null;
      if (hasMore && !isPhone()) setupIo();
    }, 350);
  });
})();
