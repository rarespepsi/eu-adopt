(function () {
	"use strict";

	function getCookie(name) {
		var m = document.cookie.match(
			new RegExp("(?:^|; )" + name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "=([^;]*)")
		);
		return m ? decodeURIComponent(m[1]) : "";
	}

	var dataEl = document.getElementById("eu-user-onboard-data");
	if (!dataEl) return;

	var payload;
	try {
		payload = JSON.parse(dataEl.textContent || "{}");
	} catch (_e) {
		return;
	}
	if (!payload || !payload.page_key || !payload.storage_key) return;

	var storageKey = payload.storage_key;
	try {
		if (localStorage.getItem(storageKey) === "1") return;
	} catch (_e2) {}

	var root = document.getElementById("eu-user-onboard");
	if (!root) return;

	var backdrop = root.querySelector(".eu-user-onboard__backdrop");
	var banner = root.querySelector(".eu-user-onboard__banner");
	var tour = root.querySelector(".eu-user-onboard__tour");
	var tourStepEl = root.querySelector(".eu-user-onboard__tour-step");
	var tourTextEl = root.querySelector(".eu-user-onboard__tour-text");
	var titleEl = root.querySelector(".eu-user-onboard__title");
	var textEl = root.querySelector(".eu-user-onboard__text");
	var hintEl = root.querySelector(".eu-user-onboard__hint");
	var btnSkip = root.querySelector("[data-onboard-skip]");
	var btnTour = root.querySelector("[data-onboard-tour]");
	var btnNext = root.querySelector("[data-onboard-next]");
	var btnDone = root.querySelector("[data-onboard-done]");

	var steps = Array.isArray(payload.steps) ? payload.steps : [];
	var stepIndex = 0;
	var highlightEl = null;
	var dismissed = false;

	if (titleEl) titleEl.textContent = payload.banner_title || "Sfat";
	if (textEl) textEl.textContent = payload.banner_text || "";
	if (hintEl) {
		if (payload.site_guide_hint) {
			hintEl.textContent = payload.site_guide_hint;
			hintEl.hidden = false;
		} else {
			hintEl.hidden = true;
		}
	}

	function clearHighlight() {
		if (highlightEl) {
			highlightEl.classList.remove("eu-user-onboard__target-highlight");
			highlightEl = null;
		}
	}

	function markSeenLocal() {
		try {
			localStorage.setItem(storageKey, "1");
		} catch (_e3) {}
	}

	function markSeenServer() {
		var url = root.getAttribute("data-dismiss-url") || "";
		if (!url) return;
		var body = new FormData();
		body.append("page_key", payload.page_key);
		var csrf = getCookie("csrftoken");
		fetch(url, {
			method: "POST",
			body: body,
			credentials: "same-origin",
			headers: csrf ? { "X-CSRFToken": csrf } : {},
		}).catch(function () {});
	}

	function dismissAll() {
		if (dismissed) return;
		dismissed = true;
		clearHighlight();
		root.classList.remove("is-active");
		if (banner) banner.hidden = true;
		if (tour) tour.hidden = true;
		markSeenLocal();
		markSeenServer();
	}

	function positionTourNear(el) {
		if (!tour || !el) return;
		var rect = el.getBoundingClientRect();
		var top = rect.bottom + 10;
		var left = Math.min(Math.max(8, rect.left), window.innerWidth - 300);
		if (top + 140 > window.innerHeight) {
			top = Math.max(8, rect.top - 140);
		}
		tour.style.top = top + "px";
		tour.style.left = left + "px";
	}

	function showStep(idx) {
		clearHighlight();
		while (idx < steps.length) {
			var sel = (steps[idx].selector || "").trim();
			var txt = (steps[idx].text || "").trim();
			if (!sel || !txt) {
				idx += 1;
				continue;
			}
			var el = document.querySelector(sel);
			if (!el) {
				idx += 1;
				continue;
			}
			stepIndex = idx;
			el.classList.add("eu-user-onboard__target-highlight");
			highlightEl = el;
			try {
				el.scrollIntoView({ block: "nearest", behavior: "smooth" });
			} catch (_e4) {}
			if (tourStepEl) {
				tourStepEl.textContent = "Pas " + (stepIndex + 1) + " / " + steps.length;
			}
			if (tourTextEl) tourTextEl.textContent = txt;
			if (btnNext) btnNext.hidden = stepIndex >= steps.length - 1;
			if (btnDone) btnDone.hidden = stepIndex < steps.length - 1;
			positionTourNear(el);
			if (tour) tour.hidden = false;
			return;
		}
		dismissAll();
	}

	function startTour() {
		if (banner) banner.hidden = true;
		if (!steps.length) {
			dismissAll();
			return;
		}
		showStep(0);
	}

	root.classList.add("is-active");
	if (banner) banner.hidden = false;

	if (btnSkip) btnSkip.addEventListener("click", dismissAll);
	if (btnTour) btnTour.addEventListener("click", startTour);
	if (btnNext) {
		btnNext.addEventListener("click", function () {
			showStep(stepIndex + 1);
		});
	}
	if (btnDone) btnDone.addEventListener("click", dismissAll);

	window.addEventListener(
		"resize",
		function () {
			if (highlightEl) positionTourNear(highlightEl);
		},
		{ passive: true }
	);
})();
