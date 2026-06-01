from __future__ import annotations

import json
import os
import re
import secrets
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = Path(os.getenv("API_STATIC_DIR", BASE_DIR / "static"))
STORE_PATH = Path(os.getenv("API_STORE_PATH", BASE_DIR / "api_store.json"))
ADMIN_TOKEN = os.getenv("API_ADMIN_TOKEN", "")

HANDLE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ATTRIBUTE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
RESERVED_HANDLES = {
    "_admin",
    "admin-assets",
    "docs",
    "redoc",
    "openapi.json",
    "favicon.ico",
}

store_lock = threading.RLock()


class HandleCreate(BaseModel):
    handle: str
    attributes: Dict[str, Any] = Field(default_factory=dict)


class HandleReplace(BaseModel):
    attributes: Dict[str, Any] = Field(default_factory=dict)


class HandleRename(BaseModel):
    handle: str


class AttributeValue(BaseModel):
    value: Any


app = FastAPI(
    title="Dongyi API Manager",
    description="Dynamic JSON endpoints managed from the api.dongyi-guo.top home page.",
    version="1.0.0",
)


def cors_origins() -> list[str]:
    configured = os.getenv("API_CORS_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return ["https://dongyi-guo.top", "https://www.dongyi-guo.top"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/admin-assets", StaticFiles(directory=STATIC_DIR), name="admin-assets")


def default_store() -> Dict[str, Dict[str, Any]]:
    return {"value": {"value": 42}}


def normalize_name(value: str) -> str:
    return value.strip().strip("/")


def validate_handle(handle: str, *, public_lookup: bool = False) -> str:
    normalized = normalize_name(handle)
    if not HANDLE_RE.fullmatch(normalized):
        status_code = 404 if public_lookup else 400
        raise HTTPException(status_code=status_code, detail="Handle must be 1-64 letters, numbers, underscores, or hyphens.")
    if normalized in RESERVED_HANDLES:
        status_code = 404 if public_lookup else 400
        raise HTTPException(status_code=status_code, detail=f"'{normalized}' is reserved and cannot be used as an API handle.")
    return normalized


def validate_attribute(attribute: str) -> str:
    normalized = normalize_name(attribute)
    if not ATTRIBUTE_RE.fullmatch(normalized):
        raise HTTPException(status_code=400, detail="Attribute must be 1-64 letters, numbers, underscores, or hyphens.")
    return normalized


def ensure_json_value(value: Any) -> Any:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Value is not valid JSON: {exc}") from exc
    return value


def validate_attributes(attributes: Dict[str, Any]) -> Dict[str, Any]:
    validated: Dict[str, Any] = {}
    for attribute, value in attributes.items():
        validated[validate_attribute(attribute)] = ensure_json_value(value)
    return validated


def read_store_unlocked() -> Dict[str, Dict[str, Any]]:
    if not STORE_PATH.exists():
        write_store_unlocked(default_store())

    try:
        raw = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"API store JSON is invalid: {exc}") from exc

    if not isinstance(raw, dict):
        raise HTTPException(status_code=500, detail="API store must be a JSON object.")

    store: Dict[str, Dict[str, Any]] = {}
    for handle, attributes in raw.items():
        valid_handle = validate_handle(str(handle))
        if not isinstance(attributes, dict):
            raise HTTPException(status_code=500, detail=f"Handle '{valid_handle}' must contain a JSON object.")
        store[valid_handle] = validate_attributes(attributes)
    return store


def write_store_unlocked(store: Dict[str, Dict[str, Any]]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(store, indent=2, sort_keys=True, allow_nan=False) + "\n"
    tmp_path = STORE_PATH.with_name(f"{STORE_PATH.name}.tmp")
    tmp_path.write_text(payload, encoding="utf-8")
    os.replace(tmp_path, STORE_PATH)


def read_store() -> Dict[str, Dict[str, Any]]:
    with store_lock:
        return read_store_unlocked()


def save_store(store: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    with store_lock:
        write_store_unlocked(store)
        return read_store_unlocked()


def require_admin(request: Request) -> None:
    if not ADMIN_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Admin editing is disabled until API_ADMIN_TOKEN is set for the FastAPI service.",
        )

    supplied = request.headers.get("x-admin-token", "")
    if not secrets.compare_digest(supplied, ADMIN_TOKEN):
        raise HTTPException(status_code=401, detail="Missing or invalid admin token.")


def handle_summary(handle: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "handle": handle,
        "path": f"/{handle}",
        "attribute_count": len(attributes),
        "attributes": attributes,
    }


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=500, detail=f"Missing admin page: {index_path}")
    return FileResponse(index_path)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/_admin/api/config", include_in_schema=False)
def admin_config() -> Dict[str, Any]:
    return {
        "admin_token_configured": bool(ADMIN_TOKEN),
        "handle_pattern": HANDLE_RE.pattern,
        "attribute_pattern": ATTRIBUTE_RE.pattern,
    }


@app.get("/_admin/api/handles", dependencies=[Depends(require_admin)])
def list_handles() -> Dict[str, Any]:
    store = read_store()
    handles = [handle_summary(handle, store[handle]) for handle in sorted(store)]
    attribute_count = sum(len(attributes) for attributes in store.values())
    return {
        "handles": handles,
        "handle_count": len(handles),
        "attribute_count": attribute_count,
    }


@app.post("/_admin/api/handles", status_code=201, dependencies=[Depends(require_admin)])
def create_handle(payload: HandleCreate) -> Dict[str, Any]:
    handle = validate_handle(payload.handle)
    attributes = validate_attributes(payload.attributes)

    with store_lock:
        store = read_store_unlocked()
        if handle in store:
            raise HTTPException(status_code=409, detail=f"Handle '/{handle}' already exists.")
        store[handle] = attributes
        write_store_unlocked(store)

    return handle_summary(handle, attributes)


@app.put("/_admin/api/handles/{handle}", dependencies=[Depends(require_admin)])
def replace_handle(handle: str, payload: HandleReplace) -> Dict[str, Any]:
    handle = validate_handle(handle)
    attributes = validate_attributes(payload.attributes)

    with store_lock:
        store = read_store_unlocked()
        if handle not in store:
            raise HTTPException(status_code=404, detail=f"Handle '/{handle}' does not exist.")
        store[handle] = attributes
        write_store_unlocked(store)

    return handle_summary(handle, attributes)


@app.patch("/_admin/api/handles/{handle}", dependencies=[Depends(require_admin)])
def rename_handle(handle: str, payload: HandleRename) -> Dict[str, Any]:
    old_handle = validate_handle(handle)
    new_handle = validate_handle(payload.handle)

    with store_lock:
        store = read_store_unlocked()
        if old_handle not in store:
            raise HTTPException(status_code=404, detail=f"Handle '/{old_handle}' does not exist.")
        if new_handle != old_handle and new_handle in store:
            raise HTTPException(status_code=409, detail=f"Handle '/{new_handle}' already exists.")
        attributes = store.pop(old_handle)
        store[new_handle] = attributes
        write_store_unlocked(store)

    return handle_summary(new_handle, attributes)


@app.delete("/_admin/api/handles/{handle}", status_code=204, dependencies=[Depends(require_admin)])
def delete_handle(handle: str) -> Response:
    handle = validate_handle(handle)

    with store_lock:
        store = read_store_unlocked()
        if handle not in store:
            raise HTTPException(status_code=404, detail=f"Handle '/{handle}' does not exist.")
        del store[handle]
        write_store_unlocked(store)

    return Response(status_code=204)


@app.put("/_admin/api/handles/{handle}/attributes/{attribute}", dependencies=[Depends(require_admin)])
def upsert_attribute(handle: str, attribute: str, payload: AttributeValue) -> Dict[str, Any]:
    handle = validate_handle(handle)
    attribute = validate_attribute(attribute)
    value = ensure_json_value(payload.value)

    with store_lock:
        store = read_store_unlocked()
        if handle not in store:
            raise HTTPException(status_code=404, detail=f"Handle '/{handle}' does not exist.")
        store[handle][attribute] = value
        write_store_unlocked(store)
        attributes = store[handle]

    return handle_summary(handle, attributes)


@app.patch("/_admin/api/handles/{handle}/attributes/{attribute}", dependencies=[Depends(require_admin)])
async def patch_attribute(handle: str, attribute: str, request: Request) -> Dict[str, Any]:
    handle = validate_handle(handle)
    old_attribute = validate_attribute(attribute)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Attribute patch body must be a JSON object.")

    new_attribute: Optional[str] = None
    if "attribute" in payload:
        new_attribute = validate_attribute(str(payload["attribute"]))
    value_was_supplied = "value" in payload
    new_value = ensure_json_value(payload["value"]) if value_was_supplied else None

    with store_lock:
        store = read_store_unlocked()
        if handle not in store:
            raise HTTPException(status_code=404, detail=f"Handle '/{handle}' does not exist.")
        if old_attribute not in store[handle]:
            raise HTTPException(status_code=404, detail=f"Attribute '{old_attribute}' does not exist.")

        target_attribute = new_attribute or old_attribute
        if target_attribute != old_attribute and target_attribute in store[handle]:
            raise HTTPException(status_code=409, detail=f"Attribute '{target_attribute}' already exists.")

        current_value = store[handle].pop(old_attribute)
        store[handle][target_attribute] = new_value if value_was_supplied else current_value
        write_store_unlocked(store)
        attributes = store[handle]

    return handle_summary(handle, attributes)


@app.delete("/_admin/api/handles/{handle}/attributes/{attribute}", status_code=204, dependencies=[Depends(require_admin)])
def delete_attribute(handle: str, attribute: str) -> Response:
    handle = validate_handle(handle)
    attribute = validate_attribute(attribute)

    with store_lock:
        store = read_store_unlocked()
        if handle not in store:
            raise HTTPException(status_code=404, detail=f"Handle '/{handle}' does not exist.")
        if attribute not in store[handle]:
            raise HTTPException(status_code=404, detail=f"Attribute '{attribute}' does not exist.")
        del store[handle][attribute]
        write_store_unlocked(store)

    return Response(status_code=204)


@app.get("/{handle}", include_in_schema=False)
def get_dynamic_handle(handle: str) -> JSONResponse:
    handle = validate_handle(handle, public_lookup=True)
    store = read_store()
    if handle not in store:
        raise HTTPException(status_code=404, detail=f"Handle '/{handle}' does not exist.")
    return JSONResponse(content=store[handle])
