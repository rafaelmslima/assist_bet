from __future__ import annotations

import unittest

from app.services.value_service import ValueService


class ValueServiceTest(unittest.TestCase):
    def test_implied_probability_and_fair_odd(self) -> None:
        service = ValueService()

        self.assertAlmostEqual(service.implied_probability(2.0), 0.5)
        self.assertAlmostEqual(service.decimal_odd_from_probability(0.5), 2.0)

    def test_calculate_value_classification(self) -> None:
        service = ValueService()

        value = service.calculate_value(estimated_probability=0.62, market_odd=1.80)

        self.assertEqual(value["confidence_level"], "value positivo")
        self.assertTrue(value["has_value"])
        self.assertGreater(value["edge"], 0.05)


if __name__ == "__main__":
    unittest.main()

