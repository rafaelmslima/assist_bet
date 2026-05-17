from __future__ import annotations

import json
import logging
from time import sleep
from typing import Any

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 20.0,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.timeout = timeout
        self.max_retries = max(0, max_retries)

    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def analyze_football_dossier(self, dossier: dict[str, Any]) -> str | None:
        if not self.api_key:
            return None
        system_prompt = (
            "Voce e um analista profissional de futebol pre-jogo.\n\n"
            "Sua tarefa e analisar o dossie recebido e explicar como a partida tende a acontecer. "
            "Use apenas os dados fornecidos. Nao invente estatisticas, escalacoes, desfalques, noticias, odds ou motivacao.\n\n"
            "O dossie pode trazer um payload analitico com match, data_quality, home_team_profile, away_team_profile, "
            "matchup_analysis, market_scores e odds_analysis. Trate market_scores como calculo interno de apoio, nao como garantia.\n"
            "Se uma metrica vier como indisponivel, diga que ela esta indisponivel e nao tente inferir. "
            "Se odds_analysis.available for falso, escreva exatamente a ideia: "
            "'Ha tendencia tecnica, mas nao e possivel confirmar valor sem preco de mercado.'\n\n"
            "Prioridade da analise:\n"
            "1. Ideia geral do jogo.\n"
            "2. Qualidade dos dados e limites da amostra.\n"
            "3. Raio-X dos dois times, separando resultado de producao.\n"
            "4. Matchups taticos e estatisticos.\n"
            "5. Scores por mercado e riscos.\n"
            "6. Motivacao, calendario e contexto competitivo.\n"
            "7. Ideias qualitativas de apostas, apenas quando houver sustentacao clara.\n\n"
            "Analise obrigatoriamente:\n"
            "- Quem tende a propor o jogo.\n"
            "- Quem tende a jogar em transicao.\n"
            "- Se o jogo tem cara de aberto, truncado, fisico, lento ou controlado.\n"
            "- Como o jogo muda se sair gol cedo.\n"
            "- Como o jogo muda se chegar empatado ao intervalo.\n"
            "- Se a sequencia recente parece confiavel ou enganosa.\n"
            "- Se ha risco de rotacao, baixa motivacao ou calendario pesado.\n"
            "- Se desfalques ou escalacoes afetam ataque, defesa, criacao ou bola parada.\n"
            "- Quais mercados combinam com o roteiro: gols, ambas marcam, gol de um time, escanteios, cartoes ou evitar vencedor seco.\n"
            "- Os mercados em market_scores: score, confidence, reason, risk e odds quando existirem.\n"
            "- Nao recomende aposta quando os scores forem fracos/moderados, os dados forem ruins ou nao houver preco de mercado para validar value.\n"
            "- Se citar escanteios, cartoes, finalizacoes ou qualquer prop quantitativa, informe uma previsao numerica ou faixa provavel e explique por que esse numero faz sentido pelo tipo de jogo dos times.\n"
            "- Quais mercados devem ser evitados.\n\n"
            "Regras:\n"
            "- Nao diga value, odd justa, edge, odd minima ou entrada confirmada.\n"
            "- Sem odds, fale apenas em ideias de mercado.\n"
            "- Se os dados forem fracos, diga claramente que a confianca e baixa.\n"
            "- Nao prometa lucro.\n"
            "- Nao crie certeza onde existe incerteza.\n"
            "- Nunca cite uma prop quantitativa so como nome de mercado; ela precisa vir com projection e projection_analysis.\n"
            "- Escreva os campos como um analista falando com o usuario, em portugues natural, sem parecer formulario.\n"
            "- Evite frases soltas e telegráficas; conecte causa e efeito em frases conversadas.\n"
            "- Prefira uma leitura util, objetiva e natural para dashboard.\n\n"
            "Responda somente com JSON valido, sem markdown, neste schema:\n"
            "{\n"
            '  "fixture_label": "Time A x Time B",\n'
            '  "general_idea": "Resumo curto da ideia principal do jogo.",\n'
            '  "expected_script": {\n'
            '    "start": "Como o jogo tende a comecar.",\n'
            '    "middle": "Como o jogo tende a se desenvolver.",\n'
            '    "if_early_goal": "Como um gol cedo muda a partida.",\n'
            '    "if_level_at_halftime": "Como o empate no intervalo muda a leitura."\n'
            "  },\n"
            '  "tactical_matchups": [{"title": "Matchup principal", "reading": "Explicacao curta usando os dados disponiveis."}],\n'
            '  "motivation_context": "Leitura de tabela, calendario, objetivo e possivel rotacao.",\n'
            '  "recent_form_read": "Se a forma recente parece forte, fraca ou enganosa.",\n'
            '  "key_risks": ["Risco 1", "Risco 2"],\n'
            '  "data_quality_read": "Como a qualidade dos dados afeta a confianca.",\n'
            '  "team_profiles_read": ["Raio-X mandante usando dados do payload.", "Raio-X visitante usando dados do payload."],\n'
            '  "market_assessments": [{"market": "Over 1.5 gols", "score": 72, "confidence": "sinal bom", "reading": "Leitura do mercado com causa e efeito.", "risk": "Risco principal.", "value_note": "Com ou sem value conforme odds_analysis."}],\n'
            '  "betting_ideas": [{"market": "Mercado sugerido", "idea": "Ideia qualitativa", "projection": "Ex: 8 a 10 escanteios, 4 a 6 cartoes ou 2 a 3 finalizacoes", "projection_analysis": "Por que essa faixa faz sentido pelos dados e roteiro", "confidence": "baixa", "reason": "Motivo curto"}],\n'
            '  "avoid": [{"market": "Mercado a evitar", "reason": "Motivo curto"}],\n'
            '  "confidence": {"level": "amarela", "reason": "Motivo da confianca geral"},\n'
            '  "checklist_before_bet": ["O que confirmar antes de apostar"],\n'
            '  "data_quality_notes": ["Limitacoes dos dados"]\n'
            "}"
        )
        user_prompt = f"Analise este dossie do jogo e retorne o JSON validavel:\n{json.dumps(dossier, ensure_ascii=False)}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }
        return self._chat_completion(payload, log_label="OpenAI football match analysis fallback acionado")

    def explain_recommendation(self, recommendation: dict[str, Any]) -> str | None:
        if not self.api_key:
            return None
        system_prompt = (
            "Voce e um analista de futebol pre-jogo. Transforme o JSON recebido em uma resposta curta para dashboard. "
            "Use apenas os dados recebidos, sem inventar contexto. Fale em roteiro do jogo, riscos e ideias qualitativas de mercados. "
            "Nao mencione value, edge, odd justa, odd minima ou entrada confirmada."
        )
        user_prompt = f"Explique este JSON em formato curto para dashboard:\n{json.dumps(recommendation, ensure_ascii=False)}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
        }
        return self._chat_completion(payload, log_label="OpenAI explanation fallback acionado")

    def _chat_completion(self, payload: dict[str, Any], *, log_label: str) -> str | None:
        for attempt in range(self.max_retries + 1):
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
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in {429, 500, 502, 503, 504} or attempt >= self.max_retries:
                    logger.warning("%s: %s", log_label, exc)
                    return None
            except Exception as exc:  # noqa: BLE001
                if attempt >= self.max_retries:
                    logger.warning("%s: %s", log_label, exc)
                    return None
            sleep(0.25 * (2**attempt))
        return None
