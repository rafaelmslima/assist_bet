from __future__ import annotations

import unittest

from app.services.football_response_service import FootballResponseService


class ProfessionalFootballResponseTest(unittest.TestCase):
    def test_response_centers_game_reading_and_market_ideas(self) -> None:
        text = FootballResponseService().format_advice(
            {
                "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
                "main_recommendation": {
                    "market": "gols",
                    "selection": "Over 1.5 gols",
                    "confidence": "media",
                    "risk_level": "medio",
                    "summary": "Arsenal deve propor mais, mas Chelsea tem transicao para incomodar.",
                },
                "context_summary": {"summary_lines": ["Arsenal: briga por titulo."]},
                "warnings": ["confirmar escalacoes"],
                "final_verdict": "Ideia qualitativa, nao certeza.",
            }
        )

        self.assertIn("A leitura aqui", text)
        self.assertIn("Como ideia de mercado, eu olharia primeiro para Over 1.5 gols", text)
        self.assertIn("O ponto de cuidado é confirmar escalacoes", text)
        self.assertIn("O contexto pesa", text)
        self.assertNotIn("Ideia geral:", text)
        self.assertNotIn("Riscos:", text)
        self.assertNotIn("value", text.lower())
        self.assertNotIn("odd", text.lower())

    def test_avoid_response_is_explicit(self) -> None:
        text = FootballResponseService().format_advice(
            {
                "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
                "main_recommendation": {
                    "market": "sem mercado claro",
                    "selection": "jogo para observacao",
                    "confidence": "baixa",
                    "risk_level": "alto",
                },
                "avoid_markets": [{"market": "vencedor seco", "reason": "roteiro instavel"}],
                "final_verdict": "Nao forcar mercado.",
            }
        )

        self.assertIn("jogo para observacao", text.lower())
        self.assertIn("vencedor seco", text.lower())

    def test_response_keeps_competitive_status_with_direct_language(self) -> None:
        text = FootballResponseService().format_advice(
            {
                "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
                "main_recommendation": {
                    "market": "gols",
                    "selection": "Over 1.5 gols",
                    "summary": "Leitura tecnica existe, mas contexto competitivo pede cautela.",
                },
                "context_summary": {
                    "summary_lines": [
                        "Arsenal: ja campeao matematicamente; objetivo principal cumprido.",
                        "Chelsea: fora da zona, mas ainda em risco matematico de rebaixamento.",
                    ]
                },
                "final_verdict": "Nao forcar mercado.",
            }
        )
        self.assertIn("ja campeao matematicamente", text)
        self.assertIn("ainda em risco matematico de rebaixamento", text)


if __name__ == "__main__":
    unittest.main()
