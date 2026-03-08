/**
 * La completare corectă / date unice: ascunde mesajele de eroare roșii când
 * utilizatorul modifică câmpurile (input/change).
 */
(function() {
	'use strict';

	function hideEl(el) {
		if (el) el.style.setProperty('display', 'none', 'important');
	}

	function setupForm(form) {
		if (!form) return;
		var entryContent = form.closest('.entry-content');
		var errornote = entryContent ? entryContent.querySelector('.errornote') : null;
		if (!errornote && form.previousElementSibling && form.previousElementSibling.classList && form.previousElementSibling.classList.contains('errornote')) {
			errornote = form.previousElementSibling;
		}

		function hideFieldError(control) {
			var block = control.closest('p') || control.closest('.reg-block') || control.closest('div');
			if (block) {
				block.querySelectorAll('.form-error').forEach(hideEl);
			}
		}

		function onInputOrChange() {
			if (errornote) hideEl(errornote);
			hideFieldError(this);
		}

		form.querySelectorAll('input, select, textarea').forEach(function(control) {
			control.addEventListener('input', onInputOrChange);
			control.addEventListener('change', onInputOrChange);
		});
	}

	function init() {
		var forms = document.querySelectorAll('.auth-page .login-form, .auth-page #signup-form');
		forms.forEach(setupForm);
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();
