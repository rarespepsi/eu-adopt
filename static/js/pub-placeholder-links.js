(function () {
	"use strict";

	var FB = "facebook.com";
	var SEL =
		'a[data-pub-fb="1"], a.pub-live-default-cover, a.pub-live-cover-link, a.pt-strip-cell--pub, a.sw-strip-cell--pub';

	function isCoarseTouch() {
		try {
			return window.matchMedia("(hover: none) and (pointer: coarse)").matches;
		} catch (e) {}
		return "ontouchstart" in window;
	}

	function isPubFbLink(a) {
		if (!a || a.tagName !== "A") return false;
		if (!a.matches(SEL)) return false;
		var href = (a.getAttribute("href") || "").trim();
		return href.indexOf(FB) !== -1;
	}

	function openPubFb(a) {
		var href = (a.getAttribute("href") || "").trim();
		if (!href) return;
		/* Mobil: același tab — target=_blank deschide adesea în fundal, invizibil utilizatorului. */
		window.location.assign(href);
	}

	if (!isCoarseTouch()) return;

	document.addEventListener(
		"click",
		function (e) {
			var a = e.target.closest("a");
			if (!isPubFbLink(a)) return;
			e.preventDefault();
			e.stopImmediatePropagation();
			openPubFb(a);
		},
		true
	);
})();
