from app.services.normalization_service import NormalizationService


def test_alias_match():
    svc = NormalizationService()
    assert svc.normalize_team_name("PSG") == "paris saint germain"


def test_fuzzy_match():
    svc = NormalizationService()
    assert svc.fuzzy_match_team_names("Man United", "Manchester United") > 0.7


def test_odds_event_match():
    svc = NormalizationService()
    fixture = {"home_team": "Arsenal", "away_team": "Chelsea", "fixture_id": 1}
    event = {"home_team": "Arsenal FC", "away_team": "Chelsea"}
    assert svc.match_fixture_to_odds_event(fixture, [event]) is not None
