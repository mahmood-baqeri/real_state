from decimal import Decimal
from django.test import SimpleTestCase
from apps.search.services import score_property_for_requirement
from apps.search.phase4 import convert_currency_amount, normalize_persian_search, search_variants


class Phase4MatchingUnitTests(SimpleTestCase):
    def test_persian_normalization_and_synonyms(self):
        self.assertEqual(normalize_persian_search("ك\u200cآپارتمان\u200c تهران"), "ک آپارتمان تهران")
        self.assertIn("اپارتمان تهران", search_variants("آپارتمان تهران"))

    def test_currency_conversion_direct_inverse_and_chain(self):
        rates = [
            ("USD", "IRT", Decimal("65000")),
            ("IRT", "IRR", Decimal("10")),
            ("USD", "AED", Decimal("3.6725")),
        ]
        self.assertEqual(convert_currency_amount("2", "USD", "AED", rates), Decimal("7.3450"))
        self.assertEqual(convert_currency_amount("10", "AED", "USD", rates), Decimal("10") / Decimal("3.6725"))
        self.assertEqual(convert_currency_amount("1", "USD", "IRR", rates), Decimal("650000"))

    def test_rental_budget_and_place_match(self):
        prop = {
            "id": "p-1", "property_code": "P-1", "title": "واحد مسکونی",
            "deal_type_id": "RENT", "property_type_id": "APARTMENT",
            "city": "تهران", "district": "زعفرانیه", "total_price": "0",
            "rent_amount": "50000000", "built_area_sqm": "150", "bedrooms": 3,
            "amenity_codes": ["PARKING", "ELEVATOR"],
        }
        req = {
            "deal_type_id": "RENT", "property_type_id": "APARTMENT", "is_rental": True,
            "target_city": "تهران", "target_districts": ["زعفرانیه"],
            "min_budget": Decimal("40000000"), "max_budget": Decimal("60000000"),
            "min_area_sqm": Decimal("120"), "max_area_sqm": Decimal("180"),
            "min_bedrooms": 2, "preferred_amenities": ["PARKING", "ELEVATOR"],
        }
        result = score_property_for_requirement(prop, req)
        self.assertEqual(result["match_score"], 100)
        self.assertIn("کاملاً در محدوده بودجه", result["reasons"])

    def test_out_of_budget_is_reported_as_mismatch(self):
        prop = {
            "id": "p-2", "property_code": "P-2", "title": "واحد",
            "deal_type_id": "SALE", "property_type_id": "APARTMENT",
            "city": "تهران", "district": "شهرک غرب", "total_price": "80000000000",
            "rent_amount": "0", "built_area_sqm": "100", "bedrooms": 1,
            "amenity_codes": [],
        }
        req = {
            "deal_type_id": "SALE", "property_type_id": "APARTMENT", "is_rental": False,
            "target_city": "تهران", "target_districts": [],
            "min_budget": Decimal("10000000000"), "max_budget": Decimal("30000000000"),
            "min_area_sqm": Decimal("50"), "max_area_sqm": Decimal("150"),
            "min_bedrooms": 1, "preferred_amenities": [],
        }
        result = score_property_for_requirement(prop, req)
        self.assertIn("خارج از بودجه هدف", result["mismatches"])
