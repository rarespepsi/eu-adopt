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
	var storageKey = "eu_site_guide_state_v1";
	var dragState = null;
	var restoring = false;

	function resetDefaultPosition() {
		root.style.left = "";
		root.style.top = "";
		root.style.right = "";
		root.style.bottom = "";
	}

	function appendMsg(html, role) {
		if (!log) return;
		var el = document.createElement("div");
		el.className = "eu-site-guide__msg eu-site-guide__msg--" + role;
		el.innerHTML = html;
		log.appendChild(el);
		log.scrollTop = log.scrollHeight;
		saveState();
	}

	function setOpen(open) {
		root.classList.toggle("is-open", !!open);
		if (toggle) toggle.setAttribute("aria-expanded", open ? "true" : "false");
		if (open && input) window.setTimeout(function () { input.focus(); }, 80);
		saveState();
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

	function saveState() {
		if (restoring) return;
		try {
			var msgs = [];
			if (log) {
				var nodes = log.querySelectorAll(".eu-site-guide__msg");
				for (var i = 0; i < nodes.length; i++) {
					var n = nodes[i];
					msgs.push({
						role: n.classList.contains("eu-site-guide__msg--user") ? "user" : "bot",
						html: n.innerHTML,
					});
				}
			}
			var state = {
				open: root.classList.contains("is-open"),
				msgs: msgs,
			};
			sessionStorage.setItem(storageKey, JSON.stringify(state));
		} catch (_e) {}
	}

	function restoreState() {
		resetDefaultPosition();
		try {
			var raw = sessionStorage.getItem(storageKey);
			if (!raw) return;
			var state = JSON.parse(raw);
			if (!state || typeof state !== "object") return;
			restoring = true;
			if (log && Array.isArray(state.msgs)) {
				log.innerHTML = "";
				for (var i = 0; i < state.msgs.length; i++) {
					var m = state.msgs[i] || {};
					appendMsg(String(m.html || ""), m.role === "user" ? "user" : "bot");
				}
			}
			setOpen(!!state.open);
		} catch (_e) {
		} finally {
			restoring = false;
		}
	}

	function clamp(val, min, max) {
		return Math.max(min, Math.min(max, val));
	}

	function bindDrag() {
		if (!toggle) return;
		toggle.addEventListener("pointerdown", function (ev) {
			if (ev.button !== 0) return;
			dragState = {
				startX: ev.clientX,
				startY: ev.clientY,
				origLeft: root.getBoundingClientRect().left,
				origTop: root.getBoundingClientRect().top,
				moved: false,
			};
			toggle.setPointerCapture(ev.pointerId);
		});
		toggle.addEventListener("pointermove", function (ev) {
			if (!dragState) return;
			var dx = ev.clientX - dragState.startX;
			var dy = ev.clientY - dragState.startY;
			if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragState.moved = true;
			if (!dragState.moved) return;
			var rect = root.getBoundingClientRect();
			var nextLeft = clamp(dragState.origLeft + dx, 4, window.innerWidth - rect.width - 4);
			var nextTop = clamp(dragState.origTop + dy, 4, window.innerHeight - rect.height - 4);
			root.style.left = nextLeft + "px";
			root.style.top = nextTop + "px";
			root.style.right = "auto";
			root.style.bottom = "auto";
		});
		function endDrag(ev) {
			if (!dragState) return;
			dragState = null;
			try { toggle.releasePointerCapture(ev.pointerId); } catch (_e) {}
		}
		toggle.addEventListener("pointerup", endDrag);
		toggle.addEventListener("pointercancel", endDrag);
	}

	if (toggle) {
		toggle.addEventListener("click", function () {
			if (dragState && dragState.moved) return;
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
	restoreState();
	bindDrag();
	document.body.addEventListener("click", hideIfModal, true);
	window.addEventListener("beforeunload", saveState);
	window.addEventListener("pageshow", function (e) {
		resetDefaultPosition();
		if (e.persisted) restoreState();
	});
})();
