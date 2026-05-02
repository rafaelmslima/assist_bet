from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

class Intent(StrEnum):
    ANALYZE_FIXTURE = "ANALYZE_FIXTURE"
    ANALYZE_TEAM = "ANALYZE_TEAM"
    ANALYZE_PLAYER = "ANALYZE_PLAYER"
    TOP_PROPS = "TOP_PROPS"
    TODAY_GAMES = "TODAY_GAMES"
    ODDS = "ODDS"
    VALUE_BETTING = "VALUE_BETTING"
    PRE_MATCH_CARD = "PRE_MATCH_CARD"
    REGISTER_BET = "REGISTER_BET"
    LIST_BETS = "LIST_BETS"
    HELP = "HELP"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class IntentRouteResult:
    intent: Intent
    message: str
    data: dict[str, Any] | None = None


class IntentService:
    """Rule-based intent layer, designed to be replaced by an LLM adapter later."""

    MARKET_KEYWORDS = (
        "finalizações",
        "finalizacoes",
        "finalizações_no_alvo",
        "finalizacoes_no_alvo",
        "gols",
        "assistências",
        "assistencias",
        "desarmes",
        "cartões",
        "cartoes",
        "pontos",
        "rebotes",
        "bolas_de_3",
        "steals",
        "blocks",
        "pra",
    )

    def detect_intent(self, text: str) -> Intent:
        normalized = _normalize(text)

        if not normalized:
            return Intent.UNKNOWN
        if any(word in normalized for word in ("ajuda", "help", "como usar")):
            return Intent.HELP
        if any(word in normalized for word in ("minhas apostas", "apostas", "roi", "lucro", "prejuizo")):
            return Intent.LIST_BETS
        if "|" in text and len([part for part in text.split("|") if part.strip()]) >= 5:
            return Intent.REGISTER_BET
        if any(word in normalized for word in ("card pre jogo", "card pré jogo", "pre match", "pré-jogo", "pre-jogo")):
            return Intent.PRE_MATCH_CARD
        if any(word in normalized for word in ("value", "valor", "edge")):
            return Intent.VALUE_BETTING
        if any(word in normalized for word in ("odd", "odds", "cotacao", "cotação")):
            return Intent.ODDS
        if any(word in normalized for word in ("top", "melhores", "bons para", "prop", "props")):
            return Intent.TOP_PROPS
        if any(word in normalized for word in ("jogos de hoje", "hoje", "agenda")):
            return Intent.TODAY_GAMES
        if any(word in normalized for word in ("jogador", "player", "atleta")):
            return Intent.ANALYZE_PLAYER
        if any(word in normalized for word in ("time", "equipe", "analise time", "análise time")):
            return Intent.ANALYZE_TEAM
        if any(word in normalized for word in ("analise", "análise", "analisar")) or _looks_like_fixture(text):
            return Intent.ANALYZE_FIXTURE

        return Intent.UNKNOWN

    def extract_entities(self, text: str) -> dict[str, Any]:
        normalized = _normalize(text)
        entities: dict[str, Any] = {
            "fixture": _extract_fixture(text),
            "team_names": _extract_team_names(text),
            "player_name": _extract_player_name(text),
            "market": _extract_market(normalized, self.MARKET_KEYWORDS),
            "odd": _extract_number_after_keywords(normalized, ("odd", "odds", "cotacao", "cotação", "a")),
            "stake": _extract_number_after_keywords(normalized, ("stake", "unidade", "valor")),
        }
        return {key: value for key, value in entities.items() if value not in (None, "", [], {})}

    def route_intent(self, intent: Intent, entities: dict[str, Any], user: Any) -> IntentRouteResult:
        # TODO: Replace this rule-based router with an application service/LLM orchestration layer.
        if intent == Intent.HELP:
            return IntentRouteResult(intent, "Posso analisar jogos, times, jogadores, odds, value, props e suas apostas.")
        if intent == Intent.LIST_BETS:
            return IntentRouteResult(intent, "LIST_BETS", entities)
        if intent == Intent.REGISTER_BET:
            return IntentRouteResult(
                intent,
                "Para registrar, envie: jogo | mercado | seleção | odd | stake | motivo",
                entities,
            )
        if intent == Intent.TODAY_GAMES:
            return IntentRouteResult(
                intent,
                "Use Futebol > Jogos de Hoje ou NBA > Jogos de Hoje para buscar jogos reais por liga.",
                entities,
            )
        if intent == Intent.ANALYZE_FIXTURE:
            fixture = entities.get("fixture") or "dados insuficientes"
            return IntentRouteResult(intent, f"Recebi o pedido de análise do jogo: {fixture}.", entities)
        if intent == Intent.ANALYZE_TEAM:
            teams = ", ".join(entities.get("team_names", [])) or "dados insuficientes"
            return IntentRouteResult(intent, f"Recebi o pedido de análise do time: {teams}.", entities)
        if intent == Intent.ANALYZE_PLAYER:
            player = entities.get("player_name") or "dados insuficientes"
            return IntentRouteResult(intent, f"Recebi o pedido de análise do jogador: {player}.", entities)
        if intent == Intent.TOP_PROPS:
            market = entities.get("market") or "dados insuficientes"
            teams = ", ".join(entities.get("team_names", [])) or "dados insuficientes"
            return IntentRouteResult(intent, f"Recebi o pedido de top props. Time: {teams}. Mercado: {market}.", entities)
        if intent == Intent.ODDS:
            fixture = entities.get("fixture") or ", ".join(entities.get("team_names", [])) or "dados insuficientes"
            return IntentRouteResult(intent, f"Recebi o pedido de odds para: {fixture}.", entities)
        if intent == Intent.VALUE_BETTING:
            fixture = entities.get("fixture") or ", ".join(entities.get("team_names", [])) or "dados insuficientes"
            odd = entities.get("odd") or "dados insuficientes"
            return IntentRouteResult(intent, f"Recebi o pedido de value. Evento: {fixture}. Odd: {odd}.", entities)
        if intent == Intent.PRE_MATCH_CARD:
            fixture = entities.get("fixture") or "dados insuficientes"
            return IntentRouteResult(intent, f"Recebi o pedido de card pré-jogo: {fixture}.", entities)

        return IntentRouteResult(
            intent,
            "Não entendi a intenção. Use o teclado ou tente algo como: analise Arsenal x Chelsea.",
            entities,
        )


def detect_intent(text: str) -> Intent:
    return IntentService().detect_intent(text)


def extract_entities(text: str) -> dict[str, Any]:
    return IntentService().extract_entities(text)


def route_intent(intent: Intent, entities: dict[str, Any], user: Any) -> IntentRouteResult:
    return IntentService().route_intent(intent, entities, user)


def _normalize(text: str) -> str:
    return text.strip().lower()


def _looks_like_fixture(text: str) -> bool:
    return bool(re.search(r"\b.+\s+x\s+.+\b", text, flags=re.IGNORECASE))


def _extract_fixture(text: str) -> str | None:
    match = re.search(r"([A-Za-zÀ-ÿ0-9 .'-]+)\s+x\s+([A-Za-zÀ-ÿ0-9 .'-]+)", text, flags=re.IGNORECASE)
    if not match:
        return None
    home = _clean_entity(match.group(1))
    away = _clean_entity(match.group(2))
    return f"{home} x {away}" if home and away else None


def _extract_team_names(text: str) -> list[str]:
    fixture = _extract_fixture(text)
    if fixture:
        return [part.strip() for part in fixture.split(" x ")]

    cleaned = re.sub(
        r"\b(analise|analisa|análise|analisar|time|equipe|odds|odd|value|valor|top|props|jogadores|bons para|hoje|do|da|de|me mostre|mostre)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    team = _clean_entity(cleaned)
    return [team] if team else []


def _extract_player_name(text: str) -> str | None:
    match = re.search(r"(jogador|player|atleta)\s+([A-Za-zÀ-ÿ .'-]+)", text, flags=re.IGNORECASE)
    if match:
        return _clean_entity(match.group(2))
    return None


def _extract_market(normalized_text: str, market_keywords: tuple[str, ...]) -> str | None:
    for market in market_keywords:
        if market in normalized_text:
            return market
    return None


def _extract_number_after_keywords(normalized_text: str, keywords: tuple[str, ...]) -> float | None:
    for keyword in keywords:
        match = re.search(rf"\b{re.escape(keyword)}\s+(\d+(?:[,.]\d+)?)", normalized_text)
        if match:
            return float(match.group(1).replace(",", "."))
    return None


def _clean_entity(value: str) -> str:
    cleaned = re.sub(
        r"\b(analise|analisa|análise|analisar|tem value no|tem value na|tem value|me mostre|mostre|quais|são|sao|bons para|hoje)\b",
        "",
        value,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:,.")
    return cleaned
