from __future__ import annotations

import unittest

from app.bot.formatters import format_bet_advisor_response


class ProfessionalFootballResponseTest(unittest.TestCase):
    def test_response_with_value_separates_price_from_context(self) -> None:
        text = format_bet_advisor_response(
            {
                "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
                "main_recommendation": {
                    "market": "Total de gols",
                    "selection": "Over 2.5 gols",
                    "confidence": "alta",
                    "risk_level": "baixo",
                    "summary": "Jogo tem ritmo e producao ofensiva para gols.",
                    "estimated_probability": 0.62,
                    "fair_odd": 1.61,
                    "value": {
                        "odd": 1.85,
                        "implied_probability": 0.5405,
                        "estimated_probability": 0.62,
                        "edge": 0.0795,
                        "classification": "value forte",
                    },
                },
                "context_summary": {"summary_lines": ["Arsenal: briga por titulo."]},
                "warnings": ["confirme escalacoes"],
                "final_verdict": "Entrada possivel com gestao.",
            }
        )

        self.assertIn("Melhor aposta: Over 2.5 gols", text)
        self.assertIn("Preco e value:", text)
        self.assertIn("Leitura: value forte.", text)
        self.assertIn("Gestao sugerida: entrada normal", text)

    def test_response_without_odds_does_not_claim_value(self) -> None:
        text = format_bet_advisor_response(
            {
                "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
                "main_recommendation": {
                    "market": "Resultado",
                    "selection": "Arsenal",
                    "confidence": "media",
                    "risk_level": "medio",
                    "estimated_probability": 0.56,
                    "fair_odd": 1.79,
                    "min_acceptable_odd": 1.90,
                },
                "warnings": ["sem odds disponiveis"],
                "final_verdict": "Shortlist apenas.",
            }
        )

        self.assertIn("Sem odds equivalentes", text)
        self.assertIn("shortlist", text.lower())
        self.assertNotIn("value forte", text)

    def test_avoid_response_is_explicit(self) -> None:
        text = format_bet_advisor_response(
            {
                "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
                "main_recommendation": {
                    "market": "sem entrada clara pre-jogo",
                    "selection": "evitar",
                    "confidence": "baixa",
                    "risk_level": "alto",
                },
                "final_verdict": "Nao forcar entrada.",
            }
        )

        self.assertIn("Melhor aposta: evitar", text)
        self.assertIn("sem entrada pre-jogo", text.lower())


if __name__ == "__main__":
    unittest.main()
