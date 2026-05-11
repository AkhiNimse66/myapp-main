"""Contracts / file upload router.

POST /api/contracts/upload         — multipart upload; stores bytes in MongoDB
GET  /api/contracts/{id}/download  — serve file from MongoDB (persistent across redeploys)

Storage strategy (MVP):
  File bytes are base64-encoded and stored directly in the contract_files collection.
  This means zero data loss on Railway redeploys. Max file size is 10 MB — after
  base64 encoding the stored document is ~13 MB, well within MongoDB's 16 MB document limit.
  Upgrade path: swap base64 field for a Cloudflare R2 presigned URL (Phase 7).
"""
from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.db import get_db
from app.deps import get_current_user
from app.repos.contracts_repo import ContractsRepo
from app.repos.creators_repo import CreatorsRepo

router = APIRouter(prefix="/api/contracts", tags=["contracts"])

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
    """Upload a contract file. Bytes are stored in MongoDB — persistent across redeploys."""
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

    # Encode bytes to base64 string for MongoDB storage
    file_data_b64 = base64.b64encode(contents).decode("utf-8")
    file_id = str(uuid.uuid4())
    storage_key = f"mongo:{file_id}"  # prefix signals bytes live in DB, not /tmp

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
        file_data=file_data_b64,
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
    """Serve the file from MongoDB. Works after any number of Railway redeploys."""
    contracts = ContractsRepo(db)
    doc = await contracts.find_by_id(file_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contract file not found.")

    file_data_b64 = doc.get("file_data")
    if not file_data_b64:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "File data not found — this contract was uploaded before persistent storage was enabled.",
        )

    file_bytes = base64.b64decode(file_data_b64)
    return Response(
        content=file_bytes,
        media_type=doc.get("mime_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f'attachment; filename="{doc.get("filename", "contract")}"',
            "Content-Length": str(len(file_bytes)),
        },
    )
