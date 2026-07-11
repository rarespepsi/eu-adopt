(function () {
	"use strict";

	var FB = "facebook.com";
	var SEL =
		'a[data-pub-fb="1"], a.pub-live-default-cover, a.pub-live-cover-link, a.pt-strip-cell--pub, a.sw-strip-cell--pub';
	var lastOpenAt = 0;
	var OPEN_DEBOUNCE_MS = 900;

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

	/** Tab nou fără location.assign — evită banda albă / pagină blocată la al 2-lea tap. */
	function openInNewTab(href) {
		var now = Date.now();
		if (now - lastOpenAt < OPEN_DEBOUNCE_MS) return;
		lastOpenAt = now;

		var temp = document.createElement("a");
		temp.href = href;
		temp.target = "_blank";
		temp.rel = "noopener noreferrer";
		temp.setAttribute("aria-hidden", "true");
		temp.style.cssText =
			"position:fixed;left:-9999px;top:0;width:1px;height:1px;opacity:0;pointer-events:none;";
		document.body.appendChild(temp);
		temp.click();
		document.body.removeChild(temp);
	}

	if (!isCoarseTouch()) return;

	document.addEventListener(
		"click",
		function (e) {
			var a = e.target.closest("a");
			if (!isPubFbLink(a)) return;
			var href = (a.getAttribute("href") || "").trim();
			if (!href) return;
			e.preventDefault();
			openInNewTab(href);
		},
		true
	);

	window.addEventListener("pageshow", function () {
		lastOpenAt = 0;
	});
})();
