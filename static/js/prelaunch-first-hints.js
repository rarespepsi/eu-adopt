(function () {
	"use strict";
	var body = document.body;
	if (!body || body.getAttribute("data-user-authenticated") !== "true") return;
	var hintEl = document.getElementById("prelaunchFirstHint");
	if (!hintEl) return;
	var hintText = (hintEl.getAttribute("data-hint-text") || "").trim();
	var hintKey = (hintEl.getAttribute("data-hint-key") || "").trim();
	if (!hintText || !hintKey) return;
	var storageKey = "euadopt_prelaunch_hint_" + hintKey;
	try {
		if (localStorage.getItem(storageKey) === "1") {
			hintEl.hidden = true;
			return;
		}
	} catch (_e) {}
	var textNode = hintEl.querySelector(".prelaunch-first-hint__text");
	if (textNode) textNode.textContent = hintText;
	hintEl.hidden = false;
	var dismiss = function () {
		hintEl.hidden = true;
		try {
			localStorage.setItem(storageKey, "1");
		} catch (_e2) {}
	};
	var okBtn = hintEl.querySelector("[data-prelaunch-hint-ok]");
	var closeBtn = hintEl.querySelector("[data-prelaunch-hint-close]");
	if (okBtn) okBtn.addEventListener("click", dismiss);
	if (closeBtn) closeBtn.addEventListener("click", dismiss);
})();
