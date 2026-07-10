/**
 * EU-Adopt — modal partajat poze/video (fișă, servicii, produse).
 * EuMediaModal.init({ shareHandler, onMediaView })
 */
(function (global) {
	"use strict";

	var initialized = false;
	var modal, modalPanel, modalBody, modalClose, modalFs, modalPrev, modalNext, modalFooter, modalShare;
	var galleryItems = [];
	var galleryIndex = -1;
	var modalMode = null;
	var cssFullscreenOn = false;
	var opts = {};

	function thumbSelector() {
		return opts.thumbSelector || ".js-eu-media-thumb, .js-pet-media-thumb";
	}

	function videoSelector() {
		return opts.videoSelector || ".js-eu-media-video, .js-pet-video-thumb";
	}

	function isVisible(el) {
		if (!el || !el.getBoundingClientRect) return false;
		var r = el.getBoundingClientRect();
		return r.width > 0 && r.height > 0;
	}

	function getModalMediaEl() {
		return modalBody ? modalBody.querySelector("img, video") : null;
	}

	function nativeFullscreenEl() {
		return document.fullscreenElement || document.webkitFullscreenElement || null;
	}

	function fsApiEnabled() {
		return !!(document.fullscreenEnabled || document.webkitFullscreenEnabled);
	}

	function requestElFullscreen(el) {
		if (!el) return Promise.reject();
		if (el.requestFullscreen) return el.requestFullscreen();
		if (el.webkitRequestFullscreen) return el.webkitRequestFullscreen();
		return Promise.reject();
	}

	function exitNativeFullscreen() {
		if (document.exitFullscreen) return document.exitFullscreen();
		if (document.webkitExitFullscreen) return document.webkitExitFullscreen();
		return Promise.resolve();
	}

	function syncFsButton() {
		if (!modalFs) return;
		var active = cssFullscreenOn || !!nativeFullscreenEl();
		modalFs.setAttribute("aria-label", active ? "Restrânge" : "Ecran complet");
		modalFs.title = active ? "Restrânge" : "Ecran complet";
		modalFs.textContent = active ? "⤡" : "⛶";
	}

	function setCssFullscreen(on) {
		cssFullscreenOn = !!on;
		if (modal) modal.classList.toggle("is-css-fs", cssFullscreenOn);
		syncFsButton();
	}

	function exitAllFullscreen() {
		setCssFullscreen(false);
		if (nativeFullscreenEl()) {
			try {
				exitNativeFullscreen();
			} catch (e) {}
		}
		syncFsButton();
	}

	function toggleModalFullscreen() {
		var media = getModalMediaEl();
		if (cssFullscreenOn || nativeFullscreenEl()) {
			exitAllFullscreen();
			return;
		}
		if (media && media.tagName === "VIDEO" && typeof media.webkitEnterFullscreen === "function") {
			try {
				media.webkitEnterFullscreen();
				syncFsButton();
				return;
			} catch (e) {}
		}
		if (modalPanel && fsApiEnabled()) {
			requestElFullscreen(modalPanel).then(syncFsButton).catch(function () {
				if (media && fsApiEnabled()) {
					requestElFullscreen(media).then(syncFsButton).catch(function () {
						setCssFullscreen(true);
					});
					return;
				}
				setCssFullscreen(true);
			});
			return;
		}
		if (media && fsApiEnabled()) {
			requestElFullscreen(media).then(syncFsButton).catch(function () {
				setCssFullscreen(true);
			});
			return;
		}
		setCssFullscreen(true);
	}

	function collectThumbs(fromEl) {
		var gal = fromEl && fromEl.getAttribute("data-eu-media-gallery");
		var sel = thumbSelector();
		var nodes;
		if (gal) {
			nodes = document.querySelectorAll(sel + '[data-eu-media-gallery="' + gal + '"]');
		} else if (fromEl) {
			var panel = fromEl.closest('[role="tabpanel"]');
			nodes = panel ? panel.querySelectorAll(sel) : document.querySelectorAll(sel);
		} else {
			nodes = document.querySelectorAll(sel);
		}
		return Array.prototype.slice.call(nodes).filter(function (img) {
			return img.tagName === "IMG" && isVisible(img);
		});
	}

	function buildGalleryItems(fromEl) {
		return collectThumbs(fromEl).map(function (img) {
			return {
				type: "image",
				thumbSrc: img.getAttribute("src") || "",
				modalSrc: img.getAttribute("data-modal-src") || img.getAttribute("src") || "",
				alt: img.getAttribute("alt") || ""
			};
		});
	}

	function updateGalleryNav() {
		var show = modalMode === "image" && galleryItems.length > 1;
		if (modalPrev) modalPrev.hidden = !show;
		if (modalNext) modalNext.hidden = !show;
	}

	function showGalleryImage(index) {
		if (!modal || !modalBody || !galleryItems.length) return;
		galleryIndex = (index + galleryItems.length) % galleryItems.length;
		var item = galleryItems[galleryIndex];
		modalBody.innerHTML = "";
		modalBody.classList.add("eu-media-modal__body--loading");
		var img = document.createElement("img");
		img.alt = item.alt || "";
		img.decoding = "async";
		img.onload = function () {
			modalBody.classList.remove("eu-media-modal__body--loading");
		};
		img.onerror = function () {
			modalBody.classList.remove("eu-media-modal__body--loading");
			if (item.thumbSrc && item.modalSrc !== item.thumbSrc) {
				img.src = item.thumbSrc;
			}
		};
		img.src = item.modalSrc;
		modalBody.appendChild(img);
		if (modalFooter) {
			modalFooter.innerHTML = "";
			modalFooter.hidden = true;
		}
		updateGalleryNav();
	}

	function closeModal() {
		if (!modal) return;
		exitAllFullscreen();
		modal.hidden = true;
		modalMode = null;
		galleryIndex = -1;
		galleryItems = [];
		document.body.style.overflow = "";
		if (modalBody) modalBody.innerHTML = "";
		if (modalFooter) {
			modalFooter.innerHTML = "";
			modalFooter.hidden = true;
		}
		updateGalleryNav();
	}

	function openImage(el) {
		if (!modal || !modalBody) return;
		galleryItems = buildGalleryItems(el);
		modalMode = "image";
		var idx = 0;
		if (el) {
			var thumbs = collectThumbs(el);
			for (var i = 0; i < thumbs.length; i++) {
				if (thumbs[i] === el) {
					idx = i;
					break;
				}
			}
		}
		showGalleryImage(idx);
		modal.hidden = false;
		syncFsButton();
		document.body.style.overflow = "hidden";
		if (typeof opts.onMediaView === "function") opts.onMediaView("image", el);
	}

	function openVideo(src, el) {
		if (!src || !modal || !modalBody) return;
		modalMode = "video";
		galleryItems = [];
		galleryIndex = -1;
		updateGalleryNav();
		modalBody.innerHTML = "";
		var v = document.createElement("video");
		v.src = src;
		v.controls = false;
		v.playsInline = true;
		v.preload = "metadata";
		v.setAttribute("aria-label", "Video");
		v.addEventListener("webkitendfullscreen", syncFsButton);
		modalBody.appendChild(v);

		if (modalFooter) {
			modalFooter.innerHTML = "";
			var controls = document.createElement("div");
			controls.className = "eu-media-modal__video-controls";

			var btnBack = document.createElement("button");
			btnBack.type = "button";
			btnBack.className = "eu-media-modal__vc-btn";
			btnBack.title = "Înapoi 5 sec";
			btnBack.setAttribute("aria-label", "Înapoi 5 secunde");
			btnBack.textContent = "⏪";

			var btnPlay = document.createElement("button");
			btnPlay.type = "button";
			btnPlay.className = "eu-media-modal__vc-btn";
			btnPlay.title = "Play / Pauză";
			btnPlay.setAttribute("aria-label", "Play sau pauză");
			btnPlay.textContent = "⏸";

			var btnFwd = document.createElement("button");
			btnFwd.type = "button";
			btnFwd.className = "eu-media-modal__vc-btn";
			btnFwd.title = "Înainte 5 sec";
			btnFwd.setAttribute("aria-label", "Înainte 5 secunde");
			btnFwd.textContent = "⏩";

			function clampTime(t) {
				if (!isFinite(t)) return 0;
				var d = v.duration;
				if (!isFinite(d) || d <= 0) return Math.max(0, t);
				return Math.min(Math.max(0, t), d);
			}
			function togglePlay() {
				if (v.paused) v.play().catch(function () {});
				else v.pause();
			}
			function syncPlayIcon() {
				btnPlay.textContent = v.paused ? "▶" : "⏸";
			}

			btnBack.addEventListener("click", function (e) {
				e.stopPropagation();
				v.currentTime = clampTime((v.currentTime || 0) - 5);
			});
			btnFwd.addEventListener("click", function (e) {
				e.stopPropagation();
				v.currentTime = clampTime((v.currentTime || 0) + 5);
			});
			btnPlay.addEventListener("click", function (e) {
				e.stopPropagation();
				togglePlay();
			});
			v.addEventListener("play", syncPlayIcon);
			v.addEventListener("pause", syncPlayIcon);
			v.addEventListener("ended", syncPlayIcon);
			v.addEventListener("loadedmetadata", syncPlayIcon);

			controls.appendChild(btnBack);
			controls.appendChild(btnPlay);
			controls.appendChild(btnFwd);
			modalFooter.appendChild(controls);
			modalFooter.hidden = false;
		}
		modal.hidden = false;
		syncFsButton();
		document.body.style.overflow = "hidden";
		try {
			v.play();
		} catch (e) {}
		if (typeof opts.onMediaView === "function") opts.onMediaView("video", el);
	}

	function bindEvents() {
		document.addEventListener("fullscreenchange", function () {
			if (!nativeFullscreenEl()) syncFsButton();
		});
		document.addEventListener("webkitfullscreenchange", function () {
			if (!nativeFullscreenEl()) syncFsButton();
		});

		if (modalShare && typeof opts.shareHandler === "function") {
			modalShare.hidden = false;
			modalShare.removeAttribute("aria-hidden");
			modalShare.tabIndex = 0;
			modalShare.addEventListener("click", function (e) {
				e.preventDefault();
				e.stopPropagation();
				opts.shareHandler();
			});
		}

		if (modalFs) {
			modalFs.addEventListener("click", function (e) {
				e.preventDefault();
				e.stopPropagation();
				toggleModalFullscreen();
			});
		}
		if (modalPrev) {
			modalPrev.addEventListener("click", function (e) {
				e.preventDefault();
				e.stopPropagation();
				if (modalMode === "image" && galleryItems.length > 1) {
					showGalleryImage(galleryIndex - 1);
				}
			});
		}
		if (modalNext) {
			modalNext.addEventListener("click", function (e) {
				e.preventDefault();
				e.stopPropagation();
				if (modalMode === "image" && galleryItems.length > 1) {
					showGalleryImage(galleryIndex + 1);
				}
			});
		}

		document.addEventListener("click", function (e) {
			var img = e.target && e.target.closest(thumbSelector());
			if (img && img.tagName === "IMG") {
				e.preventDefault();
				e.stopPropagation();
				openImage(img);
				return;
			}
			var vid = e.target && e.target.closest(videoSelector());
			if (vid) {
				var src = vid.getAttribute("data-video-src") || "";
				if (src) {
					e.preventDefault();
					e.stopPropagation();
					openVideo(src, vid);
				}
				return;
			}
			if (modal && !modal.hidden) {
				if (e.target === modal) closeModal();
				if (modalClose && e.target === modalClose) closeModal();
			}
		});

		document.addEventListener("keydown", function (e) {
			if (!modal || modal.hidden) return;
			if (e.key === "Escape") {
				if (cssFullscreenOn || nativeFullscreenEl()) {
					e.preventDefault();
					exitAllFullscreen();
					return;
				}
				closeModal();
				return;
			}
			if (modalMode === "image" && galleryItems.length > 1) {
				if (e.key === "ArrowLeft") {
					e.preventDefault();
					showGalleryImage(galleryIndex - 1);
				} else if (e.key === "ArrowRight") {
					e.preventDefault();
					showGalleryImage(galleryIndex + 1);
				}
			}
		});
	}

	function resolveNodes() {
		modal = document.getElementById("euMediaModal");
		if (!modal) return false;
		modalPanel = modal.querySelector(".eu-media-modal__panel");
		modalBody = document.getElementById("euMediaModalBody");
		modalClose = document.getElementById("euMediaModalClose");
		modalFs = document.getElementById("euMediaModalFs");
		modalPrev = document.getElementById("euMediaModalPrev");
		modalNext = document.getElementById("euMediaModalNext");
		modalFooter = document.getElementById("euMediaModalFooter");
		modalShare = document.getElementById("euMediaModalShare");
		return !!(modalBody && modalClose);
	}

	function init(userOpts) {
		opts = userOpts || {};
		if (!resolveNodes()) return null;
		if (!initialized) {
			bindEvents();
			initialized = true;
		}
		return {
			openImage: openImage,
			openVideo: openVideo,
			close: closeModal
		};
	}

	global.EuMediaModal = {
		init: init,
		close: function () {
			closeModal();
		}
	};
})(window);
