/**
 * Inbox mesaje servicii / produse (CollabServiceMessage).
 * mode: "collaborator" (Magazinul meu) | "client" (MyPet PF/ONG)
 */
(function (window) {
	"use strict";

	function getCookie(name) {
		var value = "; " + document.cookie;
		var parts = value.split("; " + name + "=");
		if (parts.length === 2) return parts.pop().split(";").shift();
		return "";
	}

	function escapeHtml(s) {
		return String(s || "")
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;")
			.replace(/'/g, "&#39;");
	}

	function updateEnvelopeCount(unreadTotal, useCombined) {
		try {
			var total = parseInt(unreadTotal || 0, 10) || 0;
			var label = total > 0 ? ("Mesaje noi: " + total) : "Nu ai mesaje noi";
			document.querySelectorAll(".a0-nav-envelope-icon").forEach(function (icon) {
				icon.classList.toggle("is-hot", total > 0);
			});
			document.querySelectorAll(".a0-nav-envelope-link").forEach(function (link) {
				link.setAttribute("title", label);
				link.setAttribute("aria-label", label);
			});
			document.querySelectorAll(".a0-nav-envelope-item").forEach(function (item) {
				var badge = item.querySelector(".a0-nav-envelope-count");
				var al = item.querySelector(".a0-nav-envelope-link");
				if (total > 0) {
					if (!badge && al) {
						badge = document.createElement("span");
						badge.className = "a0-nav-envelope-count";
						al.appendChild(badge);
					}
					if (badge) badge.textContent = String(total);
				} else if (badge && badge.parentNode) {
					badge.parentNode.removeChild(badge);
				}
			});
			void useCombined;
		} catch (e) {}
	}

	window.initCollabServiceInbox = function initCollabServiceInbox(cfg) {
		if (!cfg || !cfg.idPrefix) return;
		var mode = cfg.mode || "collaborator";
		var p = cfg.idPrefix;
		var listUrl = cfg.listUrl || "";
		var threadUrl = cfg.threadUrl || "";
		var replyUrl = cfg.replyUrl || "";
		var csrftoken = getCookie("csrftoken") || "";

		var modal = document.getElementById(p + "MsgModal");
		var title = document.getElementById(p + "MsgTitle");
		var closeBtn = document.getElementById(p + "MsgClose");
		var tabActive = document.getElementById(p + "MsgTabActive");
		var tabArchived = document.getElementById(p + "MsgTabArchived");
		var threadsEl = document.getElementById(p + "MsgThreads");
		var threadEl = document.getElementById(p + "MsgThread");
		var replyTa = document.getElementById(p + "MsgReplyTa");
		var replyBtn = document.getElementById(p + "MsgReplyBtn");
		if (!modal || !threadsEl || !threadEl || !replyTa || !replyBtn || !tabActive || !tabArchived) return;

		modal.hidden = true;
		modal.style.display = "none";

		var state = {
			scope: "active",
			listUrl: listUrl,
			peerId: null,
			collaboratorId: null,
			contextType: "general",
			contextRef: "",
			threadKey: "",
		};

		function closeModal() {
			modal.hidden = true;
			modal.style.display = "none";
			threadEl.innerHTML = "";
			threadsEl.innerHTML = "";
			replyTa.value = "";
			state.peerId = null;
			state.collaboratorId = null;
		}
		window["__closeCollabSvcMsgModal_" + p] = closeModal;

		function setScope(scope) {
			state.scope = scope === "archived" ? "archived" : "active";
			tabActive.classList.toggle("is-active", state.scope === "active");
			tabArchived.classList.toggle("is-active", state.scope === "archived");
		}

		function listUrlWithScope(url) {
			var u = new URL(url, window.location.origin);
			u.searchParams.set("scope", state.scope);
			return u.pathname + u.search;
		}

		function buildThreadFetchUrl() {
			var u = new URL(threadUrl, window.location.origin);
			u.searchParams.set("scope", state.scope);
			u.searchParams.set("context_type", state.contextType || "general");
			u.searchParams.set("context_ref", state.contextRef || "");
			if (mode === "collaborator") {
				u.searchParams.set("client_id", String(state.peerId || ""));
			} else {
				u.searchParams.set("collaborator_id", String(state.collaboratorId || ""));
			}
			return u.pathname + u.search;
		}

		closeBtn.addEventListener("click", closeModal);
		closeBtn.addEventListener("mousedown", function (e) {
			e.stopPropagation();
		});
		modal.addEventListener("click", function (e) {
			if (e.target === modal) closeModal();
		});
		document.addEventListener("keydown", function (e) {
			if (!modal.hidden && (e.key === "Escape" || e.key === "Esc")) closeModal();
		});

		function renderLocationStrip(strip) {
			if (!strip || !strip.displayName) return;
			var hasLoc = strip.mapsUrl || (strip.lines && strip.lines.length);
			if (!hasLoc) return;
			var card = document.createElement("div");
			card.className = "collab-svc-client-card";
			var ct = document.createElement("div");
			ct.className = "collab-svc-client-card-title";
			ct.textContent = (strip.cardTitle || "Fișă") + ": " + (strip.displayName || "");
			card.appendChild(ct);
			(strip.lines || []).forEach(function (ln) {
				var row = document.createElement("div");
				row.className = "collab-svc-client-card-line";
				row.textContent = ln;
				card.appendChild(row);
			});
			var act = document.createElement("div");
			act.className = "collab-svc-client-card-actions";
			if (strip.mapsUrl) {
				var mapA = document.createElement("a");
				mapA.href = strip.mapsUrl;
				mapA.target = "_blank";
				mapA.rel = "noopener noreferrer";
				mapA.className = "collab-svc-client-card-map-btn";
				mapA.textContent = "DU-MĂ LA LOCAȚIE";
				act.appendChild(mapA);
				var shareBtn = document.createElement("button");
				shareBtn.type = "button";
				shareBtn.className = "collab-svc-client-card-share-btn";
				shareBtn.textContent = "Distribuie locația";
				shareBtn.addEventListener("click", function () {
					var url = strip.mapsUrl;
					var text = strip.shareText || "";
					var title = strip.shareTitle || "EU-Adopt";
					if (navigator.share) {
						navigator.share({ title: title, text: text, url: url }).catch(function () {});
						return;
					}
					if (navigator.clipboard && navigator.clipboard.writeText) {
						navigator.clipboard.writeText(url).then(function () {
							alert("Link copiat în clipboard.");
						}).catch(function () {
							window.prompt("Copiază linkul:", url);
						});
						return;
					}
					window.prompt("Copiază linkul:", url);
				});
				act.appendChild(shareBtn);
			}
			card.appendChild(act);
			threadEl.appendChild(card);
		}

		function renderThread(messages, threadData) {
			threadEl.innerHTML = "";
			var td = threadData || {};
			var strip = null;
			if (mode === "collaborator" && td.client_card) {
				var c = td.client_card;
				strip = {
					displayName: c.client_name,
					cardTitle: "Fișă client",
					lines: c.lines || [],
					mapsUrl: c.maps_url || "",
					shareText: c.share_text || "",
					shareTitle: "Locație client EU-Adopt",
				};
			} else if (mode === "client" && td.partner_card) {
				var p = td.partner_card;
				strip = {
					displayName: p.partner_name,
					cardTitle: "Locație partener",
					lines: p.lines || [],
					mapsUrl: p.maps_url || "",
					shareText: p.share_text || "",
					shareTitle: "Locație partener EU-Adopt",
				};
			}
			renderLocationStrip(strip);
			if (!messages || !messages.length) {
				var empty = document.createElement("div");
				empty.className = "mypet-msg-thread-empty";
				empty.textContent = "Nu există încă mesaje.";
				threadEl.appendChild(empty);
				threadEl.scrollTop = threadEl.scrollHeight;
				return;
			}
			messages.forEach(function (m) {
				var div = document.createElement("div");
				var other = !m.from_me;
				div.className = "mypet-msg-bubble " + (other ? "from-owner" : "from-user");
				div.textContent = m.body || "";
				threadEl.appendChild(div);
			});
			threadEl.scrollTop = threadEl.scrollHeight;
		}

		function applyUnreadBadge(data) {
			if (cfg.useNavbarCombinedUnread && typeof data.navbar_unread_total !== "undefined") {
				updateEnvelopeCount(data.navbar_unread_total);
			} else if (typeof data.unread_total !== "undefined") {
				updateEnvelopeCount(data.unread_total);
			}
		}

		function openThread() {
			if (mode === "collaborator" && !state.peerId) return;
			if (mode === "client" && !state.collaboratorId) return;
			fetch(buildThreadFetchUrl(), { credentials: "same-origin" })
				.then(function (r) {
					return r.json();
				})
				.then(function (data) {
					if (!data || !data.ok) throw new Error("Thread indisponibil.");
					renderThread(data.messages || [], data);
					applyUnreadBadge(data);
					document.querySelectorAll(".mypet-msg-thread-item[data-thread-key]").forEach(function (it) {
						it.classList.toggle("is-active", (it.getAttribute("data-thread-key") || "") === state.threadKey);
					});
				})
				.catch(function () {
					threadEl.textContent = "Eroare la încărcarea conversației.";
				});
		}

		function makeServiceThreadItem(itemData, onClick) {
			var item = document.createElement("div");
			item.className = "mypet-msg-thread-item";
			if (itemData.threadKey) item.setAttribute("data-thread-key", itemData.threadKey);
			var icon = '<span class="mypet-msg-item-photo" aria-hidden="true" style="display:flex;align-items:center;justify-content:center;font-size:1.2rem;">💬</span>';
			var titleLine = escapeHtml(itemData.title || "");
			var subLine = escapeHtml(itemData.sub || "");
			item.innerHTML =
				'<div class="mypet-msg-item-top">' +
				'<span class="mypet-msg-item-photo-wrap">' +
				icon +
				"</span>" +
				"<div>" +
				'<div class="mypet-msg-item-title">' +
				titleLine +
				"</div>" +
				(subLine ? '<div class="mypet-msg-item-sub">' + subLine + "</div>" : "") +
				"</div>" +
				"</div>" +
				'<div class="mypet-msg-item-preview">' +
				escapeHtml(itemData.preview || "") +
				"</div>";
			item.addEventListener("click", onClick);
			return item;
		}

		function openListModal() {
			title.textContent = "Mesaje";
			modal.hidden = false;
			modal.style.display = "flex";
			threadEl.textContent = "";
			threadsEl.textContent = "Se încarcă...";
			fetch(listUrlWithScope(state.listUrl), { credentials: "same-origin" })
				.then(function (r) {
					return r.json();
				})
				.then(function (data) {
					if (!data || !data.ok) throw new Error("Listă indisponibilă.");
					var threads = data.threads || [];
					threadsEl.innerHTML = "";
					if (!threads.length) {
						threadsEl.textContent = "Fără conversații.";
						return;
					}
					threads.forEach(function (t, idx) {
						var titleText;
						var subText;
						var tkey =
							mode === "collaborator"
								? String(t.client_id) + "|" + String(t.context_type || "") + "|" + String(t.context_ref || "")
								: String(t.collaborator_id) + "|" + String(t.context_type || "") + "|" + String(t.context_ref || "");
						if (mode === "collaborator") {
							titleText = (t.client_name || "Client") + " — " + (t.context_label || t.context_type || "");
							subText = t.context_label || "";
						} else {
							titleText = (t.collaborator_name || "Colaborator") + " — " + (t.context_label || t.context_type || "");
							subText = t.context_label || "";
						}
						if (state.scope === "active" && t.unread_count) {
							titleText += " (" + t.unread_count + " noi)";
						}
						var item = makeServiceThreadItem(
							{
								threadKey: tkey,
								title: titleText,
								sub: subText,
								preview: t.last_message || "",
							},
							function () {
								state.threadKey = tkey;
								if (mode === "collaborator") {
									state.peerId = t.client_id;
									state.contextType = t.context_type || "general";
									state.contextRef = t.context_ref || "";
								} else {
									state.collaboratorId = t.collaborator_id;
									state.contextType = t.context_type || "general";
									state.contextRef = t.context_ref || "";
								}
								openThread();
							}
						);
						threadsEl.appendChild(item);
						if (idx === 0) {
							state.threadKey = tkey;
							if (mode === "collaborator") {
								state.peerId = t.client_id;
								state.contextType = t.context_type || "general";
								state.contextRef = t.context_ref || "";
							} else {
								state.collaboratorId = t.collaborator_id;
								state.contextType = t.context_type || "general";
								state.contextRef = t.context_ref || "";
							}
							openThread();
						}
					});
				})
				.catch(function () {
					threadsEl.textContent = "Eroare la încărcarea conversațiilor.";
				});
		}

		tabActive.addEventListener("click", function () {
			if (state.scope === "active") return;
			setScope("active");
			if (!modal.hidden) openListModal();
		});
		tabArchived.addEventListener("click", function () {
			if (state.scope === "archived") return;
			setScope("archived");
			if (!modal.hidden) openListModal();
		});

		function submitReply() {
			if (mode === "collaborator" && !state.peerId) {
				alert("Alege mai întâi conversația.");
				return;
			}
			if (mode === "client" && !state.collaboratorId) {
				alert("Alege mai întâi conversația.");
				return;
			}
			var text = (replyTa.value || "").trim();
			if (!text) return;
			var body = new URLSearchParams();
			body.set("message", text);
			body.set("context_type", state.contextType || "general");
			body.set("context_ref", state.contextRef || "");
			if (mode === "collaborator") body.set("client_id", String(state.peerId));
			else body.set("collaborator_id", String(state.collaboratorId));
			replyBtn.disabled = true;
			fetch(replyUrl, {
				method: "POST",
				headers: {
					"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
					"X-CSRFToken": csrftoken,
				},
				credentials: "same-origin",
				body: body.toString(),
			})
				.then(function (r) {
					return r.json();
				})
				.then(function (data) {
					if (!data || !data.ok) throw new Error((data && data.error) || "Trimitere eșuată.");
					replyTa.value = "";
					openThread();
				})
				.catch(function (err) {
					alert(err.message || "Eroare la trimitere.");
				})
				.finally(function () {
					replyBtn.disabled = false;
				});
		}
		replyBtn.addEventListener("click", submitReply);
		replyTa.addEventListener("keydown", function (e) {
			if (e.key === "Enter" && !e.shiftKey) {
				e.preventDefault();
				submitReply();
			}
		});

		if (cfg.openButtonId) {
			var ob = document.getElementById(cfg.openButtonId);
			if (ob) {
				ob.addEventListener("click", function () {
					state.listUrl = listUrl;
					openListModal();
				});
			}
		}

		if (cfg.autoOpenParam && cfg.autoOpenParamValue) {
			try {
				var params = new URLSearchParams(window.location.search || "");
				if (params.get(cfg.autoOpenParam) === cfg.autoOpenParamValue) {
					setTimeout(function () {
						state.listUrl = listUrl;
						openListModal();
					}, 80);
				}
			} catch (e) {}
		}

		window[cfg.globalOpenFn || "__openCollabServiceInboxDefault"] = function () {
			state.listUrl = listUrl;
			openListModal();
		};

		if (cfg.exposeThreadOpenFn && typeof cfg.exposeThreadOpenFn === "string") {
			window[cfg.exposeThreadOpenFn] = function (collaboratorId, contextType, contextRef) {
				var cid = parseInt(collaboratorId, 10) || 0;
				if (!cid) return;
				state.collaboratorId = cid;
				state.contextType = contextType ? String(contextType).trim().toLowerCase() : "general";
				if (!state.contextType) state.contextType = "general";
				state.contextRef =
					contextRef != null ? String(contextRef).trim().slice(0, 120) : "";
				state.peerId = null;
				state.listUrl = listUrl;
				modal.hidden = false;
				modal.style.display = "flex";
				if (threadsEl) threadsEl.innerHTML = "";
				if (title) title.textContent = "Mesaje cu partenerul";
				openThread();
			};
		}
	};
})(window);
