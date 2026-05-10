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

    def analyze_football_dossier(self, dossier: dict[str, Any]) -> str | None:
        if not self.api_key:
            return None
        system_prompt = (
            "Voce e um analista probabilistico pre-jogo de futebol. "
            "Sua tarefa principal e estimar probabilidades do que tende a acontecer na partida usando apenas o JSON recebido. "
            "A recomendacao de aposta e secundaria e so pode aparecer depois das probabilidades.\n\n"
            "Regras obrigatorias:\n"
            "- Nao invente estatisticas, odds, escalacoes, desfalques, classificacao ou motivacao.\n"
            "- Estime percentuais para os mercados em probability_targets; se a amostra for fraca, use dados_insuficientes.\n"
            "- Se odds nao estiverem disponiveis, nunca marque has_confirmed_value como true.\n"
            "- Compare probability_percent com implied_probability/available_odd do dossie antes de sugerir value.\n"
            "- Se nenhuma probabilidade compensar o risco/preco, recomende sem entrada pre-jogo.\n"
            "- Nao recomende entrada ao vivo, live, trading ou esperar bola rolar; o apostador so atua antes do jogo.\n"
            "- Sempre considere classificacao, calendario internacional, desfalques, lineups e contexto competitivo.\n"
            "- Nao prometa lucro e nao use linguagem de aposta garantida.\n\n"
            "Responda somente com JSON valido, sem markdown, no schema abaixo:\n"
            "{\n"
            '  "fixture_label": "Time A x Time B",\n'
            '  "probabilities": [\n'
            '    {"market_key":"over_1_5_goals","label":"Over 1.5 gols","probability_percent":72,"confidence":"media","rationale":"motivo curto","data_status":"estimado"},\n'
            '    {"market_key":"over_2_5_goals","label":"Over 2.5 gols","probability_percent":48,"confidence":"baixa","rationale":"motivo curto","data_status":"estimado"},\n'
            '    {"market_key":"home_over_0_5_goals","label":"Gol do mandante","probability_percent":78,"confidence":"media","rationale":"motivo curto","data_status":"estimado"},\n'
            '    {"market_key":"away_over_0_5_goals","label":"Gol do visitante","probability_percent":55,"confidence":"media","rationale":"motivo curto","data_status":"estimado"},\n'
            '    {"market_key":"favorite_win","label":"Vitoria do favorito","probability_percent":46,"confidence":"baixa","rationale":"motivo curto","data_status":"estimado"},\n'
            '    {"market_key":"corners","label":"Escanteios","probability_percent":null,"confidence":"baixa","rationale":"amostra fraca","data_status":"dados_insuficientes"}\n'
            "  ],\n"
            '  "match_reading": "2 ou 3 frases curtas.",\n'
            '  "possible_entry": {"market_key":null,"label":"sem entrada pre-jogo","min_acceptable_odd":null,"has_confirmed_value":false,"reason":"motivo curto"},\n'
            '  "avoid": "mercado/situacao a evitar"\n'
            "}"
        )
        user_prompt = f"Analise este dossie do jogo e retorne o JSON validavel:\n{json.dumps(dossier, ensure_ascii=False)}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.25,
            "response_format": {"type": "json_object"},
        }
        return self._chat_completion(payload, log_label="OpenAI football analysis fallback acionado")

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
        return self._chat_completion(payload, log_label="OpenAI fallback acionado")

    def _chat_completion(self, payload: dict[str, Any], *, log_label: str) -> str | None:
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
            logger.warning("%s: %s", log_label, exc)
            return None
