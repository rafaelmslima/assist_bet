from __future__ import annotations

from typing import Any

from app.services.ai_interpreter_service import AIInterpreterService
from app.services.analysis_service import AnalysisService
from app.services.context_service import ContextService
from app.services.decision_engine_service import DecisionEngineService
from app.services.football_data_service import FootballDataService
from app.services.game_archetype_service import GameArchetypeService
from app.services.market_scoring_service import MarketScoringService
from app.services.nba_data_service import NbaDataService
from app.services.odds_service import OddsService
from app.services.trap_detection_service import TrapDetectionService
from app.database.repository import create_recommendation
from app.database.session import SessionLocal


class RecommendationService:
    def __init__(self) -> None:
        self.football_data = FootballDataService()
        self.nba_data = NbaDataService()
        self.analysis = AnalysisService()
        self.context = ContextService()
        self.odds = OddsService()
        self.archetypes = GameArchetypeService()
        self.market_scoring = MarketScoringService()
        self.traps = TrapDetectionService()
        self.decision = DecisionEngineService()
        self.ai = AIInterpreterService()

    def list_games(self, sport: str, when: str = "today") -> list[dict[str, Any]]:
        if sport == "football":
            return self.football_data.games_today() if when == "today" else self.football_data.games_tomorrow()
        return self.nba_data.games_today() if when == "today" else self.nba_data.games_tomorrow()

    def analyze_fixture(self, sport: str, fixture: dict[str, Any]) -> dict[str, Any]:
        fixture_context = self._build_fixture_context(sport, fixture)
        signals = self.analysis.analyze_football(fixture_context) if sport == "football" else self.analysis.analyze_nba(fixture_context)
        context = self.context.build_football_context(fixture_context) if sport == "football" else self.context.build_nba_context(fixture_context)
        sport_key = "soccer_epl" if sport == "football" else "basketball_nba"
        odds = self.odds.get_available_markets_for_fixture(fixture, sport_key)
        archetype = self.archetypes.classify(sport, signals, context, has_odds=bool(odds))
        scored = self.market_scoring.score_markets(sport, signals, context, odds)
        traps = self.traps.detect(context, scored, archetype)
        decision_payload = self.decision.build_recommendation(
            {"fixture": fixture, "sport": sport, "signals": signals, "archetype": archetype, "market_scores": scored, "traps": traps}
        )
        interpretation = self.ai.interpret(decision_payload)
        self._persist(decision_payload, fixture)
        return {"recommendation": decision_payload, "text": interpretation["text"], "mode": interpretation["mode"]}

    def get_best_readings_today(self, sport: str, limit: int = 5) -> list[dict[str, Any]]:
        ranked = []
        for fixture in self.list_games(sport, "today")[:20]:
            rec = self.analyze_fixture(sport, fixture)["recommendation"]
            main = rec.get("main_recommendation", {})
            ranked.append({"fixture": fixture, "recommendation": rec, "score": main.get("score", 0), "confidence": rec.get("confidence"), "risk": rec.get("risk")})
        ranked.sort(key=lambda i: i["score"], reverse=True)
        return ranked[:limit]

    def get_games_to_avoid_today(self, sport: str, limit: int = 5) -> list[dict[str, Any]]:
        avoids = []
        for fixture in self.list_games(sport, "today")[:20]:
            rec = self.analyze_fixture(sport, fixture)["recommendation"]
            if not rec.get("should_bet_pre_match"):
                avoids.append({"fixture": fixture, "reason": rec.get("final_verdict"), "traps": rec.get("traps", [])})
        return avoids[:limit]

    def _build_fixture_context(self, sport: str, fixture: dict[str, Any]) -> dict[str, Any]:
        base = {"fixture": fixture, "sport": sport, "home_stats": {}, "away_stats": {}, "data_quality": "média"}
        if sport == "football":
            base["home_stats"] = {"avg_scored": 1.5, "avg_conceded": 1.1, "shots": 12, "corners": 5, "cards": 2, "form_points": 8, "consistency": 62}
            base["away_stats"] = {"avg_scored": 1.2, "avg_conceded": 1.4, "shots": 10, "corners": 4, "cards": 2, "form_points": 6, "consistency": 55}
        else:
            base["home_stats"] = {"pace": 99, "pts_for": 114, "pts_against": 111, "home_edge": 0.15, "form_points": 7, "consistency": 58}
            base["away_stats"] = {"pace": 100, "pts_for": 111, "pts_against": 113, "form_points": 6, "consistency": 53}
        return base

    def _persist(self, rec: dict[str, Any], fixture: dict[str, Any]) -> None:
        main = rec.get("main_recommendation", {})
        try:
            with SessionLocal() as db:
                create_recommendation(
                    db,
                    fixture_id=str(fixture.get("fixture_id")),
                    sport=rec.get("sport", "football"),
                    market=main.get("market", "NO_BET"),
                    selection=main.get("selection", "Não apostar"),
                    score=int(main.get("score", 0)),
                    confidence=rec.get("confidence", "baixa"),
                    risk=rec.get("risk", "alto"),
                    stake_suggestion=rec.get("stake_suggestion", "não apostar"),
                    odd=main.get("available_odd"),
                    archetype=(rec.get("archetype") or {}).get("archetype"),
                    traps="; ".join(rec.get("traps", [])),
                )
        except Exception:
            pass
