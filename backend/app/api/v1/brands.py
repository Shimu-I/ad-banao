from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.common import image_error, read_upload
from app.api.v1.deps import get_current_user
from app.core.config import get_settings
from app.db.models import Brand, User
from app.db.session import get_db
from app.domain.images import MIN_SIDE_LOGO, ImageRejected, inspect_image, save_image
from app.schemas.profiles import (
    BrandCreate,
    BrandLogoResult,
    BrandRead,
    BrandUpdate,
    ImageWarningRead,
)

router = APIRouter(prefix="/brands", tags=["brands"])


def _get_brand(db: Session, user: User, brand_id: int) -> Brand:
    """Another user's brand looks exactly like a missing one (404), so ids reveal nothing."""
    brand = db.get(Brand, brand_id)
    if brand is None or brand.user_id != user.id:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


def _ensure_name_free(db: Session, user: User, name: str, exclude_id: int | None = None) -> None:
    stmt = select(Brand.id).where(
        Brand.user_id == user.id,
        func.lower(Brand.name) == name.lower(),
        Brand.is_archived.is_(False),
    )
    if exclude_id is not None:
        stmt = stmt.where(Brand.id != exclude_id)
    if db.scalar(stmt.limit(1)) is not None:
        raise HTTPException(status_code=409, detail="A brand with this name already exists")


def _ensure_editable(brand: Brand) -> None:
    if brand.is_archived:
        raise HTTPException(status_code=409, detail="Brand is archived; restore it first")


@router.post("", response_model=BrandRead, status_code=201)
def create_brand(
    payload: BrandCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    _ensure_name_free(db, user, payload.name)
    brand = Brand(user_id=user.id, **payload.model_dump())
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


@router.get("", response_model=list[BrandRead])
def list_brands(
    include_archived: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Brand).where(Brand.user_id == user.id).order_by(Brand.id).limit(limit).offset(offset)
    if not include_archived:
        stmt = stmt.where(Brand.is_archived.is_(False))
    return list(db.scalars(stmt))


@router.get("/{brand_id}", response_model=BrandRead)
def get_brand(
    brand_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _get_brand(db, user, brand_id)


@router.patch("/{brand_id}", response_model=BrandRead)
def update_brand(
    brand_id: int,
    payload: BrandUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    brand = _get_brand(db, user, brand_id)
    _ensure_editable(brand)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"].lower() != brand.name.lower():
        _ensure_name_free(db, user, changes["name"], exclude_id=brand.id)
    for field, value in changes.items():
        setattr(brand, field, value)
    db.commit()
    db.refresh(brand)
    return brand


@router.post("/{brand_id}/archive", response_model=BrandRead)
def archive_brand(
    brand_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    # Archived rather than deleted: products and ads keep pointing at it.
    brand = _get_brand(db, user, brand_id)
    brand.is_archived = True
    db.commit()
    db.refresh(brand)
    return brand


@router.post("/{brand_id}/restore", response_model=BrandRead)
def restore_brand(
    brand_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    brand = _get_brand(db, user, brand_id)
    if brand.is_archived:
        _ensure_name_free(db, user, brand.name, exclude_id=brand.id)
    brand.is_archived = False
    db.commit()
    db.refresh(brand)
    return brand


@router.post("/{brand_id}/logo", response_model=BrandLogoResult)
def upload_logo(
    brand_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    brand = _get_brand(db, user, brand_id)
    _ensure_editable(brand)
    data = read_upload(file)
    try:
        info = inspect_image(data, min_side=MIN_SIDE_LOGO)
    except ImageRejected as exc:
        raise image_error(exc) from exc
    brand.logo_path = save_image(data, info, get_settings().upload_dir, "brands")
    db.commit()
    db.refresh(brand)
    return BrandLogoResult(
        brand=BrandRead.model_validate(brand),
        warnings=[ImageWarningRead(code=w.code, message=w.message) for w in info.warnings],
    )
