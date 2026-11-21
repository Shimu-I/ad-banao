from decimal import Decimal
from types import SimpleNamespace

from app.domain.grounding import Facts, check_generated_text, facts_from_product, numbers_in


def make_facts(**kw):
    base = dict(
        name="Cotton Tote Bag",
        price=Decimal("1299"),
        original_price=Decimal("1999"),
        currency="BDT",
        unit="500 g",
        key_features=("Made of 100% cotton", "Two inner pockets"),
        allowed_claims=("Machine washable",),
        specs={"color": "navy"},
        brand_name="Shuvo Crafts",
    )
    base.update(kw)
    return Facts(**base)


def codes(texts, facts=None):
    return [i.code for i in check_generated_text(texts, facts or make_facts())]


def test_numbers_are_compared_by_value():
    assert numbers_in("৳1,299.00 and 1299") == {Decimal("1299")}
    assert numbers_in("২৫০ গ্রাম") == {Decimal("250")}
    assert numbers_in("Buy 5, 6 or 7.") == {Decimal("5"), Decimal("6"), Decimal("7")}


def test_clean_text_passes():
    assert codes({"headline": "Cotton Tote Bag, ৳1,299", "tagline": "35% off, two inner pockets"}) == []


def test_discount_percent_is_derived_from_prices():
    assert make_facts().discount_percent == Decimal("35")
    assert codes({"tagline": "Save 35%"}) == []
    assert codes({"tagline": "Save 50%"}) == ["invented_number"]


def test_invented_price_is_flagged():
    assert codes({"headline": "Only ৳999 today"}) == ["invented_number"]


def test_unit_equivalents_are_allowed():
    assert codes({"description": "A 0.5 kg bag"}) == []
    assert codes({"description": "A 2 kg bag"}) == ["invented_number"]


def test_numbers_from_features_are_allowed():
    assert codes({"description": "Made of 100% cotton"}) == []


def test_wrong_currency_is_flagged():
    assert "wrong_currency" in codes({"headline": "Now $12"}, make_facts(price=Decimal("12"), original_price=None))
    assert "wrong_currency" not in codes({"headline": "Now ৳1,299"})


def test_currency_words_need_word_boundaries():
    # "task" and "stalk" contain "tk"/"usd"-like letters but are not currency marks
    assert "wrong_currency" not in codes({"description": "Great for any task"}, make_facts(currency="USD"))


def test_risky_claims_need_support_in_user_text():
    assert codes({"headline": "The best bag in town"}) == ["risky_claim"]
    assert codes({"headline": "Guaranteed to last"}) == ["risky_claim"]
    assert codes({"tagline": "Free delivery"}) == ["risky_claim"]
    supported = make_facts(key_features=("Free delivery in Dhaka",))
    assert codes({"tagline": "Free delivery"}, supported) == []


def test_contacts_are_flagged():
    assert "invented_contact" in codes({"cta": "Visit www.example.com"})
    assert "invented_contact" in codes({"description": "Call 01712345678 now"})


def test_empty_fields_are_ignored():
    assert codes({"headline": "", "tagline": ""}) == []


def test_facts_from_product_object():
    product = SimpleNamespace(
        name=" Mug ", price=Decimal("5"), original_price=None, currency="USD", unit=None,
        key_features=["Ceramic"], allowed_claims=None, specs=None,
    )
    facts = facts_from_product(product, SimpleNamespace(name="Acme", tone_notes="friendly"))
    assert facts.name == "Mug" and facts.brand_name == "Acme" and facts.key_features == ("Ceramic",)
    assert facts.specs == {} and facts.allowed_claims == ()
