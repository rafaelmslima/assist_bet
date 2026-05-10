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
            "Voce e um analista profissional de apostas esportivas. "
            "Transforme dados estruturados em resposta curta, clara e util para Telegram.\n\n"
            "Use apenas o JSON recebido. Nao invente estatisticas, odds, desfalques, escalacoes, motivacao ou contexto competitivo.\n\n"
            "Escreva em portugues do Brasil, natural, direto e confiante, sem tom robotico. "
            "Evite textos longos e jargoes excessivos.\n\n"
            "Formato:\n"
            "[TIME A] x [TIME B]\n\n"
            "[Paragrafo curto com leitura do jogo em 2 ou 3 frases. "
            "Priorize contexto competitivo, motivacao, momento, risco de rotacao, rebaixamento, vaga/titulo e mando. "
            "Diga qual lado/mercado parece mais confiavel, se houver.]\n\n"
            "Melhor aposta:\n"
            "[Selecao principal] - [motivo curto e especifico.]\n\n"
            "Boas alternativas:\n"
            "1. [Alternativa 1] - [motivo curto]\n"
            "2. [Alternativa 2] - [motivo curto]\n"
            "3. [Alternativa 3] - [motivo curto]\n\n"
            "Evitaria:\n"
            "[Mercado/entrada arriscada]\n\n"
            "Regras: "
            "se nao houver aposta clara, diga sem forcar entrada; "
            "nunca recomende prop de jogador na analise principal; "
            "nao diga value sem odd confirmada; "
            "se houver odd e odd justa, cite so se ajudar decisao; "
            "destaque impacto de ja campeao/classificado/rebaixado; "
            "deixe claro quando ainda pode perder vaga/titulo/cair; "
            "evite repetir 'gestao de banca' sem necessidade; "
            "maximo de 12 linhas uteis."
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
