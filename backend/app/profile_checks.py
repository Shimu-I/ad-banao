"""Readiness checks for product and brand profiles.

A profile can be saved incomplete. These checks say what is missing and what it
blocks, so the UI can warn clearly and the generator can refuse to run on bad
data. Objects are accessed by attribute only, so tests do not need a database.
"""

import re
from dataclasses import dataclass

LONG_DESCRIPTION = 2000

# Heuristic only. Later steps still treat all profile text as data, never as instructions.
_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier)\s+(?:instructions?|prompts?|rules)", re.I),
    re.compile(r"disregard\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier)\b", re.I),
    re.compile(r"\b(?:system|developer)\s+prompt\b", re.I),
    re.compile(r"\b(?:reveal|show|print)\s+(?:your|the)\s+(?:system\s+|hidden\s+)?(?:prompt|instructions)\b", re.I),
    re.compile(r"</?\s*(?:system|assistant|instructions?)\s*>", re.I),
)


@dataclass(frozen=True)
class ProfileIssue:
    code: str
    field: str
    message: str
    severity: str  # "critical", "warning" or "suggestion" (same values as models.Severity)
    blocks: str | None = None  # "generation", "rendering" or None


def find_prompt_injection(text: str | None) -> str | None:
    """Return the suspicious phrase if the text looks like an attempt to instruct the AI."""
    if not text:
        return None
    for pattern in _INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def check_product(product, brand) -> list[ProfileIssue]:
    """Check a product (and its brand, which may be None) for missing or risky data."""
    issues: list[ProfileIssue] = []

    def add(code, field, message, severity, blocks=None):
        issues.append(ProfileIssue(code, field, message, severity, blocks))

    name = (product.name or "").strip()
    price = product.price
    original = product.original_price

    if not name:
        add("missing_name", "name", "The product has no name.", "critical", "generation")
    if price is None:
        add("missing_price", "price", "The product has no price, so prices in ads cannot be checked.", "critical", "generation")
    elif price <= 0:
        add("invalid_price", "price", "The price must be greater than zero.", "critical", "generation")
    if original is not None and price is not None:
        if original < price:
            add("original_below_price", "original_price", "The original price is lower than the sale price.", "critical", "generation")
        elif original == price:
            add("no_discount", "original_price", "The original price equals the sale price, so there is no discount to advertise.", "warning")
    if not (product.description or "").strip():
        add("missing_description", "description", "No description: generated ad text will be generic.", "warning")
    if not product.image_path:
        add("missing_image", "image_path", "No product photo: a visual ad cannot be created.", "critical", "rendering")
    if not product.allowed_claims:
        add("no_allowed_claims", "allowed_claims", "No allowed claims: any benefit claim in an ad will be flagged as unsupported.", "suggestion")
    if not getattr(product, "key_features", None):
        add("no_key_features", "key_features", "No key features: generated text will be generic. Add two or three selling points.", "warning")
    if not product.unit:
        add("missing_unit", "unit", "No unit or pack size: size mentions in ads cannot be checked.", "suggestion")
    if product.is_archived:
        add("archived_product", "is_archived", "This product is archived.", "critical", "generation")

    description = product.description or ""
    if len(description) > LONG_DESCRIPTION:
        add("long_description", "description", f"The description is over {LONG_DESCRIPTION} characters; the generator may ignore parts of it.", "warning")
    for field, text in (("name", product.name), ("description", description), ("allowed_claims", " ".join(product.allowed_claims or [])), ("key_features", " ".join(getattr(product, "key_features", None) or []))):
        phrase = find_prompt_injection(text)
        if phrase:
            add("possible_prompt_injection", field, f"The {field} contains text that looks like an instruction to the AI ({phrase!r}). Please review it.", "warning")

    if brand is None:
        add("missing_brand", "brand_id", "The product has no brand.", "critical", "generation")
    else:
        if brand.is_archived:
            add("archived_brand", "brand_id", "The brand is archived.", "critical", "generation")
        if not brand.primary_colors:
            add("brand_no_colors", "brand.primary_colors", "The brand has no colors, so color consistency cannot be checked.", "warning")
        if not brand.logo_path:
            add("brand_no_logo", "brand.logo_path", "The brand has no logo, so logo placement cannot be checked.", "suggestion")

    return issues


def blocked_for(issues: list[ProfileIssue], stage: str) -> bool:
    """True if any issue stops the stage. Rendering also needs everything generation needs."""
    if stage == "generation":
        return any(i.blocks == "generation" for i in issues)
    if stage == "rendering":
        return any(i.blocks in ("generation", "rendering") for i in issues)
    raise ValueError(f"unknown stage {stage!r}")
