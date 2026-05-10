from __future__ import annotations

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
        "wait_live_or_no_bet",
    }.issubset(keys)


def test_ai_fallback_returns_short_no_bet_text():
    service = FootballAIAnalysisService(client=DummyOpenAIClient())
    result = service.analyze(
        {
            "fixture": {"home_team": "Arsenal", "away_team": "Chelsea"},
            "market_candidates": [{"key": "wait_live_or_no_bet", "signal": "alto"}],
            "data_quality": {"level": "fraco", "notes": ["sem odds equivalentes disponiveis"]},
        }
    )

    assert result["mode"] == "football_ai_fallback"
    assert "Melhor decisao: sem entrada pre-jogo." in result["advisor_text"]
    assert "Onde olhar:" in result["advisor_text"]
