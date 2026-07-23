/**
 * PUB EU direct — luni liber/ocupat, crop +/- , media exclusivă, preview pe wire.
 */
(function () {
  "use strict";
  var form = document.getElementById("pubEuUploadForm");
  if (!form) return;

  var slot = (form.getAttribute("data-eu-slot") || "").trim();
  var section = (form.getAttribute("data-eu-section") || "home").trim();
  var hasServerMedia = form.getAttribute("data-eu-has-media") === "1";
  var keepMediaEl = document.getElementById("pubEuKeepMedia");
  var startEl = document.getElementById("pubEuStartDate");
  var endEl = document.getElementById("pubEuEndDate");
  var imageEl = document.getElementById("pubEuImage");
  var videoEl = document.getElementById("pubEuVideo");
  var linkEl = document.getElementById("pubEuLink");
  var plainEl = document.getElementById("pubEuPlain");
  var cropBox = document.getElementById("pubEuCropBox");
  var cropTools = document.getElementById("pubEuCropTools");
  var btnPost = document.getElementById("pubEuBtnPost");
  var btnMod = document.getElementById("pubEuBtnMod");
  var btnClearMedia = document.getElementById("pubEuBtnClearMedia");
  var monthsRoot = document.getElementById("pubEuMonths");
  var cropper = null;
  var objectUrl = null;
  var mediaCleared = false;
  var isBurtiera = section === "home" && slot === "Burtieră";
  var submitting = false;

  function revokeUrl() {
    if (objectUrl) {
      try {
        URL.revokeObjectURL(objectUrl);
      } catch (_e) {}
      objectUrl = null;
    }
  }

  function destroyCropper() {
    if (cropper) {
      try {
        cropper.destroy();
      } catch (_e) {}
      cropper = null;
    }
    if (cropTools) cropTools.hidden = true;
  }

  function setCropEmpty(text) {
    if (!cropBox) return;
    destroyCropper();
    revokeUrl();
    cropBox.innerHTML = "";
    var span = document.createElement("span");
    span.className = "pub-eu-crop-empty";
    span.id = "pubEuCropEmpty";
    span.textContent = text || "Imagine / video";
    cropBox.appendChild(span);
  }

  function slotAspectRatio() {
    if (!slot) return 4 / 3;
    var node = document.querySelector('[data-slot="' + slot.replace(/"/g, "") + '"]');
    if (!node) return 4 / 3;
    var preview = node.querySelector(".reclama-slot-preview") || node;
    var r = preview.getBoundingClientRect();
    if (r.width > 8 && r.height > 8) return r.width / r.height;
    var r2 = node.getBoundingClientRect();
    if (r2.width > 8 && r2.height > 8) return r2.width / r2.height;
    return 4 / 3;
  }

  function applyCropBoxAspect() {
    var ar = slotAspectRatio();
    if (cropBox) cropBox.style.setProperty("--eu-crop-ar", String(ar));
    return ar;
  }

  function initCropperOn(img) {
    if (typeof Cropper === "undefined" || !img) return;
    destroyCropper();
    var ar = applyCropBoxAspect();
    cropper = new Cropper(img, {
      aspectRatio: ar,
      viewMode: 1,
      dragMode: "move",
      autoCropArea: 1,
      restore: false,
      guides: true,
      center: true,
      highlight: false,
      cropBoxMovable: true,
      cropBoxResizable: true,
      zoomOnWheel: true,
      wheelZoomRatio: 0.12,
    });
    if (cropTools) cropTools.hidden = false;
  }

  function showImageFile(file) {
    if (!cropBox || !file) return;
    destroyCropper();
    revokeUrl();
    objectUrl = URL.createObjectURL(file);
    cropBox.innerHTML = "";
    var img = document.createElement("img");
    img.id = "pubEuCropImg";
    img.alt = "";
    img.src = objectUrl;
    cropBox.appendChild(img);
    img.onload = function () {
      initCropperOn(img);
    };
  }

  function showVideoFile(file) {
    if (!cropBox || !file) return;
    destroyCropper();
    revokeUrl();
    objectUrl = URL.createObjectURL(file);
    cropBox.innerHTML = "";
    var video = document.createElement("video");
    video.id = "pubEuCropVideo";
    video.src = objectUrl;
    video.controls = true;
    video.muted = true;
    video.playsInline = true;
    cropBox.appendChild(video);
  }

  function hasImageFile() {
    return !!(imageEl && imageEl.files && imageEl.files[0]);
  }
  function hasVideoFile() {
    return !!(videoEl && videoEl.files && videoEl.files[0]);
  }

  function canPublish() {
    if (!slot) return false;
    if (!startEl || !endEl || !startEl.value || !endEl.value) return false;
    if (startEl.value > endEl.value) return false;
    if (isBurtiera) {
      var plain = (plainEl && plainEl.value) || "";
      var link = (linkEl && linkEl.value) || "";
      return !!(plain.trim() || link.trim());
    }
    if (hasImageFile() || hasVideoFile()) return true;
    if ((linkEl && linkEl.value.trim()) || "") return true;
    if (hasServerMedia && !mediaCleared && keepMediaEl && keepMediaEl.value === "1") return true;
    return false;
  }

  function refreshButtons() {
    var ok = canPublish();
    if (btnPost) btnPost.disabled = !ok;
    if (btnMod) btnMod.disabled = !ok;
  }

  function syncMonthPicks() {
    if (!monthsRoot || !startEl || !endEl) return;
    var s = startEl.value;
    var e = endEl.value;
    monthsRoot.querySelectorAll(".pub-eu-cal-day[data-iso]").forEach(function (btn) {
      var iso = btn.getAttribute("data-iso") || "";
      var picked = !!(s && e && iso && iso >= s && iso <= e);
      btn.classList.toggle("is-picked", picked);
    });
  }

  var pickAnchor = null;
  if (monthsRoot) {
    monthsRoot.addEventListener("click", function (ev) {
      var btn = ev.target && ev.target.closest(".pub-eu-cal-day[data-iso]");
      if (!btn || !startEl || !endEl) return;
      var iso = btn.getAttribute("data-iso") || "";
      if (!iso) return;
      if (!pickAnchor || ev.shiftKey) {
        pickAnchor = iso;
        startEl.value = iso;
        endEl.value = iso;
      } else {
        if (iso < pickAnchor) {
          startEl.value = iso;
          endEl.value = pickAnchor;
        } else {
          startEl.value = pickAnchor;
          endEl.value = iso;
        }
        pickAnchor = null;
      }
      syncMonthPicks();
      refreshButtons();
    });
  }

  function paintWirePreview(url, isVideo) {
    if (!slot || !url) return;
    var node = document.querySelector('[data-slot="' + slot.replace(/"/g, "") + '"]');
    if (!node) return;
    var preview = node.querySelector(".reclama-slot-preview");
    if (!preview) {
      preview = document.createElement("div");
      preview.className = "reclama-slot-preview";
      node.appendChild(preview);
    }
    preview.classList.add("has-eu-live-preview");
    preview.innerHTML = "";
    if (isVideo) {
      var v = document.createElement("video");
      v.src = url;
      v.muted = true;
      v.autoplay = true;
      v.loop = true;
      v.playsInline = true;
      preview.appendChild(v);
    } else {
      var img = document.createElement("img");
      img.className = "eu-wire-prev";
      img.alt = "";
      img.src = url;
      preview.appendChild(img);
    }
  }

  function getCroppedBlob(cb) {
    if (!cropper) {
      cb(null);
      return;
    }
    var canvas = cropper.getCroppedCanvas({
      maxWidth: 1600,
      maxHeight: 1600,
      imageSmoothingEnabled: true,
      imageSmoothingQuality: "high",
    });
    if (!canvas) {
      cb(null);
      return;
    }
    canvas.toBlob(
      function (blob) {
        cb(blob || null);
      },
      "image/jpeg",
      0.9
    );
  }

  function assignFileToInput(input, blob, name) {
    if (!input || !blob || typeof DataTransfer === "undefined") return false;
    try {
      var dt = new DataTransfer();
      dt.items.add(new File([blob], name || "eu-crop.jpg", { type: blob.type || "image/jpeg" }));
      input.files = dt.files;
      return true;
    } catch (_e) {
      return false;
    }
  }

  if (startEl) startEl.addEventListener("change", function () {
    syncMonthPicks();
    refreshButtons();
  });
  if (endEl) endEl.addEventListener("change", function () {
    syncMonthPicks();
    refreshButtons();
  });
  if (linkEl) linkEl.addEventListener("input", refreshButtons);
  if (plainEl) plainEl.addEventListener("input", refreshButtons);

  if (imageEl) {
    imageEl.addEventListener("change", function () {
      if (hasImageFile()) {
        if (videoEl) videoEl.value = "";
        mediaCleared = false;
        if (keepMediaEl) keepMediaEl.value = "1";
        showImageFile(imageEl.files[0]);
        paintWirePreview(URL.createObjectURL(imageEl.files[0]), false);
      }
      refreshButtons();
    });
  }
  if (videoEl) {
    videoEl.addEventListener("change", function () {
      if (hasVideoFile()) {
        if (imageEl) imageEl.value = "";
        destroyCropper();
        mediaCleared = false;
        if (keepMediaEl) keepMediaEl.value = "1";
        showVideoFile(videoEl.files[0]);
        paintWirePreview(URL.createObjectURL(videoEl.files[0]), true);
      }
      refreshButtons();
    });
  }

  var zoomIn = document.getElementById("pubEuZoomIn");
  var zoomOut = document.getElementById("pubEuZoomOut");
  if (zoomIn) {
    zoomIn.addEventListener("click", function () {
      if (cropper) cropper.zoom(0.1);
    });
  }
  if (zoomOut) {
    zoomOut.addEventListener("click", function () {
      if (cropper) cropper.zoom(-0.1);
    });
  }

  if (btnClearMedia) {
    btnClearMedia.addEventListener("click", function () {
      mediaCleared = true;
      if (keepMediaEl) keepMediaEl.value = "0";
      if (imageEl) imageEl.value = "";
      if (videoEl) videoEl.value = "";
      setCropEmpty("Imagine / video");
      var node = document.querySelector('[data-slot="' + slot.replace(/"/g, "") + '"]');
      if (node) {
        var preview = node.querySelector(".reclama-slot-preview");
        if (preview) {
          preview.classList.remove("has-eu-live-preview");
          preview.innerHTML = "";
        }
      }
      refreshButtons();
      // Persistă ștergerea media pe server dacă exista
      if (hasServerMedia && slot) {
        var hidden = document.createElement("input");
        hidden.type = "hidden";
        hidden.name = "action";
        hidden.value = "clear_media";
        form.appendChild(hidden);
        form.submit();
      }
    });
  }

  // Init cropper pe imaginea existentă de pe server
  applyCropBoxAspect();
  var existingImg = document.getElementById("pubEuCropImg");
  if (existingImg && typeof Cropper !== "undefined") {
    initCropperOn(existingImg);
  }

  form.addEventListener("submit", function (ev) {
    if (submitting) return;
    var submitter = ev.submitter;
    var actionVal = (submitter && submitter.value) || "publish";
    if (actionVal === "clear") return;
    if (!canPublish()) {
      ev.preventDefault();
      return;
    }
    if (actionVal === "publish") {
      ev.preventDefault();
      function doSubmit() {
        submitting = true;
        var act = document.createElement("input");
        act.type = "hidden";
        act.name = "action";
        act.value = "publish";
        form.appendChild(act);
        HTMLFormElement.prototype.submit.call(form);
      }
      if (cropper) {
        getCroppedBlob(function (blob) {
          if (blob) {
            assignFileToInput(imageEl, blob, "eu-crop.jpg");
            if (videoEl) videoEl.value = "";
            if (keepMediaEl) keepMediaEl.value = "0";
            paintWirePreview(URL.createObjectURL(blob), false);
          }
          setTimeout(doSubmit, 100);
        });
        return;
      }
      if (hasVideoFile()) {
        paintWirePreview(URL.createObjectURL(videoEl.files[0]), true);
      } else if (hasImageFile()) {
        paintWirePreview(URL.createObjectURL(imageEl.files[0]), false);
      } else if (existingImg && existingImg.src) {
        paintWirePreview(existingImg.src, false);
      }
      setTimeout(doSubmit, 120);
    }
  });

  // Preview media existentă pe wire la încărcare
  if (slot && hasServerMedia) {
    var exVid = document.getElementById("pubEuCropVideo");
    if (exVid && exVid.src) paintWirePreview(exVid.src, true);
    else if (existingImg && existingImg.src) paintWirePreview(existingImg.src, false);
  }

  syncMonthPicks();
  refreshButtons();
})();
