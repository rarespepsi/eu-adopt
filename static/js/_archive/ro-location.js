/**
 * Romania County + City dependent dropdowns.
 * Loads ro_counties_cities.json (by_slug: { "neamt": ["Piatra Neamț", ...], ... }).
 * Use data-ro-location="1" on wrapper; inside: select[data-ro-county], select[data-ro-city], optional input[data-ro-city-manual].
 * Optional on wrapper: data-ro-user-judet, data-ro-user-oras for pre-fill.
 */
(function () {
	"use strict";

	var DATA_URL = window.RO_COUNTIES_CITIES_URL || "/api/ro-counties-cities.json";
	var cache = null;

	function getData(cb) {
		if (cache && cache.by_slug) {
			cb(cache);
			return;
		}
		var xhr = new XMLHttpRequest();
		xhr.open("GET", DATA_URL, true);
		xhr.onload = function () {
			if (xhr.status >= 200 && xhr.status < 300) {
				try {
					cache = JSON.parse(xhr.responseText);
					cb(cache);
				} catch (e) {
					cb({ by_slug: {} });
				}
			} else {
				cb({ by_slug: {} });
			}
		};
		xhr.onerror = function () {
			cb({ by_slug: {} });
		};
		xhr.send();
	}

	function fillCitySelect(select, cities, selectedValue) {
		if (!select || select.nodeName !== "SELECT") return;
		select.innerHTML = "";
		var first = document.createElement("option");
		first.value = "";
		first.textContent = "— Alege orașul —";
		first.selected = true;
		select.appendChild(first);
		var found = false;
		(cities || []).forEach(function (name) {
			var opt = document.createElement("option");
			opt.value = name;
			opt.textContent = name;
			if (selectedValue && name.toLowerCase() === selectedValue.toLowerCase()) {
				opt.selected = true;
				found = true;
			}
			select.appendChild(opt);
		});
		select.disabled = false;
	}

	function bindPair(wrapper) {
		var countySelect = wrapper.querySelector("select[data-ro-county]");
		if (!countySelect) {
			var countySel = wrapper.getAttribute("data-ro-county-selector");
			countySelect = countySel ? document.querySelector(countySel) : null;
		}
		var citySelect = wrapper.querySelector("select[data-ro-city]");
		var cityManual = wrapper.querySelector("input[data-ro-city-manual]");
		var outSel = wrapper.getAttribute("data-ro-city-output");
		var cityOutput = outSel ? document.querySelector(outSel) : wrapper.querySelector("input[data-ro-city-output]") || null;
		var userJudet = (wrapper.getAttribute("data-ro-user-judet") || "").trim();
		var userOras = (wrapper.getAttribute("data-ro-user-oras") || "").trim();

		if (!countySelect) return;

		function updateCity(slug, preferValue) {
			var cities = cache && cache.by_slug && cache.by_slug[slug];
			if (citySelect) {
				if (cities && cities.length > 0) {
					citySelect.style.display = "block";
					citySelect.removeAttribute("disabled");
					if (!cityOutput) {
						citySelect.setAttribute("name", citySelect.getAttribute("data-ro-city-name") || "oras");
						citySelect.setAttribute("required", "required");
					} else {
						citySelect.removeAttribute("name");
						citySelect.removeAttribute("required");
					}
					fillCitySelect(citySelect, cities, preferValue);
					if (cityOutput && citySelect.value) cityOutput.value = citySelect.value;
					if (cityManual) {
						cityManual.style.display = "none";
						cityManual.removeAttribute("name");
						cityManual.removeAttribute("required");
						cityManual.value = "";
					}
					var hint = wrapper.querySelector("[data-ro-city-hint]");
					if (hint) { hint.textContent = ""; hint.style.display = "none"; }
				} else {
					citySelect.innerHTML = "";
					var emptyOpt = document.createElement("option");
					emptyOpt.value = "";
					emptyOpt.textContent = "— Introduceți localitatea mai jos —";
					emptyOpt.selected = true;
					citySelect.appendChild(emptyOpt);
					citySelect.disabled = true;
					citySelect.style.display = "none";
					citySelect.removeAttribute("name");
					citySelect.removeAttribute("required");
					if (cityManual) {
						cityManual.style.display = "block";
						cityManual.setAttribute("name", cityManual.getAttribute("data-ro-city-name") || "oras");
						cityManual.setAttribute("required", "required");
						if (preferValue) cityManual.value = preferValue;
					}
					var hint = wrapper.querySelector("[data-ro-city-hint]");
					if (hint) { hint.textContent = "Pentru acest județ introduceți localitatea mai jos."; hint.style.display = ""; }
				}
			}
		}

		countySelect.addEventListener("change", function () {
			updateCity((countySelect.value || "").trim(), "");
		});
		if (cityOutput && citySelect) {
			citySelect.addEventListener("change", function () {
				if (citySelect.value) cityOutput.value = citySelect.value;
			});
		}

		getData(function () {
			var slug = (countySelect.value || "").trim();
			if (slug) {
				updateCity(slug, userOras);
			} else if (userJudet) {
				var opt = Array.prototype.find.call(countySelect.options, function (o) {
					return o.value === userJudet;
				});
				if (opt) {
					countySelect.value = userJudet;
					updateCity(userJudet, userOras);
				}
			}
		});
	}

	function init() {
		var wrappers = document.querySelectorAll("[data-ro-location=\"1\"]");
		wrappers.forEach(bindPair);
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", init);
	} else {
		init();
	}
})();
