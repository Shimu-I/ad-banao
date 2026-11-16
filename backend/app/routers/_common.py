"""Helpers shared by the brand and product routers."""

from fastapi import HTTPException, UploadFile

from app.images import MAX_BYTES, ImageRejected


def read_upload(file: UploadFile) -> bytes:
    """Read an upload without loading more than the size limit (plus one byte to detect overflow)."""
    return file.file.read(MAX_BYTES + 1)


def image_error(exc: ImageRejected) -> HTTPException:
    status = 413 if exc.code == "too_large" else 422
    return HTTPException(status_code=status, detail={"code": exc.code, "message": exc.message})
