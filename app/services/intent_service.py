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
    """Rule-based intent layer for football analysis routing."""

    MARKET_KEYWORDS = (
        "finalizacoes",
        "gols",
        "assistencias",
        "desarmes",
        "cartoes",
        "escanteios",
        "ambas marcam",
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
        if any(word in normalized for word in ("card pre jogo", "pre match", "pre-jogo")):
            return Intent.PRE_MATCH_CARD
        if any(word in normalized for word in ("value", "edge", "odd", "odds", "cotacao")):
            return Intent.VALUE_BETTING
        if any(word in normalized for word in ("top", "melhores", "bons para", "prop", "props")):
            return Intent.TOP_PROPS
        if any(word in normalized for word in ("jogos de hoje", "hoje", "agenda")):
            return Intent.TODAY_GAMES
        if any(word in normalized for word in ("jogador", "player", "atleta")):
            return Intent.ANALYZE_PLAYER
        if any(word in normalized for word in ("time", "equipe", "analise time")):
            return Intent.ANALYZE_TEAM
        if any(word in normalized for word in ("analise", "analisar", "analisar jogo")) or _looks_like_fixture(text):
            return Intent.ANALYZE_FIXTURE

        return Intent.UNKNOWN

    def extract_entities(self, text: str) -> dict[str, Any]:
        normalized = _normalize(text)
        entities: dict[str, Any] = {
            "fixture": _extract_fixture(text),
            "team_names": _extract_team_names(text),
            "player_name": _extract_player_name(text),
            "market": _extract_market(normalized, self.MARKET_KEYWORDS),
        }
        return {key: value for key, value in entities.items() if value not in (None, "", [], {})}

    def route_intent(self, intent: Intent, entities: dict[str, Any], user: Any) -> IntentRouteResult:
        if intent == Intent.HELP:
            return IntentRouteResult(intent, "Posso analisar jogos de futebol com IA: roteiro provavel, matchups, riscos e ideias qualitativas de mercados.")
        if intent == Intent.TODAY_GAMES:
            return IntentRouteResult(intent, "Use Futebol > Jogos de Hoje para buscar jogos reais por liga.", entities)
        if intent == Intent.ANALYZE_FIXTURE:
            fixture = entities.get("fixture") or "dados insuficientes"
            return IntentRouteResult(intent, f"Recebi o pedido de analise do jogo: {fixture}.", entities)
        if intent == Intent.ANALYZE_TEAM:
            return IntentRouteResult(intent, "A leitura principal agora e por confronto. Envie Time A x Time B.", entities)
        if intent == Intent.ANALYZE_PLAYER:
            return IntentRouteResult(intent, "Para jogadores, escolha Futebol > Jogadores do Jogo e selecione o confronto.", entities)
        if intent == Intent.TOP_PROPS:
            return IntentRouteResult(intent, "As ideias individuais ficam dentro do contexto do jogo. Use Futebol > Jogadores do Jogo.", entities)
        if intent in {Intent.ODDS, Intent.VALUE_BETTING, Intent.REGISTER_BET, Intent.LIST_BETS}:
            return IntentRouteResult(intent, "Esta versao foca em analise de jogo com IA, sem modulo de precificacao ou tracking.", entities)
        if intent == Intent.PRE_MATCH_CARD:
            fixture = entities.get("fixture") or "dados insuficientes"
            return IntentRouteResult(intent, f"Recebi o pedido de contexto pre-jogo: {fixture}.", entities)

        return IntentRouteResult(
            intent,
            "Nao entendi a intencao. Use o teclado ou tente algo como: analise Arsenal x Chelsea.",
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
    match = re.search(r"([A-Za-z0-9 .'-]+)\s+x\s+([A-Za-z0-9 .'-]+)", text, flags=re.IGNORECASE)
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
        r"\b(analise|analisa|analisar|time|equipe|top|props|jogadores|bons para|hoje|do|da|de|me mostre|mostre)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    team = _clean_entity(cleaned)
    return [team] if team else []


def _extract_player_name(text: str) -> str | None:
    match = re.search(r"(jogador|player|atleta)\s+([A-Za-z .'-]+)", text, flags=re.IGNORECASE)
    if match:
        return _clean_entity(match.group(2))
    return None


def _extract_market(normalized_text: str, market_keywords: tuple[str, ...]) -> str | None:
    for market in market_keywords:
        if market in normalized_text:
            return market
    return None


def _clean_entity(value: str) -> str:
    cleaned = re.sub(
        r"\b(analise|analisa|analisar|me mostre|mostre|quais|sao|bons para|hoje)\b",
        "",
        value,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:,.")
    return cleaned
