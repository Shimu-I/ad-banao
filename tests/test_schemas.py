from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import (
    BrandCreate,
    BrandUpdate,
    ProductCreate,
    ProductUpdate,
    normalize_hex_color,
)


def errors(exc_info):
    return " | ".join(e["msg"] for e in exc_info.value.errors())


# ------------------------------------------------------------------ brands


@pytest.mark.parametrize(
    "raw, expected",
    [("#abc", "#AABBCC"), ("ff0000", "#FF0000"), ("  #1a2b3c ", "#1A2B3C"), ("FFF", "#FFFFFF")],
)
def test_hex_colors_are_normalized(raw, expected):
    assert normalize_hex_color(raw) == expected


@pytest.mark.parametrize("raw", ["red", "#12", "#1234", "#GG0000", "", "#1234567"])
def test_bad_hex_colors_are_rejected(raw):
    with pytest.raises(ValueError):
        normalize_hex_color(raw)


def test_brand_create_cleans_input():
    brand = BrandCreate(
        name="  Demo Brand  ",
        primary_colors=["#abc", "AABBCC", "ff0000"],
        fonts=["Inter", " inter ", "", "Noto Sans Bengali"],
        tone_notes="   ",
    )
    assert brand.name == "Demo Brand"
    assert brand.primary_colors == ["#AABBCC", "#FF0000"]  # duplicates merged
    assert brand.fonts == ["Inter", "Noto Sans Bengali"]
    assert brand.tone_notes is None
    assert brand.secondary_colors == []


def test_brand_requires_a_real_name():
    with pytest.raises(ValidationError):
        BrandCreate(name="   ")
    with pytest.raises(ValidationError):
        BrandCreate()


def test_brand_rejects_bad_color_and_unknown_fields():
    with pytest.raises(ValidationError) as bad_color:
        BrandCreate(name="X", primary_colors=["blue"])
    assert "hex color" in errors(bad_color)
    with pytest.raises(ValidationError):
        BrandCreate(name="X", colour="#fff")  # typo is not silently ignored


def test_brand_update_only_contains_sent_fields():
    update = BrandUpdate(fonts=["Inter"])
    assert update.model_dump(exclude_unset=True) == {"fonts": ["Inter"]}
    with pytest.raises(ValidationError):
        BrandUpdate(name=None)
    with pytest.raises(ValidationError):
        BrandUpdate(primary_colors=None)


def test_brand_limits():
    with pytest.raises(ValidationError):
        BrandCreate(name="X", primary_colors=[f"#{i:06X}" for i in range(13)])
    with pytest.raises(ValidationError):
        BrandCreate(name="X" * 201)


# ---------------------------------------------------------------- products


def make(**fields):
    return ProductCreate(brand_id=1, name="Green Tea", **fields)


def test_price_text_is_normalized_and_currency_detected():
    product = make(price="৳1,299", original_price="১,৫৯৯ টাকা", unit="0.5kg")
    assert product.price == Decimal("1299.00")
    assert product.original_price == Decimal("1599.00")
    assert product.currency == "BDT"
    assert product.unit == "500 g"


def test_currency_symbol_sets_currency():
    product = make(price="$12.99")
    assert product.price == Decimal("12.99")
    assert product.currency == "USD"


def test_default_currency_is_bdt_when_nothing_says_otherwise():
    assert make().currency == "BDT"
    assert make(price="1299").currency == "BDT"
    assert make(price=1299).price == Decimal("1299.00")


def test_explicit_currency_is_used_for_a_plain_number():
    assert make(price="12.99", currency="usd").currency == "USD"


def test_currency_conflicts_are_rejected():
    with pytest.raises(ValidationError) as conflict:
        make(price="$12.99", currency="BDT")
    assert "currency conflict" in errors(conflict)
    with pytest.raises(ValidationError):
        make(price="$12", original_price="৳2000")


def test_unsupported_currency_is_rejected():
    with pytest.raises(ValidationError) as bad:
        make(price="5", currency="XYZ")
    assert "unsupported currency" in errors(bad)


@pytest.mark.parametrize("price", ["From ৳999", "up to 500", "999+"])
def test_inexact_prices_cannot_be_stored(price):
    with pytest.raises(ValidationError) as bad:
        make(price=price)
    assert "exact amount" in errors(bad)


@pytest.mark.parametrize("price", ["12,99", "abc", "0", 0, -5, "12.999", True])
def test_bad_prices_are_rejected(price):
    with pytest.raises(ValidationError):
        make(price=price)


def test_price_can_be_left_out_so_incomplete_profiles_can_be_saved():
    product = make()
    assert product.price is None
    assert product.original_price is None


def test_bad_unit_is_rejected_with_a_helpful_message():
    with pytest.raises(ValidationError) as bad:
        make(unit="2 x 500g")
    assert "multi-pack" in errors(bad)


def test_blank_unit_becomes_none():
    assert make(unit="  ").unit is None


def test_claims_are_cleaned():
    product = make(allowed_claims=["Hand picked", " hand picked ", "", "Organic"])
    assert product.allowed_claims == ["Hand picked", "Organic"]


def test_name_and_description_are_trimmed():
    product = ProductCreate(brand_id=1, name="  Green Tea  ", description="  Fresh.  ")
    assert product.name == "Green Tea"
    assert product.description == "Fresh."
    assert ProductCreate(brand_id=1, name="X", description="   ").description is None


def test_product_requires_brand_and_name_and_forbids_unknown_fields():
    with pytest.raises(ValidationError):
        ProductCreate(name="X")
    with pytest.raises(ValidationError):
        ProductCreate(brand_id=1, name="   ")
    with pytest.raises(ValidationError):
        ProductCreate(brand_id=1, name="X", pric="5")  # typo


def test_specs_limits():
    assert make(specs={"origin": "Sylhet", "organic": True, "weight_g": 500}).specs["organic"] is True
    with pytest.raises(ValidationError):
        make(specs={f"k{i}": "v" for i in range(51)})
    with pytest.raises(ValidationError):
        make(specs={"note": "x" * 501})


def test_product_update_only_contains_sent_fields():
    update = ProductUpdate(description="New text")
    assert update.model_dump(exclude_unset=True) == {"description": "New text"}
    assert ProductUpdate().model_dump(exclude_unset=True) == {}


def test_product_update_price_with_symbol_also_sets_currency():
    update = ProductUpdate(price="$5")
    assert update.model_dump(exclude_unset=True) == {"price": Decimal("5.00"), "currency": "USD"}


def test_product_update_plain_price_leaves_currency_alone():
    assert ProductUpdate(price="450").model_dump(exclude_unset=True) == {"price": Decimal("450.00")}


def test_product_update_can_clear_price_but_not_name_or_currency():
    assert ProductUpdate(price=None).model_dump(exclude_unset=True) == {"price": None}
    with pytest.raises(ValidationError):
        ProductUpdate(name=None)
    with pytest.raises(ValidationError):
        ProductUpdate(currency=None)


def test_product_update_cannot_move_a_product_to_another_brand():
    with pytest.raises(ValidationError):
        ProductUpdate(brand_id=2)
