(function () {
	"use strict";

	function getCookie(name) {
		var m = document.cookie.match(new RegExp("(?:^|; )" + name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "=([^;]*)"));
		return m ? decodeURIComponent(m[1]) : "";
	}

	function mdLite(text) {
		var s = String(text || "");
		s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
		return s;
	}

	function escHtml(s) {
		return String(s || "")
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;");
	}

	var root = document.getElementById("eu-site-guide");
	if (!root) return;

	var askUrl = root.getAttribute("data-ask-url") || "";
	if (!askUrl) return;

	var toggle = root.querySelector(".eu-site-guide__toggle");
	var panel = root.querySelector(".eu-site-guide__panel");
	var closeBtn = root.querySelector(".eu-site-guide__close");
	var log = root.querySelector(".eu-site-guide__log");
	var form = root.querySelector(".eu-site-guide__form");
	var input = root.querySelector(".eu-site-guide__input");
	var sendBtn = root.querySelector(".eu-site-guide__send");
	var busy = false;

	function appendMsg(html, role) {
		if (!log) return;
		var el = document.createElement("div");
		el.className = "eu-site-guide__msg eu-site-guide__msg--" + role;
		el.innerHTML = html;
		log.appendChild(el);
		log.scrollTop = log.scrollHeight;
	}

	function setOpen(open) {
		root.classList.toggle("is-open", !!open);
		if (toggle) toggle.setAttribute("aria-expanded", open ? "true" : "false");
		if (open && input) window.setTimeout(function () { input.focus(); }, 80);
	}

	function hideIfModal() {
		var ov = document.getElementById("login-required-modal-overlay");
		if (ov && ov.classList.contains("is-visible")) {
			root.classList.add("is-hidden");
		} else {
			root.classList.remove("is-hidden");
		}
	}

	function ask(payload) {
		if (busy) return;
		busy = true;
		if (sendBtn) sendBtn.disabled = true;
		var body = new FormData();
		body.append("page_path", window.location.pathname || "/");
		if (payload.faq_id) body.append("faq_id", payload.faq_id);
		if (payload.question) body.append("question", payload.question);
		var csrf = getCookie("csrftoken");
		fetch(askUrl, {
			method: "POST",
			body: body,
			credentials: "same-origin",
			headers: csrf ? { "X-CSRFToken": csrf } : {},
		})
			.then(function (r) { return r.json().then(function (j) { return { ok: r.ok, status: r.status, j: j }; }); })
			.then(function (res) {
				if (!res.ok || !res.j || !res.j.ok) {
					var err = (res.j && res.j.error) || "Nu am putut răspunde acum. Încearcă din nou.";
					appendMsg(escHtml(err), "bot");
					return;
				}
				appendMsg(mdLite(res.j.answer), "bot");
			})
			.catch(function () {
				appendMsg(escHtml("Conexiune indisponibilă. Verifică rețeaua sau încearcă mai târziu."), "bot");
			})
			.finally(function () {
				busy = false;
				if (sendBtn) sendBtn.disabled = false;
			});
	}

	if (toggle) {
		toggle.addEventListener("click", function () {
			setOpen(!root.classList.contains("is-open"));
		});
	}
	if (closeBtn) {
		closeBtn.addEventListener("click", function () { setOpen(false); });
	}
	document.addEventListener("click", function (e) {
		if (!root.classList.contains("is-open")) return;
		var t = e.target;
		if (root === t || root.contains(t)) return;
		setOpen(false);
	});
	document.addEventListener("keydown", function (e) {
		if (e.key === "Escape") setOpen(false);
	});

	if (form) {
		form.addEventListener("submit", function (e) {
			e.preventDefault();
			var q = input ? (input.value || "").trim() : "";
			if (!q) return;
			appendMsg(escHtml(q), "user");
			if (input) input.value = "";
			ask({ question: q });
		});
	}

	hideIfModal();
	document.body.addEventListener("click", hideIfModal, true);
})();
