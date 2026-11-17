"""Facts about a product and checks that generated text sticks to them.

Pure logic with no web or database imports, so it can be tested anywhere.
The rule: text written by an AI may only mention numbers, prices and claims
that the user entered. Anything else is reported, never silently accepted.
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from app.normalize import _BANGLA_DIGITS, NormalizationError, parse_unit

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_URL = re.compile(r"(?:https?://|www\.)\S+|\b[\w.-]+@[\w-]+\.\w+\b", re.I)
_PHONE = re.compile(r"(?<!\d)\+?\d[\d\s-]{8,}\d(?!\d)")
_CURRENCY_MARKS = {
    "BDT": ("৳", "bdt", "tk", "taka"),
    "USD": ("$", "usd"),
    "EUR": ("€", "eur"),
    "GBP": ("£", "gbp"),
    "INR": ("₹", "inr"),
}

# Phrases that need support from the user's own text. Matched case-insensitively.
RISKY_PHRASES = (
    r"\bbest\b", r"#\s?1\b", r"\bno\.?\s?1\b", r"\bnumber\s+one\b", r"\bcheapest\b", r"\blowest\s+price\b",
    r"\bguarantee[sd]?\b", r"\b100\s?%", r"\bcures?\b", r"\bheals?\b", r"\btreats?\b", r"\bclinically\b",
    r"\bdoctor[- ]recommended\b", r"\bfda\b", r"\bcertified\b", r"\bbest[- ]sell(?:er|ing)\b",
    r"\bworld[- ]class\b", r"\bunmatched\b", r"\bno\s+side\s+effects\b", r"\bfree\s+(?:delivery|shipping)\b",
    r"\bwarranty\b", r"\blimited\s+time\b", r"\bwhile\s+stocks?\s+last\b",
)
_RISKY = tuple(re.compile(p, re.I) for p in RISKY_PHRASES)


@dataclass(frozen=True)
class GroundingIssue:
    code: str  # invented_number, wrong_currency, risky_claim, invented_contact
    field: str  # which generated field: description, headline, tagline, cta
    message: str
    found: str


@dataclass(frozen=True)
class Facts:
    name: str
    price: Decimal | None
    original_price: Decimal | None
    currency: str
    unit: str | None
    key_features: tuple[str, ...] = ()
    allowed_claims: tuple[str, ...] = ()
    specs: dict = field(default_factory=dict)
    brand_name: str = ""
    tone_notes: str = ""

    @property
    def discount_percent(self) -> Decimal | None:
        if self.price is None or self.original_price is None or self.original_price <= self.price:
            return None
        return ((self.original_price - self.price) / self.original_price * 100).quantize(Decimal("1"))

    def source_text(self) -> str:
        """Everything the user typed. Claims and numbers are allowed only if they appear here."""
        parts = [self.name, self.unit or "", self.brand_name, *self.key_features, *self.allowed_claims]
        parts += [f"{k} {v}" for k, v in self.specs.items()]
        return "\n".join(p for p in parts if p)


def facts_from_product(product, brand=None) -> Facts:
    """Build Facts from a Product row (or any object with the same attributes)."""
    return Facts(
        name=(product.name or "").strip(),
        price=product.price,
        original_price=product.original_price,
        currency=product.currency or "BDT",
        unit=product.unit,
        key_features=tuple(getattr(product, "key_features", None) or ()),
        allowed_claims=tuple(product.allowed_claims or ()),
        specs=dict(product.specs or {}),
        brand_name=(getattr(brand, "name", "") or "").strip(),
        tone_notes=(getattr(brand, "tone_notes", "") or "").strip(),
    )


def _norm(number: Decimal) -> Decimal:
    return number.normalize() if number != 0 else Decimal(0)


def numbers_in(text: str) -> set[Decimal]:
    """Every number in the text as a Decimal, so 1,299 and 1299.00 are the same."""
    found: set[Decimal] = set()
    for raw in _NUMBER.findall((text or "").translate(_BANGLA_DIGITS)):
        raw = raw.rstrip(",")
        try:
            found.add(_norm(Decimal(raw.replace(",", ""))))
        except InvalidOperation:
            continue
    return found


def allowed_numbers(facts: Facts) -> set[Decimal]:
    allowed = numbers_in(facts.source_text())
    for amount in (facts.price, facts.original_price, facts.discount_percent):
        if amount is not None:
            allowed.add(_norm(Decimal(amount)))
    if facts.unit:
        try:
            quantity = parse_unit(facts.unit).quantity
            allowed.add(_norm(quantity))
            if parse_unit(facts.unit).dimension in ("mass", "volume"):
                allowed.add(_norm(quantity / 1000))
        except NormalizationError:
            pass
    return allowed


def _wrong_currency_marks(text: str, currency: str) -> list[str]:
    lowered = text.lower()
    wrong: list[str] = []
    for code, marks in _CURRENCY_MARKS.items():
        if code == currency:
            continue
        for mark in marks:
            if mark.isalpha():
                if re.search(rf"(?<![a-z]){re.escape(mark)}(?![a-z])", lowered):
                    wrong.append(mark)
            elif mark in text:
                wrong.append(mark)
    return wrong


def check_generated_text(texts: dict[str, str], facts: Facts) -> list[GroundingIssue]:
    """Compare each generated field to the facts. An empty list means nothing was found."""
    issues: list[GroundingIssue] = []
    allowed = allowed_numbers(facts)
    source = facts.source_text().lower()
    for fld, text in texts.items():
        if not text:
            continue
        for number in sorted(numbers_in(text)):
            if number not in allowed:
                issues.append(GroundingIssue("invented_number", fld, f"The {fld} mentions {number:f}, which is not in the product details.", f"{number:f}"))
        for mark in _wrong_currency_marks(text, facts.currency):
            issues.append(GroundingIssue("wrong_currency", fld, f"The {fld} uses {mark!r}, but the product price is in {facts.currency}.", mark))
        for match in _URL.finditer(text):
            issues.append(GroundingIssue("invented_contact", fld, f"The {fld} contains a link or email address that was not entered.", match.group(0)))
        for match in _PHONE.finditer(text):
            issues.append(GroundingIssue("invented_contact", fld, f"The {fld} contains a phone-like number that was not entered.", match.group(0)))
        for pattern in _RISKY:
            for match in pattern.finditer(text):
                phrase = match.group(0).strip().lower()
                if phrase not in source:
                    issues.append(GroundingIssue("risky_claim", fld, f"The {fld} makes a claim ({match.group(0)!r}) that the product details do not support.", match.group(0)))
    return issues
