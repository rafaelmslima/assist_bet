from __future__ import annotations

import difflib
import logging
import re
import unicodedata
from typing import Any


logger = logging.getLogger(__name__)


class NormalizationService:
    TEAM_ALIASES = {
        "psg": "paris saint germain",
        "man united": "manchester united",
        "man utd": "manchester united",
        "man city": "manchester city",
        "bayern munich": "bayern munchen",
        "inter milan": "internazionale",
        "atletico madrid": "atletico madrid",
    }

    def normalize_team_name(self, name: str) -> str:
        compact = self._compact(name)
        return self.TEAM_ALIASES.get(compact, compact)

    def normalize_market_name(self, market: str) -> str:
        return self._compact(market).replace(" ", "_").upper()

    def normalize_league_name(self, league: str) -> str:
        return self._compact(league).title()

    def fuzzy_match_team_names(self, name_a: str, name_b: str) -> float:
        return round(difflib.SequenceMatcher(None, self.normalize_team_name(name_a), self.normalize_team_name(name_b)).ratio(), 3)

    def match_fixture_to_odds_event(self, fixture: dict[str, Any], odds_events: list[dict[str, Any]]) -> dict[str, Any] | None:
        home = str(fixture.get("home_team") or "")
        away = str(fixture.get("away_team") or "")
        best = None
        best_score = 0.0
        for event in odds_events:
            eh = str(event.get("home_team") or "")
            ea = str(event.get("away_team") or "")
            score = (self.fuzzy_match_team_names(home, eh) + self.fuzzy_match_team_names(away, ea)) / 2
            if score > best_score:
                best_score = score
                best = event
        if best_score < 0.65:
            logger.warning("odds_event_match_low_confidence fixture=%s score=%.3f", fixture.get("fixture_id"), best_score)
            return None
        return {**best, "match_confidence": round(best_score * 100, 1)}

    def _compact(self, text: str) -> str:
        norm = unicodedata.normalize("NFKD", text or "")
        ascii_text = "".join(c for c in norm if not unicodedata.combining(c))
        ascii_text = re.sub(r"[^a-zA-Z0-9]+", " ", ascii_text).lower()
        return re.sub(r"\s+", " ", ascii_text).strip()
