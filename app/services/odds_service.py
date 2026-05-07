from __future__ import annotations

from typing import Any

from app.integrations.odds_api_client import OddsApiClient
from app.services.normalization_service import NormalizationService


FOOTBALL_LEAGUE_TO_ODDS_SPORT: dict[int, str] = {
    39: "soccer_epl",
    140: "soccer_spain_la_liga",
    135: "soccer_italy_serie_a",
    78: "soccer_germany_bundesliga",
    61: "soccer_france_ligue_one",
    2: "soccer_uefa_champs_league",
    3: "soccer_uefa_europa_league",
    13: "soccer_conmebol_copa_libertadores",
    11: "soccer_conmebol_copa_sudamericana",
    71: "soccer_brazil_campeonato",
    88: "soccer_netherlands_eredivisie",
}


class OddsService:
    def __init__(self, client: OddsApiClient | None = None, normalization: NormalizationService | None = None) -> None:
        self.client = client or OddsApiClient()
        self.normalization = normalization or NormalizationService()

    def get_available_markets_for_fixture(self, fixture: dict[str, Any], sport_key: str) -> list[dict[str, Any]]:
        response = self.client.get_today_odds(sport_key)
        if not response.get("ok"):
            return []
        events = response.get("data") or []
        matched = self.normalization.match_fixture_to_odds_event(fixture, events)
        if not matched:
            return []
        markets = []
        for bookmaker in matched.get("bookmakers", []) or []:
            for market in bookmaker.get("markets", []) or []:
                markets.append({"bookmaker": bookmaker.get("title"), "key": market.get("key"), "outcomes": market.get("outcomes", [])})
        return markets

    def find_football_fixture_odds(
        self,
        league_id: int | str | None,
        home_team: str,
        away_team: str,
    ) -> dict[str, Any]:
        sport_key = self._football_sport_key(league_id)
        if not sport_key:
            return {"ok": False, "data": [], "error": "Liga sem mapeamento de odds.", "meta": {"league_id": league_id}}

        response = self.client.get_today_odds(sport_key)
        if not response.get("ok"):
            return {"ok": False, "data": [], "error": response.get("error"), "meta": response.get("meta", {})}

        fixture = {"home_team": home_team, "away_team": away_team}
        matched = self.normalization.match_fixture_to_odds_event(fixture, response.get("data") or [])
        if not matched:
            return {"ok": True, "data": [], "error": None, "meta": {"sport_key": sport_key, "matched": False}}

        markets = []
        for bookmaker in matched.get("bookmakers", []) or []:
            for market in bookmaker.get("markets", []) or []:
                markets.append(
                    {
                        "bookmaker": bookmaker.get("title"),
                        "key": market.get("key"),
                        "outcomes": market.get("outcomes", []),
                    }
                )
        return {"ok": True, "data": markets, "error": None, "meta": {"sport_key": sport_key, "matched": True}}

    def find_best_matching_market(self, recommended_market: str, available_odds: list[dict[str, Any]]) -> dict[str, Any] | None:
        rec = self.normalization.normalize_market_name(recommended_market).lower()
        for market in available_odds:
            key = str(market.get("key") or "").lower()
            if rec in key or key in rec:
                return market
        return available_odds[0] if available_odds else None

    def calculate_implied_probability(self, odd: float) -> float:
        return 0.0 if odd <= 1 else 1 / odd

    def calculate_edge(self, estimated_probability: float, odd: float) -> float:
        return (estimated_probability - self.calculate_implied_probability(odd)) * 100

    def classify_value(self, edge: float) -> str:
        if edge > 7:
            return "value forte"
        if edge >= 4:
            return "value moderado"
        if edge >= 2:
            return "value leve"
        return "sem value claro"

    @staticmethod
    def _football_sport_key(league_id: int | str | None) -> str | None:
        try:
            normalized = int(league_id) if league_id is not None else None
        except (TypeError, ValueError):
            return None
        if normalized is None:
            return None
        return FOOTBALL_LEAGUE_TO_ODDS_SPORT.get(normalized)
