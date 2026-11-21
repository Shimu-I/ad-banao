"""Price, discount and unit normalization.

Pure Python with no third-party imports, so it is cheap to test and can be reused
by the verification modules later. Anything ambiguous raises an error instead of
guessing; callers turn that into a validation error or a "Cannot verify" result.
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


class NormalizationError(ValueError):
    """The input cannot be understood without guessing."""


class PriceParseError(NormalizationError):
    pass


class PercentParseError(NormalizationError):
    pass


class UnitParseError(NormalizationError):
    pass


_BANGLA_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
_CENT = Decimal("0.01")

# ---------------------------------------------------------------- prices

# Patterns run on lower-cased text. Alphabetic codes must not sit inside a longer word.
_CURRENCY_PATTERNS = (
    ("BDT", re.compile(r"৳|টাকা|(?<![a-z])(?:bdt|tk|taka)(?![a-z])\.?")),
    ("USD", re.compile(r"us\s*\$|\$|(?<![a-z])usd(?![a-z])")),
    ("EUR", re.compile(r"€|(?<![a-z])eur(?![a-z])")),
    ("GBP", re.compile(r"£|(?<![a-z])gbp(?![a-z])")),
    ("INR", re.compile(r"₹|(?<![a-z])inr(?![a-z])")),
)

_PREFIX_QUALIFIERS = (
    ("from", re.compile(r"^(?:from|starting\s+(?:at|from)|starts\s+(?:at|from))\b\s*")),
    ("up_to", re.compile(r"^up\s*to\b\s*")),
)
_SUFFIX_FROM = re.compile(r"\s*(?:onwards|and\s+up|\+)$")
_NOISE_PREFIX = re.compile(r"^only\b\s*")
_NOISE_SUFFIX = re.compile(r"\s*(?:/-|only)$")

# Plain (1299.50), western grouping (1,299.50) or Indian grouping (1,29,999.50).
# Anything else with commas, such as "12,99", is ambiguous and rejected.
_NUMBER = re.compile(
    r"(?:\d+|\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})(?:\.\d+)?|\.\d+"
)


@dataclass(frozen=True)
class ParsedPrice:
    amount: Decimal
    currency: str | None  # ISO code if the text named one, otherwise None
    qualifier: str | None  # "from", "up_to" or None for an exact price

    @property
    def is_exact(self) -> bool:
        return self.qualifier is None


def _two_places(amount: Decimal) -> Decimal:
    try:
        rounded = amount.quantize(_CENT)
    except InvalidOperation:
        raise PriceParseError("price is too large") from None
    if rounded != amount:
        raise PriceParseError("price has more than 2 decimal places")
    return rounded


def parse_price(value: "str | int | float | Decimal") -> ParsedPrice:
    """Parse "1,299", "৳1,299", "BDT 1299", "$12.99", "From ৳999" and similar.

    Commas are only accepted as thousands separators. Ambiguous input such as
    "12,99" (decimal comma or a typo?) raises PriceParseError.
    """
    if value is None or isinstance(value, bool):
        raise PriceParseError("price must be a number or text")

    if isinstance(value, (int, float, Decimal)):
        try:
            amount = Decimal(str(value))  # str() avoids binary float noise
        except InvalidOperation:
            raise PriceParseError("price is not a number") from None
        if not amount.is_finite():
            raise PriceParseError("price is not a finite number")
        return ParsedPrice(_two_places(amount), None, None)

    if not isinstance(value, str):
        raise PriceParseError("price must be a number or text")

    text = value.strip().lower().translate(_BANGLA_DIGITS)
    if not text:
        raise PriceParseError("price is empty")

    found = [code for code, pattern in _CURRENCY_PATTERNS if pattern.search(text)]
    if len(found) > 1:
        raise PriceParseError("more than one currency in the price")
    for _, pattern in _CURRENCY_PATTERNS:
        text = pattern.sub(" ", text)
    text = text.strip()

    qualifier = None
    for name, pattern in _PREFIX_QUALIFIERS:
        if pattern.match(text):
            qualifier = name
            text = pattern.sub("", text, count=1).strip()
            break
    text = _NOISE_PREFIX.sub("", text).strip()
    if _SUFFIX_FROM.search(text):
        qualifier = qualifier or "from"
        text = _SUFFIX_FROM.sub("", text).strip()
    text = _NOISE_SUFFIX.sub("", text).strip()

    if not _NUMBER.fullmatch(text):
        if re.fullmatch(r"\d+,\d{1,2}", text):
            raise PriceParseError(
                f"{value!r} is ambiguous: a comma followed by 1-2 digits could be a "
                "decimal comma. Write it with a dot, for example 12.99"
            )
        raise PriceParseError(f"cannot read a price from {value!r}")

    try:
        amount = Decimal(text.replace(",", ""))
    except InvalidOperation:
        raise PriceParseError(f"cannot read a price from {value!r}") from None
    return ParsedPrice(_two_places(amount), found[0] if found else None, qualifier)


# -------------------------------------------------------------- discounts

_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|percent|pct|শতাংশ)")


@dataclass(frozen=True)
class ParsedPercent:
    value: Decimal
    qualifier: str | None  # "up_to" for "up to 50% off", otherwise None


def parse_percent(value: "str | int | float | Decimal") -> ParsedPercent:
    """Parse "50% off", "up to 50% off", "৫০%" or a bare number such as 12.5."""
    if value is None or isinstance(value, bool):
        raise PercentParseError("percentage must be a number or text")

    qualifier = None
    if isinstance(value, (int, float, Decimal)):
        try:
            number = Decimal(str(value))
        except InvalidOperation:
            raise PercentParseError("percentage is not a number") from None
    elif isinstance(value, str):
        text = value.strip().lower().translate(_BANGLA_DIGITS)
        matches = _PERCENT.findall(text)
        if not matches:
            raise PercentParseError(f"no percentage found in {value!r}")
        if len(matches) > 1:
            raise PercentParseError(f"more than one percentage in {value!r}")
        number = Decimal(matches[0])
        if re.search(r"\bup\s*to\b", text):
            qualifier = "up_to"
    else:
        raise PercentParseError("percentage must be a number or text")

    if not number.is_finite() or number < 0 or number > 100:
        raise PercentParseError("percentage must be between 0 and 100")
    return ParsedPercent(number, qualifier)


@dataclass(frozen=True)
class DiscountCheck:
    consistent: bool
    actual_percent: Decimal | None
    reason: str


def check_discount(
    original: Decimal,
    price: Decimal,
    claimed_percent: Decimal | None = None,
    tolerance: Decimal = Decimal("1"),
) -> DiscountCheck:
    """Check original price, sale price and an optional "N% off" claim agree.

    The claim may differ from the real discount by up to ``tolerance`` percentage
    points, because marketing rounds ("33% off" for 33.33%).
    """
    if original <= 0:
        return DiscountCheck(False, None, "original price must be greater than zero")
    if price > original:
        return DiscountCheck(False, None, "sale price is higher than the original price")

    actual = ((original - price) / original * 100).quantize(_CENT)
    if claimed_percent is None:
        return DiscountCheck(True, actual, f"discount is {actual}%")
    if abs(actual - claimed_percent) <= tolerance:
        return DiscountCheck(True, actual, f"claimed {claimed_percent}% matches actual {actual}%")
    return DiscountCheck(
        False, actual, f"claimed {claimed_percent}% off but the real discount is {actual}%"
    )


# ------------------------------------------------------------------ units

_UNITS: dict[str, tuple[str, Decimal]] = {}


def _alias(dimension: str, factor: str, *names: str) -> None:
    for name in names:
        _UNITS[name] = (dimension, Decimal(factor))


# Mass is stored in grams, volume in millilitres, count in pieces.
_alias("mass", "0.001", "mg")
_alias("mass", "1", "g", "gm", "gms", "gram", "grams", "গ্রাম")
_alias("mass", "1000", "kg", "kgs", "kilo", "kilos", "kilogram", "kilograms", "কেজি")
_alias("volume", "1", "ml", "milliliter", "milliliters", "millilitre", "millilitres", "মিলি")
_alias("volume", "1000", "l", "lt", "ltr", "liter", "liters", "litre", "litres", "লিটার")
_alias("count", "1", "pc", "pcs", "piece", "pieces", "pack", "packs", "unit", "units", "পিস")

_UNIT_TEXT = re.compile(r"(\d+(?:\.\d+)?|\.\d+)\s*([a-zঀ-৿]+)\.?")
_MULTIPACK = re.compile(r"\d\s*[x×*]\s*\d")


def _format_number(value: Decimal) -> str:
    return format(value.normalize(), "f")


@dataclass(frozen=True)
class ParsedUnit:
    dimension: str  # "mass", "volume" or "count"
    quantity: Decimal  # in grams, millilitres or pieces

    def canonical(self) -> str:
        """The same amount in a consistent form, e.g. 0.5kg and 500g both give "500 g"."""
        q = self.quantity
        if self.dimension == "mass":
            if q >= 1000:
                return f"{_format_number(q / 1000)} kg"
            if q < 1:
                return f"{_format_number(q * 1000)} mg"
            return f"{_format_number(q)} g"
        if self.dimension == "volume":
            if q >= 1000:
                return f"{_format_number(q / 1000)} l"
            return f"{_format_number(q)} ml"
        return f"{_format_number(q)} pcs"


def parse_unit(text: str) -> ParsedUnit:
    """Parse "500g", "0.5 kg", "1L", "250 ml", "২৫০ গ্রাম", "6 pcs"."""
    if not isinstance(text, str) or not text.strip():
        raise UnitParseError("unit is empty")
    cleaned = text.strip().lower().translate(_BANGLA_DIGITS)
    if _MULTIPACK.search(cleaned):
        raise UnitParseError(f"{text!r} looks like a multi-pack, which is not supported yet")
    match = _UNIT_TEXT.fullmatch(cleaned)
    if not match:
        raise UnitParseError(f"cannot read a unit from {text!r}; use a form like 500g or 1 L")
    number, name = match.groups()
    if name not in _UNITS:
        raise UnitParseError(f"unknown unit {name!r} in {text!r}")
    dimension, factor = _UNITS[name]
    quantity = Decimal(number) * factor
    if quantity <= 0:
        raise UnitParseError("unit amount must be greater than zero")
    if dimension == "count" and quantity != quantity.to_integral_value():
        raise UnitParseError("a piece count must be a whole number")
    return ParsedUnit(dimension, quantity)


def units_equal(a: str, b: str) -> bool:
    """True when two unit strings describe the same amount, e.g. "500g" and "0.5kg"."""
    first, second = parse_unit(a), parse_unit(b)
    return first.dimension == second.dimension and first.quantity == second.quantity
