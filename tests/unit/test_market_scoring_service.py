from app.services.market_scoring_service import MarketScoringService


def test_goals_recommends_over():
    svc = MarketScoringService()
    signals = {"goals_trend_signal": 78, "btts_signal": 70, "under_signal": 30, "home_away_signal": 55}
    markets = svc.score_markets("football", signals, {"rotation_risk": 20}, [])
    assert markets[0]["market"] == "OVER_1_5_GOALS"


def test_rotation_reduces_home_ml():
    svc = MarketScoringService()
    signals = {"goals_trend_signal": 60, "btts_signal": 55, "under_signal": 45, "home_away_signal": 80}
    markets = svc.score_markets("football", signals, {"rotation_risk": 80}, [])
    ml = next(m for m in markets if m["market"] == "HOME_WIN")
    assert ml["score"] < 80
