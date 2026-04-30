"""Contracts / file upload router.

POST /api/contracts/upload         — multipart upload; stores metadata in DB
GET  /api/contracts/{id}/download  — serve file (stub; returns metadata until S3 lands)
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.db import get_db
from app.deps import get_current_user
from app.repos.contracts_repo import ContractsRepo
from app.repos.creators_repo import CreatorsRepo

router = APIRouter(prefix="/api/contracts", tags=["contracts"])

# Temp storage dir — in production this is replaced by S3 pre-signed upload
_UPLOAD_DIR = "/tmp/mypay_uploads"
os.makedirs(_UPLOAD_DIR, exist_ok=True)

MAX_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME = {
    "application/pdf", "image/jpeg", "image/png",
    "image/jpg", "text/plain",
}


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_contract(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    # Size guard — read first chunk to detect early
    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "File exceeds 10 MB limit.",
        )

    mime = file.content_type or "application/octet-stream"
    if mime not in ALLOWED_MIME:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported file type: {mime}. Allowed: PDF, PNG, JPG, TXT.",
        )

    # Persist to local temp storage (replace with S3 put_object in Day 8)
    file_id = str(uuid.uuid4())
    storage_key = f"{file_id}_{file.filename}"
    local_path = os.path.join(_UPLOAD_DIR, storage_key)
    with open(local_path, "wb") as f:
        f.write(contents)

    # Resolve optional creator_id
    creators = CreatorsRepo(db)
    creator = await creators.find_by_user_id(current_user["id"])
    creator_id = creator["id"] if creator else None

    contracts = ContractsRepo(db)
    doc = await contracts.create(
        user_id=current_user["id"],
        creator_id=creator_id,
        filename=file.filename or "contract",
        storage_key=storage_key,
        mime_type=mime,
        size_bytes=len(contents),
    )

    return {
        "id": doc["id"],
        "filename": doc["filename"],
        "content_type": doc["mime_type"],
        "size": doc["size_bytes"],
        "storage_key": doc["storage_key"],
    }


@router.get("/{file_id}/download")
async def download_contract(
    file_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Serve the uploaded file from local temp storage.

    In production this returns a pre-signed S3 URL instead.
    """
    contracts = ContractsRepo(db)
    doc = await contracts.find_by_id(file_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contract file not found.")

    local_path = os.path.join(_UPLOAD_DIR, doc["storage_key"])
    if not os.path.exists(local_path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File data not found on server.")

    from fastapi.responses import FileResponse
    return FileResponse(
        local_path,
        media_type=doc.get("mime_type", "application/octet-stream"),
        filename=doc.get("filename", "contract"),
    )
