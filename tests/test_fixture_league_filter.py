from __future__ import annotations

import unittest

from app.services.fixture_menu_service import FixtureMenuService, LeagueConfig


class FakeFixtureMenuService(FixtureMenuService):
    def __init__(self) -> None:
        pass

    def get_supported_leagues(self):
        return (
            LeagueConfig("premier_league", "Premier League", 39, 2025),
            LeagueConfig("la_liga", "La Liga", 140, 2025),
            LeagueConfig("serie_a", "Serie A", 135, 2025),
        )

    def get_fixtures_for_day(self, league_key: str, day_offset: int = 0) -> dict:
        fixtures_by_day = {
            0: {
                "premier_league": [{"fixture_id": 1}],
                "la_liga": [],
                "serie_a": [],
            },
            1: {
                "premier_league": [],
                "la_liga": [{"fixture_id": 2}],
                "serie_a": [],
            },
        }
        return {
            "ok": True,
            "fixtures": fixtures_by_day.get(day_offset, {}).get(league_key, []),
            "league": self.get_league(league_key),
        }


class FixtureLeagueFilterTest(unittest.TestCase):
    def test_league_with_games_today_appears(self) -> None:
        service = FakeFixtureMenuService()
        leagues = service.get_leagues_with_fixtures(day_offset=0)
        self.assertEqual([league.key for league in leagues], ["premier_league"])

    def test_league_without_games_today_does_not_appear(self) -> None:
        service = FakeFixtureMenuService()
        leagues = service.get_leagues_with_fixtures(day_offset=0)
        keys = [league.key for league in leagues]
        self.assertNotIn("la_liga", keys)
        self.assertNotIn("serie_a", keys)

    def test_tomorrow_league_appears_only_tomorrow(self) -> None:
        service = FakeFixtureMenuService()
        today_keys = [league.key for league in service.get_leagues_with_fixtures(day_offset=0)]
        tomorrow_keys = [league.key for league in service.get_leagues_with_fixtures(day_offset=1)]
        self.assertNotIn("la_liga", today_keys)
        self.assertIn("la_liga", tomorrow_keys)

    def test_no_leagues_returns_empty_list(self) -> None:
        class EmptyFixtureMenuService(FakeFixtureMenuService):
            def get_fixtures_for_day(self, league_key: str, day_offset: int = 0) -> dict:
                return {"ok": True, "fixtures": [], "league": self.get_league(league_key)}

        self.assertEqual(EmptyFixtureMenuService().get_leagues_with_fixtures(day_offset=0), [])


if __name__ == "__main__":
    unittest.main()
