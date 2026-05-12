from __future__ import annotations

import unittest

from app.services.fixture_menu_service import FixtureMenuService


class SulamericanaSupportTest(unittest.TestCase):
    def test_supported_leagues_includes_sulamericana(self) -> None:
        leagues = FixtureMenuService().get_supported_leagues()
        league = next((item for item in leagues if item.key == "sulamericana"), None)

        self.assertIsNotNone(league)
        self.assertEqual(league.league_id, 11)


if __name__ == "__main__":
    unittest.main()
