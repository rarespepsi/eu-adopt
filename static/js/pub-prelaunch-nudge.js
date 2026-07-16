(function () {
	"use strict";
	var el = document.getElementById("pubPrelaunchNudge");
	if (!el) return;
	if (document.body && document.body.classList.contains("page-publicitate-harta")) return;
	var interval = parseInt(el.getAttribute("data-nudge-interval") || "3", 10) || 3;
	if (interval < 1) interval = 3;
	var storageKey = "euadopt_pub_nudge_visits";
	try {
		var visits = parseInt(localStorage.getItem(storageKey) || "0", 10) + 1;
		localStorage.setItem(storageKey, String(visits));
		if (visits % interval !== 0) return;
	} catch (_e) {
		return;
	}
	el.hidden = false;
	var close = function () {
		el.hidden = true;
	};
	var closeBtn = el.querySelector("[data-pub-nudge-close]");
	if (closeBtn) closeBtn.addEventListener("click", close);
})();
