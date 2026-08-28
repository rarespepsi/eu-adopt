/**
 * Upload poze pe mobil — helper partajat (MyPet, campanii, servicii/colaborator, avatar).
 */
(function (global) {
	function isTouchDevice() {
		try {
			return global.matchMedia("(hover: none) and (pointer: coarse)").matches;
		} catch (e) {
			return false;
		}
	}

	function isAcceptableImageFile(file) {
		if (!file) return false;
		var t = (file.type || "").toLowerCase();
		if (t.indexOf("image/") === 0) return true;
		return /\.(jpe?g|png|gif|webp|heic|heif|bmp)$/i.test(file.name || "");
	}

	function compressImageFileToJpeg(file, opts, done) {
		if (typeof opts === "function") {
			done = opts;
			opts = {};
		}
		opts = opts || {};
		var maxDim = opts.maxDim || 1600;
		var quality = opts.quality || 0.9;
		var square = !!opts.square;

		var reader = new FileReader();
		reader.onerror = function () {
			done(null);
		};
		reader.onload = function (ev) {
			var img = new Image();
			img.onerror = function () {
				done(null);
			};
			img.onload = function () {
				var sw = img.naturalWidth || img.width;
				var sh = img.naturalHeight || img.height;
				if (!sw || !sh) {
					done(null);
					return;
				}
				var sx = 0;
				var sy = 0;
				var cw = sw;
				var ch = sh;
				if (square) {
					var side = Math.min(sw, sh);
					sx = Math.floor((sw - side) / 2);
					sy = Math.floor((sh - side) / 2);
					cw = side;
					ch = side;
				}
				var w = cw;
				var h = ch;
				if (w > maxDim || h > maxDim) {
					if (w >= h) {
						h = Math.round(h * maxDim / w);
						w = maxDim;
					} else {
						w = Math.round(w * maxDim / h);
						h = maxDim;
					}
				}
				var canvas = document.createElement("canvas");
				canvas.width = w;
				canvas.height = h;
				var ctx = canvas.getContext("2d");
				if (!ctx) {
					done(null);
					return;
				}
				ctx.drawImage(img, sx, sy, cw, ch, 0, 0, w, h);
				canvas.toBlob(function (blob) {
					done(blob);
				}, "image/jpeg", quality);
			};
			img.src = ev.target.result;
		};
		reader.readAsDataURL(file);
	}

	global.EuPhotoUpload = {
		isTouchDevice: isTouchDevice,
		isAcceptableImageFile: isAcceptableImageFile,
		compressImageFileToJpeg: compressImageFileToJpeg,
		IMAGE_ACCEPT: "image/*,.heic,.heif",
	};
})(window);
