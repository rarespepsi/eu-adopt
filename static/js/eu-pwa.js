(function () {
	"use strict";

	var WEEK_MS = 7 * 24 * 60 * 60 * 1000;
	var FIRST_LOGINS = 5;
	var PULSE_COOKIE = "eu_pwa_login_pulse";
	var STORAGE_PREFIX = "eu_pwa_prompt_v1:";

	function isStandalone() {
		try {
			if (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) return true;
		} catch (e) {}
		return !!window.navigator.standalone;
	}

	function isMobileTouch() {
		var ua = navigator.userAgent || "";
		if (/Android|iPhone|iPad|iPod|Mobile|webOS|IEMobile/i.test(ua) && window.innerWidth <= 1100) {
			return true;
		}
		try {
			if (window.matchMedia("(max-width: 900px) and (hover: none) and (pointer: coarse)").matches) {
				return true;
			}
			if (window.matchMedia("(max-width: 900px) and (pointer: coarse)").matches) {
				return true;
			}
		} catch (e) {}
		return window.innerWidth <= 900 && ("ontouchstart" in window || navigator.maxTouchPoints > 0);
	}

	function getCookie(name) {
		var m = document.cookie.match(
			new RegExp("(?:^|; )" + name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "=([^;]*)")
		);
		return m ? decodeURIComponent(m[1]) : "";
	}

	function clearCookie(name) {
		document.cookie = name + "=; Max-Age=0; path=/; SameSite=Lax";
	}

	function storageKey() {
		var uid = (document.body && document.body.getAttribute("data-user-id")) || "";
		return STORAGE_PREFIX + (uid || "anon");
	}

	function readState() {
		try {
			var raw = localStorage.getItem(storageKey());
			if (!raw) return { loginCount: 0, lastShownAt: 0, installed: false };
			var o = JSON.parse(raw);
			return {
				loginCount: Math.max(0, parseInt(o.loginCount, 10) || 0),
				lastShownAt: parseInt(o.lastShownAt, 10) || 0,
				installed: !!o.installed,
			};
		} catch (e) {
			return { loginCount: 0, lastShownAt: 0, installed: false };
		}
	}

	function writeState(st) {
		try {
			localStorage.setItem(
				storageKey(),
				JSON.stringify({
					loginCount: st.loginCount,
					lastShownAt: st.lastShownAt,
					installed: !!st.installed,
				})
			);
		} catch (e) {}
	}

	function shouldShowAfterLogin(st) {
		if (st.installed) return false;
		if (st.loginCount <= FIRST_LOGINS) return true;
		if (!st.lastShownAt) return true;
		return Date.now() - st.lastShownAt >= WEEK_MS;
	}

	/* SW registration — independent of banner UI */
	var swUrl = document.body && document.body.getAttribute("data-pwa-sw-url");
	if (swUrl && "serviceWorker" in navigator) {
		window.addEventListener("load", function () {
			navigator.serviceWorker.register(swUrl, { scope: "/" }).catch(function () {});
		});
	}

	if (isStandalone()) {
		var stInstalled = readState();
		if (!stInstalled.installed) {
			stInstalled.installed = true;
			writeState(stInstalled);
		}
		return;
	}

	var banner = document.getElementById("eu-pwa-install-banner");
	var btnInstall = document.getElementById("eu-pwa-install-btn");
	var btnDismiss = document.getElementById("eu-pwa-install-dismiss");
	var iosHint = document.getElementById("eu-pwa-ios-hint");
	if (!banner) return;

	var deferredPrompt = null;
	var isIos = /iphone|ipad|ipod/i.test(navigator.userAgent || "");
	var authenticated =
		document.body && document.body.getAttribute("data-user-authenticated") === "true";

	function hideBanner() {
		banner.hidden = true;
		banner.setAttribute("aria-hidden", "true");
	}

	function showBanner() {
		banner.hidden = false;
		banner.style.display = "";
		banner.removeAttribute("aria-hidden");
		if (btnInstall) {
			btnInstall.hidden = false;
			btnInstall.removeAttribute("hidden");
		}
		if (iosHint) {
			if (deferredPrompt) {
				iosHint.hidden = true;
			} else {
				iosHint.hidden = false;
				iosHint.textContent = isIos
					? "iPhone: Share → Adaugă pe ecranul principal"
					: "Meniu browser (⋮) → Instalează aplicația / Add to Home screen";
			}
		}
	}

	function markShown(st) {
		st.lastShownAt = Date.now();
		writeState(st);
	}

	function markInstalled() {
		var st = readState();
		st.installed = true;
		writeState(st);
		hideBanner();
	}

	function showManualInstallTip() {
		if (iosHint) {
			iosHint.hidden = false;
			iosHint.textContent = isIos
				? "iPhone: Share → Adaugă pe ecranul principal"
				: "Meniu browser (⋮) → Instalează aplicația / Add to Home screen";
			iosHint.style.color = "#fde68a";
			iosHint.style.fontWeight = "700";
		}
		try {
			window.alert(
				isIos
					? "Da — pe iPhone: Share → Adaugă pe ecranul principal."
					: "Da — deschide meniul browser (⋮) și alege Instalează aplicația / Add to Home screen."
			);
		} catch (e) {}
	}

	window.addEventListener("beforeinstallprompt", function (e) {
		if (!isMobileTouch()) return;
		e.preventDefault();
		deferredPrompt = e;
		if (!banner.hidden) {
			if (btnInstall) btnInstall.hidden = false;
			if (iosHint) iosHint.hidden = true;
		}
	});

	window.addEventListener("appinstalled", function () {
		markInstalled();
	});

	if (btnInstall) {
		btnInstall.addEventListener("click", function () {
			if (deferredPrompt) {
				deferredPrompt.prompt();
				deferredPrompt.userChoice
					.then(function (choice) {
						if (choice && choice.outcome === "accepted") {
							markInstalled();
						} else {
							hideBanner();
						}
					})
					.finally(function () {
						deferredPrompt = null;
					});
				return;
			}
			showManualInstallTip();
		});
	}

	if (btnDismiss) {
		btnDismiss.addEventListener("click", function () {
			hideBanner();
		});
	}

	if (!authenticated || !isMobileTouch()) return;

	var pulseCookie = getCookie(PULSE_COOKIE) === "1";
	var pulseAttr =
		document.body && document.body.getAttribute("data-eu-pwa-login-pulse") === "1";
	if (!pulseCookie && !pulseAttr) return;
	if (pulseCookie) clearCookie(PULSE_COOKIE);

	var st = readState();
	if (st.installed) return;

	st.loginCount += 1;
	writeState(st);

	if (!shouldShowAfterLogin(st)) return;

	markShown(st);
	showBanner();
})();
