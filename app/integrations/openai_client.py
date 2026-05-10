from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: float = 20.0) -> None:
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.timeout = timeout

    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def explain_recommendation(self, recommendation: dict[str, Any]) -> str | None:
        if not self.api_key:
            return None
        system_prompt = (
            "Voce e um assessor profissional de apostas esportivas para Telegram. "
            "Responda em portugues natural, direto e curto. "
            "Use somente o JSON recebido. Nao invente dados, odds, lesoes, escalações ou estatisticas. "
            "Comece com leitura do jogo e decisao principal. "
            "Depois separe em: melhor entrada, motivo, riscos, preco/value e veredito. "
            "Mostre contexto e alternativas em formato compacto quando existirem. "
            "Nunca prometa lucro. Se faltar odd equivalente, diga que nao da para confirmar value."
        )
        user_prompt = f"Explique este JSON em formato curto para Telegram:\n{json.dumps(recommendation, ensure_ascii=False)}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAI fallback acionado: %s", exc)
            return None
