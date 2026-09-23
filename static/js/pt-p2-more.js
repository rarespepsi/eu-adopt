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
  // Telefon portrait: loturi noi la apropierea de capăt (scroll pagină sau container).
  // Detecție lată: touch + portrait + lățime telefon — fără hover/pointer (unele browsere mint).
  var portraitPageScroll = false;
  try {
    var w0 = window.innerWidth || document.documentElement.clientWidth || 0;
    portraitPageScroll =
      touchDevice &&
      w0 <= 767.98 &&
      window.matchMedia("(orientation: portrait)").matches;
  } catch (ePort) {
    portraitPageScroll = false;
  }

  function isPhone() {
    if (window.euadoptPtIsPhone) return window.euadoptPtIsPhone();
    return (window.innerWidth || document.documentElement.clientWidth || 0) <= 767.98;
  }

  function markUserBusy(ms) {
    if (portraitPageScroll) return;
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
    if (io) {
      try {
        io.disconnect();
      } catch (eF) {}
      io = null;
    }
  }

  function pickIoRoot() {
    if (portraitPageScroll) return null;
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
    if (portraitPageScroll) return 900;
    return isPhone() ? 24 : 400;
  }

  function maxAutoChainAllowed() {
    if (portraitPageScroll) return 6;
    return isPhone() ? 0 : maxAutoChain;
  }

  function currentScrollTop() {
    var mw = document.getElementById("main_wrap");
    var mc = document.getElementById("main_content");
    var tops = [
      window.pageYOffset || 0,
      document.documentElement ? document.documentElement.scrollTop : 0,
      document.body ? document.body.scrollTop : 0,
      scrollEl ? scrollEl.scrollTop : 0,
      mw ? mw.scrollTop : 0,
      mc ? mc.scrollTop : 0,
    ];
    var max = 0;
    for (var i = 0; i < tops.length; i++) {
      if (tops[i] > max) max = tops[i];
    }
    return max;
  }

  function sentinelNearVisibleEdge() {
    if (!sentinel || !sentinel.isConnected || !hasMore) return false;
    if (isPhone() && !portraitPageScroll && !phoneCanLoad()) return false;
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
    if (isPhone() && !portraitPageScroll) return;
    if (io) {
      try {
        io.disconnect();
      } catch (e) {}
      io = null;
    }
    if (!hasMore || typeof IntersectionObserver === "undefined") return;
    io = new IntersectionObserver(
      function (entries) {
        if (!portraitPageScroll && Date.now() < tapNavUntil) return;
        for (var i = 0; i < entries.length; i++) {
          if (entries[i].isIntersecting) loadMore();
        }
      },
      { root: pickIoRoot(), rootMargin: scrollMargin() + "px 0px", threshold: 0 }
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
    if (loading || !hasMore) return;
    if (!portraitPageScroll && Date.now() < tapNavUntil) return;
    if (isPhone() && !portraitPageScroll && !phoneCanLoad()) return;
    var chainMax = maxAutoChainAllowed();
    if (!portraitPageScroll && !userScrolledSinceChain && autoChainCount >= chainMax) return;
    abortFetch();
    loading = true;
    fetchAbort = typeof AbortController !== "undefined" ? new AbortController() : null;
    var fetchOpts = { credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" } };
    if (fetchAbort) fetchOpts.signal = fetchAbort.signal;
    fetch(buildPageUrl(), fetchOpts)
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.ok) throw new Error("p2-more");
        if (isPhone() && !portraitPageScroll && Date.now() < userBusyUntil) {
          throw new Error("aborted-user");
        }
        var html = data.html || "";
        if (isPhone() && !portraitPageScroll) {
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
        if (!ok || !hasMore) return;
        if (portraitPageScroll) {
          requestAnimationFrame(function () {
            setupIo();
            if (!loading && hasMore && sentinelNearVisibleEdge()) {
              if (autoChainCount < maxAutoChainAllowed()) {
                autoChainCount++;
                loadMore();
              }
            }
          });
          return;
        }
        if (isPhone()) return;
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
    if (isPhone() && !portraitPageScroll && !phoneUserScrolledDown) return;
    clearTimeout(scrollProbeT);
    var wait = portraitPageScroll ? 120 : isPhone() ? 750 : 180;
    scrollProbeT = setTimeout(function () {
      scrollProbeT = null;
      if (!loading && hasMore && sentinelNearVisibleEdge()) loadMore();
    }, wait);
  }

  function onScroll() {
    lastScrollAt = Date.now();
    var st = currentScrollTop();
    if (isPhone() && st > 120) phoneUserScrolledDown = true;
    if (Math.abs(st - lastScrollTop) > 8) {
      userScrolledSinceChain = true;
      autoChainCount = 0;
    }
    lastScrollTop = st;
    scheduleScrollProbe();
  }

  function onPortraitScroll() {
    lastScrollAt = Date.now();
    phoneUserScrolledDown = true;
    userScrolledSinceChain = true;
    if (!hasMore || loading) {
      scheduleScrollProbe();
      return;
    }
    clearTimeout(scrollProbeT);
    scrollProbeT = setTimeout(function () {
      scrollProbeT = null;
      if (!loading && hasMore && sentinelNearVisibleEdge()) loadMore();
    }, 100);
  }

  function bindPortraitScrollTargets() {
    var opts = { passive: true, capture: true };
    var targets = [
      window,
      document,
      document.documentElement,
      document.body,
      document.getElementById("main_wrap"),
      document.getElementById("main_content"),
      document.getElementById("PW"),
      scrollEl,
    ];
    for (var i = 0; i < targets.length; i++) {
      var t = targets[i];
      if (!t || !t.addEventListener) continue;
      t.addEventListener("scroll", onPortraitScroll, opts);
    }
    document.addEventListener("touchmove", onPortraitScroll, { passive: true });
  }

  if (portraitPageScroll) {
    bindPortraitScrollTargets();
    setupIo();
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        onPortraitScroll();
        if (hasMore && sentinelNearVisibleEdge()) loadMore();
      });
    });
  } else if (isPhone()) {
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
      if (hasMore && (!isPhone() || portraitPageScroll)) setupIo();
    }, 350);
  });
})();
