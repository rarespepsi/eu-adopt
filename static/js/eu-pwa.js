(function () {
	"use strict";

	/* Temporar oprit — reactivare după test login PF invitat */
	var INSTALL_BANNER_ENABLED = false;

	function isStandalone() {
		try {
			if (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) return true;
		} catch (e) {}
		return !!window.navigator.standalone;
	}

	function isMobileTouch() {
		try {
			return window.matchMedia("(max-width: 900px) and (hover: none) and (pointer: coarse)").matches;
		} catch (e) {
			return window.innerWidth <= 900;
		}
	}

	if (!("serviceWorker" in navigator)) return;

	var swUrl = document.body && document.body.getAttribute("data-pwa-sw-url");
	if (!swUrl) return;

	window.addEventListener("load", function () {
		navigator.serviceWorker.register(swUrl, { scope: "/" }).catch(function () {});
	});

	if (!INSTALL_BANNER_ENABLED) return;

	if (isStandalone()) return;

	var deferredPrompt = null;
	var banner = document.getElementById("eu-pwa-install-banner");
	var btnInstall = document.getElementById("eu-pwa-install-btn");
	var btnDismiss = document.getElementById("eu-pwa-install-dismiss");
	var iosHint = document.getElementById("eu-pwa-ios-hint");

	function hideBanner() {
		if (banner) banner.hidden = true;
		try { sessionStorage.setItem("eu_pwa_install_dismissed", "1"); } catch (e) {}
	}

	if (banner && sessionStorage.getItem("eu_pwa_install_dismissed") === "1") {
		banner.hidden = true;
		return;
	}

	var isIos = /iphone|ipad|ipod/i.test(navigator.userAgent || "");
	var isSafari = isIos && !window.MSStream && !/crios|fxios|edgios/i.test(navigator.userAgent || "");

	window.addEventListener("beforeinstallprompt", function (e) {
		if (!isMobileTouch()) return;
		e.preventDefault();
		deferredPrompt = e;
		if (banner) banner.hidden = false;
		if (iosHint) iosHint.hidden = true;
	});

	if (btnInstall) {
		btnInstall.addEventListener("click", function () {
			if (!deferredPrompt) return;
			deferredPrompt.prompt();
			deferredPrompt.userChoice.finally(function () {
				deferredPrompt = null;
				hideBanner();
			});
		});
	}

	if (btnDismiss) {
		btnDismiss.addEventListener("click", hideBanner);
	}

	if (isSafari && isMobileTouch() && banner && sessionStorage.getItem("eu_pwa_install_dismissed") !== "1") {
		banner.hidden = false;
		if (iosHint) iosHint.hidden = false;
		if (btnInstall) btnInstall.hidden = true;
	}
})();
