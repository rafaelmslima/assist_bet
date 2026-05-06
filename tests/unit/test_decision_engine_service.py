from app.services.decision_engine_service import DecisionEngineService


def test_no_force_bet_with_weak_data():
    svc = DecisionEngineService()
    out = svc.build_recommendation(
        {"fixture": {}, "sport": "football", "signals": {"data_quality": "baixa"}, "market_scores": [], "archetype": {}, "traps": {"should_avoid_pre_match": True, "traps": []}}
    )
    assert out["main_recommendation"]["market"] == "NO_BET"


def test_selects_main_recommendation():
    svc = DecisionEngineService()
    out = svc.build_recommendation(
        {
            "fixture": {},
            "sport": "football",
            "signals": {"data_quality": "alta"},
            "archetype": {},
            "traps": {"should_avoid_pre_match": False, "traps": []},
            "market_scores": [{"market": "OVER_1_5_GOALS", "selection": "Over 1.5", "score": 71, "warnings": [], "reasons": []}],
        }
    )
    assert out["main_recommendation"]["market"] == "OVER_1_5_GOALS"
