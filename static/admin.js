(function () {
	"use strict";

	const tokenStorageKey = "dongyi_api_admin_token";
	const state = {
		handles: [],
		selectedHandle: null,
		token: localStorage.getItem(tokenStorageKey) || "",
		tokenConfigured: false,
	};

	const $ = (selector, root = document) => root.querySelector(selector);
	const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

	const elements = {
		adminToken: $("#adminToken"),
		tokenForm: $("#tokenForm"),
		clearToken: $("#clearToken"),
		tokenStatus: $("#tokenStatus"),
		handleCount: $("#handleCount"),
		attributeCount: $("#attributeCount"),
		selectedPath: $("#selectedPath"),
		createHandleForm: $("#createHandleForm"),
		newHandle: $("#newHandle"),
		newHandleJson: $("#newHandleJson"),
		refreshHandles: $("#refreshHandles"),
		handlesList: $("#handlesList"),
		emptyEditor: $("#emptyEditor"),
		editorContent: $("#editorContent"),
		renameHandleForm: $("#renameHandleForm"),
		renameHandle: $("#renameHandle"),
		openSelected: $("#openSelected"),
		deleteHandle: $("#deleteHandle"),
		selectedAttributeCount: $("#selectedAttributeCount"),
		attributesList: $("#attributesList"),
		addAttributeForm: $("#addAttributeForm"),
		newAttribute: $("#newAttribute"),
		newAttributeValue: $("#newAttributeValue"),
		fullJsonForm: $("#fullJsonForm"),
		fullJson: $("#fullJson"),
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

	function normalizeName(value) {
		return value.trim().replace(/^\/+|\/+$/g, "");
	}

	function parseJsonish(raw) {
		const trimmed = raw.trim();
		if (trimmed === "") {
			return "";
		}
		try {
			return JSON.parse(trimmed);
		} catch (_error) {
			return trimmed;
		}
	}

	function parseJsonObject(raw) {
		const parsed = JSON.parse(raw);
		if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
			throw new Error("Expected a JSON object.");
		}
		return parsed;
	}

	function formatJson(value) {
		return JSON.stringify(value, null, 2);
	}

	function adminHeaders() {
		return {
			"Content-Type": "application/json",
			"X-Admin-Token": state.token,
		};
	}

	async function requestJson(url, options = {}) {
		const response = await fetch(url, {
			...options,
			headers: {
				...(options.body ? adminHeaders() : { "X-Admin-Token": state.token }),
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
			throw new Error(detail);
		}
		return payload;
	}

	async function loadConfig() {
		const response = await fetch("/_admin/api/config");
		const config = await response.json();
		state.tokenConfigured = Boolean(config.admin_token_configured);
		if (!state.tokenConfigured) {
			elements.tokenStatus.textContent = "Set API_ADMIN_TOKEN in systemd before editing is enabled.";
			elements.tokenStatus.className = "form-note warning";
			return;
		}

		if (state.token) {
			elements.adminToken.value = state.token;
			elements.tokenStatus.textContent = "Token loaded from this browser.";
			elements.tokenStatus.className = "form-note ok";
			await loadHandles();
		} else {
			elements.tokenStatus.textContent = "Enter the server admin token to load and save APIs.";
			elements.tokenStatus.className = "form-note";
		}
	}

	async function loadHandles() {
		if (!state.token) {
			showToast("Enter the admin token first.", true);
			return;
		}

		const data = await requestJson("/_admin/api/handles");
		state.handles = data.handles || [];
		elements.handleCount.textContent = data.handle_count || 0;
		elements.attributeCount.textContent = data.attribute_count || 0;
		renderHandles();

		if (state.selectedHandle && !findHandle(state.selectedHandle)) {
			state.selectedHandle = null;
		}
		if (!state.selectedHandle && state.handles.length > 0) {
			state.selectedHandle = state.handles[0].handle;
		}
		renderEditor();
	}

	function findHandle(handle) {
		return state.handles.find((item) => item.handle === handle);
	}

	function publicUrl(path) {
		return `${window.location.origin}${path}`;
	}

	function renderHandles() {
		if (state.handles.length === 0) {
			elements.handlesList.innerHTML = '<div class="empty-state">No handles yet.</div>';
			return;
		}

		elements.handlesList.innerHTML = "";
		state.handles.forEach((item) => {
			const button = document.createElement("button");
			button.type = "button";
			button.className = "handle-item";
			button.classList.toggle("active", item.handle === state.selectedHandle);
			button.innerHTML = `
				<span class="handle-path">${item.path}</span>
				<span class="handle-meta">${item.attribute_count} attributes</span>
			`;
			button.addEventListener("click", () => {
				state.selectedHandle = item.handle;
				renderHandles();
				renderEditor();
			});
			elements.handlesList.appendChild(button);
		});
	}

	function renderEditor() {
		const selected = state.selectedHandle ? findHandle(state.selectedHandle) : null;
		if (!selected) {
			elements.emptyEditor.hidden = false;
			elements.editorContent.hidden = true;
			elements.openSelected.href = "#";
			elements.selectedPath.textContent = "none";
			return;
		}

		elements.emptyEditor.hidden = true;
		elements.editorContent.hidden = false;
		elements.renameHandle.value = selected.handle;
		elements.openSelected.href = publicUrl(selected.path);
		elements.selectedPath.textContent = selected.path;
		elements.fullJson.value = formatJson(selected.attributes);

		const entries = Object.entries(selected.attributes);
		elements.selectedAttributeCount.textContent = `${entries.length} ${entries.length === 1 ? "attribute" : "attributes"}`;
		elements.attributesList.innerHTML = "";

		if (entries.length === 0) {
			elements.attributesList.innerHTML = '<div class="empty-state">This handle has no attributes.</div>';
			return;
		}

		entries.forEach(([attribute, value]) => {
			const row = document.createElement("form");
			row.className = "attribute-row";
			row.dataset.attribute = attribute;
			row.innerHTML = `
				<label>Attribute</label>
				<input name="attribute" value="${escapeHtml(attribute)}" pattern="[A-Za-z0-9_-]{1,64}" required />
				<label>Value</label>
				<textarea name="value" rows="3" spellcheck="false">${escapeHtml(formatJson(value))}</textarea>
				<button type="submit" class="button small">Save</button>
				<button type="button" class="button small danger" data-delete-attribute>Delete</button>
			`;
			row.addEventListener("submit", saveAttribute);
			$("[data-delete-attribute]", row).addEventListener("click", () => deleteAttribute(attribute));
			elements.attributesList.appendChild(row);
		});
	}

	function escapeHtml(value) {
		return String(value)
			.replaceAll("&", "&amp;")
			.replaceAll("<", "&lt;")
			.replaceAll(">", "&gt;")
			.replaceAll('"', "&quot;");
	}

	async function createHandle(event) {
		event.preventDefault();
		const handle = normalizeName(elements.newHandle.value);
		let attributes;
		try {
			attributes = parseJsonObject(elements.newHandleJson.value);
		} catch (error) {
			showToast(error.message, true);
			return;
		}

		try {
			await requestJson("/_admin/api/handles", {
				method: "POST",
				body: JSON.stringify({ handle, attributes }),
			});
			state.selectedHandle = handle;
			elements.newHandle.value = "";
			await loadHandles();
			showToast(`Created /${handle}.`);
		} catch (error) {
			showToast(error.message, true);
		}
	}

	async function renameHandle(event) {
		event.preventDefault();
		const selected = state.selectedHandle;
		const nextHandle = normalizeName(elements.renameHandle.value);
		if (!selected || !nextHandle) {
			return;
		}

		try {
			await requestJson(`/_admin/api/handles/${encodeURIComponent(selected)}`, {
				method: "PATCH",
				body: JSON.stringify({ handle: nextHandle }),
			});
			state.selectedHandle = nextHandle;
			await loadHandles();
			showToast(`Renamed to /${nextHandle}.`);
		} catch (error) {
			showToast(error.message, true);
		}
	}

	async function deleteSelectedHandle() {
		const selected = state.selectedHandle;
		if (!selected) {
			return;
		}
		if (!window.confirm(`Delete /${selected} and all of its attributes?`)) {
			return;
		}

		try {
			await requestJson(`/_admin/api/handles/${encodeURIComponent(selected)}`, { method: "DELETE" });
			state.selectedHandle = null;
			await loadHandles();
			showToast(`Deleted /${selected}.`);
		} catch (error) {
			showToast(error.message, true);
		}
	}

	async function saveAttribute(event) {
		event.preventDefault();
		const selected = state.selectedHandle;
		const row = event.currentTarget;
		const oldAttribute = row.dataset.attribute;
		const nextAttribute = normalizeName($('input[name="attribute"]', row).value);
		const nextValue = parseJsonish($('textarea[name="value"]', row).value);
		const body = { attribute: nextAttribute, value: nextValue };

		try {
			await requestJson(`/_admin/api/handles/${encodeURIComponent(selected)}/attributes/${encodeURIComponent(oldAttribute)}`, {
				method: "PATCH",
				body: JSON.stringify(body),
			});
			await loadHandles();
			showToast(`Saved ${nextAttribute}.`);
		} catch (error) {
			showToast(error.message, true);
		}
	}

	async function deleteAttribute(attribute) {
		const selected = state.selectedHandle;
		if (!selected || !window.confirm(`Delete attribute '${attribute}' from /${selected}?`)) {
			return;
		}

		try {
			await requestJson(`/_admin/api/handles/${encodeURIComponent(selected)}/attributes/${encodeURIComponent(attribute)}`, {
				method: "DELETE",
			});
			await loadHandles();
			showToast(`Deleted ${attribute}.`);
		} catch (error) {
			showToast(error.message, true);
		}
	}

	async function addAttribute(event) {
		event.preventDefault();
		const selected = state.selectedHandle;
		const attribute = normalizeName(elements.newAttribute.value);
		const value = parseJsonish(elements.newAttributeValue.value);
		if (!selected) {
			showToast("Select a handle first.", true);
			return;
		}

		try {
			await requestJson(`/_admin/api/handles/${encodeURIComponent(selected)}/attributes/${encodeURIComponent(attribute)}`, {
				method: "PUT",
				body: JSON.stringify({ value }),
			});
			elements.newAttribute.value = "";
			elements.newAttributeValue.value = "43";
			await loadHandles();
			showToast(`Added ${attribute}.`);
		} catch (error) {
			showToast(error.message, true);
		}
	}

	async function saveFullJson(event) {
		event.preventDefault();
		const selected = state.selectedHandle;
		let attributes;
		try {
			attributes = parseJsonObject(elements.fullJson.value);
		} catch (error) {
			showToast(error.message, true);
			return;
		}

		try {
			await requestJson(`/_admin/api/handles/${encodeURIComponent(selected)}`, {
				method: "PUT",
				body: JSON.stringify({ attributes }),
			});
			await loadHandles();
			showToast(`Saved /${selected}.`);
		} catch (error) {
			showToast(error.message, true);
		}
	}

	function saveToken(event) {
		event.preventDefault();
		state.token = elements.adminToken.value.trim();
		if (state.token) {
			localStorage.setItem(tokenStorageKey, state.token);
			elements.tokenStatus.textContent = "Token saved in this browser.";
			elements.tokenStatus.className = "form-note ok";
			loadHandles().catch((error) => showToast(error.message, true));
		}
	}

	function clearToken() {
		state.token = "";
		localStorage.removeItem(tokenStorageKey);
		elements.adminToken.value = "";
		state.handles = [];
		state.selectedHandle = null;
		elements.tokenStatus.textContent = "Token cleared.";
		elements.tokenStatus.className = "form-note";
		renderHandles();
		renderEditor();
		elements.handleCount.textContent = "-";
		elements.attributeCount.textContent = "-";
	}

	function bindEvents() {
		elements.tokenForm.addEventListener("submit", saveToken);
		elements.clearToken.addEventListener("click", clearToken);
		elements.refreshHandles.addEventListener("click", () => {
			loadHandles().catch((error) => showToast(error.message, true));
		});
		elements.createHandleForm.addEventListener("submit", createHandle);
		elements.renameHandleForm.addEventListener("submit", renameHandle);
		elements.deleteHandle.addEventListener("click", deleteSelectedHandle);
		elements.addAttributeForm.addEventListener("submit", addAttribute);
		elements.fullJsonForm.addEventListener("submit", saveFullJson);
	}

	function init() {
		bindEvents();
		renderHandles();
		renderEditor();
		loadConfig().catch((error) => showToast(error.message, true));
	}

	document.addEventListener("DOMContentLoaded", init);
})();
