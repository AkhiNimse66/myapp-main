"""Emergent-managed object storage for contract files.

Initialises once at startup. Uploads + downloads use the module-level
``storage_key`` cached after :func:`init_storage`. Never expose the raw
storage URL to the browser — all access flows through the FastAPI backend.
"""
from __future__ import annotations
import os
import logging
import requests
from typing import Optional, Tuple

logger = logging.getLogger("mypay.storage")

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = os.environ.get("APP_NAME", "mypay")

_storage_key: Optional[str] = None


def init_storage() -> Optional[str]:
    global _storage_key
    if _storage_key:
        return _storage_key
    emergent_key = os.environ.get("EMERGENT_LLM_KEY")
    if not emergent_key:
        logger.warning("EMERGENT_LLM_KEY missing — object storage disabled")
        return None
    try:
        r = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": emergent_key}, timeout=30)
        r.raise_for_status()
        _storage_key = r.json()["storage_key"]
        logger.info("Object storage initialised")
        return _storage_key
    except Exception as e:
        logger.warning(f"Storage init failed: {e}")
        return None


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    if not key:
        raise RuntimeError("Storage unavailable")
    r = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type or "application/octet-stream"},
        data=data,
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


def get_object(path: str) -> Tuple[bytes, str]:
    key = init_storage()
    if not key:
        raise RuntimeError("Storage unavailable")
    r = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60,
    )
    r.raise_for_status()
    return r.content, r.headers.get("Content-Type", "application/octet-stream")


def is_available() -> bool:
    return init_storage() is not None


MIME_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp", "pdf": "application/pdf",
    "txt": "text/plain", "csv": "text/csv",
}


def mime_for(filename: str, fallback: str = "application/octet-stream") -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return MIME_TYPES.get(ext, fallback)
