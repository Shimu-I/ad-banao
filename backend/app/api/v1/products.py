from dataclasses import asdict

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.common import image_error, read_upload
from app.api.v1.deps import get_current_user
from app.core.config import get_settings
from app.db.activity import record
from app.db.models import Brand, Product, User
from app.db.session import get_db
from app.domain import activity as ACT
from app.domain.generation import generate_copy
from app.domain.grounding import facts_from_product
from app.domain.images import MIN_SIDE_PRODUCT, ImageRejected, inspect_image, save_image
from app.domain.profile_checks import blocked_for, check_product
from app.providers.llm import providers_from_settings
from app.schemas.profiles import (
    GenerateCopyRequest,
    GeneratedCopyRead,
    GroundingIssueRead,
    ImageWarningRead,
    ProductCreate,
    ProductImageResult,
    ProductRead,
    ProductUpdate,
    Readiness,
    ReadinessIssue,
)

router = APIRouter(prefix="/products", tags=["products"])


def _get_product(db: Session, user: User, product_id: int) -> Product:
    """A product belongs to the user who owns its brand. Others get 404, as if it did not exist."""
    product = db.get(Product, product_id)
    if product is None or product.brand.user_id != user.id:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def _ensure_editable(product: Product) -> None:
    if product.is_archived:
        raise HTTPException(status_code=409, detail="Product is archived; restore it first")


def _ensure_name_free(db: Session, brand_id: int, name: str, exclude_id: int | None = None) -> None:
    stmt = select(Product.id).where(
        Product.brand_id == brand_id,
        func.lower(Product.name) == name.lower(),
        Product.is_archived.is_(False),
    )
    if exclude_id is not None:
        stmt = stmt.where(Product.id != exclude_id)
    if db.scalar(stmt.limit(1)) is not None:
        raise HTTPException(status_code=409, detail="This brand already has a product with this name")


@router.post("", response_model=ProductRead, status_code=201)
def create_product(
    payload: ProductCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    brand = db.get(Brand, payload.brand_id)
    if brand is None or brand.user_id != user.id:
        raise HTTPException(status_code=404, detail="Brand not found")
    if brand.is_archived:
        raise HTTPException(status_code=409, detail="Brand is archived; restore it first")
    _ensure_name_free(db, brand.id, payload.name)
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    record(db, ACT.PRODUCT_CREATED, user.id, detail=product.name)
    return product


@router.get("", response_model=list[ProductRead])
def list_products(
    brand_id: int | None = None,
    include_archived: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Product)
        .join(Brand, Product.brand_id == Brand.id)
        .where(Brand.user_id == user.id)
        .order_by(Product.id)
        .limit(limit)
        .offset(offset)
    )
    if brand_id is not None:
        stmt = stmt.where(Product.brand_id == brand_id)
    if not include_archived:
        stmt = stmt.where(Product.is_archived.is_(False))
    return list(db.scalars(stmt))


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _get_product(db, user, product_id)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product = _get_product(db, user, product_id)
    _ensure_editable(product)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"].lower() != product.name.lower():
        _ensure_name_free(db, product.brand_id, changes["name"], exclude_id=product.id)
    for field, value in changes.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.post("/{product_id}/archive", response_model=ProductRead)
def archive_product(
    product_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    # Archived rather than deleted: existing ads keep pointing at it.
    product = _get_product(db, user, product_id)
    product.is_archived = True
    db.commit()
    db.refresh(product)
    return product


@router.post("/{product_id}/restore", response_model=ProductRead)
def restore_product(
    product_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    product = _get_product(db, user, product_id)
    if product.is_archived:
        if product.brand.is_archived:
            raise HTTPException(status_code=409, detail="Brand is archived; restore it first")
        _ensure_name_free(db, product.brand_id, product.name, exclude_id=product.id)
    product.is_archived = False
    db.commit()
    db.refresh(product)
    return product


@router.post("/{product_id}/image", response_model=ProductImageResult)
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product = _get_product(db, user, product_id)
    _ensure_editable(product)
    data = read_upload(file)
    try:
        info = inspect_image(data, min_side=MIN_SIDE_PRODUCT)
    except ImageRejected as exc:
        raise image_error(exc) from exc

    warnings = [ImageWarningRead(code=w.code, message=w.message) for w in info.warnings]
    duplicate = db.scalar(
        select(Product)
        .where(
            Product.brand_id == product.brand_id,
            Product.image_sha256 == info.sha256,
            Product.id != product.id,
            Product.is_archived.is_(False),
        )
        .limit(1)
    )
    if duplicate is not None:
        warnings.append(
            ImageWarningRead(
                code="duplicate_image",
                message=f"The same photo is already used by product #{duplicate.id} ({duplicate.name}).",
            )
        )

    # The original bytes are stored untouched; their hash is what integrity checks compare against.
    product.image_path = save_image(data, info, get_settings().upload_dir, "products")
    product.image_sha256 = info.sha256
    db.commit()
    db.refresh(product)
    record(db, ACT.PHOTO_UPLOADED, user.id, detail=product.name)
    return ProductImageResult(product=ProductRead.model_validate(product), warnings=warnings)


@router.get("/{product_id}/readiness", response_model=Readiness)
def product_readiness(
    product_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    product = _get_product(db, user, product_id)
    issues = check_product(product, product.brand)
    return Readiness(
        can_generate=not blocked_for(issues, "generation"),
        can_render=not blocked_for(issues, "rendering"),
        issues=[ReadinessIssue(**asdict(issue)) for issue in issues],
    )


@router.post("/{product_id}/generate-copy", response_model=GeneratedCopyRead)
def generate_product_copy(
    product_id: int,
    payload: GenerateCopyRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Write the description, headline, tagline and button text from the entered facts.

    Nothing is saved: the user reviews the text first. If AI writing is unavailable
    or invents facts, plain template text is returned and labelled source "basic"."""
    product = _get_product(db, user, product_id)
    issues = check_product(product, product.brand)
    if blocked_for(issues, "generation"):
        raise HTTPException(
            status_code=422,
            detail={
                "message": "The product is not ready for text generation.",
                "issues": [asdict(i) for i in issues if i.blocks == "generation"],
            },
        )
    language = (payload or GenerateCopyRequest()).language
    facts = facts_from_product(product, product.brand)
    copy = generate_copy(facts, providers_from_settings(get_settings()), language)
    record(db, ACT.TEXT_GENERATED, user.id, detail=f"{product.name} ({copy.source})")
    return GeneratedCopyRead(
        description=copy.description,
        headline=copy.headline,
        tagline=copy.tagline,
        cta=copy.cta,
        source=copy.source,
        language=copy.language,
        warnings=copy.warnings,
        issues=[GroundingIssueRead(**asdict(i)) for i in copy.issues],
    )
