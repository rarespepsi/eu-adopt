// Wishlist hearts: toggle + UI update
(function() {
	'use strict';

	function isAuth() {
		return document.body.getAttribute('data-user-authenticated') === 'true';
	}

	function getCookie(name) {
		var value = '; ' + document.cookie;
		var parts = value.split('; ' + name + '=');
		if (parts.length === 2) return parts.pop().split(';').shift();
		return '';
	}

	function setActive(btn, active) {
		if (!btn) return;
		btn.classList.toggle('is-active', !!active);
		btn.setAttribute('aria-pressed', active ? 'true' : 'false');
	}

	function attach(btn) {
		if (!btn || btn.__wishBound) return;
		btn.__wishBound = true;

		// Guest: modal-ul existent se ocupă dacă avem data-require-login
		if (!isAuth()) {
			btn.setAttribute('data-require-login', '1');
			return;
		}

		btn.addEventListener('click', function(e) {
			e.preventDefault();
			e.stopPropagation();

			var animalId = btn.getAttribute('data-animal-id');
			if (!animalId) return;

			var fd = new FormData();
			fd.append('animal_id', animalId);

			fetch('/wishlist/toggle/', {
				method: 'POST',
				credentials: 'same-origin',
				headers: { 'X-CSRFToken': getCookie('csrftoken') },
				body: fd
			}).then(function(r) { return r.json(); }).then(function(data) {
				if (!data || !data.ok) return;
				setActive(btn, !!data.active);

				// Update navbar badge if present
				var nav = document.querySelector('[data-wishlist-count]');
				if (nav && typeof data.user_wishlist_count === 'number') {
					nav.textContent = String(data.user_wishlist_count);
				}

				// Update per-card count if present
				var countEl = btn.querySelector('.wish-count');
				if (countEl && typeof data.wish_count === 'number') {
					countEl.textContent = String(data.wish_count);
				}

				// I Love: la scoatere din listă, elimină cardul din grilă (și mesaj gol dacă nu mai rămâne nimic)
				if (document.body.classList.contains('page-ilove') && data.active === false) {
					var card = btn.closest('.ilove-pet-card');
					if (card && card.parentNode) {
						card.remove();
						var grid = document.querySelector('.ilove-pets-grid');
						if (grid && !grid.querySelector('.ilove-pet-card')) {
							var empty = document.createElement('div');
							empty.className = 'ilove-empty';
							empty.textContent = 'Nu ai niciun câine salvat încă. Apasă inimioara de pe poze.';
							grid.appendChild(empty);
						}
					}
				}
			}).catch(function() {});
		}, true);
	}

	function init() {
		var buttons = document.querySelectorAll('.wish-btn[data-animal-id]');
		buttons.forEach(attach);
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();

