from __future__ import annotations

import unittest

from app.services.football_context_service import FootballContextService


class FootballContextServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = FootballContextService()

    def test_leader_champion_locked(self) -> None:
        context = self.service.build_context_summary(
            fixture=_fixture(home_id=1, home="Arsenal", away_id=2, away="Liverpool"),
            standings_response=_standings_locked_champion(),
            home_schedule_response={"ok": True, "data": []},
            away_schedule_response={"ok": True, "data": []},
        )
        self.assertEqual(context["competitive_states"]["home"], "champion_locked")
        self.assertIn("ja campeao matematicamente", context["home_context_summary"])

    def test_leader_still_at_risk(self) -> None:
        context = self.service.build_context_summary(
            fixture=_fixture(home_id=1, home="Arsenal", away_id=2, away="Liverpool"),
            standings_response=_standings_title_risk(),
            home_schedule_response={"ok": True, "data": []},
            away_schedule_response={"ok": True, "data": []},
        )
        self.assertEqual(context["competitive_states"]["home"], "title_still_at_risk")
        self.assertIn("ainda pode perder o titulo", context["home_context_summary"])

    def test_continental_locked(self) -> None:
        context = self.service.build_context_summary(
            fixture=_fixture(home_id=4, home="Tottenham", away_id=8, away="Brighton"),
            standings_response=_standings_continental_locked(),
            home_schedule_response={"ok": True, "data": []},
            away_schedule_response={"ok": True, "data": []},
        )
        self.assertEqual(context["competitive_states"]["home"], "continental_locked")
        self.assertIn("ja garantiu vaga", context["home_context_summary"])

    def test_continental_at_risk(self) -> None:
        context = self.service.build_context_summary(
            fixture=_fixture(home_id=6, home="Chelsea", away_id=8, away="Brighton"),
            standings_response=_standings_title_risk(),
            home_schedule_response={"ok": True, "data": []},
            away_schedule_response={"ok": True, "data": []},
        )
        self.assertEqual(context["competitive_states"]["home"], "continental_at_risk")
        self.assertIn("ainda pode perder a vaga", context["home_context_summary"])

    def test_relegated_locked(self) -> None:
        context = self.service.build_context_summary(
            fixture=_fixture(home_id=20, home="Sheffield United", away_id=18, away="Burnley"),
            standings_response=_standings_relegated_locked(),
            home_schedule_response={"ok": True, "data": []},
            away_schedule_response={"ok": True, "data": []},
        )
        self.assertEqual(context["competitive_states"]["home"], "relegated_locked")
        self.assertIn("ja rebaixado matematicamente", context["home_context_summary"])

    def test_outside_zone_but_relegation_risk(self) -> None:
        context = self.service.build_context_summary(
            fixture=_fixture(home_id=17, home="Nottingham Forest", away_id=10, away="Brentford"),
            standings_response=_standings_relegation_risk(),
            home_schedule_response={"ok": True, "data": []},
            away_schedule_response={"ok": True, "data": []},
        )
        self.assertEqual(context["competitive_states"]["home"], "relegation_at_risk")
        self.assertIn("ainda em risco matematico de rebaixamento", context["home_context_summary"])


def _fixture(home_id: int, home: str, away_id: int, away: str) -> dict:
    return {
        "fixture_date": "2026-05-01T19:00:00+00:00",
        "league_id": 39,
        "home_team_id": home_id,
        "away_team_id": away_id,
        "home_team": home,
        "away_team": away,
    }


def _rows(points: list[tuple[str, int]], played: int = 37) -> dict:
    standings = []
    for idx, (name, pts) in enumerate(points, start=1):
        standings.append({"rank": idx, "points": pts, "all": {"played": played}, "team": {"id": idx, "name": name}})
    return {"ok": True, "data": [{"league": {"standings": [standings]}}]}


def _standings_locked_champion() -> dict:
    return _rows(
        [
            ("Arsenal", 90),
            ("Liverpool", 82),
            ("Man City", 79),
            ("Tottenham", 68),
            ("Newcastle", 61),
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
    )


def _standings_title_risk() -> dict:
    return _rows(
        [
            ("Arsenal", 83),
            ("Liverpool", 81),
            ("Man City", 80),
            ("Tottenham", 66),
            ("Newcastle", 62),
            ("Chelsea", 60),
            ("Aston Villa", 59),
            ("Brighton", 58),
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
    )


def _standings_continental_locked() -> dict:
    return _rows(
        [
            ("Arsenal", 90),
            ("Liverpool", 84),
            ("Man City", 81),
            ("Tottenham", 70),
            ("Newcastle", 59),
            ("Chelsea", 58),
            ("Aston Villa", 57),
            ("Brighton", 48),
            ("West Ham", 47),
            ("Brentford", 44),
            ("Crystal Palace", 41),
            ("Fulham", 40),
            ("Everton", 38),
            ("Wolves", 36),
            ("Leeds", 34),
            ("Sunderland", 31),
            ("Nottingham Forest", 30),
            ("Burnley", 28),
            ("Bournemouth", 27),
            ("Sheffield United", 20),
        ]
    )


def _standings_relegated_locked() -> dict:
    return _rows(
        [
            ("Arsenal", 82),
            ("Liverpool", 80),
            ("Man City", 78),
            ("Tottenham", 68),
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
            ("Sheffield United", 19),
        ]
    )


def _standings_relegation_risk() -> dict:
    return _rows(
        [
            ("Arsenal", 82),
            ("Liverpool", 80),
            ("Man City", 78),
            ("Tottenham", 68),
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
            ("Sunderland", 33),
            ("Nottingham Forest", 30),
            ("Burnley", 29),
            ("Bournemouth", 28),
            ("Sheffield United", 27),
        ]
    )


if __name__ == "__main__":
    unittest.main()
