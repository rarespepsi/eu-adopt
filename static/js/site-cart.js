// Coș I Love: toggle pe carduri + badge navbar
(function () {
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

	/** Cookie (dacă există) sau input din pagină (ex. Magazin foto: #smfCsrfHolder). */
	function getCsrfToken() {
		var c = getCookie('csrftoken');
		if (c) return c;
		var inp = document.querySelector('input[name=csrfmiddlewaretoken]');
		return inp && inp.value ? inp.value : '';
	}

	function toggleUrl() {
		return (document.body.getAttribute('data-site-cart-toggle-url') || '').trim() || '/site-cart/toggle/';
	}

	function setCartActive(btn, active) {
		if (!btn) return;
		btn.classList.toggle('is-active', !!active);
		btn.setAttribute('aria-pressed', active ? 'true' : 'false');
	}

	function updateNavCartCount(n) {
		document.querySelectorAll('[data-site-cart-count]').forEach(function (el) {
			el.textContent = String(n);
		});
	}

	function syncAllByRefKey(refKey, active) {
		if (!refKey) return;
		document.querySelectorAll('[data-site-cart-toggle][data-ref-key]').forEach(function (b) {
			if ((b.getAttribute('data-ref-key') || '') === refKey) {
				setCartActive(b, active);
			}
		});
	}

	function postToggle(btn) {
		var kind = btn.getAttribute('data-kind') || '';
		var refKey = btn.getAttribute('data-ref-key') || '';
		var title = btn.getAttribute('data-title') || '';
		var detailUrl = btn.getAttribute('data-detail-url') || '';
		var fd = new URLSearchParams();
		fd.set('kind', kind);
		fd.set('ref_key', refKey);
		fd.set('title', title);
		fd.set('detail_url', detailUrl);
		btn.setAttribute('aria-busy', 'true');
		fetch(toggleUrl(), {
			method: 'POST',
			credentials: 'same-origin',
			headers: {
				'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
				'X-CSRFToken': getCsrfToken()
			},
			body: fd.toString()
		})
			.then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
			.then(function (x) {
				if (!x.ok || !x.d || !x.d.ok) {
					if (x.d && x.d.error === 'login_required') return;
					return;
				}
				var act = !!x.d.active;
				setCartActive(btn, act);
				syncAllByRefKey(x.d.ref_key, act);
				if (typeof x.d.user_site_cart_count === 'number') {
					updateNavCartCount(x.d.user_site_cart_count);
				}
				// Elimină rândul din coș pe I Love
				if (document.body.classList.contains('page-ilove') && !act) {
					var row = btn.closest('.ilove-cart-row');
					if (row && row.parentNode) row.remove();
					var list = document.querySelector('.ilove-cart-list');
					if (list && !list.querySelector('.ilove-cart-row')) {
						var empty = document.createElement('p');
						empty.className = 'ilove-cart-empty';
						empty.textContent = 'Nu ai produse în coș. Apasă coșul pe oferte sau în Shop.';
						list.appendChild(empty);
					}
				}
			})
			.catch(function () {})
			.finally(function () {
				btn.removeAttribute('aria-busy');
			});
	}

	function bind(btn) {
		if (!btn || btn.__siteCartBound) return;
		btn.__siteCartBound = true;
		if (!isAuth()) {
			btn.setAttribute('data-require-login', '1');
			return;
		}
		btn.addEventListener('click', function (e) {
			e.preventDefault();
			e.stopPropagation();
			postToggle(btn);
		}, true);
	}

	function init() {
		document.querySelectorAll('[data-site-cart-toggle]').forEach(bind);
	}

	window.euadoptSiteCartBindRoot = function (root) {
		if (!root || !root.querySelectorAll) return;
		root.querySelectorAll('[data-site-cart-toggle]').forEach(bind);
	};

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();
