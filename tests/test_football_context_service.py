from __future__ import annotations

import unittest

from app.services.football_context_service import FootballContextService


class FootballContextServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = FootballContextService()

    def test_table_classifies_european_spots_middle_and_relegation(self) -> None:
        standings_response = _standings_response(
            [
                (1, "Arsenal"),
                (6, "Chelsea"),
                (12, "Fulham"),
                (20, "Burnley"),
            ],
            total=20,
        )

        champions = self.service.build_context_summary(
            fixture=_fixture(home_id=1, home="Arsenal", away_id=6, away="Chelsea", league_id=39),
            standings_response=standings_response,
            home_schedule_response={"ok": True, "data": []},
            away_schedule_response={"ok": True, "data": []},
        )
        middle = self.service.build_context_summary(
            fixture=_fixture(home_id=12, home="Fulham", away_id=20, away="Burnley", league_id=39),
            standings_response=standings_response,
            home_schedule_response={"ok": True, "data": []},
            away_schedule_response={"ok": True, "data": []},
        )

        self.assertIn("briga por Champions", champions["home_context_summary"])
        self.assertIn("briga por vaga europeia", champions["away_context_summary"])
        self.assertIn("meio de tabela", middle["home_context_summary"])
        self.assertIn("luta contra rebaixamento", middle["away_context_summary"])

    def test_detects_upcoming_international_game_inside_five_days_only(self) -> None:
        context = self.service.build_context_summary(
            fixture=_fixture(home_id=1, home="Arsenal", away_id=6, away="Chelsea", league_id=39),
            standings_response=_standings_response([(1, "Arsenal"), (6, "Chelsea")], total=20),
            home_schedule_response={
                "ok": True,
                "data": [_scheduled_game("2026-05-05T20:00:00+00:00", "Champions League")],
            },
            away_schedule_response={
                "ok": True,
                "data": [_scheduled_game("2026-05-12T20:00:00+00:00", "Europa League")],
            },
        )

        self.assertIn("Champions League em 4 dias", context["home_context_summary"])
        self.assertNotIn("Europa League", context["away_context_summary"])


def _fixture(home_id: int, home: str, away_id: int, away: str, league_id: int) -> dict:
    return {
        "fixture_date": "2026-05-01T19:00:00+00:00",
        "league_id": league_id,
        "home_team_id": home_id,
        "away_team_id": away_id,
        "home_team": home,
        "away_team": away,
    }


def _standings_response(rows: list[tuple[int, str]], total: int) -> dict:
    standings = []
    for position, name in rows:
        standings.append({"rank": position, "team": {"id": position, "name": name}})
    while len(standings) < total:
        position = len(standings) + 1
        standings.append({"rank": position, "team": {"id": 1000 + position, "name": f"Team {position}"}})
    return {"ok": True, "data": [{"league": {"standings": [standings]}}]}


def _scheduled_game(date: str, league: str) -> dict:
    return {"fixture": {"date": date}, "league": {"name": league}}


if __name__ == "__main__":
    unittest.main()

