from __future__ import annotations

from app.integrations.openai_client import OpenAIClient


class AIInterpreterService:
    def __init__(self, client: OpenAIClient | None = None) -> None:
        self.client = client or OpenAIClient()

    def interpret(self, recommendation: dict) -> dict:
        text = self.client.explain_recommendation(recommendation)
        if text:
            return {"text": text, "mode": "ai_interpreter"}
        return {"text": self._local_format(recommendation), "mode": "local_formatter"}

    def _local_format(self, rec: dict) -> str:
        main = rec.get("main_recommendation", {})
        alternatives = rec.get("alternative_recommendations", [])
        avoid = rec.get("avoid_markets", [])
        traps = rec.get("traps", [])
        lines = [
            "🎯 Melhor leitura",
            f"{main.get('selection', 'Não apostar pré-jogo')}",
            "",
            "📊 Por que faz sentido",
        ]
        lines.extend([f"- {r}" for r in (main.get("reasons") or ["Sem edge claro no momento"])])
        lines.extend(["", "⚠️ O que me preocupa"])
        lines.extend([f"- {w}" for w in (main.get("warnings") or traps or ["Contexto sensível"])])
        lines.extend(["", "💰 Odds / Value"])
        if main.get("available_odd"):
            lines.append(f"Odd disponível: @{main['available_odd']}")
        else:
            lines.append("Sem odd equivalente para confirmar value.")
        lines.extend(["", "🔁 Alternativas"])
        lines.extend([f"- {m.get('selection')}" for m in alternatives] or ["- Esperar live"])
        lines.extend(["", "🚫 Eu evitaria"])
        lines.extend([f"- {m.get('selection')}" for m in avoid] or ["- Entrada sem edge"])
        lines.extend(["", "✅ Veredito", rec.get("final_verdict", "Sem aposta clara no pré-jogo.")])
        return "\n".join(lines)
