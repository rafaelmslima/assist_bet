from __future__ import annotations

import unittest

from app.bot.formatters import format_bet_advisor_response


class CompactFormatterTest(unittest.TestCase):
    def test_formatter_returns_short_decision_first_response(self) -> None:
        text = format_bet_advisor_response(
            {
                "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
                "main_recommendation": {
                    "market": "Total de gols",
                    "selection": "Over 1.5 gols",
                    "summary": "Jogo tem mais cara de gols do que vencedor.",
                    "fair_odd": 1.62,
                },
                "context_summary": {
                    "summary_lines": [
                        "Arsenal: jogo de Champions League em 4 dias.",
                        "Chelsea: meio de tabela.",
                    ]
                },
                "alternative_recommendations": [{"market": "Resultado", "selection": "Arsenal DNB", "reason": "mais seguro"}],
                "avoid_markets": [{"market": "vitoria seca do Arsenal", "reason": "odd pode estar baixa"}],
                "final_verdict": "Eu olharia gols antes de vencedor.",
            }
        )

        self.assertIn("Melhor aposta:", text)
        self.assertIn("Contexto:", text)
        self.assertIn("Arsenal: jogo de Champions League em 4 dias.", text)
        self.assertNotIn("Por que faz sentido", text)
        self.assertLessEqual(len(text.splitlines()), 24)


if __name__ == "__main__":
    unittest.main()

