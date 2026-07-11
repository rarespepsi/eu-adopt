(function () {
	"use strict";

	var FB = "facebook.com";

	function isPubFbLink(a) {
		if (!a) return false;
		var href = (a.getAttribute("href") || "").trim();
		return href.indexOf(FB) !== -1;
	}

	function openInNewTab(a) {
		var href = (a.getAttribute("href") || "").trim();
		if (!href) return;
		var w = window.open(href, "_blank", "noopener,noreferrer");
		if (!w) {
			/* Popup blocat: nu navigăm peste EU-Adopt — utilizatorul rămâne pe site. */
			return;
		}
		try {
			w.opener = null;
		} catch (e) {}
	}

	document.addEventListener(
		"click",
		function (e) {
			var a = e.target.closest(
				'a[data-pub-fb="1"], a.pub-live-default-cover, a.pt-strip-cell--pub, a.sw-strip-cell--pub'
			);
			if (!a || !isPubFbLink(a)) return;
			e.preventDefault();
			e.stopImmediatePropagation();
			openInNewTab(a);
		},
		true
	);
})();
