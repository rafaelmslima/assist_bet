from __future__ import annotations

import unicodedata
from typing import Any

from app.integrations.odds_api_client import OddsApiClient
from app.services.cache_service import cache_key, default_cache


FOOTBALL_LEAGUE_TO_ODDS_SPORT = {
    39: "soccer_epl",
    140: "soccer_spain_la_liga",
    135: "soccer_italy_serie_a",
    78: "soccer_germany_bundesliga",
    61: "soccer_france_ligue_one",
    2: "soccer_uefa_champs_league",
    3: "soccer_uefa_europa_league",
    71: "soccer_brazil_campeonato",
    88: "soccer_netherlands_eredivisie",
    13: "soccer_conmebol_copa_libertadores",
    11: "soccer_conmebol_copa_sudamericana",
}


class OddsService:
    def __init__(self, client: OddsApiClient | None = None) -> None:
        self.client = client or OddsApiClient()

    def get_event_odds(self, sport_key: str, event_id: str) -> dict:
        return default_cache.get_or_set(
            cache_key("odds.event", sport_key, event_id),
            120,
            lambda: self.client.get_event_odds(sport_key=sport_key, event_id=event_id),
        )

    def get_today_odds(self, sport_key: str) -> dict:
        return default_cache.get_or_set(
            cache_key("odds.today", sport_key),
            120,
            lambda: self.client.get_today_odds(sport_key=sport_key),
        )

    def get_market_odds(self, sport_key: str, market: str) -> dict:
        return default_cache.get_or_set(
            cache_key("odds.market", sport_key, market),
            120,
            lambda: self.client.get_market_odds(sport_key=sport_key, market=market),
        )

    def find_football_fixture_odds(
        self,
        league_id: int | None,
        home_team: str,
        away_team: str,
    ) -> dict[str, Any]:
        sport_key = FOOTBALL_LEAGUE_TO_ODDS_SPORT.get(int(league_id or 0))
        if not sport_key:
            return {"ok": False, "data": [], "error": "Liga sem sport_key mapeado na The Odds API."}

        response = self.get_market_odds(sport_key, "h2h,totals")
        if not response.get("ok"):
            return response

        events = response.get("data") or []
        event = _find_matching_event(events, home_team, away_team)
        if event is None:
            samples = _event_samples(events)
            sample_text = "; ".join(samples) if samples else "nenhum evento retornado"
            return {
                "ok": False,
                "data": [],
                "error": (
                    f"Odds não encontradas para {home_team} x {away_team} em {sport_key}. "
                    f"A Odds API retornou {len(events)} evento(s). Amostras: {sample_text}."
                ),
                "meta": response.get("meta"),
            }

        return {
            "ok": True,
            "data": _normalize_event_odds(event),
            "error": None,
            "meta": {**(response.get("meta") or {}), "sport_key": sport_key, "event_id": event.get("id")},
        }

    def find_nba_game_odds(
        self,
        home_team: str,
        away_team: str,
        markets: str = "h2h,spreads,totals",
    ) -> dict[str, Any]:
        sport_key = "basketball_nba"
        response = self.get_market_odds(sport_key, markets)
        if not response.get("ok"):
            return response

        events = response.get("data") or []
        event = _find_matching_event(events, home_team, away_team)
        if event is None:
            samples = _event_samples(events)
            sample_text = "; ".join(samples) if samples else "nenhum evento retornado"
            return {
                "ok": False,
                "data": [],
                "error": (
                    f"Odds não encontradas para {away_team} @ {home_team} em {sport_key}. "
                    f"A Odds API retornou {len(events)} evento(s). Amostras: {sample_text}."
                ),
                "meta": response.get("meta"),
            }

        return {
            "ok": True,
            "data": _normalize_event_odds(event),
            "error": None,
            "meta": {**(response.get("meta") or {}), "sport_key": sport_key, "event_id": event.get("id")},
        }


def _find_matching_event(events: list[dict[str, Any]], home_team: str, away_team: str) -> dict[str, Any] | None:
    wanted_home = _normalize_name(home_team)
    wanted_away = _normalize_name(away_team)
    for event in events:
        event_home = _normalize_name(event.get("home_team"))
        event_away = _normalize_name(event.get("away_team"))
        if _event_score(wanted_home, wanted_away, event_home, event_away) >= 1.6:
            return event
        if _event_score(wanted_home, wanted_away, event_away, event_home) >= 1.6:
            return event
    return None


def _normalize_event_odds(event: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = []
    for bookmaker in event.get("bookmakers") or []:
        bookmaker_name = bookmaker.get("title") or bookmaker.get("key")
        for market in bookmaker.get("markets") or []:
            market_key = market.get("key")
            for outcome in market.get("outcomes") or []:
                normalized.append(
                    {
                        "bookmaker": bookmaker_name,
                        "market": market_key,
                        "selection": outcome.get("name"),
                        "point": outcome.get("point"),
                        "odd": outcome.get("price"),
                    }
                )
    return normalized


def _event_samples(events: list[dict[str, Any]], limit: int = 4) -> list[str]:
    samples = []
    for event in events[:limit]:
        home = event.get("home_team") or "mandante?"
        away = event.get("away_team") or "visitante?"
        commence = event.get("commence_time") or "sem data"
        samples.append(f"{home} x {away} ({commence})")
    return samples


def _normalize_name(value: Any) -> str:
    text = str(value or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    replacements = {" fc": "", " afc": "", " cf": "", " sc": "", ".": "", "-": " "}
    aliases = {
        "man utd": "manchester united",
        "man united": "manchester united",
        "man city": "manchester city",
        "spurs": "tottenham",
        "psg": "paris saint germain",
        "internazionale": "inter milan",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    normalized = " ".join(text.split())
    return aliases.get(normalized, normalized)


def _names_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return _name_score(left, right) >= 0.8


def _event_score(wanted_home: str, wanted_away: str, event_home: str, event_away: str) -> float:
    return _name_score(wanted_home, event_home) + _name_score(wanted_away, event_away)


def _name_score(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if left in right or right in left:
        return 0.9
    left_tokens = {token for token in left.split() if len(token) >= 3}
    right_tokens = {token for token in right.split() if len(token) >= 3}
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    return overlap / max(len(left_tokens), len(right_tokens))
