/**
 * Sincronizează caseta de prefix CUI cu <select class="signup-cui-ro-select">:
 * valoare "da" → afișează "RO"; "nu" → casetă goală.
 */
(function () {
	function syncRoDisplay(select) {
		var id = select.getAttribute("data-ro-display-id");
		if (!id) return;
		var box = document.getElementById(id);
		if (!box) return;
		var v = (select.value || "").toString().toLowerCase();
		var showRo = v === "da";
		box.value = showRo ? "RO" : "";
		box.setAttribute("aria-label", showRo ? "Prefix CUI: RO" : "Fără prefix RO");
	}

	function bind(select) {
		syncRoDisplay(select);
		select.addEventListener("change", function () {
			syncRoDisplay(select);
		});
	}

	function init() {
		document.querySelectorAll("select.signup-cui-ro-select").forEach(bind);
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", init);
	} else {
		init();
	}
})();
