(function () {
	"use strict";

	const tokenStorageKey = "dongyi_api_admin_session_token";
	const legacyTokenStorageKey = "dongyi_api_admin_token";
	const namePattern = /^[A-Za-z0-9_-]{1,64}$/;

	const state = {
		handles: [],
		token: sessionStorage.getItem(tokenStorageKey) || "",
		tokenConfigured: false,
		storeError: "",
		isSaving: false,
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
		storeAlert: $("#storeAlert"),
		storeErrorText: $("#storeErrorText"),
		resetStore: $("#resetStore"),
		handleCount: $("#handleCount"),
		attributeCount: $("#attributeCount"),
		refreshHandles: $("#refreshHandles"),
		handlesList: $("#handlesList"),
		createHandleForm: $("#createHandleForm"),
		newHandle: $("#newHandle"),
		createPairs: $("#createPairs"),
		addCreatePair: $("#addCreatePair"),
		bulkEditBar: $("#bulkEditBar"),
		bulkEditSummary: $("#bulkEditSummary"),
		cancelAllChanges: $("#cancelAllChanges"),
		saveAllChanges: $("#saveAllChanges"),
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

	function valueSignature(value) {
		return JSON.stringify({ type: valueType(value), value });
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
			const error = new Error(detail);
			error.status = response.status;
			error.payload = payload;
			if (response.status === 401) {
				lockApp("Token was rejected. Enter the admin token to unlock again.");
			}
			throw error;
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
			await requestJson("/_admin/api/session");
			sessionStorage.setItem(tokenStorageKey, state.token);
			setUnlocked();
			await loadHandles();
			if (!quiet) {
				showToast("Unlocked.");
			}
		} catch (error) {
			if (error.status === 401 || error.status === 503) {
				state.token = "";
				sessionStorage.removeItem(tokenStorageKey);
				setLocked("Token was not accepted. Check it and try again.", "warning");
				if (!quiet) {
					showToast(error.message, true);
				}
				return;
			}

			setUnlocked();
			showStoreError(error.message);
			if (!quiet) {
				showToast(error.message, true);
			}
		}
	}

	function setUnlocked() {
		state.unlocked = true;
		document.body.classList.remove("is-locked");
		document.body.classList.add("is-unlocked");
		elements.unlockScreen.hidden = true;
		elements.appShell.hidden = false;
		renderHandles();
	}

	function setLocked(message, tone) {
		state.unlocked = false;
		state.handles = [];
		state.storeError = "";
		document.body.classList.add("is-locked");
		document.body.classList.remove("is-unlocked");
		elements.appShell.hidden = true;
		elements.unlockScreen.hidden = false;
		elements.storeAlert.hidden = true;
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
		state.storeError = "";
		state.handles = data.handles || [];
		elements.handleCount.textContent = data.handle_count || 0;
		elements.attributeCount.textContent = data.attribute_count || 0;
		elements.storeAlert.hidden = true;
		renderHandles();
	}

	function showStoreError(message) {
		state.storeError = message;
		state.handles = [];
		elements.handleCount.textContent = "!";
		elements.attributeCount.textContent = "!";
		elements.storeErrorText.textContent = message;
		elements.storeAlert.hidden = false;
		renderHandles();
	}

	function handleStoreRequestError(error) {
		if (error.status && error.status >= 500) {
			showStoreError(error.message);
		}
		showToast(error.message, true);
	}

	function findHandle(handle) {
		return state.handles.find((item) => item.handle === handle);
	}

	function dirtyRows() {
		return $$("form.kv-row.is-dirty", elements.handlesList);
	}

	function hasDirtyRows() {
		return dirtyRows().length > 0;
	}

	function inputValueSignature(raw) {
		return valueSignature(parseFlatValue(raw));
	}

	function updateBulkBar() {
		const count = dirtyRows().length;
		const hasChanges = count > 0;
		elements.bulkEditBar.hidden = !hasChanges;
		elements.bulkEditSummary.textContent = `${count} unsaved ${count === 1 ? "change" : "changes"}`;
		elements.cancelAllChanges.disabled = !hasChanges || state.isSaving;
		elements.saveAllChanges.disabled = !hasChanges || state.isSaving;
	}

	function updateRowDirty(row) {
		const attributeInput = $('input[name="attribute"]', row);
		const valueInput = $('textarea[name="value"]', row);
		const saveButton = $("[data-save-attribute]", row);
		let isDirty = false;
		let isInvalid = false;

		try {
			const nextAttribute = validateName(normalizeName(attributeInput.value), "Key");
			const nextValueSignature = inputValueSignature(valueInput.value);
			isDirty = nextAttribute !== row.dataset.originalAttribute || nextValueSignature !== row.dataset.originalValueSignature;
		} catch (_error) {
			isDirty = true;
			isInvalid = true;
		}

		row.classList.toggle("is-dirty", isDirty);
		row.classList.toggle("is-invalid", isInvalid);
		saveButton.disabled = !isDirty || state.isSaving;
		updateBulkBar();
		return isDirty;
	}

	function updateRowOriginal(row, attribute, value) {
		const inputValue = valueToInput(value);
		row.dataset.attribute = attribute;
		row.dataset.originalAttribute = attribute;
		row.dataset.originalValueInput = inputValue;
		row.dataset.originalValueSignature = valueSignature(value);
		$('input[name="attribute"]', row).value = attribute;
		$('textarea[name="value"]', row).value = inputValue;

		const typeBadge = $(".value-type", row);
		typeBadge.textContent = valueType(value);
		typeBadge.title = displayValue(value);
		updateRowDirty(row);
	}

	function resetRowToOriginal(row) {
		$('input[name="attribute"]', row).value = row.dataset.originalAttribute;
		$('textarea[name="value"]', row).value = row.dataset.originalValueInput;
		updateRowDirty(row);
	}

	function updateRenameDirty(form, handle) {
		const input = $('input[name="handle"]', form);
		const button = $("[data-save-handle]", form);
		button.disabled = normalizeName(input.value) === handle || state.isSaving;
	}

	function collectCardAttributes(card) {
		const attributes = {};
		$$("form.kv-row", card).forEach((row) => {
			const attribute = validateName(normalizeName($('input[name="attribute"]', row).value), "Key");
			if (Object.prototype.hasOwnProperty.call(attributes, attribute)) {
				throw new Error(`Duplicate key '${attribute}' in /${card.dataset.handle}.`);
			}
			attributes[attribute] = parseFlatValue($('textarea[name="value"]', row).value);
		});
		return attributes;
	}

	function updateStateHandle(handle, attributes) {
		const item = findHandle(handle);
		if (!item) {
			return;
		}
		item.attributes = attributes;
		item.attribute_count = Object.keys(attributes).length;
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
			updateBulkBar();
			return;
		}

		if (state.handles.length === 0) {
			elements.handlesList.innerHTML = state.storeError
				? '<div class="empty-state">Repair the store file above before handles can be listed or edited.</div>'
				: '<div class="empty-state">No handles yet. Create one below to start serving JSON.</div>';
			updateBulkBar();
			return;
		}

		state.handles.forEach((item) => {
			elements.handlesList.appendChild(renderHandleCard(item));
		});
		updateBulkBar();
	}

	function renderHandleCard(item) {
		const card = document.createElement("article");
		card.className = "handle-card";
		card.dataset.handle = item.handle;

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
					<button type="submit" class="button small" data-save-handle>Save path</button>
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
		const renameForm = $(".handle-rename-form", card);
		$('input[name="handle"]', renameForm).addEventListener("input", () => updateRenameDirty(renameForm, item.handle));
		updateRenameDirty(renameForm, item.handle);

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

		renameForm.addEventListener("submit", (event) => renameHandle(event, item.handle));
		$("[data-delete-handle]", card).addEventListener("click", () => deleteHandle(item.handle));
		$(".add-pair-form", card).addEventListener("submit", (event) => addAttribute(event, item));

		return card;
	}

	function renderAttributeRow(item, attribute, value) {
		const row = document.createElement("form");
		row.className = "kv-row";
		row.dataset.handle = item.handle;
		row.dataset.attribute = attribute;
		row.dataset.originalAttribute = attribute;
		row.dataset.originalValueInput = valueToInput(value);
		row.dataset.originalValueSignature = valueSignature(value);

		row.innerHTML = `
			<input name="attribute" type="text" pattern="[A-Za-z0-9_-]{1,64}" required aria-label="Key" />
			<textarea name="value" rows="2" spellcheck="false" aria-label="Value"></textarea>
			<span class="value-type" title="${escapeHtml(displayValue(value))}">${escapeHtml(valueType(value))}</span>
			<div class="row-actions">
				<button type="submit" class="button small" data-save-attribute disabled>Save</button>
				<button type="button" class="button small danger" data-delete-attribute>Delete</button>
			</div>
		`;

		$('input[name="attribute"]', row).value = attribute;
		$('textarea[name="value"]', row).value = valueToInput(value);
		$('input[name="attribute"]', row).addEventListener("input", () => updateRowDirty(row));
		$('textarea[name="value"]', row).addEventListener("input", () => updateRowDirty(row));
		row.addEventListener("submit", (event) => saveAttribute(event, item));
		$("[data-delete-attribute]", row).addEventListener("click", () => deleteAttribute(item.handle, row.dataset.attribute));
		updateRowDirty(row);
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
		if (rows.length === 0) {
			throw new Error("Add at least one key/value pair before creating a handle.");
		}

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
		if (state.storeError) {
			showToast("Repair the store file before creating handles.", true);
			return;
		}
		if (hasDirtyRows() && !window.confirm("Creating a handle will refresh the list and discard unsaved key/value edits. Continue?")) {
			return;
		}

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
			handleStoreRequestError(error);
		}
	}

	async function renameHandle(event, currentHandle) {
		event.preventDefault();
		if (hasDirtyRows() && !window.confirm("Renaming a handle will refresh the list and discard unsaved key/value edits. Continue?")) {
			return;
		}

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
			handleStoreRequestError(error);
		}
	}

	async function deleteHandle(handle) {
		const dirtyWarning = hasDirtyRows() ? "\n\nAny unsaved edits currently on the page will be discarded when the list refreshes." : "";
		if (!window.confirm(`Delete /${handle} and all of its key/value pairs?${dirtyWarning}`)) {
			return;
		}

		try {
			await requestJson(`/_admin/api/handles/${encodeURIComponent(handle)}`, { method: "DELETE" });
			await loadHandles();
			showToast(`Deleted /${handle}.`);
		} catch (error) {
			handleStoreRequestError(error);
		}
	}

	async function saveAttribute(event, item) {
		event.preventDefault();
		const row = event.currentTarget;
		const oldAttribute = row.dataset.attribute;
		if (!updateRowDirty(row)) {
			showToast("No changes to save.");
			return;
		}

		let nextAttribute;
		let nextValue;
		try {
			collectCardAttributes(row.closest(".handle-card"));
			nextAttribute = validateName(normalizeName($('input[name="attribute"]', row).value), "Key");
			nextValue = parseFlatValue($('textarea[name="value"]', row).value);
		} catch (error) {
			showToast(error.message, true);
			return;
		}

		try {
			const data = await requestJson(`/_admin/api/handles/${encodeURIComponent(item.handle)}/attributes/${encodeURIComponent(oldAttribute)}`, {
				method: "PATCH",
				body: JSON.stringify({ attribute: nextAttribute, value: nextValue }),
			});
			updateStateHandle(item.handle, data.attributes);
			updateRowOriginal(row, nextAttribute, nextValue);
			showToast(`Saved ${nextAttribute} on /${item.handle}.`);
		} catch (error) {
			handleStoreRequestError(error);
		}
	}

	async function addAttribute(event, item) {
		event.preventDefault();
		if (hasDirtyRows() && !window.confirm("Adding a new key/value pair will refresh the list and discard unsaved edits. Continue?")) {
			return;
		}

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
			handleStoreRequestError(error);
		}
	}

	async function deleteAttribute(handle, attribute) {
		const item = findHandle(handle);
		const willDeleteHandle = item && item.attribute_count === 1;
		const dirtyWarning = hasDirtyRows() ? "\n\nAny unsaved edits currently on the page will be discarded when the list refreshes." : "";
		const message = willDeleteHandle
			? `Delete key '${attribute}' from /${handle}? This is the last key/value pair, so /${handle} will also be deleted and released.${dirtyWarning}`
			: `Delete key '${attribute}' from /${handle}?${dirtyWarning}`;
		if (!window.confirm(message)) {
			return;
		}

		try {
			await requestJson(`/_admin/api/handles/${encodeURIComponent(handle)}/attributes/${encodeURIComponent(attribute)}`, {
				method: "DELETE",
			});
			await loadHandles();
			showToast(willDeleteHandle
				? `Deleted ${attribute}; /${handle} was removed because no key/value pairs remain.`
				: `Deleted ${attribute} from /${handle}.`);
		} catch (error) {
			handleStoreRequestError(error);
		}
	}

	function cancelAllChanges() {
		const rows = dirtyRows();
		rows.forEach(resetRowToOriginal);
		updateBulkBar();
		showToast(`Canceled ${rows.length} unsaved ${rows.length === 1 ? "change" : "changes"}.`);
	}

	async function saveAllChanges() {
		const rows = dirtyRows();
		if (rows.length === 0) {
			return;
		}

		const cards = Array.from(new Set(rows.map((row) => row.closest(".handle-card"))));
		let payloads;
		try {
			payloads = cards.map((card) => ({
				handle: card.dataset.handle,
				attributes: collectCardAttributes(card),
			}));
		} catch (error) {
			showToast(error.message, true);
			return;
		}

		state.isSaving = true;
		updateBulkBar();
		dirtyRows().forEach(updateRowDirty);

		try {
			for (const payload of payloads) {
				await requestJson(`/_admin/api/handles/${encodeURIComponent(payload.handle)}`, {
					method: "PUT",
					body: JSON.stringify({ attributes: payload.attributes }),
				});
			}
			await loadHandles();
			showToast(`Saved ${rows.length} ${rows.length === 1 ? "change" : "changes"}.`);
		} catch (error) {
			handleStoreRequestError(error);
		} finally {
			state.isSaving = false;
			updateBulkBar();
			$$("form.kv-row", elements.handlesList).forEach(updateRowDirty);
		}
	}

	async function resetBrokenStore() {
		if (!state.storeError) {
			showToast("The store is already loading normally.");
			return;
		}

		if (!window.confirm("Reset api_store.json to the default /value handle? The current broken file will be copied to a timestamped backup first.")) {
			return;
		}

		try {
			const data = await requestJson("/_admin/api/store/reset", { method: "POST" });
			applyHandlesData(data);
			const backupNote = data.backup_path ? ` Backup: ${data.backup_path}` : "";
			showToast(`${data.message || "Store reset."}${backupNote}`);
		} catch (error) {
			handleStoreRequestError(error);
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
			loadHandles().then(() => showToast("Refreshed.")).catch(handleStoreRequestError);
		});
		elements.resetStore.addEventListener("click", resetBrokenStore);
		elements.cancelAllChanges.addEventListener("click", cancelAllChanges);
		elements.saveAllChanges.addEventListener("click", saveAllChanges);
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
