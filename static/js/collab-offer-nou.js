/**
 * Adaugă ofertă (My List Vet): previzualizare + Cropper ca la MyPet.
 * Flux: Alege poza → Salvează poza (înghețare decupaj) → Alege poza (schimbă imaginea).
 */
(function () {
	var form =
		document.getElementById("collab-oferte-nou-form") ||
		document.getElementById("collab-oferte-edit-form");
	var fileInput = document.getElementById("id_collab_offer_image");
	var preview = document.getElementById("collab_offer_preview_photo");
	var slot = document.querySelector(".collab-offer-photo-slot");
	if (!form || !fileInput || !preview || !slot) return;

	var editMode = form.getAttribute("data-offer-edit") === "1";

	function hasNewImageWork() {
		return !!(savedBlob || (fileInput.files && fileInput.files[0]) || cropper);
	}

	var cropper = null;
	var savedBlob = null;
	var MAX_BYTES = 2 * 1024 * 1024;

	var PLACEHOLDER_TEXT = editMode
		? "Max 2 MB. Lasă imaginea curentă sau alege una nouă → +/− → Salvează poza → Salvează modificările."
		: "Max 2 MB. Alege poza → reglează cu +/− → Salvează poza → apoi Publică oferta.";

	function getLabelBtn() {
		return document.getElementById("collab_offer_photo_btn_label") || slot.querySelector("label.collab-offer-photo-btn");
	}

	function destroyCropper() {
		if (cropper) {
			cropper.destroy();
			cropper = null;
		}
	}

	function setLabelChoose() {
		var lab = getLabelBtn();
		if (!lab) return;
		lab.textContent = "Alege poza";
		lab.setAttribute("for", "id_collab_offer_image");
	}

	function setLabelSave() {
		var lab = getLabelBtn();
		if (!lab) return;
		lab.textContent = "Salvează poza";
		lab.removeAttribute("for");
	}

	function setPlaceholder() {
		preview.innerHTML = "";
		var ph = document.createElement("span");
		ph.className = "collab-offer-photo-hint";
		ph.textContent = PLACEHOLDER_TEXT;
		preview.appendChild(ph);
	}

	function setHasPhoto(on) {
		if (on) slot.classList.add("has-photo");
		else slot.classList.remove("has-photo");
	}

	function revokePreviewImages() {
		preview.querySelectorAll("img").forEach(function (img) {
			if (img.src && img.src.indexOf("blob:") === 0) URL.revokeObjectURL(img.src);
		});
	}

	function resetPreviewFully() {
		destroyCropper();
		savedBlob = null;
		revokePreviewImages();
		setPlaceholder();
		setHasPhoto(false);
		slot.classList.remove("is-saved");
		setLabelChoose();
		fileInput.value = "";
	}

	function freezePhoto() {
		if (!cropper) return;
		var box = cropper.getCropBoxData();
		var w = Math.round(box.width) || 800;
		var h = Math.round(box.height) || 800;
		var canvas = cropper.getCroppedCanvas({
			width: w,
			height: h,
			imageSmoothingEnabled: true,
			imageSmoothingQuality: "high",
		});
		if (!canvas) return;
		canvas.toBlob(function (blob) {
			if (!blob) return;
			savedBlob = blob;
			destroyCropper();
			revokePreviewImages();
			preview.innerHTML = "";
			var img = document.createElement("img");
			img.className = "img-crop";
			img.alt = "Poză ofertă salvată";
			img.src = URL.createObjectURL(blob);
			img.style.display = "block";
			img.style.width = "100%";
			img.style.height = "100%";
			img.style.objectFit = "cover";
			preview.appendChild(img);
			setHasPhoto(true);
			slot.classList.add("is-saved");
			setLabelChoose();
			fileInput.value = "";
		}, "image/jpeg", 0.9);
	}

	var labelBtn = getLabelBtn();
	if (labelBtn) {
		labelBtn.addEventListener("click", function (e) {
			if (!this.getAttribute("for")) {
				e.preventDefault();
				freezePhoto();
			}
		});
	}

	fileInput.addEventListener("change", function () {
		destroyCropper();
		savedBlob = null;
		slot.classList.remove("is-saved");
		revokePreviewImages();

		var file = fileInput.files && fileInput.files[0];
		if (!file) {
			setPlaceholder();
			setHasPhoto(false);
			setLabelChoose();
			return;
		}
		if (!file.type.match(/^image\//)) {
			alert("Alege un fișier imagine.");
			fileInput.value = "";
			resetPreviewFully();
			return;
		}
		if (file.size > MAX_BYTES) {
			alert("Fișierul este prea mare. Maxim 2 MB.");
			fileInput.value = "";
			resetPreviewFully();
			return;
		}

		preview.innerHTML = "";
		setHasPhoto(true);

		var img = document.createElement("img");
		img.className = "img-crop";
		img.alt = "Previzualizare ofertă";
		img.src = URL.createObjectURL(file);
		preview.appendChild(img);

		if (typeof Cropper === "undefined") {
			setLabelChoose();
			return;
		}

		var w0 = preview.offsetWidth;
		var h0 = preview.offsetHeight;
		var ratio = w0 && h0 ? w0 / h0 : 1;
		cropper = new Cropper(img, {
			aspectRatio: ratio,
			viewMode: 3,
			dragMode: "move",
			autoCropArea: 1,
			restore: false,
			guides: true,
			center: true,
			highlight: false,
			cropBoxMovable: true,
			cropBoxResizable: true,
			ready: function () {
				if (!cropper) return;
				var containerData = cropper.getContainerData();
				var imageData = cropper.getImageData();
				if (!containerData || !imageData || !imageData.width) return;
				var cw = containerData.width;
				var ch = containerData.height;
				var iw = imageData.width;
				var ih = imageData.height;
				var scaleW = cw / iw;
				var scaleH = ch / ih;
				var scale = Math.max(scaleW, scaleH, 1);
				cropper.zoom(scale);
			},
		});
		setLabelSave();
	});

	document.addEventListener("click", function (e) {
		var btn = e.target && e.target.closest(".collab-offer-zoom-btn");
		if (!btn || !cropper) return;
		var action = btn.getAttribute("data-action");
		var delta = action === "in" ? 0.1 : -0.1;
		cropper.zoom(delta);
	});

	function getImageBlob() {
		return new Promise(function (resolve) {
			if (savedBlob) {
				resolve(savedBlob);
				return;
			}
			if (cropper) {
				var box = cropper.getCropBoxData();
				var w = Math.round(box.width) || 800;
				var h = Math.round(box.height) || 800;
				var canvas = cropper.getCroppedCanvas({
					width: w,
					height: h,
					imageSmoothingEnabled: true,
					imageSmoothingQuality: "high",
				});
				if (!canvas) {
					resolve(null);
					return;
				}
				canvas.toBlob(function (blob) {
					resolve(blob);
				}, "image/jpeg", 0.9);
				return;
			}
			var f = fileInput.files && fileInput.files[0];
			if (f && f.type.match(/^image\//)) {
				resolve(f);
				return;
			}
			resolve(null);
		});
	}

	form.addEventListener("submit", function (e) {
		var titleEl = form.querySelector('[name="title"]');
		var title = titleEl && titleEl.value ? String(titleEl.value).trim() : "";
		if (!title) {
			e.preventDefault();
			alert("Completează titlul serviciului.");
			if (titleEl) titleEl.focus();
			return;
		}
		if (editMode && !hasNewImageWork()) {
			return;
		}
		e.preventDefault();
		if (cropper) {
			alert(
				editMode
					? 'Ai o poză nedefinită: apasă „Salvează poza” înainte de a salva modificările.'
					: 'Ai o poză nedefinită: apasă „Salvează poza” înainte de „Publică oferta”.'
			);
			return;
		}
		getImageBlob().then(function (blob) {
			if (!blob) {
				if (editMode) {
					try {
						form.submit();
					} catch (err) {
						alert("Nu s-a putut trimite formularul. Încearcă din nou.");
					}
					return;
				}
				alert("Alege o imagine pentru ofertă și salvează decupajul cu „Salvează poza”.");
				return;
			}
			var fd = new FormData();
			var csrf = form.querySelector("[name=csrfmiddlewaretoken]");
			if (csrf) fd.append("csrfmiddlewaretoken", csrf.value);
			fd.append("title", (form.querySelector('[name="title"]') || {}).value || "");
			fd.append("description", (form.querySelector('[name="description"]') || {}).value || "");
			fd.append("price_hint", (form.querySelector('[name="price_hint"]') || {}).value || "");
			var disc = form.querySelector('[name="discount_percent"]');
			fd.append("discount_percent", disc ? disc.value || "" : "");
			var qty = form.querySelector('[name="quantity_available"]');
			fd.append("quantity_available", qty ? qty.value || "" : "");
			var vf = form.querySelector('[name="valid_from"]');
			var vu = form.querySelector('[name="valid_until"]');
			fd.append("valid_from", vf ? vf.value || "" : "");
			fd.append("valid_until", vu ? vu.value || "" : "");
			fd.append("image", blob, "offer.jpg");
			var action = form.getAttribute("action") || window.location.pathname;
			fetch(action, {
				method: "POST",
				body: fd,
				credentials: "same-origin",
				headers: { Accept: "text/html,application/xhtml+xml" },
			})
				.then(function (res) {
					if (res.redirected && res.url) {
						window.location.href = res.url;
						return;
					}
					if (res.ok) {
						window.location.href = action;
						return;
					}
					window.location.reload();
				})
				.catch(function () {
					alert("Eroare la trimitere. Încearcă din nou.");
				});
		});
	});
})();
