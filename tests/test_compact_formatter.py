from __future__ import annotations

import unittest

from app.bot.formatters import format_bet_advisor_response


class CompactFormatterTest(unittest.TestCase):
    def test_formatter_returns_qualitative_analysis_response(self) -> None:
        text = format_bet_advisor_response(
            {
                "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
                "main_recommendation": {
                    "market": "gols",
                    "selection": "Over 1.5 gols",
                    "summary": "Jogo tem mais cara de gols do que vencedor.",
                },
                "context_summary": {
                    "summary_lines": [
                        "Arsenal: jogo de Champions League em 4 dias.",
                        "Chelsea: meio de tabela.",
                    ]
                },
                "alternative_recommendations": [{"market": "gol do mandante", "selection": "Arsenal marcar", "reason": "bom recorte casa/fora"}],
                "avoid_markets": [{"market": "vitoria seca do Arsenal", "reason": "risco de roteiro travado"}],
                "final_verdict": "Eu olharia gols antes de vencedor.",
            }
        )

        self.assertIn("A leitura aqui", text)
        self.assertIn("Como ideia de mercado", text)
        self.assertIn("O contexto pesa", text)
        self.assertIn("Se quiser uma segunda leitura", text)
        self.assertIn("Arsenal: jogo de Champions League em 4 dias.", text)
        self.assertNotIn("Ideia geral:", text)
        self.assertNotIn("Ideias alternativas:", text)
        self.assertNotIn("value", text.lower())
        self.assertNotIn("odd", text.lower())
        self.assertLessEqual(len(text.splitlines()), 20)

    def test_formatter_keeps_context_for_player_recommendation(self) -> None:
        text = format_bet_advisor_response(
            {
                "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
                "main_recommendation": {
                    "market": "jogador - finalizacoes",
                    "selection": "Saka: olhar finalizacoes",
                    "summary": "Mercado de jogo sem clareza; jogador tem caminho melhor.",
                },
                "context_summary": {
                    "summary_lines": [
                        "Arsenal: jogo de Champions League em 4 dias.",
                        "Chelsea: meio de tabela.",
                    ]
                },
                "final_verdict": "Usar como shortlist qualitativa.",
            }
        )

        self.assertIn("Arsenal: jogo de Champions League em 4 dias.", text)
        self.assertIn("Chelsea: meio de tabela.", text)

    def test_formatter_shows_competitive_status_objectively(self) -> None:
        text = format_bet_advisor_response(
            {
                "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
                "main_recommendation": {
                    "market": "gols",
                    "selection": "Over 1.5 gols",
                    "summary": "Leitura de gols segue valida pelo roteiro.",
                },
                "context_summary": {
                    "summary_lines": [
                        "Arsenal: ja garantiu vaga em Champions matematicamente.",
                        "Chelsea: lidera, mas ainda pode perder o titulo matematicamente.",
                    ]
                },
                "final_verdict": "Ideia com cautela.",
            }
        )
        self.assertIn("ja garantiu vaga", text)
        self.assertIn("ainda pode perder o titulo", text)


if __name__ == "__main__":
    unittest.main()
