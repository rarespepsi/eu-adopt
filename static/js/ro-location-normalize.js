/**
 * Județe / localități RO — formă canonică (diacritice, potrivire fără diacritice).
 * Necesită fetch la ro_counties_cities.json (setează window.RO_COUNTIES_CITIES_URL).
 */
(function (global) {
	"use strict";

	var COUNTIES = [
		"Alba", "Arad", "Argeș", "Bacău", "Bihor", "Bistrița-Năsăud", "Botoșani", "Brăila", "Brașov",
		"București", "Buzău", "Călărași", "Caraș-Severin", "Cluj", "Constanța", "Covasna", "Dâmbovița",
		"Dolj", "Galați", "Giurgiu", "Gorj", "Harghita", "Hunedoara", "Ialomița", "Iași", "Ilfov",
		"Maramureș", "Mehedinți", "Mureș", "Neamț", "Olt", "Prahova", "Sălaj", "Satu Mare", "Sibiu",
		"Suceava", "Teleorman", "Timiș", "Tulcea", "Vâlcea", "Vaslui", "Vrancea"
	];

	var localitiesByCounty = {};
	var cityIndexByCounty = {};
	var dataReady = false;
	var readyQueue = [];

	function fold(s) {
		return String(s || "")
			.normalize("NFD")
			.replace(/[\u0300-\u036f]/g, "")
			.toLowerCase()
			.replace(/\s+/g, " ")
			.trim();
	}

	function foldKey(s) {
		return fold(s).replace(/[\s\-_]+/g, " ").trim();
	}

	function buildCityIndex(county) {
		var list = localitiesByCounty[county] || [];
		var idx = {};
		for (var i = 0; i < list.length; i++) {
			var k = foldKey(list[i]);
			if (k && !idx[k]) idx[k] = list[i];
		}
		cityIndexByCounty[county] = idx;
	}

	function resolveCounty(raw) {
		var text = String(raw || "").trim();
		if (!text) return "";
		var key = foldKey(text);
		for (var i = 0; i < COUNTIES.length; i++) {
			if (foldKey(COUNTIES[i]) === key) return COUNTIES[i];
		}
		return text;
	}

	function resolveLocality(raw, county) {
		var text = String(raw || "").trim();
		if (!text) return "";
		var countyCanon = resolveCounty(county);
		var key = foldKey(text);
		if (countyCanon) {
			if (!cityIndexByCounty[countyCanon]) buildCityIndex(countyCanon);
			var hit = cityIndexByCounty[countyCanon][key];
			if (hit) return hit;
			return text;
		}
		for (var c = 0; c < COUNTIES.length; c++) {
			var cn = COUNTIES[c];
			if (!cityIndexByCounty[cn]) buildCityIndex(cn);
			hit = cityIndexByCounty[cn][key];
			if (hit) return hit;
		}
		return text;
	}

	function suggestLocalities(raw, county, limit) {
		limit = limit || 12;
		var countyCanon = resolveCounty(county);
		var list = localitiesByCounty[countyCanon] || [];
		var key = foldKey(raw);
		if (!key) return list.slice(0, limit);
		var hits = [];
		for (var i = 0; i < list.length; i++) {
			if (foldKey(list[i]).indexOf(key) !== -1) hits.push(list[i]);
			if (hits.length >= limit) break;
		}
		return hits;
	}

	function normalizeCountyInput(el) {
		if (!el) return;
		var v = resolveCounty(el.value);
		if (v) el.value = v;
	}

	function normalizeLocalityInput(el, countyEl) {
		if (!el) return;
		var county = countyEl ? countyEl.value : "";
		var v = resolveLocality(el.value, county);
		if (v) el.value = v;
	}

	function updateCityDatalist(countyInput, cityList) {
		if (!countyInput || !cityList) return;
		var county = resolveCounty(countyInput.value);
		cityList.innerHTML = "";
		if (!county || !localitiesByCounty[county]) return;
		var list = localitiesByCounty[county];
		for (var i = 0; i < list.length; i++) {
			var opt = document.createElement("option");
			opt.value = list[i];
			cityList.appendChild(opt);
		}
	}

	function wireCountyLocality(countyInputId, cityListId, cityInputId) {
		var countyInput = document.getElementById(countyInputId);
		var cityList = cityListId ? document.getElementById(cityListId) : null;
		var cityInput = cityInputId ? document.getElementById(cityInputId) : null;
		if (!countyInput) return;
		function refresh() {
			updateCityDatalist(countyInput, cityList);
		}
		function onCountyBlur() {
			normalizeCountyInput(countyInput);
			refresh();
		}
		function onCityBlur() {
			normalizeLocalityInput(cityInput || { value: "" }, countyInput);
		}
		countyInput.addEventListener("input", refresh);
		countyInput.addEventListener("change", onCountyBlur);
		countyInput.addEventListener("blur", onCountyBlur);
		if (cityInput) {
			cityInput.addEventListener("blur", onCityBlur);
			cityInput.addEventListener("change", onCityBlur);
		}
		refresh();
	}

	function whenReady(fn) {
		if (dataReady) fn();
		else readyQueue.push(fn);
	}

	function loadData(url) {
		var u = url || global.RO_COUNTIES_CITIES_URL || "/static/data/ro_counties_cities.json";
		return fetch(u).then(function (r) { return r.json(); }).then(function (data) {
			localitiesByCounty = data || {};
			dataReady = true;
			for (var i = 0; i < readyQueue.length; i++) readyQueue[i]();
			readyQueue = [];
		}).catch(function () {
			dataReady = true;
			for (var j = 0; j < readyQueue.length; j++) readyQueue[j]();
			readyQueue = [];
		});
	}

	global.RoLocation = {
		COUNTIES: COUNTIES,
		foldKey: foldKey,
		resolveCounty: resolveCounty,
		resolveLocality: resolveLocality,
		suggestLocalities: suggestLocalities,
		normalizeCountyInput: normalizeCountyInput,
		normalizeLocalityInput: normalizeLocalityInput,
		wireCountyLocality: wireCountyLocality,
		whenReady: whenReady,
		loadData: loadData
	};

	loadData();
})(typeof window !== "undefined" ? window : this);
