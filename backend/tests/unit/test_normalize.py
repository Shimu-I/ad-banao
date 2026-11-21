from decimal import Decimal

import pytest

from app.domain.normalize import (
    NormalizationError,
    PercentParseError,
    PriceParseError,
    UnitParseError,
    check_discount,
    parse_percent,
    parse_price,
    parse_unit,
    units_equal,
)

D = Decimal


# ---------------------------------------------------------------- prices


@pytest.mark.parametrize(
    "text, amount, currency",
    [
        ("1299", "1299.00", None),
        ("1,299", "1299.00", None),
        ("1299.00", "1299.00", None),
        ("1,299.50", "1299.50", None),
        ("1,29,999", "129999.00", None),  # Indian grouping
        ("৳1,299", "1299.00", "BDT"),
        ("৳ 999", "999.00", "BDT"),
        ("BDT 1299", "1299.00", "BDT"),
        ("bdt1299", "1299.00", "BDT"),
        ("Tk. 500", "500.00", "BDT"),
        ("500 tk", "500.00", "BDT"),
        ("১,২৯৯ টাকা", "1299.00", "BDT"),  # Bangla digits and word
        ("৳১২৯৯/-", "1299.00", "BDT"),
        ("1299/-", "1299.00", None),
        ("$12.99", "12.99", "USD"),
        ("US $ 12.99", "12.99", "USD"),
        ("USD 5", "5.00", "USD"),
        ("€9.50", "9.50", "EUR"),
        ("£3", "3.00", "GBP"),
        ("₹499", "499.00", "INR"),
        ("  only ৳ 250  ", "250.00", "BDT"),
        (".99", "0.99", None),
    ],
)
def test_parse_price_exact(text, amount, currency):
    parsed = parse_price(text)
    assert parsed.amount == D(amount)
    assert parsed.currency == currency
    assert parsed.is_exact


@pytest.mark.parametrize(
    "text, amount, qualifier",
    [
        ("From ৳999", "999.00", "from"),
        ("starting at $5", "5.00", "from"),
        ("999 onwards", "999.00", "from"),
        ("৳999+", "999.00", "from"),
        ("up to ৳500", "500.00", "up_to"),
        ("Upto 500", "500.00", "up_to"),
    ],
)
def test_parse_price_qualifiers_are_not_exact(text, amount, qualifier):
    parsed = parse_price(text)
    assert parsed.amount == D(amount)
    assert parsed.qualifier == qualifier
    assert not parsed.is_exact


@pytest.mark.parametrize(
    "value, amount",
    [(12.99, "12.99"), (5, "5.00"), (D("1299"), "1299.00"), (0.1, "0.10")],
)
def test_parse_price_numbers(value, amount):
    parsed = parse_price(value)
    assert parsed.amount == D(amount)
    assert parsed.currency is None


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "   ",
        "abc",
        "৳",
        "12,99",  # decimal comma or typo: refuse to guess
        "1,2345",
        "1,29",
        "12.999",  # more than 2 decimal places
        "৳$5",  # two currencies
        "Rs. 500",  # unsupported currency text
        "1 299",
        "5-10",
        "1e5",
        True,
        None,
        float("nan"),
        float("inf"),
        [1],
    ],
)
def test_parse_price_rejects_unreadable_or_ambiguous(bad):
    with pytest.raises(PriceParseError):
        parse_price(bad)


def test_decimal_comma_error_explains_the_fix():
    with pytest.raises(PriceParseError, match="ambiguous"):
        parse_price("12,99")


def test_errors_are_value_errors():
    assert issubclass(PriceParseError, NormalizationError)
    assert issubclass(NormalizationError, ValueError)


def test_equivalent_formats_give_the_same_amount():
    forms = ["1299", "1,299", "1299.00", "৳1,299", "BDT 1299", "১২৯৯", "Tk. 1299/-"]
    assert len({parse_price(f).amount for f in forms}) == 1


# ------------------------------------------------------------- percentages


@pytest.mark.parametrize(
    "text, value, qualifier",
    [
        ("50% off", "50", None),
        ("৫০%", "50", None),
        ("12.5 percent", "12.5", None),
        ("up to 50% off", "50", "up_to"),
        ("UPTO 30%", "30", "up_to"),
        (25, "25", None),
        (D("12.5"), "12.5", None),
    ],
)
def test_parse_percent(text, value, qualifier):
    parsed = parse_percent(text)
    assert parsed.value == D(value)
    assert parsed.qualifier == qualifier


@pytest.mark.parametrize("bad", ["50", "off", "10% to 50% off", "150%", -5, 101, True, None])
def test_parse_percent_rejects(bad):
    with pytest.raises(PercentParseError):
        parse_percent(bad)


# --------------------------------------------------------------- discounts


def test_discount_matching_claim_is_consistent():
    result = check_discount(D("1000"), D("500"), D("50"))
    assert result.consistent
    assert result.actual_percent == D("50.00")


def test_discount_rounding_within_tolerance():
    # 999 -> 499 is really 50.05% off; "50% off" is fair marketing rounding.
    assert check_discount(D("999"), D("499"), D("50")).consistent
    # 33.33% claimed as 33%
    assert check_discount(D("300"), D("200"), D("33")).consistent


def test_discount_wrong_claim_is_flagged():
    result = check_discount(D("1000"), D("700"), D("50"))
    assert not result.consistent
    assert result.actual_percent == D("30.00")
    assert "30.00%" in result.reason


def test_discount_without_claim_just_reports_percent():
    result = check_discount(D("200"), D("150"))
    assert result.consistent
    assert result.actual_percent == D("25.00")


def test_sale_price_above_original_is_inconsistent():
    result = check_discount(D("100"), D("120"), D("10"))
    assert not result.consistent
    assert result.actual_percent is None


def test_no_discount_but_claimed_is_flagged():
    assert not check_discount(D("100"), D("100"), D("20")).consistent
    assert check_discount(D("100"), D("100"), D("0")).consistent


def test_zero_original_price_is_inconsistent():
    assert not check_discount(D("0"), D("0"), D("10")).consistent


# ------------------------------------------------------------------- units


@pytest.mark.parametrize(
    "a, b",
    [
        ("500g", "0.5kg"),
        ("500 g", "0.5 KG"),
        ("1L", "1000ml"),
        ("1 litre", "1000 ml"),
        ("250 ML", "0.25 l"),
        ("500 gm", "500 grams"),
        ("২৫০ গ্রাম", "250g"),
        ("১ কেজি", "1000 g"),
        ("500mg", "0.5g"),
        ("6 pcs", "6 pieces"),
        ("12 পিস", "12 pcs"),
    ],
)
def test_equivalent_units_are_equal(a, b):
    assert units_equal(a, b)


@pytest.mark.parametrize(
    "a, b",
    [("500g", "1kg"), ("500g", "500ml"), ("1L", "1kg"), ("6 pcs", "12 pcs"), ("500 ml", "0.5 kg")],
)
def test_different_units_are_not_equal(a, b):
    assert not units_equal(a, b)


@pytest.mark.parametrize(
    "text, canonical",
    [
        ("500g", "500 g"),
        ("0.5kg", "500 g"),
        ("1000g", "1 kg"),
        ("1.5 kg", "1.5 kg"),
        ("500mg", "500 mg"),
        ("0.5 g", "500 mg"),
        ("250 ml", "250 ml"),
        ("0.25 l", "250 ml"),
        ("1000 ml", "1 l"),
        ("1.5 L", "1.5 l"),
        ("6 pcs", "6 pcs"),
        ("২৫০ গ্রাম", "250 g"),
    ],
)
def test_canonical_unit_text(text, canonical):
    assert parse_unit(text).canonical() == canonical


@pytest.mark.parametrize(
    "bad",
    ["", "  ", "500", "g", "2 x 500g", "2×500 g", "5 oz", "3 lb", "abc", "0 g", "0 ml", "1,5 kg", "1.5 pcs", None, 5],
)
def test_parse_unit_rejects(bad):
    with pytest.raises(UnitParseError):
        parse_unit(bad)


def test_unparseable_unit_raises_instead_of_returning_false():
    # Callers must treat this as "cannot verify", not as a mismatch.
    with pytest.raises(UnitParseError):
        units_equal("500g", "a handful")
