(function () {
	"use strict";
	var banner = document.getElementById("population-org-banner");
	if (!banner || banner.getAttribute("data-banner-mode") !== "intermittent") return;

	var hiddenMs = (parseInt(banner.getAttribute("data-hidden-sec"), 10) || 600) * 1000;
	var visibleMs = (parseInt(banner.getAttribute("data-visible-sec"), 10) || 5) * 1000;
	var userId = banner.getAttribute("data-user-id") || "0";
	var storageKey = "eu_pop_banner_anchor_" + userId;
	var anchor = parseInt(localStorage.getItem(storageKey) || "0", 10);
	if (!anchor) {
		anchor = Date.now();
		try {
			localStorage.setItem(storageKey, String(anchor));
		} catch (e) {}
	}

	var cycleMs = hiddenMs + visibleMs;

	function syncBannerVisibility() {
		var elapsed = (Date.now() - anchor) % cycleMs;
		var show = elapsed >= hiddenMs;
		banner.classList.toggle("is-pop-collapsed", !show);
	}

	syncBannerVisibility();
	window.setInterval(syncBannerVisibility, 250);
})();
