from app.services.ai_interpreter_service import AIInterpreterService


class DummyClient:
    def explain_recommendation(self, recommendation):
        return None


def test_fallback_without_openai_key():
    svc = AIInterpreterService(client=DummyClient())
    out = svc.interpret({"main_recommendation": {}, "final_verdict": "ok"})
    assert out["mode"] == "local_formatter"


def test_handles_incomplete_json():
    svc = AIInterpreterService(client=DummyClient())
    out = svc.interpret({})
    assert "Veredito" in out["text"]
