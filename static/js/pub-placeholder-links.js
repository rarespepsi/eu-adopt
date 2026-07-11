(function () {
	"use strict";

	var FB = "facebook.com";

	function isPubFbLink(a) {
		if (!a) return false;
		var href = (a.getAttribute("href") || "").trim();
		return href.indexOf(FB) !== -1;
	}

	function navigate(a) {
		var href = (a.getAttribute("href") || "").trim();
		if (!href) return;
		window.location.assign(href);
	}

	document.addEventListener(
		"click",
		function (e) {
			var a = e.target.closest('a[data-pub-fb="1"], a.pub-live-default-cover');
			if (!a || !isPubFbLink(a)) return;
			e.preventDefault();
			e.stopImmediatePropagation();
			navigate(a);
		},
		true
	);
})();
