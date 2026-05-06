from app.services.trap_detection_service import TrapDetectionService


def test_detects_favorite_trap():
    svc = TrapDetectionService()
    out = svc.detect({"rotation_risk": 85, "lineup_risk": 20}, [], {"archetype": "BALANCED_GAME"})
    assert "Risco alto de rotação" in out["traps"]


def test_detects_lineup_uncertain():
    svc = TrapDetectionService()
    out = svc.detect({"rotation_risk": 10, "lineup_risk": 90}, [], {"archetype": "BALANCED_GAME"})
    assert "Escalação indefinida" in out["traps"]
