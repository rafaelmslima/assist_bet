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
                {"team": {"id": team_id}, "statistics": [{"type": "Corner Kicks", "value": 6}]},
                {"team": {"id": opponent_id}, "statistics": [{"type": "Corner Kicks", "value": 4}]},
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
                "general_idea": "Arsenal deve propor mais, mas Chelsea tem transicao para incomodar.",
                "expected_script": {
                    "start": "Arsenal pressionando e tentando empurrar o Chelsea.",
                    "middle": "Chelsea deve alternar bloco medio e contra-ataque.",
                    "if_early_goal": "O jogo fica mais aberto e favorece mercados de gols.",
                    "if_level_at_halftime": "A cautela cresce e o banco passa a pesar mais.",
                },
                "tactical_matchups": [
                    {"title": "Mandante por dentro", "reading": "Arsenal tem melhor sinal ofensivo em casa."}
                ],
                "motivation_context": "Arsenal briga por titulo; Chelsea tem calendario pesado.",
                "recent_form_read": "A forma do Arsenal parece mais confiavel que a do Chelsea.",
                "key_risks": ["escalações ainda nao confirmadas"],
                "betting_ideas": [
                    {
                        "market": "escanteios",
                        "idea": "linha de escanteios",
                        "projection": "8 a 10 escanteios",
                        "projection_analysis": "o volume lateral dos times e o roteiro de pressao do Arsenal sustentam essa faixa.",
                        "confidence": "media",
                        "reason": "roteiro favorece pressão territorial e cruzamentos.",
                    }
                ],
                "avoid": [{"market": "vencedor seco", "reason": "risco de transicao visitante."}],
                "confidence": {"level": "amarela", "reason": "boa leitura, mas falta escalação."},
                "checklist_before_bet": ["confirmar titulares"],
                "data_quality_notes": ["escalações ainda nao confirmadas"],
            }
        )


class InvalidOpenAIClient:
    def analyze_football_dossier(self, dossier):
        return '{"fixture_label": "Arsenal x Chelsea", "general_idea": ""}'


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


def test_dossier_contains_context_and_qualitative_market_targets():
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
    )

    assert dossier["fixture"]["home_team"] == "Arsenal"
    assert dossier["schema_version"] == "football_ai_dossier_v2"
    assert dossier["match"]["competition"] == "Premier League"
    assert dossier["data_quality"]["lineups_available"] is False
    assert "confidence_penalty" in dossier["data_quality"]
    assert dossier["home_team_profile"]["attack"]["goals_per_game"] == 1.9
    assert dossier["away_team_profile"]["defense"]["goals_against_per_game"] == 1.5
    assert dossier["matchup_analysis"]["home_attack_vs_away_defense"]["signal"] == "forte pro-mandante marcar"
    assert dossier["market_scores"]["home_team_goal"]["score"] >= 50
    assert dossier["odds_analysis"]["available"] is False
    assert "Chelsea: jogo de Champions League em 4 dias." in dossier["competitive_context"]["summary_lines"]
    assert dossier["corners_context"]["home"]["avg_for"] == 6.0
    assert "odds" not in dossier
    keys = {item["key"] for item in dossier["market_candidates"]}
    assert {"corners", "home_over_0_5_goals", "over_1_5_goals", "favorite_win", "no_pre_match_bet"}.issubset(keys)
    target = next(item for item in dossier["probability_targets"] if item["key"] == "over_1_5_goals")
    assert "available_odd" not in target
    assert "qualitativa" in target["ai_instruction"]


def test_ai_fallback_returns_script_and_market_ideas_without_price_language():
    service = FootballAIAnalysisService(client=DummyOpenAIClient())
    result = service.analyze(
        {
            "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
            "teams": {
                "home": {"goals": {"home_avg_scored": 1.8, "home_avg_conceded": 0.8}, "form": {"last_5": "WWDLW"}},
                "away": {"goals": {"away_avg_scored": 1.1, "away_avg_conceded": 1.5}, "form": {"last_5": "LDWWW"}},
            },
            "corners_context": {"combined_team_corners_avg": 8.5},
            "competitive_context": {"summary_lines": ["Arsenal: briga por titulo."]},
            "data_quality": {"level": "parcial", "notes": ["escalações ainda nao confirmadas"]},
        }
    )

    assert result["mode"] == "football_ai_fallback"
    assert "O jogo tende" in result["advisor_text"]
    assert "Se o jogo abrir cedo" in result["advisor_text"]
    assert "Ideias de mercado" in result["advisor_text"]
    assert "Projeção: 8 a 10 escanteios" in result["advisor_text"]
    assert "media combinada recente" in result["advisor_text"]
    assert "Confiança" in result["advisor_text"]
    assert "Ideia geral:" not in result["advisor_text"]
    assert "Como deve ocorrer:" not in result["advisor_text"]
    assert "value" not in result["advisor_text"].lower()
    assert "odd" not in result["advisor_text"].lower()


def test_ai_structured_response_formats_script_before_betting_ideas():
    service = FootballAIAnalysisService(client=StructuredOpenAIClient())
    result = service.analyze({"fixture": {"home_team": "Arsenal", "away_team": "Chelsea"}})

    assert result["mode"] == "football_ai"
    text = result["advisor_text"]
    assert text.index("Arsenal deve propor") < text.index("Ideias de mercado")
    assert "Se o jogo abrir cedo" in text
    assert "Ideias de apostas:" not in text
    assert "linha de escanteios" in text
    assert "Projeção: 8 a 10 escanteios" in text
    assert "volume lateral" in text
    assert "vencedor seco" in text


def test_ai_invalid_structured_response_uses_safe_fallback():
    service = FootballAIAnalysisService(client=InvalidOpenAIClient())
    result = service.analyze(
        {
            "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
            "teams": {},
            "data_quality": {"notes": ["payload da IA invalido"]},
        }
    )

    assert result["mode"] == "football_ai_fallback"
    assert "Leitura do jogo" in result["advisor_text"]
    assert "Ideias de mercado" in result["advisor_text"]
