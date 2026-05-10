from __future__ import annotations

import json

from app.services.football_ai_analysis_service import FootballAIAnalysisService
from app.services.football_match_dossier_service import FootballMatchDossierService


class FakeClient:
    def get_team_fixtures(self, team_id, last=5, league_id=None, season=None):
        return {
            "ok": True,
            "data": [
                {"fixture": {"id": team_id * 10 + 1}},
                {"fixture": {"id": team_id * 10 + 2}},
            ],
        }

    def get_fixture_statistics(self, fixture_id):
        team_id = fixture_id // 10
        opponent_id = 999
        return {
            "ok": True,
            "data": [
                {
                    "team": {"id": team_id},
                    "statistics": [{"type": "Corner Kicks", "value": 6}],
                },
                {
                    "team": {"id": opponent_id},
                    "statistics": [{"type": "Corner Kicks", "value": 4}],
                },
            ],
        }


class DummyOpenAIClient:
    def analyze_football_dossier(self, dossier):
        return None


class StructuredOpenAIClient:
    def analyze_football_dossier(self, dossier):
        return json.dumps(
            {
                "fixture_label": "Arsenal x Chelsea",
                "probabilities": [
                    {
                        "market_key": "over_1_5_goals",
                        "label": "Over 1.5 gols",
                        "probability_percent": 72,
                        "confidence": "media",
                        "rationale": "boa soma ofensiva",
                        "data_status": "estimado",
                    },
                    {
                        "market_key": "over_2_5_goals",
                        "label": "Over 2.5 gols",
                        "probability_percent": 49,
                        "confidence": "baixa",
                        "rationale": "risco de controle",
                        "data_status": "estimado",
                    },
                    {
                        "market_key": "home_over_0_5_goals",
                        "label": "Gol do mandante",
                        "probability_percent": 78,
                        "confidence": "media",
                        "rationale": "mandante cria bem",
                        "data_status": "estimado",
                    },
                    {
                        "market_key": "away_over_0_5_goals",
                        "label": "Gol do visitante",
                        "probability_percent": 55,
                        "confidence": "media",
                        "rationale": "visitante tem volume suficiente",
                        "data_status": "estimado",
                    },
                    {
                        "market_key": "favorite_win",
                        "label": "Vitoria do favorito",
                        "probability_percent": 46,
                        "confidence": "baixa",
                        "rationale": "favorito com preco curto",
                        "data_status": "estimado",
                    },
                    {
                        "market_key": "corners",
                        "label": "Escanteios",
                        "probability_percent": None,
                        "confidence": "baixa",
                        "rationale": "amostra fraca",
                        "data_status": "dados_insuficientes",
                    },
                ],
                "match_reading": (
                    "Arsenal chega melhor em casa, mas o contexto ainda tem risco de rotacao. "
                    "Chelsea tem ataque para incomodar, embora a confianca geral nao seja alta."
                ),
                "possible_entry": {
                    "market_key": "over_1_5_goals",
                    "label": "Over 1.5 gols",
                    "min_acceptable_odd": 1.45,
                    "has_confirmed_value": True,
                    "reason": "probabilidade estimada acima do preco minimo",
                },
                "avoid": "Vitoria seca do favorito com odd espremida.",
            }
        )


class InvalidOpenAIClient:
    def analyze_football_dossier(self, dossier):
        return '{"fixture_label": "Arsenal x Chelsea", "probabilities": []}'


def _fixture():
    return {
        "fixture_id": 10,
        "league_id": 39,
        "league": "Premier League",
        "season": 2025,
        "fixture_date": "2026-05-10T16:00:00+00:00",
        "status": "NS",
        "home_team_id": 1,
        "away_team_id": 2,
        "home_team": "Arsenal",
        "away_team": "Chelsea",
    }


def _team(team_id, name, side):
    return {
        "id": team_id,
        "name": name,
        "side": side,
        "last_5_form": "WWDLW",
        "season_form": "WWDLWDLWWD",
        "avg_scored": 1.7,
        "avg_conceded": 1.0,
        "home_avg_scored": 1.9 if side == "home" else None,
        "home_avg_conceded": 0.8 if side == "home" else None,
        "away_avg_scored": 1.2 if side == "away" else None,
        "away_avg_conceded": 1.5 if side == "away" else None,
        "last_5_avg_scored": 1.6,
        "last_5_avg_conceded": 1.0,
    }


def test_dossier_contains_context_and_required_markets():
    service = FootballMatchDossierService(client=FakeClient())
    dossier = service.build_dossier(
        fixture=_fixture(),
        home_team_data=_team(1, "Arsenal", "home"),
        away_team_data=_team(2, "Chelsea", "away"),
        football_context={
            "summary_lines": [
                "Arsenal: ainda briga matematicamente pelo titulo.",
                "Chelsea: jogo de Champions League em 4 dias.",
            ],
            "context_alerts": ["Chelsea: jogo de Champions League em 4 dias."],
            "competitive_states": {"home": "title_race", "away": "continental_at_risk"},
        },
        odds=[
            {
                "bookmaker": "Mock",
                "key": "h2h",
                "outcomes": [{"name": "Arsenal", "price": 1.75}, {"name": "Chelsea", "price": 4.2}],
            },
            {
                "bookmaker": "Mock",
                "key": "totals",
                "outcomes": [{"name": "Over", "point": 2.5, "price": 1.92}],
            },
        ],
    )

    assert dossier["fixture"]["home_team"] == "Arsenal"
    assert "Chelsea: jogo de Champions League em 4 dias." in dossier["competitive_context"]["summary_lines"]
    assert dossier["corners_context"]["home"]["avg_for"] == 6.0
    keys = {item["key"] for item in dossier["market_candidates"]}
    assert {
        "corners",
        "home_over_0_5_goals",
        "away_over_0_5_goals",
        "over_1_5_goals",
        "over_2_5_goals",
        "favorite_win",
        "no_pre_match_bet",
    }.issubset(keys)
    target_keys = {item["key"] for item in dossier["probability_targets"]}
    assert {
        "corners",
        "home_over_0_5_goals",
        "away_over_0_5_goals",
        "over_1_5_goals",
        "over_2_5_goals",
        "favorite_win",
    }.issubset(target_keys)
    over_25 = next(item for item in dossier["probability_targets"] if item["key"] == "over_2_5_goals")
    assert over_25["available_odd"] == 1.92
    assert over_25["implied_probability"] is not None


def test_ai_fallback_prioritizes_probabilities_and_no_value_claim():
    service = FootballAIAnalysisService(client=DummyOpenAIClient())
    result = service.analyze(
        {
            "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
            "market_candidates": [{"key": "no_pre_match_bet", "signal": "alto"}],
            "probability_targets": [
                {"key": "over_1_5_goals", "base_probability_hint": 0.68, "confidence_hint": "media"},
                {"key": "over_2_5_goals", "base_probability_hint": None, "confidence_hint": "baixa"},
            ],
            "data_quality": {"level": "fraco", "notes": ["sem odds equivalentes disponiveis"]},
        }
    )

    assert result["mode"] == "football_ai_fallback"
    assert result["advisor_text"].index("Probabilidades estimadas:") < result["advisor_text"].index("Possivel entrada:")
    assert "Over 1.5 gols: 68% base" in result["advisor_text"]
    assert "sem entrada pre-jogo" in result["advisor_text"]
    assert "value confirmado" not in result["advisor_text"].lower()


def test_ai_structured_response_prioritizes_probabilities_before_entry():
    service = FootballAIAnalysisService(client=StructuredOpenAIClient())
    result = service.analyze({"fixture": {"home_team": "Arsenal", "away_team": "Chelsea"}})

    assert result["mode"] == "football_ai"
    text = result["advisor_text"]
    assert text.index("Probabilidades estimadas:") < text.index("Possivel entrada:")
    assert "- Over 1.5 gols: 72% | confianca media" in text
    assert "- Escanteios: dados insuficientes | confianca baixa" in text
    assert "odd minima 1.45" in text
    assert "sem value confirmado" not in text


def test_ai_invalid_structured_response_uses_safe_fallback():
    service = FootballAIAnalysisService(client=InvalidOpenAIClient())
    result = service.analyze(
        {
            "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
            "probability_targets": [],
            "data_quality": {"notes": ["payload da IA invalido"]},
        }
    )

    assert result["mode"] == "football_ai_fallback"
    assert "Probabilidades estimadas:" in result["advisor_text"]
    assert "sem entrada pre-jogo" in result["advisor_text"]
