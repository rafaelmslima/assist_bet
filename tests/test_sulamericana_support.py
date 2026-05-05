from __future__ import annotations

import unittest

from app.services.fixture_menu_service import FixtureMenuService
from app.services.odds_service import FOOTBALL_LEAGUE_TO_ODDS_SPORT


class SulamericanaSupportTest(unittest.TestCase):
    def test_supported_leagues_includes_sulamericana(self) -> None:
        leagues = FixtureMenuService().get_supported_leagues()
        league = next((item for item in leagues if item.key == "sulamericana"), None)

        self.assertIsNotNone(league)
        self.assertEqual(league.league_id, 11)

    def test_odds_mapping_includes_sulamericana(self) -> None:
        self.assertEqual(FOOTBALL_LEAGUE_TO_ODDS_SPORT[11], "soccer_conmebol_copa_sudamericana")


if __name__ == "__main__":
    unittest.main()

