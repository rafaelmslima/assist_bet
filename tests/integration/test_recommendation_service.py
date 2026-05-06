from app.services.recommendation_service import RecommendationService


def test_full_flow_mocked():
    svc = RecommendationService()
    fixture = {"fixture_id": 101, "home_team": "Arsenal", "away_team": "Chelsea", "league": "Premier League"}
    out = svc.analyze_fixture("football", fixture)
    assert "recommendation" in out
    assert "text" in out
