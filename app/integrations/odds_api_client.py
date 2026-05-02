from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


class OddsApiClient:
    """HTTP client for The Odds API."""

    BASE_URL = "https://api.the-odds-api.com/v4/"

    def __init__(self, api_key: str | None = None, timeout: float = 10.0) -> None:
        self.api_key = api_key or settings.odds_api_key
        self.timeout = httpx.Timeout(timeout)

    def get_event_odds(self, sport_key: str, event_id: str) -> dict[str, Any]:
        # TODO: Confirm exact event odds endpoint and supported markets per sport.
        return self._get(f"/sports/{sport_key}/events/{event_id}/odds", self._default_params())

    def get_today_odds(self, sport_key: str) -> dict[str, Any]:
        # TODO: Add regions/bookmakers based on target user locale.
        return self._get(f"/sports/{sport_key}/odds", self._default_params())

    def get_market_odds(self, sport_key: str, market: str) -> dict[str, Any]:
        # TODO: Validate market keys such as h2h, spreads, totals, player props.
        params = self._default_params()
        params["markets"] = market
        return self._get(f"/sports/{sport_key}/odds", params)

    def get_sports(self) -> dict[str, Any]:
        # Kept for future setup/config screens.
        return self._get("/sports")

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.api_key:
            return self._error("ODDS_API_KEY não configurada.", endpoint, params)

        request_params = {"apiKey": self.api_key, **(params or {})}
        try:
            with httpx.Client(base_url=self.BASE_URL, timeout=self.timeout) as client:
                response = client.get(endpoint.lstrip("/"), params=request_params)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("The Odds API returned status error: %s", exc.response.status_code)
            return self._http_error(exc, endpoint, params)
        except httpx.HTTPError as exc:
            logger.warning("The Odds API request failed for endpoint %s: %s", endpoint, exc.__class__.__name__)
            return self._error("Falha de rede ao consultar The Odds API.", endpoint, params)

        return {
            "ok": True,
            "data": response.json(),
            "error": None,
            "meta": {
                "endpoint": endpoint,
                "params": params or {},
                "provider": "the_odds_api",
                "requests_remaining": response.headers.get("x-requests-remaining"),
                "requests_used": response.headers.get("x-requests-used"),
            },
        }

    @staticmethod
    def _default_params() -> dict[str, Any]:
        return {
            "regions": settings.odds_api_regions,
            "markets": settings.odds_api_markets,
            "oddsFormat": settings.odds_api_odds_format,
            "dateFormat": "iso",
        }

    @staticmethod
    def _error(error: str, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": False,
            "data": None,
            "error": error,
            "meta": {
                "endpoint": endpoint,
                "params": params or {},
                "provider": "the_odds_api",
            },
        }

    @staticmethod
    def _http_error(
        exc: httpx.HTTPStatusError,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        detail = ""
        try:
            payload = exc.response.json()
            detail = str(payload.get("message") or payload)
        except ValueError:
            detail = exc.response.text[:240]
        return OddsApiClient._error(f"HTTP {exc.response.status_code}: {detail}", endpoint, params)

    @staticmethod
    def _mock_response(endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": True,
            "data": [
                {"market": "h2h", "selection": "Home", "odd": 1.85},
                {"market": "h2h", "selection": "Away", "odd": 2.05},
            ],
            "error": None,
            "meta": {
                "endpoint": endpoint,
                "params": params or {},
                "provider": "the_odds_api",
                "mock": True,
                "todo": "Configure ODDS_API_KEY and adjust markets/bookmakers against official docs.",
            },
        }
