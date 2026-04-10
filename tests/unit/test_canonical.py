"""Unit tests for scraper/canonical.py — product name canonicalization.

Tests are organized in three categories:
1. Must-match pairs — two names that should produce identical canonical_key
2. Must-not-match pairs — names that should NOT share the same canonical_key
3. Component tests — verify specific fields (quantity, brand, product_type)
"""
import pytest
from scraper.canonical import CanonicalProduct, canonicalize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def key(raw: str) -> str:
    return canonicalize(raw).canonical_key


# ---------------------------------------------------------------------------
# Must-match pairs (same canonical_key expected)
# ---------------------------------------------------------------------------

class TestMustMatch:
    """Pairs of names that describe the same product and must yield the same key."""

    def test_becherovka_volume_variants(self):
        """0,5 l and 500 ml are the same volume."""
        assert key("Becherovka 0,5 l") == key("Becherovka 500 ml")

    def test_rum_comma_vs_dot_decimal(self):
        """Czech comma decimal equals dot decimal."""
        assert key("Rum Jamaica 0,7 l") == key("Rum Jamaica 0.7 l")

    def test_litre_vs_ml(self):
        """1 l == 1000 ml."""
        assert key("Vodka 1 l") == key("Vodka 1000 ml")

    def test_kg_vs_gram(self):
        """1 kg == 1000 g."""
        assert key("Sýr Eidam 1 kg") == key("Sýr Eidam 1000 g")

    def test_stopword_akce_ignored(self):
        """'akce' stopword is stripped before comparison."""
        assert key("Pivo Pilsner 0,5 l akce") == key("Pivo Pilsner 0,5 l")

    def test_stopword_sleva_ignored(self):
        assert key("Rum Jamaica 0,7 l sleva") == key("Rum Jamaica 0,7 l")

    def test_stopword_novinka_ignored(self):
        assert key("Pivo Budvar 0,5 l novinka") == key("Pivo Budvar 0,5 l")

    def test_case_insensitive(self):
        """Uppercase vs lowercase product name."""
        assert key("RUM JAMAICA 0,7 L") == key("rum jamaica 0,7 l")

    def test_diacritics_stripped(self):
        """Diacritics are removed for comparison."""
        assert key("Mléko plnotučné 1 l") == key("Mleko plnotucne 1 l")

    def test_beer_with_different_casing(self):
        assert key("PIVO Pilsner Urquell 0,5 l") == key("pivo pilsner urquell 0,5 l")

    def test_vodka_dl_vs_ml(self):
        """1 dl == 100 ml."""
        assert key("Vodka 5 dl") == key("Vodka 500 ml")

    def test_cl_vs_ml(self):
        """50 cl == 500 ml."""
        assert key("Rum 50 cl") == key("Rum 500 ml")

    def test_same_brand_same_size(self):
        """Two identical items should obviously match."""
        assert key("Becherovka 0,5 l") == key("Becherovka 0,5 l")

    def test_wine_type_normalizes(self):
        """Víno and vino should resolve to same product type."""
        assert canonicalize("Víno Chardonnay 0,75 l").product_type == \
               canonicalize("vino chardonnay 750 ml").product_type

    def test_bio_stopword_ignored(self):
        assert key("Bio Mléko 1 l") == key("Mléko 1 l")


# ---------------------------------------------------------------------------
# Must-NOT-match pairs (different canonical_key expected)
# ---------------------------------------------------------------------------

class TestMustNotMatch:
    """Pairs of names that are different products and must NOT share the same key."""

    def test_different_volumes(self):
        """0,5 l != 0,7 l."""
        assert key("Becherovka 0,5 l") != key("Becherovka 0,7 l")

    def test_different_brands(self):
        """Rum Jamaica vs Becherovka are different products."""
        assert key("Rum Jamaica 0,7 l") != key("Becherovka 0,7 l")

    def test_different_product_types(self):
        """Beer vs wine are different types."""
        assert key("Pivo Pilsner 0,5 l") != key("Víno Chardonnay 0,5 l")

    def test_different_weight_units(self):
        """250 g != 500 g."""
        assert key("Sýr Eidam 250 g") != key("Sýr Eidam 500 g")

    def test_milk_vs_beer(self):
        assert key("Mléko plnotučné 1 l") != key("Pivo Pilsner 1 l")

    def test_kg_vs_litre_different_unit(self):
        """1 kg and 1 l are different canonical units."""
        assert key("Produkt 1 kg") != key("Produkt 1 l")

    def test_different_sizes_same_category(self):
        """Same category, different volumes → different keys."""
        assert key("Vodka 0,5 l") != key("Vodka 0,7 l")

    def test_different_quantity_pieces(self):
        """10 ks != 6 ks."""
        assert key("Jogurt 10 ks") != key("Jogurt 6 ks")

    def test_large_vs_small(self):
        assert key("Pivo 0,33 l") != key("Pivo 0,5 l")

    def test_brand_present_vs_absent(self):
        """With brand vs without brand — different canonical keys."""
        assert key("Becherovka 0,5 l") != key("Bylinný likér 0,5 l")


# ---------------------------------------------------------------------------
# Component tests
# ---------------------------------------------------------------------------

class TestQuantityExtraction:
    def test_extracts_litres_as_ml(self):
        cp = canonicalize("Pivo 0,5 l")
        assert cp.quantity_value == 500.0
        assert cp.quantity_unit == "ml"

    def test_extracts_kg_as_grams(self):
        cp = canonicalize("Sýr 250 g")
        assert cp.quantity_value == 250.0
        assert cp.quantity_unit == "g"

    def test_extracts_kilograms(self):
        cp = canonicalize("Mouka 1 kg")
        assert cp.quantity_value == 1000.0
        assert cp.quantity_unit == "g"

    def test_extracts_pieces(self):
        cp = canonicalize("Vajíčka 10 ks")
        assert cp.quantity_value == 10.0
        assert cp.quantity_unit == "ks"

    def test_no_quantity_returns_none(self):
        cp = canonicalize("Mléko plnotučné")
        assert cp.quantity_value is None
        assert cp.quantity_unit is None

    def test_comma_decimal(self):
        cp = canonicalize("Rum 0,7 l")
        assert cp.quantity_value == pytest.approx(700.0)

    def test_dot_decimal(self):
        cp = canonicalize("Rum 0.7 l")
        assert cp.quantity_value == pytest.approx(700.0)


class TestBrandExtraction:
    def test_known_brand_extracted(self):
        cp = canonicalize("Becherovka 0,5 l")
        assert cp.brand == "becherovka"

    def test_unknown_brand_is_none(self):
        cp = canonicalize("Neznámý produkt 0,5 l")
        assert cp.brand is None

    def test_brand_case_insensitive(self):
        cp = canonicalize("BECHEROVKA 0,5 l")
        assert cp.brand == "becherovka"


class TestProductTypeClassification:
    def test_rum_is_lihoviny(self):
        assert canonicalize("Rum Jamaica 0,7 l").product_type == "lihoviny"

    def test_pivo_is_pivo(self):
        assert canonicalize("Pilsner Urquell 0,5 l").product_type == "pivo"

    def test_vino_is_vino(self):
        assert canonicalize("Víno Chardonnay 0,75 l").product_type == "víno"

    def test_mleko_is_mlecne(self):
        assert canonicalize("Mléko plnotučné 1 l").product_type == "mléčné výrobky"

    def test_chleb_is_pecivo(self):
        assert canonicalize("Chléb celozrnný 500 g").product_type == "pečivo"

    def test_kava_is_kava(self):
        assert canonicalize("Káva mletá 250 g").product_type == "káva"

    def test_unknown_is_ostatni(self):
        assert canonicalize("Šroubky 100 ks").product_type == "ostatní"


class TestCanonicalKey:
    def test_key_format(self):
        """Key must be 'type|brand|qty'."""
        cp = canonicalize("Becherovka 0,5 l")
        parts = cp.canonical_key.split("|")
        assert len(parts) == 3
        assert parts[0] == cp.product_type
        assert parts[1] == (cp.brand or "-")

    def test_no_brand_uses_dash(self):
        cp = canonicalize("Rum Jamaica 0,7 l")
        # "rum" not in brands.txt → brand is None → "-" in key
        parts = cp.canonical_key.split("|")
        # product_type should be lihoviny
        assert parts[0] == "lihoviny"
        assert parts[1] == "-"

    def test_no_quantity_key_ends_empty(self):
        cp = canonicalize("Neznámý produkt")
        assert cp.canonical_key.endswith("|")
