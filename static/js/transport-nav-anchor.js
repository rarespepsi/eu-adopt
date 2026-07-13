/**
 * Transport zone navigation: session anchor + browser Back → /transport/
 */
(function (global) {
	"use strict";

	var STORAGE_KEY = "eu_transport_nav";
	var TRANSPORT_PATH = "/transport/";

	function isTransportSursa(s) {
		if (!s) return false;
		s = String(s).trim().toLowerCase();
		return s === "transport" || s === "transport_hub" || s.indexOf("transport_") === 0;
	}

	function getSursaFromUrl() {
		try {
			return new URLSearchParams(global.location.search).get("sursa") || "";
		} catch (e) {
			return "";
		}
	}

	function setTransportAnchor() {
		try {
			global.sessionStorage.setItem(STORAGE_KEY, "1");
		} catch (e) { /* ignore */ }
	}

	function hasTransportAnchor() {
		try {
			return global.sessionStorage.getItem(STORAGE_KEY) === "1";
		} catch (e) {
			return false;
		}
	}

	function initAuxBack() {
		if (!isTransportSursa(getSursaFromUrl())) return;
		setTransportAnchor();
		global.history.pushState({ euTransportBack: 1 }, "", global.location.href);
		global.addEventListener("popstate", function () {
			global.location.assign(TRANSPORT_PATH);
		});
	}

	function maybeInitOnLoad() {
		var path = global.location.pathname || "";
		if (path === "/transport/" || path === "/transport") {
			setTransportAnchor();
			return;
		}
		initAuxBack();
	}

	var api = {
		STORAGE_KEY: STORAGE_KEY,
		TRANSPORT_PATH: TRANSPORT_PATH,
		isTransportSursa: isTransportSursa,
		getSursaFromUrl: getSursaFromUrl,
		setTransportAnchor: setTransportAnchor,
		hasTransportAnchor: hasTransportAnchor,
		initAuxBack: initAuxBack
	};

	global.EUTransportNav = api;

	if (global.document) {
		if (global.document.readyState === "loading") {
			global.document.addEventListener("DOMContentLoaded", maybeInitOnLoad);
		} else {
			maybeInitOnLoad();
		}
	}
})(window);
