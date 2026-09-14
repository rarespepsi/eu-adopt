/**
 * Benzi cursive (PT P1/P3, Servicii S1/S7): după click pe o casetă (link
 * partener într-un tab nou) sau după Back, animația CSS rămâne adesea oprită
 * — :hover lipit pe touch, sau play-state înghețat la revenirea în tab.
 * Repornim banda când pagina e din nou vizibilă.
 */
(function () {
	"use strict";

	var TRACK_SEL = ".pt-strip-track, .sw-strip-track, .home-v2-burtiera-marquee-track";
	var RESUME_CLASS = "eu-strip-resume";
	var hoverClearBound = false;

	function tracks() {
		return document.querySelectorAll(TRACK_SEL);
	}

	function playTrack(el) {
		el.style.animationPlayState = "running";
		if (typeof el.getAnimations !== "function") return;
		try {
			el.getAnimations().forEach(function (anim) {
				if (typeof anim.updatePlaybackRate === "function") {
					anim.updatePlaybackRate(1);
				}
				anim.play();
			});
		} catch (e) {}
	}

	function bindHoverClear() {
		if (hoverClearBound) return;
		hoverClearBound = true;
		window.addEventListener(
			"mousemove",
			function () {
				if (!document.documentElement.classList.contains(RESUME_CLASS)) return;
				document.documentElement.classList.remove(RESUME_CLASS);
			},
			{ passive: true }
		);
	}

	function resumeStrip() {
		document.documentElement.classList.add(RESUME_CLASS);
		tracks().forEach(playTrack);
		bindHoverClear();
	}

	document.addEventListener("visibilitychange", function () {
		if (!document.hidden) resumeStrip();
	});
	window.addEventListener("pageshow", function (e) {
		if (e.persisted) resumeStrip();
	});

	document.addEventListener(
		"click",
		function (ev) {
			var t = ev.target;
			if (!t || !t.closest) return;
			if (!t.closest(TRACK_SEL)) return;
			resumeStrip();
			var link = t.closest("a");
			if (link && typeof link.blur === "function") {
				try {
					link.blur();
				} catch (e) {}
			}
		},
		true
	);
})();
