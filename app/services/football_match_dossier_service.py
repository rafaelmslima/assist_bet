from __future__ import annotations

from statistics import mean
from typing import Any

from app.integrations.api_football_client import ApiFootballClient
from app.services.cache_service import cache_key, default_cache
from app.services.football_context_service import FootballContextService


MARKET_CANDIDATES = (
    "corners",
    "home_over_0_5_goals",
    "away_over_0_5_goals",
    "over_1_5_goals",
    "over_2_5_goals",
    "favorite_win",
    "wait_live_or_no_bet",
)


class FootballMatchDossierService:
    """Builds the structured match payload that the AI can analyze safely."""

    def __init__(
        self,
        client: ApiFootballClient | None = None,
        football_context_service: FootballContextService | None = None,
    ) -> None:
        self.client = client or ApiFootballClient()
        self.football_context_service = football_context_service or FootballContextService()

    def build_dossier(
        self,
        *,
        fixture: dict[str, Any],
        home_team_data: dict[str, Any],
        away_team_data: dict[str, Any],
        football_context: dict[str, Any],
        odds: list[dict[str, Any]],
        player_context: Any | None = None,
        odds_error: str | None = None,
    ) -> dict[str, Any]:
        lineups = getattr(player_context, "lineups", {}) or {}
        injuries = list(getattr(player_context, "injuries", []) or [])
        predictions = getattr(player_context, "predictions", {}) or {}
        coverage = getattr(player_context, "coverage", {}) or {}
        player_quality = list(getattr(player_context, "data_quality", []) or [])
        corners = self._build_corners_context(fixture)
        markets = self._build_market_candidates(
            fixture=fixture,
            home=home_team_data,
            away=away_team_data,
            corners=corners,
            odds=odds,
            football_context=football_context,
            lineups=lineups,
            injuries=injuries,
        )

        quality_notes = self._quality_notes(
            home_team_data=home_team_data,
            away_team_data=away_team_data,
            football_context=football_context,
            coverage=coverage,
            lineups=lineups,
            injuries=injuries,
            odds=odds,
            odds_error=odds_error,
            corners=corners,
            player_quality=player_quality,
        )

        return {
            "schema_version": "football_ai_dossier_v1",
            "fixture": _compact_fixture(fixture),
            "teams": {
                "home": self._team_section(home_team_data),
                "away": self._team_section(away_team_data),
            },
            "competitive_context": football_context or {},
            "calendar_context": {
                "alerts": football_context.get("context_alerts") if isinstance(football_context, dict) else [],
                "summary_lines": football_context.get("summary_lines") if isinstance(football_context, dict) else [],
            },
            "lineups": self._lineup_summary(lineups),
            "absences": self._injury_summary(injuries),
            "predictions": _compact_prediction(predictions),
            "odds": {
                "available": bool(odds),
                "error": odds_error,
                "markets": _summarize_odds(odds),
            },
            "corners_context": corners,
            "market_candidates": markets,
            "analysis_rules": {
                "ai_must_choose_from_or_reject": list(MARKET_CANDIDATES),
                "do_not_invent": ["odds", "lineups", "injuries", "standings", "statistics"],
                "no_value_without_odd": True,
                "fallback_when_weak": "sem entrada pre-jogo / esperar live",
            },
            "data_quality": {
                "level": _quality_level(quality_notes),
                "notes": quality_notes,
            },
        }

    def _team_section(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "side": data.get("side"),
            "form": {
                "last_5": data.get("last_5_form"),
                "season": data.get("season_form"),
            },
            "goals": {
                "avg_scored_total": data.get("avg_scored"),
                "avg_conceded_total": data.get("avg_conceded"),
                "home_avg_scored": data.get("home_avg_scored"),
                "home_avg_conceded": data.get("home_avg_conceded"),
                "away_avg_scored": data.get("away_avg_scored"),
                "away_avg_conceded": data.get("away_avg_conceded"),
                "last_5_avg_scored": data.get("last_5_avg_scored"),
                "last_5_avg_conceded": data.get("last_5_avg_conceded"),
            },
        }

    def _build_corners_context(self, fixture: dict[str, Any]) -> dict[str, Any]:
        home = self._team_recent_corners(
            team_id=fixture.get("home_team_id"),
            league_id=fixture.get("league_id"),
            season=fixture.get("season"),
            side="home",
        )
        away = self._team_recent_corners(
            team_id=fixture.get("away_team_id"),
            league_id=fixture.get("league_id"),
            season=fixture.get("season"),
            side="away",
        )
        totals = [item for item in (home.get("avg_for"), away.get("avg_for")) if item is not None]
        match_avg = round(sum(totals), 2) if totals else None
        return {
            "home": home,
            "away": away,
            "combined_team_corners_avg": match_avg,
            "source": "recent fixture statistics from API-Football when available",
        }

    def _team_recent_corners(self, *, team_id: Any, league_id: Any, season: Any, side: str) -> dict[str, Any]:
        if team_id in (None, ""):
            return {"avg_for": None, "avg_against": None, "sample_size": 0, "notes": ["team id ausente"]}

        response = _cached_call(
            "api_football.dossier_team_recent_fixtures",
            300,
            lambda: self.client.get_team_fixtures(int(team_id), last=5, league_id=league_id, season=season),
            team_id,
            league_id,
            season,
            side,
        )
        fixtures = _as_list(response.get("data")) if response.get("ok") else []
        corner_for: list[float] = []
        corner_against: list[float] = []
        notes: list[str] = []

        for raw in fixtures[:5]:
            fixture_id = _nested_get(raw, "fixture", "id") or raw.get("fixture_id")
            if not fixture_id:
                continue
            stats_response = _cached_call(
                "api_football.dossier_fixture_statistics",
                900,
                lambda fixture_id=fixture_id: self.client.get_fixture_statistics(int(fixture_id)),
                fixture_id,
            )
            if not stats_response.get("ok"):
                continue
            values = _extract_corner_stats(_as_list(stats_response.get("data")), team_id)
            if values.get("for") is not None:
                corner_for.append(values["for"])
            if values.get("against") is not None:
                corner_against.append(values["against"])

        if not corner_for:
            notes.append("escanteios recentes indisponiveis")
        return {
            "avg_for": round(mean(corner_for), 2) if corner_for else None,
            "avg_against": round(mean(corner_against), 2) if corner_against else None,
            "sample_size": len(corner_for),
            "notes": notes,
        }

    def _build_market_candidates(
        self,
        *,
        fixture: dict[str, Any],
        home: dict[str, Any],
        away: dict[str, Any],
        corners: dict[str, Any],
        odds: list[dict[str, Any]],
        football_context: dict[str, Any],
        lineups: dict[str, Any],
        injuries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        home_name = str(fixture.get("home_team") or home.get("name") or "Mandante")
        away_name = str(fixture.get("away_team") or away.get("name") or "Visitante")
        home_goal_signal = _avg_known(home.get("home_avg_scored"), away.get("away_avg_conceded"), home.get("last_5_avg_scored"))
        away_goal_signal = _avg_known(away.get("away_avg_scored"), home.get("home_avg_conceded"), away.get("last_5_avg_scored"))
        total_signal = _sum_known(home_goal_signal, away_goal_signal)
        favorite = _favorite_from_odds_or_stats(odds, home_name, away_name, home_goal_signal, away_goal_signal)
        risk_flags = _risk_flags(football_context, lineups, injuries)

        candidates = [
            {
                "key": "corners",
                "label": "Escanteios",
                "signal": _corner_signal(corners),
                "evidence": _corner_evidence(corners),
                "risk_flags": risk_flags,
                "available_odd": _find_total_like_odd(odds, ("corners", "corner", "escanteios")),
            },
            {
                "key": "home_over_0_5_goals",
                "label": f"{home_name} over 0.5 gol",
                "signal": _signal_from_goal_rate(home_goal_signal),
                "evidence": [f"sinal estimado de gol do mandante: {_fmt(home_goal_signal)}"],
                "risk_flags": risk_flags,
                "available_odd": _find_team_total_odd(odds, home_name),
            },
            {
                "key": "away_over_0_5_goals",
                "label": f"{away_name} over 0.5 gol",
                "signal": _signal_from_goal_rate(away_goal_signal),
                "evidence": [f"sinal estimado de gol do visitante: {_fmt(away_goal_signal)}"],
                "risk_flags": risk_flags,
                "available_odd": _find_team_total_odd(odds, away_name),
            },
            {
                "key": "over_1_5_goals",
                "label": "Over 1.5 gols",
                "signal": _signal_from_goal_rate(total_signal, target=1.8),
                "evidence": [f"soma projetada de gols: {_fmt(total_signal)}"],
                "risk_flags": risk_flags,
                "available_odd": _find_total_odd(odds, 1.5),
            },
            {
                "key": "over_2_5_goals",
                "label": "Over 2.5 gols",
                "signal": _signal_from_goal_rate(total_signal, target=2.6),
                "evidence": [f"soma projetada de gols: {_fmt(total_signal)}"],
                "risk_flags": risk_flags,
                "available_odd": _find_total_odd(odds, 2.5),
            },
            {
                "key": "favorite_win",
                "label": f"Vitoria do favorito: {favorite.get('team') or 'indefinido'}",
                "signal": favorite.get("signal"),
                "evidence": favorite.get("evidence") or [],
                "risk_flags": risk_flags + favorite.get("risk_flags", []),
                "available_odd": favorite.get("odd"),
            },
            {
                "key": "wait_live_or_no_bet",
                "label": "Esperar live / sem entrada pre-jogo",
                "signal": _wait_signal(risk_flags, total_signal, odds),
                "evidence": ["opcao obrigatoria quando dados, odds ou escalações nao sustentam entrada"],
                "risk_flags": risk_flags,
                "available_odd": None,
            },
        ]
        return candidates

    def _lineup_summary(self, lineups: dict[str, Any]) -> dict[str, Any]:
        teams = lineups.get("teams") if isinstance(lineups.get("teams"), dict) else {}
        return {
            "confirmed": bool(lineups.get("confirmed")),
            "teams": [
                {
                    "team": _nested_get(item, "team", "name"),
                    "formation": item.get("formation"),
                    "starters": [player.get("name") for player in (item.get("starters") or [])[:11]],
                }
                for item in teams.values()
                if isinstance(item, dict)
            ],
        }

    def _injury_summary(self, injuries: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "count": len(injuries),
            "items": [
                {
                    "team": item.get("team_name"),
                    "player": item.get("player_name"),
                    "reason": item.get("reason") or item.get("type"),
                }
                for item in injuries[:12]
            ],
        }

    def _quality_notes(
        self,
        *,
        home_team_data: dict[str, Any],
        away_team_data: dict[str, Any],
        football_context: dict[str, Any],
        coverage: dict[str, bool],
        lineups: dict[str, Any],
        injuries: list[dict[str, Any]],
        odds: list[dict[str, Any]],
        odds_error: str | None,
        corners: dict[str, Any],
        player_quality: list[str],
    ) -> list[str]:
        notes: list[str] = []
        for label, team in (("mandante", home_team_data), ("visitante", away_team_data)):
            if team.get("avg_scored") is None or team.get("avg_conceded") is None:
                notes.append(f"medias de gols incompletas para {label}")
        if not (football_context.get("summary_lines") if isinstance(football_context, dict) else None):
            notes.append("contexto competitivo/classificacao indisponivel")
        if coverage and not coverage.get("lineups"):
            notes.append("liga sem cobertura de escalacoes")
        elif not lineups.get("confirmed"):
            notes.append("escalacoes ainda nao confirmadas")
        if coverage and not coverage.get("injuries"):
            notes.append("liga sem cobertura de desfalques")
        elif not injuries:
            notes.append("sem desfalques confirmados na API")
        if not odds:
            notes.append(odds_error or "sem odds equivalentes disponiveis")
        if not _nested_get(corners, "home", "sample_size") and not _nested_get(corners, "away", "sample_size"):
            notes.append("escanteios sem amostra recente")
        notes.extend(player_quality[:4])
        return _unique(notes)


def _cached_call(namespace: str, ttl_seconds: int, factory, *parts: Any) -> dict[str, Any]:
    key = cache_key(namespace, *parts)
    return default_cache.get_or_set(key, ttl_seconds, factory)


def _compact_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    return {
        "fixture_id": fixture.get("fixture_id"),
        "league_id": fixture.get("league_id"),
        "league": fixture.get("league"),
        "round": fixture.get("round"),
        "season": fixture.get("season"),
        "fixture_date": fixture.get("fixture_date"),
        "status": fixture.get("status"),
        "home_team": fixture.get("home_team"),
        "away_team": fixture.get("away_team"),
    }


def _compact_prediction(predictions: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(predictions, dict) or not predictions:
        return {}
    prediction = predictions.get("predictions") if isinstance(predictions.get("predictions"), dict) else {}
    return {
        "winner": _nested_get(prediction, "winner", "name"),
        "advice": prediction.get("advice"),
        "percent": prediction.get("percent"),
    }


def _extract_corner_stats(raw_stats: list[dict[str, Any]], team_id: Any) -> dict[str, float | None]:
    target = str(team_id)
    team_value = None
    opponent_value = None
    for item in raw_stats:
        item_team_id = str(_nested_get(item, "team", "id") or "")
        value = _stat_value(item.get("statistics"), "Corner Kicks")
        if value is None:
            continue
        if item_team_id == target:
            team_value = value
        else:
            opponent_value = value
    return {"for": team_value, "against": opponent_value}


def _stat_value(stats: Any, stat_type: str) -> float | None:
    for item in stats or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "").lower() == stat_type.lower():
            return _to_float(item.get("value"))
    return None


def _summarize_odds(odds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for market in odds:
        key = market.get("key") or market.get("market")
        bookmaker = market.get("bookmaker")
        for outcome in market.get("outcomes") or []:
            rows.append(
                {
                    "bookmaker": bookmaker,
                    "market": key,
                    "selection": outcome.get("name") or outcome.get("selection"),
                    "point": outcome.get("point"),
                    "price": outcome.get("price") or outcome.get("odd"),
                }
            )
            if len(rows) >= 20:
                return rows
        if not market.get("outcomes") and market.get("selection"):
            rows.append(
                {
                    "bookmaker": bookmaker,
                    "market": key,
                    "selection": market.get("selection"),
                    "point": market.get("point"),
                    "price": market.get("price") or market.get("odd"),
                }
            )
    return rows


def _favorite_from_odds_or_stats(
    odds: list[dict[str, Any]],
    home_name: str,
    away_name: str,
    home_signal: float | None,
    away_signal: float | None,
) -> dict[str, Any]:
    home_odd = _find_h2h_odd(odds, home_name)
    away_odd = _find_h2h_odd(odds, away_name)
    if home_odd and away_odd:
        team = home_name if home_odd < away_odd else away_name
        odd = min(home_odd, away_odd)
        return {
            "team": team,
            "odd": odd,
            "signal": "medio" if odd >= 1.45 else "baixo",
            "evidence": [f"favorito por odds h2h: {team} @{odd:.2f}"],
            "risk_flags": ["odd baixa/espremida"] if odd < 1.45 else [],
        }
    if home_signal is None and away_signal is None:
        return {"team": None, "odd": None, "signal": "baixo", "evidence": ["favorito indefinido"], "risk_flags": ["sem odds h2h"]}
    if (home_signal or 0) >= (away_signal or 0):
        team = home_name
        diff = (home_signal or 0) - (away_signal or 0)
    else:
        team = away_name
        diff = (away_signal or 0) - (home_signal or 0)
    return {
        "team": team,
        "odd": None,
        "signal": "alto" if diff >= 0.6 else "medio" if diff >= 0.25 else "baixo",
        "evidence": [f"favorito estatistico por producao de gols: {team}"],
        "risk_flags": ["sem odds h2h para confirmar favorito"],
    }


def _risk_flags(
    football_context: dict[str, Any],
    lineups: dict[str, Any],
    injuries: list[dict[str, Any]],
) -> list[str]:
    flags: list[str] = []
    alerts = football_context.get("context_alerts") if isinstance(football_context, dict) else []
    states = football_context.get("competitive_states") if isinstance(football_context, dict) else {}
    if alerts:
        flags.extend(str(item) for item in alerts[:3])
    if isinstance(states, dict) and any(str(value or "") in {"champion_locked", "continental_locked", "relegated_locked"} for value in states.values()):
        flags.append("risco de motivacao/rotacao por objetivo ja definido")
    if not lineups.get("confirmed"):
        flags.append("escalacoes nao confirmadas")
    if injuries:
        flags.append("ha desfalques listados na API")
    return _unique(flags)


def _corner_signal(corners: dict[str, Any]) -> str:
    combined = _to_float(corners.get("combined_team_corners_avg"))
    if combined is None:
        return "indisponivel"
    if combined >= 10:
        return "alto"
    if combined >= 8:
        return "medio"
    return "baixo"


def _corner_evidence(corners: dict[str, Any]) -> list[str]:
    home = corners.get("home") if isinstance(corners.get("home"), dict) else {}
    away = corners.get("away") if isinstance(corners.get("away"), dict) else {}
    return [
        f"mandante: {_fmt(home.get('avg_for'))} escanteios a favor em {home.get('sample_size', 0)} jogos",
        f"visitante: {_fmt(away.get('avg_for'))} escanteios a favor em {away.get('sample_size', 0)} jogos",
    ]


def _wait_signal(risk_flags: list[str], total_signal: float | None, odds: list[dict[str, Any]]) -> str:
    if len(risk_flags) >= 3 or not odds:
        return "alto"
    if total_signal is None:
        return "medio"
    return "baixo"


def _signal_from_goal_rate(value: float | None, target: float = 1.0) -> str:
    if value is None:
        return "indisponivel"
    if value >= target + 0.45:
        return "alto"
    if value >= target:
        return "medio"
    return "baixo"


def _find_total_odd(odds: list[dict[str, Any]], point: float) -> float | None:
    for market in odds:
        key = str(market.get("key") or market.get("market") or "").lower()
        if "total" not in key:
            continue
        for outcome in market.get("outcomes") or []:
            if str(outcome.get("name") or "").lower() == "over" and abs((_to_float(outcome.get("point")) or -1) - point) < 0.01:
                return _to_float(outcome.get("price") or outcome.get("odd"))
    return None


def _find_total_like_odd(odds: list[dict[str, Any]], terms: tuple[str, ...]) -> float | None:
    normalized_terms = tuple(term.lower() for term in terms)
    for market in odds:
        label = " ".join(str(market.get(key, "")) for key in ("key", "market", "selection")).lower()
        if any(term in label for term in normalized_terms):
            outcomes = market.get("outcomes") or []
            if outcomes:
                return _to_float(outcomes[0].get("price") or outcomes[0].get("odd"))
            return _to_float(market.get("price") or market.get("odd"))
    return None


def _find_team_total_odd(odds: list[dict[str, Any]], team_name: str) -> float | None:
    return _find_total_like_odd(odds, (team_name.lower(), "team total", "gols do time"))


def _find_h2h_odd(odds: list[dict[str, Any]], team_name: str) -> float | None:
    wanted = _norm(team_name)
    for market in odds:
        key = str(market.get("key") or market.get("market") or "").lower()
        if key != "h2h":
            continue
        for outcome in market.get("outcomes") or []:
            name = _norm(outcome.get("name") or outcome.get("selection"))
            if wanted and (wanted == name or wanted in name or name in wanted):
                return _to_float(outcome.get("price") or outcome.get("odd"))
    return None


def _quality_level(notes: list[str]) -> str:
    if len(notes) <= 2:
        return "completo"
    if len(notes) <= 5:
        return "parcial"
    return "fraco"


def _avg_known(*values: Any) -> float | None:
    numbers = [_to_float(value) for value in values]
    known = [value for value in numbers if value is not None]
    return round(mean(known), 2) if known else None


def _sum_known(*values: Any) -> float | None:
    numbers = [_to_float(value) for value in values]
    known = [value for value in numbers if value is not None]
    if len(known) < 2:
        return None
    return round(sum(known), 2)


def _as_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        nested = value.get("response")
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        return [value]
    return []


def _nested_get(data: Any, *keys: str) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip("%").replace(",", "."))
        except ValueError:
            return None
    return None


def _fmt(value: Any) -> str:
    number = _to_float(value)
    return "indisponivel" if number is None else f"{number:.2f}"


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().replace("-", " ").split())


def _unique(items: list[str]) -> list[str]:
    unique: list[str] = []
    for item in items:
        if item and item not in unique:
            unique.append(item)
    return unique
