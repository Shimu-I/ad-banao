"""Request and response schemas for brands and products.

Only depends on pydantic and app.normalize, so it can be tested without a database.
Input is normalized on the way in: hex colors, prices ("৳1,299" -> 1299.00 BDT) and
units ("0.5kg" -> "500 g"). Ambiguous input is rejected with a clear message.
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.normalize import NormalizationError, parse_price, parse_unit

SUPPORTED_CURRENCIES = ("BDT", "USD", "EUR", "GBP", "INR")
DEFAULT_CURRENCY = "BDT"
MAX_PRICE = Decimal("9999999999.99")  # fits Numeric(12, 2)

_HEX_COLOR = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


# ---------------------------------------------------------------- helpers


def normalize_hex_color(value: str) -> str:
    match = _HEX_COLOR.match(value.strip())
    if not match:
        raise ValueError(f"{value!r} is not a hex color such as #1A2B3C")
    digits = match.group(1).upper()
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return "#" + digits


def _clean_texts(values: list[str], *, max_items: int, max_length: int, label: str) -> list[str]:
    """Strip, drop blanks, remove case-insensitive duplicates, keep order."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in values:
        item = raw.strip()
        if not item:
            continue
        if len(item) > max_length:
            raise ValueError(f"each {label} must be at most {max_length} characters")
        key = item.casefold()
        if key not in seen:
            seen.add(key)
            cleaned.append(item)
    if len(cleaned) > max_items:
        raise ValueError(f"at most {max_items} {label}s are allowed")
    return cleaned


def _normalize_money(data: Any, default_currency: str | None) -> Any:
    """Parse price strings and settle the currency before field validation runs."""
    if not isinstance(data, dict):
        return data
    data = dict(data)
    explicit = data.get("currency")
    if isinstance(explicit, str):
        explicit = explicit.strip().upper() or None

    currencies: set[str] = set()
    for key in ("price", "original_price"):
        value = data.get(key)
        if value is None:
            continue
        try:
            parsed = parse_price(value)
        except NormalizationError as exc:
            raise ValueError(f"{key}: {exc}") from exc
        if not parsed.is_exact:
            label = parsed.qualifier.replace("_", " ")
            raise ValueError(f"{key} must be an exact amount, not a '{label}' price")
        if parsed.currency:
            currencies.add(parsed.currency)
        data[key] = parsed.amount
    if explicit:
        currencies.add(explicit)

    if len(currencies) > 1:
        raise ValueError(f"currency conflict: {', '.join(sorted(currencies))}")
    if currencies:
        data["currency"] = next(iter(currencies))
    elif default_currency:
        data["currency"] = default_currency
    return data


# ----------------------------------------------------------------- brands


class _BrandFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    primary_colors: list[str] | None = None
    secondary_colors: list[str] | None = None
    fonts: list[str] | None = None
    tone_notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("name cannot be blank")
        value = value.strip()
        if len(value) > 200:
            raise ValueError("name must be at most 200 characters")
        return value

    @field_validator("primary_colors", "secondary_colors")
    @classmethod
    def _colors(cls, value: list[str] | None) -> list[str]:
        if value is None:
            raise ValueError("cannot be null; send an empty list to clear")
        colors = list(dict.fromkeys(normalize_hex_color(item) for item in value))
        if len(colors) > 12:
            raise ValueError("at most 12 colors are allowed")
        return colors

    @field_validator("fonts")
    @classmethod
    def _fonts(cls, value: list[str] | None) -> list[str]:
        if value is None:
            raise ValueError("cannot be null; send an empty list to clear")
        return _clean_texts(value, max_items=10, max_length=100, label="font")

    @field_validator("tone_notes")
    @classmethod
    def _tone(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None


class BrandCreate(_BrandFields):
    name: str = Field(min_length=1, max_length=200)
    primary_colors: list[str] = Field(default_factory=list)
    secondary_colors: list[str] = Field(default_factory=list)
    fonts: list[str] = Field(default_factory=list)


class BrandUpdate(_BrandFields):
    """Only fields that are sent are changed."""


class BrandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    primary_colors: list[str]
    secondary_colors: list[str]
    fonts: list[str]
    logo_path: str | None
    tone_notes: str | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------- products


class _ProductFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = Field(default=None, max_length=5000)
    price: Decimal | None = None
    original_price: Decimal | None = None
    currency: str | None = None
    unit: str | None = None
    specs: dict[str, str | int | float | bool] | None = None
    allowed_claims: list[str] | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("name cannot be blank")
        value = value.strip()
        if len(value) > 300:
            raise ValueError("name must be at most 300 characters")
        return value

    @field_validator("description")
    @classmethod
    def _description(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None

    @field_validator("price", "original_price")
    @classmethod
    def _amount(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not (0 < value <= MAX_PRICE):
            raise ValueError("must be greater than zero")
        return value

    @field_validator("currency")
    @classmethod
    def _currency(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("currency cannot be null")
        value = value.strip().upper()
        if value not in SUPPORTED_CURRENCIES:
            raise ValueError(f"unsupported currency; use one of {', '.join(SUPPORTED_CURRENCIES)}")
        return value

    @field_validator("unit")
    @classmethod
    def _unit(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        try:
            return parse_unit(value).canonical()
        except NormalizationError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("specs")
    @classmethod
    def _specs(cls, value: dict | None) -> dict:
        if value is None:
            raise ValueError("cannot be null; send an empty object to clear")
        if len(value) > 50:
            raise ValueError("at most 50 specs are allowed")
        for key, item in value.items():
            if not key.strip() or len(key) > 100:
                raise ValueError("spec names must be 1-100 characters")
            if isinstance(item, str) and len(item) > 500:
                raise ValueError("spec values must be at most 500 characters")
        return value

    @field_validator("allowed_claims")
    @classmethod
    def _claims(cls, value: list[str] | None) -> list[str]:
        if value is None:
            raise ValueError("cannot be null; send an empty list to clear")
        return _clean_texts(value, max_items=50, max_length=300, label="claim")


class ProductCreate(_ProductFields):
    brand_id: int
    name: str = Field(min_length=1, max_length=300)
    currency: str = DEFAULT_CURRENCY
    specs: dict[str, str | int | float | bool] = Field(default_factory=dict)
    allowed_claims: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _money(cls, data: Any) -> Any:
        return _normalize_money(data, DEFAULT_CURRENCY)


class ProductUpdate(_ProductFields):
    """Only fields that are sent are changed. A price with a currency symbol
    (for example "$12.99") also sets the currency, because the user typed it."""

    @model_validator(mode="before")
    @classmethod
    def _money(cls, data: Any) -> Any:
        return _normalize_money(data, None)


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_id: int
    name: str
    description: str | None
    price: Decimal | None
    original_price: Decimal | None
    currency: str
    unit: str | None
    specs: dict
    allowed_claims: list[str]
    image_path: str | None
    image_sha256: str | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


# ------------------------------------------------------- other responses


class ImageWarningRead(BaseModel):
    code: str
    message: str


class ProductImageResult(BaseModel):
    product: ProductRead
    warnings: list[ImageWarningRead]


class BrandLogoResult(BaseModel):
    brand: BrandRead
    warnings: list[ImageWarningRead]


class ReadinessIssue(BaseModel):
    code: str
    field: str
    message: str
    severity: str
    blocks: str | None


class Readiness(BaseModel):
    can_generate: bool
    can_render: bool
    issues: list[ReadinessIssue]
