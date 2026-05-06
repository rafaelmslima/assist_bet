from __future__ import annotations

from typing import Any

from app.integrations.odds_api_client import OddsApiClient
from app.services.normalization_service import NormalizationService


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
