from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.providers.llm import providers_from_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "environment": get_settings().app_env}


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # Do not leak connection details to the client.
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ok"}


@router.get("/health/providers")
def health_providers() -> dict:
    """Which AI services are set up. Nothing is called and no key is shown."""
    found = providers_from_settings(get_settings())
    return {
        "configured": [{"name": p.name, "model": getattr(p, "model", "")} for p in found],
        "fallback": "basic",  # without a working provider the text comes from the built-in template
    }
