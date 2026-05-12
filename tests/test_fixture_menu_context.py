from __future__ import annotations

import unittest

from app.services.fixture_menu_service import FixtureMenuService, LeagueConfig


class FakeFixtureMenuService(FixtureMenuService):
    def __init__(self) -> None:
        pass

    def get_supported_leagues(self):
        return (LeagueConfig("premier_league", "Premier League", 39, 2025),)

    def get_today_fixtures(self, league_key: str) -> dict:
        return {
            "ok": True,
            "fixtures": [{"fixture_id": 10, "home_team": "Arsenal", "away_team": "Chelsea"}],
            "league": self.get_supported_leagues()[0],
        }

    def build_fixture_advisor_payload(self, fixture_id: int | str, include_players: bool = True) -> dict:
        return {
            "fixture": {"fixture_id": fixture_id, "home_team": "Arsenal", "away_team": "Chelsea"},
            "advice": {
                "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
                "main_recommendation": {
                    "market": "gols",
                    "selection": "Over 1.5 gols",
                    "confidence": "media",
                    "risk_level": "medio",
                    "summary": "Arsenal deve propor e Chelsea pode responder em transicao.",
                },
                "context_summary": {
                    "summary_lines": [
                        "Arsenal: jogo de Champions League em 4 dias.",
                        "Chelsea: meio de tabela.",
                    ]
                },
                "final_verdict": "Eu olharia gols antes de vencedor.",
            },
            "analysis": {
                "general_idea": "Arsenal deve propor e Chelsea pode responder em transicao.",
                "confidence": {"level": "amarela", "reason": "boa leitura, mas falta escalação."},
            },
        }


class FixtureMenuContextTest(unittest.TestCase):
    def test_best_games_today_includes_context(self) -> None:
        text = FakeFixtureMenuService().get_best_games_today()

        self.assertIn("Contexto:", text)
        self.assertIn("Arsenal: jogo de Champions League em 4 dias.", text)
        self.assertIn("Chelsea: meio de tabela.", text)


if __name__ == "__main__":
    unittest.main()
