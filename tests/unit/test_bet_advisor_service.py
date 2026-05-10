from __future__ import annotations

import unittest

from app.services.bet_advisor_service import BetAdvisorService


class BetAdvisorServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = BetAdvisorService()

    def test_never_returns_player_prop_in_main_analysis(self) -> None:
        response = self.service.advise_fixture_bets(_fixture_analysis_with_player())
        market = str((response.get("main_recommendation") or {}).get("market") or "")
        self.assertNotIn("Prop de jogador", market)

    def test_competitive_locked_context_increases_caution(self) -> None:
        payload = _fixture_analysis_with_player()
        payload["context"]["football_context"] = {
            "competitive_states": {"home": "champion_locked", "away": "safe_midtable"},
            "context_alerts": ["ALTA: time ja campeao; risco de rotacao."],
            "summary_lines": [],
        }
        response = self.service.advise_fixture_bets(payload)
        self.assertIn((response.get("main_recommendation") or {}).get("risk_level"), {"médio", "alto", "medio"})
        warnings = " ".join(response.get("warnings") or []).lower()
        self.assertIn("contexto competitivo", warnings)

    def test_weak_game_returns_no_entry_without_prop_fallback(self) -> None:
        response = self.service.advise_fixture_bets(_weak_fixture_analysis())
        main = response.get("main_recommendation") or {}
        self.assertEqual(main.get("selection"), "evitar")
        self.assertIn("sem entrada clara", str(main.get("market") or "").lower())


def _fixture_analysis_with_player() -> dict:
    return {
        "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
        "home_team_data": {
            "name": "Arsenal",
            "home_avg_scored": 1.7,
            "home_avg_conceded": 1.1,
            "last_5_avg_scored": 1.6,
            "last_5_avg_conceded": 1.0,
            "last_5_form": "WWDWL",
        },
        "away_team_data": {
            "name": "Chelsea",
            "away_avg_scored": 1.2,
            "away_avg_conceded": 1.5,
            "last_5_avg_scored": 1.1,
            "last_5_avg_conceded": 1.4,
            "last_5_form": "DWLWD",
        },
        "context": {},
        "odds": [],
        "player_advice": {
            "best": {
                "player": "Saka",
                "market": "finalizacoes",
                "selection": "over 2.5",
                "risk_level": "baixo",
                "warnings": [],
                "reasons": ["volume alto"],
            }
        },
    }


def _weak_fixture_analysis() -> dict:
    return {
        "fixture": {"home_team": "Time A", "away_team": "Time B"},
        "home_team_data": {
            "name": "Time A",
            "home_avg_scored": 0.7,
            "home_avg_conceded": 1.6,
            "last_5_avg_scored": 0.6,
            "last_5_avg_conceded": 1.7,
            "last_5_form": "LLDLL",
        },
        "away_team_data": {
            "name": "Time B",
            "away_avg_scored": 0.6,
            "away_avg_conceded": 1.5,
            "last_5_avg_scored": 0.7,
            "last_5_avg_conceded": 1.6,
            "last_5_form": "LDLLL",
        },
        "context": {},
        "odds": [],
        "player_advice": {
            "best": {
                "player": "Atacante",
                "market": "finalizacoes",
                "selection": "over 1.5",
                "risk_level": "baixo",
            }
        },
    }


if __name__ == "__main__":
    unittest.main()
