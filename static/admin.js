(function () {
	"use strict";

	const tokenStorageKey = "dongyi_api_admin_session_token";
	const legacyTokenStorageKey = "dongyi_api_admin_token";
	const namePattern = /^[A-Za-z0-9_-]{1,64}$/;

	const state = {
		handles: [],
		token: sessionStorage.getItem(tokenStorageKey) || "",
		tokenConfigured: false,
		unlocked: false,
	};

	const $ = (selector, root = document) => root.querySelector(selector);
	const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

	const elements = {
		unlockScreen: $("#unlockScreen"),
		appShell: $("#appShell"),
		unlockForm: $("#unlockForm"),
		unlockToken: $("#unlockToken"),
		unlockStatus: $("#unlockStatus"),
		lockButton: $("#lockButton"),
		handleCount: $("#handleCount"),
		attributeCount: $("#attributeCount"),
		refreshHandles: $("#refreshHandles"),
		handlesList: $("#handlesList"),
		createHandleForm: $("#createHandleForm"),
		newHandle: $("#newHandle"),
		createPairs: $("#createPairs"),
		addCreatePair: $("#addCreatePair"),
		toast: $("#toast"),
	};

	function showToast(message, isError) {
		elements.toast.textContent = message;
		elements.toast.classList.toggle("error", Boolean(isError));
		elements.toast.classList.add("show");
		window.clearTimeout(showToast.timeoutId);
		showToast.timeoutId = window.setTimeout(() => {
			elements.toast.classList.remove("show");
		}, 3200);
	}

	function setUnlockStatus(message, tone) {
		elements.unlockStatus.textContent = message;
		elements.unlockStatus.className = `form-note${tone ? ` ${tone}` : ""}`;
	}

	function normalizeName(value) {
		return value.trim().replace(/^\/+|\/+$/g, "");
	}

	function validateName(value, label) {
		if (!namePattern.test(value)) {
			throw new Error(`${label} must be 1-64 letters, numbers, underscores, or hyphens.`);
		}
		return value;
	}

	function parseFlatValue(raw) {
		const trimmed = raw.trim();
		if (trimmed === "") {
			return "";
		}

		let parsed;
		try {
			parsed = JSON.parse(trimmed);
		} catch (_error) {
			return raw;
		}

		if (parsed && typeof parsed === "object") {
			throw new Error("Values must stay flat. Objects and arrays are not allowed inside a handle.");
		}
		return parsed;
	}

	function valueToInput(value) {
		if (typeof value === "string") {
			return value;
		}
		return JSON.stringify(value);
	}

	function valueType(value) {
		if (value === null) {
			return "null";
		}
		if (Array.isArray(value)) {
			return "array";
		}
		return typeof value;
	}

	function displayValue(value) {
		if (typeof value === "string") {
			return value === "" ? '""' : value;
		}
		return JSON.stringify(value);
	}

	function adminHeaders(hasBody) {
		const headers = { "X-Admin-Token": state.token };
		if (hasBody) {
			headers["Content-Type"] = "application/json";
		}
		return headers;
	}

	async function requestJson(url, options = {}) {
		const response = await fetch(url, {
			...options,
			headers: {
				...adminHeaders(Boolean(options.body)),
				...(options.headers || {}),
			},
		});

		if (response.status === 204) {
			return null;
		}

		let payload = null;
		try {
			payload = await response.json();
		} catch (_error) {
			payload = null;
		}

		if (!response.ok) {
			const detail = payload && payload.detail ? payload.detail : `${response.status} ${response.statusText}`;
			if (response.status === 401) {
				lockApp("Token was rejected. Enter the admin token to unlock again.");
			}
			throw new Error(detail);
		}
		return payload;
	}

	async function loadConfig() {
		const response = await fetch("/_admin/api/config");
		const config = await response.json();
		state.tokenConfigured = Boolean(config.admin_token_configured);

		if (!state.tokenConfigured) {
			setUnlockStatus("API_ADMIN_TOKEN is not set on the server, so admin editing is disabled.", "warning");
			return;
		}

		if (state.token) {
			elements.unlockToken.value = state.token;
			setUnlockStatus("Unlocking with this browser session...", "");
			await unlockWithToken(state.token, true);
			return;
		}

		setUnlockStatus("Enter the server admin token to unlock the manager.", "");
	}

	async function unlockWithToken(token, quiet) {
		state.token = token.trim();
		if (!state.token) {
			setUnlockStatus("Enter the server admin token to unlock the manager.", "warning");
			return;
		}

		try {
			const data = await requestJson("/_admin/api/handles");
			sessionStorage.setItem(tokenStorageKey, state.token);
			setUnlocked(data);
			if (!quiet) {
				showToast("Unlocked.");
			}
		} catch (error) {
			state.token = "";
			sessionStorage.removeItem(tokenStorageKey);
			setLocked("Token was not accepted. Check it and try again.", "warning");
			if (!quiet) {
				showToast(error.message, true);
			}
		}
	}

	function setUnlocked(data) {
		state.unlocked = true;
		document.body.classList.remove("is-locked");
		document.body.classList.add("is-unlocked");
		elements.unlockScreen.hidden = true;
		elements.appShell.hidden = false;
		applyHandlesData(data);
	}

	function setLocked(message, tone) {
		state.unlocked = false;
		state.handles = [];
		document.body.classList.add("is-locked");
		document.body.classList.remove("is-unlocked");
		elements.appShell.hidden = true;
		elements.unlockScreen.hidden = false;
		elements.handleCount.textContent = "0";
		elements.attributeCount.textContent = "0";
		renderHandles();
		if (message) {
			setUnlockStatus(message, tone);
		}
	}

	function lockApp(message) {
		state.token = "";
		sessionStorage.removeItem(tokenStorageKey);
		elements.unlockToken.value = "";
		setLocked(message || "Locked. Enter the admin token to unlock the manager.", "");
	}

	function applyHandlesData(data) {
		state.handles = data.handles || [];
		elements.handleCount.textContent = data.handle_count || 0;
		elements.attributeCount.textContent = data.attribute_count || 0;
		renderHandles();
	}

	async function loadHandles() {
		if (!state.token) {
			lockApp("Enter the admin token to unlock the manager.");
			return;
		}
		const data = await requestJson("/_admin/api/handles");
		applyHandlesData(data);
	}

	function publicUrl(path) {
		return `${window.location.origin}${path}`;
	}

	function renderHandles() {
		elements.handlesList.innerHTML = "";

		if (!state.unlocked) {
			return;
		}

		if (state.handles.length === 0) {
			elements.handlesList.innerHTML = '<div class="empty-state">No handles yet. Create one below to start serving JSON.</div>';
			return;
		}

		state.handles.forEach((item) => {
			elements.handlesList.appendChild(renderHandleCard(item));
		});
	}

	function renderHandleCard(item) {
		const card = document.createElement("article");
		card.className = "handle-card";

		card.innerHTML = `
			<div class="handle-card-header">
				<div>
					<p class="handle-path">${escapeHtml(item.path)}</p>
					<p class="handle-meta">${item.attribute_count} ${item.attribute_count === 1 ? "pair" : "pairs"} at <code>GET/POST ${escapeHtml(item.path)}</code></p>
				</div>
				<div class="handle-actions">
					<a class="button small" href="${escapeHtml(publicUrl(item.path))}" target="_blank" rel="noreferrer">Open API</a>
					<button type="button" class="button small danger" data-delete-handle>Delete handle</button>
				</div>
			</div>

			<form class="handle-rename-form">
				<label>Handle path</label>
				<div class="inline-controls">
					<div class="prefixed-input grow">
						<span>/</span>
						<input name="handle" type="text" pattern="[A-Za-z0-9_-]{1,64}" required />
					</div>
					<button type="submit" class="button small">Save path</button>
				</div>
			</form>

			<div class="kv-list"></div>

			<form class="add-pair-form">
				<label>Add key/value pair</label>
				<div class="kv-row add-row">
					<input name="attribute" type="text" placeholder="key" pattern="[A-Za-z0-9_-]{1,64}" required aria-label="New key" />
					<textarea name="value" rows="2" spellcheck="false" placeholder="value" aria-label="New value"></textarea>
					<button type="submit" class="button primary small">Add pair</button>
				</div>
			</form>
		`;

		$('input[name="handle"]', card).value = item.handle;
		const keyValueList = $(".kv-list", card);
		const entries = Object.entries(item.attributes);

		if (entries.length === 0) {
			keyValueList.innerHTML = '<div class="empty-state compact">This handle currently returns <code>{}</code>.</div>';
		} else {
			const header = document.createElement("div");
			header.className = "kv-header";
			header.innerHTML = "<span>Key</span><span>Value</span><span>Type</span><span>Actions</span>";
			keyValueList.appendChild(header);
			entries.forEach(([attribute, value]) => {
				keyValueList.appendChild(renderAttributeRow(item, attribute, value));
			});
		}

		$(".handle-rename-form", card).addEventListener("submit", (event) => renameHandle(event, item.handle));
		$("[data-delete-handle]", card).addEventListener("click", () => deleteHandle(item.handle));
		$(".add-pair-form", card).addEventListener("submit", (event) => addAttribute(event, item));

		return card;
	}

	function renderAttributeRow(item, attribute, value) {
		const row = document.createElement("form");
		row.className = "kv-row";
		row.dataset.attribute = attribute;

		row.innerHTML = `
			<input name="attribute" type="text" pattern="[A-Za-z0-9_-]{1,64}" required aria-label="Key" />
			<textarea name="value" rows="2" spellcheck="false" aria-label="Value"></textarea>
			<span class="value-type" title="${escapeHtml(displayValue(value))}">${escapeHtml(valueType(value))}</span>
			<div class="row-actions">
				<button type="submit" class="button small">Save</button>
				<button type="button" class="button small danger" data-delete-attribute>Delete</button>
			</div>
		`;

		$('input[name="attribute"]', row).value = attribute;
		$('textarea[name="value"]', row).value = valueToInput(value);
		row.addEventListener("submit", (event) => saveAttribute(event, item));
		$("[data-delete-attribute]", row).addEventListener("click", () => deleteAttribute(item.handle, attribute));
		return row;
	}

	function addCreatePairRow(attribute = "", value = "") {
		const row = document.createElement("div");
		row.className = "pair-row";
		row.innerHTML = `
			<label>
				<span>Key</span>
				<input name="attribute" type="text" placeholder="value" pattern="[A-Za-z0-9_-]{1,64}" required />
			</label>
			<label>
				<span>Value</span>
				<textarea name="value" rows="2" spellcheck="false" placeholder="42"></textarea>
			</label>
			<button type="button" class="button small danger" data-remove-pair>Remove</button>
		`;
		$('input[name="attribute"]', row).value = attribute;
		$('textarea[name="value"]', row).value = value;
		$("[data-remove-pair]", row).addEventListener("click", () => {
			row.remove();
		});
		elements.createPairs.appendChild(row);
	}

	function resetCreateForm() {
		elements.createHandleForm.reset();
		elements.createPairs.innerHTML = "";
		addCreatePairRow("value", "42");
	}

	function collectCreateAttributes() {
		const attributes = {};
		const rows = $$(".pair-row", elements.createPairs);

		rows.forEach((row) => {
			const attribute = validateName(normalizeName($('input[name="attribute"]', row).value), "Key");
			if (Object.prototype.hasOwnProperty.call(attributes, attribute)) {
				throw new Error(`Duplicate key '${attribute}'.`);
			}
			attributes[attribute] = parseFlatValue($('textarea[name="value"]', row).value);
		});

		return attributes;
	}

	async function createHandle(event) {
		event.preventDefault();
		let handle;
		let attributes;
		try {
			handle = validateName(normalizeName(elements.newHandle.value), "Handle");
			attributes = collectCreateAttributes();
		} catch (error) {
			showToast(error.message, true);
			return;
		}

		try {
			await requestJson("/_admin/api/handles", {
				method: "POST",
				body: JSON.stringify({ handle, attributes }),
			});
			resetCreateForm();
			await loadHandles();
			window.location.hash = "handles";
			showToast(`Created /${handle}.`);
		} catch (error) {
			showToast(error.message, true);
		}
	}

	async function renameHandle(event, currentHandle) {
		event.preventDefault();
		let nextHandle;
		try {
			nextHandle = validateName(normalizeName($('input[name="handle"]', event.currentTarget).value), "Handle");
		} catch (error) {
			showToast(error.message, true);
			return;
		}

		if (nextHandle === currentHandle) {
			showToast(`/${currentHandle} is already saved.`);
			return;
		}

		try {
			await requestJson(`/_admin/api/handles/${encodeURIComponent(currentHandle)}`, {
				method: "PATCH",
				body: JSON.stringify({ handle: nextHandle }),
			});
			await loadHandles();
			showToast(`Renamed /${currentHandle} to /${nextHandle}.`);
		} catch (error) {
			showToast(error.message, true);
		}
	}

	async function deleteHandle(handle) {
		if (!window.confirm(`Delete /${handle} and all of its key/value pairs?`)) {
			return;
		}

		try {
			await requestJson(`/_admin/api/handles/${encodeURIComponent(handle)}`, { method: "DELETE" });
			await loadHandles();
			showToast(`Deleted /${handle}.`);
		} catch (error) {
			showToast(error.message, true);
		}
	}

	async function saveAttribute(event, item) {
		event.preventDefault();
		const row = event.currentTarget;
		const oldAttribute = row.dataset.attribute;
		let nextAttribute;
		let nextValue;
		try {
			nextAttribute = validateName(normalizeName($('input[name="attribute"]', row).value), "Key");
			if (nextAttribute !== oldAttribute && Object.prototype.hasOwnProperty.call(item.attributes, nextAttribute)) {
				throw new Error(`Key '${nextAttribute}' already exists on /${item.handle}.`);
			}
			nextValue = parseFlatValue($('textarea[name="value"]', row).value);
		} catch (error) {
			showToast(error.message, true);
			return;
		}

		try {
			await requestJson(`/_admin/api/handles/${encodeURIComponent(item.handle)}/attributes/${encodeURIComponent(oldAttribute)}`, {
				method: "PATCH",
				body: JSON.stringify({ attribute: nextAttribute, value: nextValue }),
			});
			await loadHandles();
			showToast(`Saved ${nextAttribute} on /${item.handle}.`);
		} catch (error) {
			showToast(error.message, true);
		}
	}

	async function addAttribute(event, item) {
		event.preventDefault();
		const form = event.currentTarget;
		let attribute;
		let value;
		try {
			attribute = validateName(normalizeName($('input[name="attribute"]', form).value), "Key");
			if (Object.prototype.hasOwnProperty.call(item.attributes, attribute)) {
				throw new Error(`Key '${attribute}' already exists on /${item.handle}. Edit its row instead.`);
			}
			value = parseFlatValue($('textarea[name="value"]', form).value);
		} catch (error) {
			showToast(error.message, true);
			return;
		}

		try {
			await requestJson(`/_admin/api/handles/${encodeURIComponent(item.handle)}/attributes/${encodeURIComponent(attribute)}`, {
				method: "PUT",
				body: JSON.stringify({ value }),
			});
			form.reset();
			await loadHandles();
			showToast(`Added ${attribute} to /${item.handle}.`);
		} catch (error) {
			showToast(error.message, true);
		}
	}

	async function deleteAttribute(handle, attribute) {
		if (!window.confirm(`Delete key '${attribute}' from /${handle}?`)) {
			return;
		}

		try {
			await requestJson(`/_admin/api/handles/${encodeURIComponent(handle)}/attributes/${encodeURIComponent(attribute)}`, {
				method: "DELETE",
			});
			await loadHandles();
			showToast(`Deleted ${attribute} from /${handle}.`);
		} catch (error) {
			showToast(error.message, true);
		}
	}

	function escapeHtml(value) {
		return String(value)
			.replaceAll("&", "&amp;")
			.replaceAll("<", "&lt;")
			.replaceAll(">", "&gt;")
			.replaceAll('"', "&quot;");
	}

	function bindEvents() {
		elements.unlockForm.addEventListener("submit", (event) => {
			event.preventDefault();
			unlockWithToken(elements.unlockToken.value, false);
		});
		elements.lockButton.addEventListener("click", () => lockApp());
		elements.refreshHandles.addEventListener("click", () => {
			loadHandles().then(() => showToast("Refreshed.")).catch((error) => showToast(error.message, true));
		});
		elements.addCreatePair.addEventListener("click", () => addCreatePairRow());
		elements.createHandleForm.addEventListener("submit", createHandle);
	}

	function init() {
		try {
			localStorage.removeItem(legacyTokenStorageKey);
		} catch (_error) {
			// Ignore storage policy failures; the session token is the only one used now.
		}

		bindEvents();
		resetCreateForm();
		setLocked("", "");
		if (state.token) {
			elements.unlockToken.value = state.token;
		}
		loadConfig().catch((error) => {
			setUnlockStatus("Could not reach the admin service.", "warning");
			showToast(error.message, true);
		});
	}

	document.addEventListener("DOMContentLoaded", init);
})();
