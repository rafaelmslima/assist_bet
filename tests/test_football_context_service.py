from __future__ import annotations

import unittest

from app.services.football_context_service import FootballContextService


class FootballContextServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = FootballContextService()

    def test_table_classifies_european_spots_middle_and_relegation(self) -> None:
        standings_response = _premier_standings()

        champions = self.service.build_context_summary(
            fixture=_fixture(home_id=1, home="Arsenal", away_id=6, away="Chelsea", league_id=39),
            standings_response=standings_response,
            home_schedule_response={"ok": True, "data": []},
            away_schedule_response={"ok": True, "data": []},
        )
        middle = self.service.build_context_summary(
            fixture=_fixture(home_id=13, home="Everton", away_id=18, away="Burnley", league_id=39),
            standings_response=standings_response,
            home_schedule_response={"ok": True, "data": []},
            away_schedule_response={"ok": True, "data": []},
        )

        self.assertIn("zona de Champions", champions["home_context_summary"])
        self.assertIn("zona de vaga europeia", champions["away_context_summary"])
        self.assertIn("meio de tabela", middle["home_context_summary"])
        self.assertIn("pressionado por rebaixamento", middle["away_context_summary"])

    def test_team_near_european_zone_is_direct_race(self) -> None:
        context = self.service.build_context_summary(
            fixture=_fixture(home_id=8, home="Brighton", away_id=12, away="Fulham", league_id=39),
            standings_response=_premier_standings(),
            home_schedule_response={"ok": True, "data": []},
            away_schedule_response={"ok": True, "data": []},
        )

        self.assertIn("briga diretamente por vaga europeia", context["home_context_summary"])
        self.assertIn("esta a 3 pontos do 7o", context["home_context_summary"])

    def test_team_with_math_chance_but_distant_is_marked_as_distant(self) -> None:
        context = self.service.build_context_summary(
            fixture=_fixture(home_id=10, home="Brentford", away_id=12, away="Fulham", league_id=39),
            standings_response=_premier_standings(),
            home_schedule_response={"ok": True, "data": []},
            away_schedule_response={"ok": True, "data": []},
        )

        self.assertIn("chance matematica de vaga europeia", context["home_context_summary"])
        self.assertIn("cenario distante", context["home_context_summary"])

    def test_standings_without_played_uses_fallback_and_does_not_break(self) -> None:
        standings = _premier_standings(include_played=False)
        context = self.service.build_context_summary(
            fixture=_fixture(home_id=8, home="Brighton", away_id=12, away="Fulham", league_id=39),
            standings_response=standings,
            home_schedule_response={"ok": True, "data": []},
            away_schedule_response={"ok": True, "data": []},
        )

        self.assertIn("briga por vaga europeia", context["home_context_summary"])

    def test_detects_upcoming_international_game_inside_five_days_only(self) -> None:
        context = self.service.build_context_summary(
            fixture=_fixture(home_id=1, home="Arsenal", away_id=6, away="Chelsea", league_id=39),
            standings_response=_premier_standings(),
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


def _premier_standings(include_played: bool = True) -> dict:
    table = [
        ("Arsenal", 75),
        ("Liverpool", 73),
        ("Man City", 71),
        ("Tottenham", 66),
        ("Newcastle", 62),
        ("Chelsea", 60),
        ("Aston Villa", 58),
        ("Brighton", 55),
        ("West Ham", 52),
        ("Brentford", 49),
        ("Crystal Palace", 46),
        ("Fulham", 43),
        ("Everton", 40),
        ("Wolves", 38),
        ("Leeds", 35),
        ("Sunderland", 32),
        ("Nottingham Forest", 30),
        ("Burnley", 28),
        ("Bournemouth", 27),
        ("Sheffield United", 20),
    ]
    standings = []
    for index, (name, points) in enumerate(table, start=1):
        row = {"rank": index, "points": points, "team": {"id": index, "name": name}}
        if include_played:
            row["all"] = {"played": 33}
        standings.append(row)
    return {"ok": True, "data": [{"league": {"standings": [standings]}}]}


def _scheduled_game(date: str, league: str) -> dict:
    return {"fixture": {"date": date}, "league": {"name": league}}


if __name__ == "__main__":
    unittest.main()
