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

        self.assertIn("Leitura geral:", text)
        self.assertIn("Melhor entrada: Over 2.5 gols (Total de gols)", text)
        self.assertIn("Preco: odd 1.85, justa 1.61, value forte.", text)
        self.assertIn("Contexto:", text)
        self.assertIn("Alternativas:", text)
        self.assertLessEqual(len(text.splitlines()), 20)

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

        self.assertIn("Preco/value:", text)
        self.assertIn("sem linha equivalente", text.lower())
        self.assertIn("shortlist", text.lower())
        self.assertNotIn("Antes de entrar:", text)
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

        self.assertIn("Leitura geral: pre-jogo sem vantagem clara para entrar.", text)
        self.assertIn("sem entrada pre-jogo", text.lower())

    def test_response_always_keeps_context_and_alternatives(self) -> None:
        text = format_bet_advisor_response(
            {
                "fixture": {"home_team": "Bayern München", "away_team": "Paris Saint Germain"},
                "main_recommendation": {
                    "market": "Prop de jogador - finalizacoes",
                    "selection": "H. Kane: over em finalizacoes, se a linha estiver perto de 2.5",
                    "confidence": "media",
                    "risk_level": "medio",
                    "summary": "O mercado de jogo nao ficou tao claro, entao eu olharia primeiro para H. Kane em finalizacoes. A leitura vem do volume individual e do risco menor em relacao aos mercados principais.",
                    "fair_odd": 1.82,
                    "odds_note": "A Odds API nao retornou linha de prop equivalente para confirmar value.",
                },
                "context_summary": {
                    "summary_lines": [
                        "Bayern München: briga por vaga na final (semi-final).",
                        "Paris Saint Germain: briga por vaga na final (semi-final).",
                    ]
                },
                "alternative_recommendations": [
                    {"market": "Total de gols", "selection": "Over 2.5 gols", "reason": "medias combinadas sao fortes para tres gols."},
                    {"market": "Ambas marcam", "selection": "Sim", "reason": "os dois ataques tem producao minima para participar."},
                ],
                "avoid_markets": [{"market": "forcar vencedor pre-jogo", "reason": "leitura por time nao ficou forte."}],
                "warnings": [
                    "titularidade ainda precisa ser confirmada.",
                    "sem odds de props disponiveis, nao da para confirmar value.",
                ],
                "final_verdict": "Eu trataria H. Kane em finalizacoes como a melhor shortlist, mas so entraria com linha e odd justas.",
            }
        )

        self.assertIn("Contexto:", text)
        self.assertIn("Alternativas:", text)
        self.assertIn("Bayern München: briga por vaga na final", text)
        self.assertIn("Over 2.5 gols", text)
        self.assertIn("Preco/value: sem linha equivalente para props", text)
        self.assertNotIn("Preco e value:", text)
        self.assertLessEqual(len(text.splitlines()), 22)

    def test_response_keeps_compact_structure_with_verdict_first_half(self) -> None:
        text = format_bet_advisor_response(
            {
                "fixture": {"home_team": "Inter", "away_team": "Milan"},
                "main_recommendation": {
                    "market": "Ambas marcam",
                    "selection": "Sim",
                    "confidence": "media",
                    "risk_level": "medio",
                    "summary": "Os dois ataques produzem, mas ha risco por oscilacao no segundo tempo.",
                },
                "context_summary": {"summary_lines": ["Derbi com pressao alta e ritmo intenso."]},
                "final_verdict": "Entrada possivel apenas com odd justa.",
            }
        )

        first_half = "\n".join(text.splitlines()[:7]).lower()
        self.assertIn("leitura geral", first_half)
        self.assertIn("melhor entrada", first_half)
        self.assertIn("motivo", first_half)
        self.assertIn("riscos", first_half)


if __name__ == "__main__":
    unittest.main()
