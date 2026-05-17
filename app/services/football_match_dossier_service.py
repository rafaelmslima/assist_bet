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
    "no_pre_match_bet",
)
RECENT_CORNER_SAMPLE = 3


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
        player_context: Any | None = None,
        odds: list[dict[str, Any]] | None = None,
        odds_error: Any | None = None,
    ) -> dict[str, Any]:
        lineups = getattr(player_context, "lineups", {}) or {}
        injuries = list(getattr(player_context, "injuries", []) or [])
        predictions = getattr(player_context, "predictions", {}) or {}
        coverage = getattr(player_context, "coverage", {}) or {}
        player_quality = list(getattr(player_context, "data_quality", []) or [])
        odds_items = odds or []
        corners = self._build_corners_context(fixture)
        markets = self._build_market_candidates(
            fixture=fixture,
            home=home_team_data,
            away=away_team_data,
            corners=corners,
            football_context=football_context,
            lineups=lineups,
            injuries=injuries,
        )
        probability_targets = _build_probability_targets(markets)

        quality_notes = self._quality_notes(
            home_team_data=home_team_data,
            away_team_data=away_team_data,
            football_context=football_context,
            coverage=coverage,
            lineups=lineups,
            injuries=injuries,
            corners=corners,
            player_quality=player_quality,
        )
        data_quality = _build_data_quality(
            home_team_data=home_team_data,
            away_team_data=away_team_data,
            football_context=football_context,
            coverage=coverage,
            lineups=lineups,
            injuries=injuries,
            corners=corners,
            odds=odds_items,
            odds_error=odds_error,
            quality_notes=quality_notes,
        )
        home_profile = self._team_profile(home_team_data, fixture, side="home", injuries=injuries, lineups=lineups)
        away_profile = self._team_profile(away_team_data, fixture, side="away", injuries=injuries, lineups=lineups)
        matchup_analysis = _build_matchup_analysis(home_profile, away_profile)
        odds_analysis = _build_odds_analysis(odds_items, home_profile, away_profile)
        market_scores = _build_market_scores(
            home_profile=home_profile,
            away_profile=away_profile,
            matchup=matchup_analysis,
            data_quality=data_quality,
            odds_analysis=odds_analysis,
        )

        return {
            "schema_version": "football_ai_dossier_v2",
            "match": _compact_match(fixture),
            "data_quality": data_quality,
            "home_team_profile": home_profile,
            "away_team_profile": away_profile,
            "matchup_analysis": matchup_analysis,
            "market_scores": market_scores,
            "odds_analysis": odds_analysis,
            # Legacy keys kept for the current UI/advice adapter.
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
            "corners_context": corners,
            "market_candidates": markets,
            "probability_targets": probability_targets,
            "analysis_rules": {
                "ai_must_estimate": list(MARKET_CANDIDATES[:-1]),
                "ai_may_recommend": list(MARKET_CANDIDATES),
                "do_not_invent": ["lineups", "injuries", "standings", "statistics", "news"],
                "primary_task": "explicar o roteiro provavel do jogo usando o payload analitico antes de sugerir mercados",
                "fallback_when_weak": "confianca baixa, sem recomendacao quando data_quality ou odds nao sustentarem valor claro",
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

    def _team_profile(
        self,
        data: dict[str, Any],
        fixture: dict[str, Any],
        *,
        side: str,
        injuries: list[dict[str, Any]],
        lineups: dict[str, Any],
    ) -> dict[str, Any]:
        split_key = "home" if side == "home" else "away"
        recent = data.get("recent_form") if isinstance(data.get("recent_form"), dict) else {}
        recent_5 = recent.get("last_5") if isinstance(recent.get("last_5"), dict) else {}
        recent_10 = recent.get("last_10") if isinstance(recent.get("last_10"), dict) else {}
        raw_stats = data.get("team_statistics_raw") if isinstance(data.get("team_statistics_raw"), dict) else {}
        split = _home_away_split(data, split_key, recent_10, raw_stats)
        attack = _attack_profile(data, split, recent_5, raw_stats)
        defense = _defense_profile(data, split, recent_5, raw_stats)
        team_id = data.get("id")
        team_lineup = (lineups.get("teams") or {}).get(str(team_id), {}) if isinstance(lineups, dict) else {}

        return {
            "id": team_id,
            "name": data.get("name"),
            "side": side,
            "overall": {
                "avg_goals_for": data.get("avg_scored"),
                "avg_goals_against": data.get("avg_conceded"),
                "fixtures_played": _nested_get(data, "fixtures_played", "total"),
                "form": data.get("season_form"),
                "xg": "indisponivel",
                "xga": "indisponivel",
            },
            f"{split_key}_split": split,
            "recent_form": {
                "last_5": recent_5,
                "last_10": recent_10,
                "matches": recent.get("matches") or [],
                "form_string": data.get("last_5_form"),
                "note": "forma em W/D/L e apenas apoio; leitura principal usa médias e frequências calculadas.",
            },
            "attack": attack,
            "defense": defense,
            "players": {
                "lineup_confirmed": bool(lineups.get("confirmed")) if isinstance(lineups, dict) else False,
                "formation": team_lineup.get("formation"),
                "starters": [player.get("name") for player in (team_lineup.get("starters") or [])[:11]],
                "main_finishers": "indisponivel",
                "main_creators": "indisponivel",
                "dependency_note": "indisponivel",
            },
            "injuries": {
                "items": [item for item in injuries if str(item.get("team_id") or "") == str(team_id) or item.get("team_name") == data.get("name")],
                "impact_by_sector": _injury_sector_impact(injuries, team_id),
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
            lambda: self.client.get_team_fixtures(
                int(team_id),
                last=RECENT_CORNER_SAMPLE,
                league_id=league_id,
                season=season,
            ),
            team_id,
            league_id,
            season,
            side,
        )
        fixtures = _as_list(response.get("data")) if response.get("ok") else []
        corner_for: list[float] = []
        corner_against: list[float] = []
        notes: list[str] = []

        for raw in fixtures[:RECENT_CORNER_SAMPLE]:
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
        football_context: dict[str, Any],
        lineups: dict[str, Any],
        injuries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        home_name = str(fixture.get("home_team") or home.get("name") or "Mandante")
        away_name = str(fixture.get("away_team") or away.get("name") or "Visitante")
        home_goal_signal = _avg_known(home.get("home_avg_scored"), away.get("away_avg_conceded"), home.get("last_5_avg_scored"))
        away_goal_signal = _avg_known(away.get("away_avg_scored"), home.get("home_avg_conceded"), away.get("last_5_avg_scored"))
        total_signal = _sum_known(home_goal_signal, away_goal_signal)
        favorite = _favorite_from_stats(home_name, away_name, home_goal_signal, away_goal_signal)
        risk_flags = _risk_flags(football_context, lineups, injuries)

        candidates = [
            {
                "key": "corners",
                "label": "Escanteios",
                "signal": _corner_signal(corners),
                "evidence": _corner_evidence(corners),
                "risk_flags": risk_flags,
            },
            {
                "key": "home_over_0_5_goals",
                "label": f"{home_name} over 0.5 gol",
                "signal": _signal_from_goal_rate(home_goal_signal),
                "evidence": [f"sinal estimado de gol do mandante: {_fmt(home_goal_signal)}"],
                "risk_flags": risk_flags,
            },
            {
                "key": "away_over_0_5_goals",
                "label": f"{away_name} over 0.5 gol",
                "signal": _signal_from_goal_rate(away_goal_signal),
                "evidence": [f"sinal estimado de gol do visitante: {_fmt(away_goal_signal)}"],
                "risk_flags": risk_flags,
            },
            {
                "key": "over_1_5_goals",
                "label": "Over 1.5 gols",
                "signal": _signal_from_goal_rate(total_signal, target=1.8),
                "evidence": [f"soma projetada de gols: {_fmt(total_signal)}"],
                "risk_flags": risk_flags,
            },
            {
                "key": "over_2_5_goals",
                "label": "Over 2.5 gols",
                "signal": _signal_from_goal_rate(total_signal, target=2.6),
                "evidence": [f"soma projetada de gols: {_fmt(total_signal)}"],
                "risk_flags": risk_flags,
            },
            {
                "key": "favorite_win",
                "label": f"Vitoria do favorito: {favorite.get('team') or 'indefinido'}",
                "signal": favorite.get("signal"),
                "evidence": favorite.get("evidence") or [],
                "risk_flags": risk_flags + favorite.get("risk_flags", []),
            },
            {
                "key": "no_pre_match_bet",
                "label": "Sem entrada pre-jogo",
                "signal": _wait_signal(risk_flags, total_signal),
                "evidence": ["opcao obrigatoria quando dados ou escalacoes nao sustentam uma leitura clara"],
                "risk_flags": risk_flags,
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


def _compact_match(fixture: dict[str, Any]) -> dict[str, Any]:
    return {
        "fixture_id": fixture.get("fixture_id"),
        "home_team": fixture.get("home_team"),
        "away_team": fixture.get("away_team"),
        "competition": fixture.get("league"),
        "date": fixture.get("fixture_date"),
        "venue": "indisponivel",
        "round": fixture.get("round"),
        "home_advantage": True,
    }


def _build_data_quality(
    *,
    home_team_data: dict[str, Any],
    away_team_data: dict[str, Any],
    football_context: dict[str, Any],
    coverage: dict[str, bool],
    lineups: dict[str, Any],
    injuries: list[dict[str, Any]],
    corners: dict[str, Any],
    odds: list[dict[str, Any]],
    odds_error: Any,
    quality_notes: list[str],
) -> dict[str, Any]:
    missing: list[str] = []
    recent_available = (
        bool(_nested_get(home_team_data, "recent_form", "last_5", "sample_size"))
        and bool(_nested_get(away_team_data, "recent_form", "last_5", "sample_size"))
    ) or (bool(home_team_data.get("last_5_form")) and bool(away_team_data.get("last_5_form")))
    home_away_available = home_team_data.get("home_avg_scored") is not None and away_team_data.get("away_avg_scored") is not None
    standings_available = bool(football_context.get("summary_lines")) if isinstance(football_context, dict) else False
    odds_available = _has_normalizable_odds(odds)
    sample_size_ok = (
        (_to_float(_nested_get(home_team_data, "recent_form", "last_5", "sample_size")) or 0) >= 4
        and (_to_float(_nested_get(away_team_data, "recent_form", "last_5", "sample_size")) or 0) >= 4
    )

    checks = {
        "lineups": bool(lineups.get("confirmed")),
        "odds": odds_available,
        "xg": False,
        "injuries": bool(injuries) or bool(coverage.get("injuries")) if isinstance(coverage, dict) else bool(injuries),
        "standings": standings_available,
        "home_away_split": home_away_available,
        "recent_form": recent_available,
        "sample_size": sample_size_ok,
    }
    labels = {
        "lineups": "lineups_available",
        "odds": "odds_available",
        "xg": "xg_available",
        "injuries": "injuries_available",
        "standings": "standings_available",
        "home_away_split": "home_away_split_available",
        "recent_form": "recent_form_available",
        "sample_size": "sample_size_ok",
    }
    for key, available in checks.items():
        if not available:
            missing.append(labels[key])
    if odds_error:
        missing.append("odds_error")

    penalty = 0
    penalty += 8 if not checks["recent_form"] else 0
    penalty += 5 if not checks["home_away_split"] else 0
    penalty += 5 if not checks["standings"] else 0
    penalty += 5 if not checks["lineups"] else 0
    penalty += 4 if not checks["odds"] else 0
    penalty += 3 if not checks["sample_size"] else 0
    penalty = min(30, penalty)

    return {
        "lineups_available": checks["lineups"],
        "odds_available": checks["odds"],
        "xg_available": checks["xg"],
        "injuries_available": checks["injuries"],
        "standings_available": checks["standings"],
        "home_away_split_available": checks["home_away_split"],
        "recent_form_available": checks["recent_form"],
        "sample_size_ok": checks["sample_size"],
        "missing_critical_fields": _unique(missing),
        "confidence_penalty": penalty,
        "level": "completo" if penalty <= 8 else "parcial" if penalty <= 18 else "fraco",
        "notes": _unique(quality_notes + (["odds indisponiveis ou nao retornadas pela API"] if not odds_available else [])),
    }


def _home_away_split(data: dict[str, Any], split_key: str, recent: dict[str, Any], raw_stats: dict[str, Any]) -> dict[str, Any]:
    goals_for = data.get(f"{split_key}_avg_scored")
    goals_against = data.get(f"{split_key}_avg_conceded")
    played = _nested_get(raw_stats, "fixtures", "played", split_key)
    return {
        "sample_size": played,
        "goals_for_avg": goals_for,
        "goals_against_avg": goals_against,
        "xg_avg": "indisponivel",
        "xga_avg": "indisponivel",
        "over_1_5_pct": recent.get("over_1_5_pct"),
        "over_2_5_pct": recent.get("over_2_5_pct"),
        "btts_pct": recent.get("btts_pct"),
        "clean_sheet_pct": recent.get("clean_sheet_pct"),
        "scored_1_plus_pct": recent.get("scored_1_plus_pct"),
        "scored_2_plus_pct": recent.get("scored_2_plus_pct"),
        "conceded_1_plus_pct": recent.get("conceded_1_plus_pct"),
        "conceded_2_plus_pct": recent.get("conceded_2_plus_pct"),
        "first_half_goals_for_avg": recent.get("first_half_goals_for_avg"),
        "first_half_goals_against_avg": recent.get("first_half_goals_against_avg"),
        "second_half_goals_for_avg": recent.get("second_half_goals_for_avg"),
        "second_half_goals_against_avg": recent.get("second_half_goals_against_avg"),
        "first_goal_pct": "indisponivel",
    }


def _attack_profile(data: dict[str, Any], split: dict[str, Any], recent: dict[str, Any], raw_stats: dict[str, Any]) -> dict[str, Any]:
    avg_for = _first_number(split.get("goals_for_avg"), data.get("avg_scored"), recent.get("avg_scored"))
    shots_total = _nested_get(raw_stats, "shots", "total")
    shots_on = _nested_get(raw_stats, "shots", "on")
    return {
        "goals_per_game": avg_for,
        "xg_per_game": "indisponivel",
        "shots_per_game": shots_total or "indisponivel",
        "shots_on_target_per_game": shots_on or "indisponivel",
        "big_chances_created": "indisponivel",
        "chance_conversion": "indisponivel",
        "xg_vs_goals": "indisponivel",
        "scored_1_plus_pct": recent.get("scored_1_plus_pct"),
        "scored_2_plus_pct": recent.get("scored_2_plus_pct"),
        "main_finishers": "indisponivel",
        "main_creators": "indisponivel",
    }


def _defense_profile(data: dict[str, Any], split: dict[str, Any], recent: dict[str, Any], raw_stats: dict[str, Any]) -> dict[str, Any]:
    avg_against = _first_number(split.get("goals_against_avg"), data.get("avg_conceded"), recent.get("avg_conceded"))
    return {
        "goals_against_per_game": avg_against,
        "xga_per_game": "indisponivel",
        "shots_conceded_per_game": "indisponivel",
        "shots_on_target_conceded_per_game": "indisponivel",
        "big_chances_conceded": "indisponivel",
        "clean_sheet_pct": recent.get("clean_sheet_pct"),
        "conceded_1_plus_pct": recent.get("conceded_1_plus_pct"),
        "conceded_2_plus_pct": recent.get("conceded_2_plus_pct"),
        "defensive_errors": "indisponivel",
        "set_piece_vulnerability": "indisponivel",
        "transition_vulnerability": "indisponivel",
    }


def _build_matchup_analysis(home_profile: dict[str, Any], away_profile: dict[str, Any]) -> dict[str, Any]:
    home_goal_signal = _avg_known(
        _nested_get(home_profile, "attack", "goals_per_game"),
        _nested_get(away_profile, "defense", "goals_against_per_game"),
    )
    away_goal_signal = _avg_known(
        _nested_get(away_profile, "attack", "goals_per_game"),
        _nested_get(home_profile, "defense", "goals_against_per_game"),
    )
    total = _sum_known(home_goal_signal, away_goal_signal)
    home_mark_signal = _signal_label(home_goal_signal, high=1.45, medium=1.05)
    away_mark_signal = _signal_label(away_goal_signal, high=1.35, medium=0.95)
    over_signal = _signal_label(total, high=2.75, medium=2.15)
    risks = []
    if total is None:
        risks.append("sem base numerica suficiente para gols totais")
    if over_signal == "baixo":
        risks.append("risco alto de jogo travado ou baixa eficiencia")
    return {
        "home_attack_vs_away_defense": {
            "projected_goal_signal": home_goal_signal,
            "signal": f"{home_mark_signal} pro-mandante marcar",
        },
        "away_attack_vs_home_defense": {
            "projected_goal_signal": away_goal_signal,
            "signal": f"{away_mark_signal} pro-visitante marcar",
        },
        "tempo_expectation": "mais aberto" if total is not None and total >= 2.65 else "controlado/moderado" if total is not None else "indisponivel",
        "goal_expectation": f"{over_signal} tendencia de over",
        "tactical_edges": [
            f"Ataque mandante vs defesa visitante: {home_mark_signal}",
            f"Ataque visitante vs defesa mandante: {away_mark_signal}",
        ],
        "main_risks": risks,
    }


def _build_odds_analysis(odds: list[dict[str, Any]], home_profile: dict[str, Any], away_profile: dict[str, Any]) -> dict[str, Any]:
    markets = _normalize_odds(odds, home_profile.get("name"), away_profile.get("name"))
    return {
        "available": bool(markets),
        "markets": markets,
        "value_spots": [],
        "avoid_markets": [] if markets else ["Há tendência técnica, mas não é possível confirmar valor sem preço de mercado."],
    }


def _build_market_scores(
    *,
    home_profile: dict[str, Any],
    away_profile: dict[str, Any],
    matchup: dict[str, Any],
    data_quality: dict[str, Any],
    odds_analysis: dict[str, Any],
) -> dict[str, Any]:
    penalty = int(data_quality.get("confidence_penalty") or 0)
    home_goal = _to_float(_nested_get(matchup, "home_attack_vs_away_defense", "projected_goal_signal"))
    away_goal = _to_float(_nested_get(matchup, "away_attack_vs_home_defense", "projected_goal_signal"))
    total = _sum_known(home_goal, away_goal)
    home_recent = _nested_get(home_profile, "recent_form", "last_5") or {}
    away_recent = _nested_get(away_profile, "recent_form", "last_5") or {}

    scores = {
        "home_win": _score_payload(
            50 + _spread(home_goal, away_goal, 18) - penalty * 0.45,
            "resultado do mandante",
            "depende de converter superioridade em placar; empate reduz valor.",
        ),
        "double_chance_home": _score_payload(
            58 + _spread(home_goal, away_goal, 12) - penalty * 0.35,
            "proteção melhor que vitória seca quando o mandante tem sinal ofensivo.",
            "odd costuma vir baixa; precisa preço mínimo.",
        ),
        "over_1_5": _score_payload(
            45 + ((_to_float(total) or 0) * 11) + _pct_bonus(home_recent.get("over_1_5_pct"), away_recent.get("over_1_5_pct"), 0.12) - penalty * 0.45,
            "soma entre projeção de gols e frequências recentes.",
            "perde força se escalações vierem conservadoras ou jogo travar cedo.",
        ),
        "over_2_5": _score_payload(
            35 + ((_to_float(total) or 0) * 10) + _pct_bonus(home_recent.get("over_2_5_pct"), away_recent.get("over_2_5_pct"), 0.14) - penalty * 0.55,
            "precisa de jogo mais aberto e participação dos dois lados.",
            "linha mais sensível à eficiência e ao primeiro gol.",
        ),
        "under_2_5": _score_payload(
            72 - ((_to_float(total) or 2.4) * 9) + _pct_bonus(100 - (_to_float(home_recent.get("over_2_5_pct")) or 50), 100 - (_to_float(away_recent.get("over_2_5_pct")) or 50), 0.10) - penalty * 0.35,
            "ganha peso quando o total projetado é baixo.",
            "sofre se houver gol cedo ou escalações muito ofensivas.",
        ),
        "btts": _score_payload(
            38 + ((_to_float(home_goal) or 0) * 9) + ((_to_float(away_goal) or 0) * 9) + _pct_bonus(home_recent.get("btts_pct"), away_recent.get("btts_pct"), 0.10) - penalty * 0.50,
            "cruza capacidade dos dois ataques com fragilidade defensiva adversária.",
            "visitante sem produção fora derruba muito esse mercado.",
        ),
        "home_team_goal": _score_payload(
            45 + ((_to_float(home_goal) or 0) * 18) + _pct_bonus(_nested_get(home_profile, "attack", "scored_1_plus_pct"), _nested_get(away_profile, "defense", "conceded_1_plus_pct"), 0.10) - penalty * 0.40,
            "mercado sustentado pelo cruzamento ataque mandante x defesa visitante.",
            "confirmar titulares ofensivos e preço.",
        ),
        "away_team_goal": _score_payload(
            42 + ((_to_float(away_goal) or 0) * 17) + _pct_bonus(_nested_get(away_profile, "attack", "scored_1_plus_pct"), _nested_get(home_profile, "defense", "conceded_1_plus_pct"), 0.10) - penalty * 0.45,
            "mede se o visitante tem caminho real para responder.",
            "cai se postura fora for reativa ou escalação poupar ataque.",
        ),
    }
    _attach_value_read(scores, odds_analysis)
    return scores


def _score_payload(score: float, reason: str, risk: str) -> dict[str, Any]:
    clean_score = max(0, min(100, int(round(score))))
    return {"score": clean_score, "confidence": _score_confidence(clean_score), "reason": reason, "risk": risk}


def _score_confidence(score: int) -> str:
    if score >= 80:
        return "sinal forte"
    if score >= 65:
        return "sinal bom"
    if score >= 50:
        return "sinal moderado"
    if score >= 35:
        return "sinal fraco"
    return "evitar"


def _normalize_odds(odds: list[dict[str, Any]], home_name: Any, away_name: Any) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for event in odds:
        bookmakers = event.get("bookmakers") if isinstance(event.get("bookmakers"), list) else []
        for bookmaker in bookmakers[:3]:
            for bet in bookmaker.get("bets") or []:
                bet_name = str(bet.get("name") or "")
                for value in bet.get("values") or []:
                    odd = _to_float(value.get("odd"))
                    if not odd:
                        continue
                    label = str(value.get("value") or "")
                    key = _market_key_from_odd(bet_name, label, home_name, away_name)
                    if not key:
                        continue
                    normalized.setdefault(key, []).append(
                        {
                            "bookmaker": bookmaker.get("name"),
                            "market": bet_name,
                            "selection": label,
                            "odd": odd,
                            "implied_probability": round(1 / odd, 4) if odd > 1 else None,
                        }
                    )
    return normalized


def _has_normalizable_odds(odds: list[dict[str, Any]]) -> bool:
    for event in odds:
        bookmakers = event.get("bookmakers") if isinstance(event.get("bookmakers"), list) else []
        for bookmaker in bookmakers:
            bets = bookmaker.get("bets") if isinstance(bookmaker.get("bets"), list) else []
            if bets:
                return True
    return False


def _market_key_from_odd(market: str, selection: str, home_name: Any, away_name: Any) -> str | None:
    text = _norm(f"{market} {selection}")
    home = _norm(home_name)
    away = _norm(away_name)
    if "match winner" in text or "1x2" in text:
        if home and home in text:
            return "home_win"
        if away and away in text:
            return "away_win"
        if "draw" in text:
            return "draw"
    if "over/under" in text or "goals over/under" in text:
        if "over" in text and "1.5" in text:
            return "over_1_5"
        if "over" in text and "2.5" in text:
            return "over_2_5"
        if "under" in text and "2.5" in text:
            return "under_2_5"
    if "both teams score" in text or "btts" in text:
        if "yes" in text or "sim" in text:
            return "btts"
    return None


def _attach_value_read(scores: dict[str, Any], odds_analysis: dict[str, Any]) -> None:
    markets = odds_analysis.get("markets") if isinstance(odds_analysis.get("markets"), dict) else {}
    for key, score_data in scores.items():
        rows = markets.get(key) or []
        if not rows:
            continue
        best = max(rows, key=lambda item: _to_float(item.get("odd")) or 0)
        odd = _to_float(best.get("odd"))
        if not odd:
            continue
        estimated = max(0.01, min(0.95, score_data["score"] / 100))
        implied = 1 / odd
        edge = estimated - implied
        score_data["odds"] = {
            "best_odd": odd,
            "implied_probability": round(implied, 4),
            "estimated_probability": round(estimated, 4),
            "edge": round(edge, 4),
            "value_label": "possivel value" if edge >= 0.04 and score_data["score"] >= 65 else "sem value claro",
        }


def _injury_sector_impact(injuries: list[dict[str, Any]], team_id: Any) -> dict[str, Any]:
    team_injuries = [item for item in injuries if str(item.get("team_id") or "") == str(team_id)]
    return {
        "attack": "indisponivel",
        "midfield": "indisponivel",
        "defense": "indisponivel",
        "goalkeeper": "indisponivel",
        "known_absences": len(team_injuries),
    }


def _pct_bonus(left: Any, right: Any, weight: float) -> float:
    values = [_to_float(left), _to_float(right)]
    nums = [value for value in values if value is not None]
    if not nums:
        return 0.0
    return (sum(nums) / len(nums) - 50) * weight


def _spread(left: Any, right: Any, multiplier: float) -> float:
    lnum = _to_float(left)
    rnum = _to_float(right)
    if lnum is None or rnum is None:
        return 0.0
    return (lnum - rnum) * multiplier


def _signal_label(value: Any, *, high: float, medium: float) -> str:
    number = _to_float(value)
    if number is None:
        return "indisponivel"
    if number >= high:
        return "forte"
    if number >= medium:
        return "medio"
    return "fraco"


def _first_number(*values: Any) -> float | None:
    for value in values:
        number = _to_float(value)
        if number is not None:
            return number
    return None


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


def _build_probability_targets(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for item in candidates:
        key = str(item.get("key") or "")
        if key == "no_pre_match_bet":
            continue
        base_probability = _base_probability_from_signal(item.get("signal"))
        targets.append(
            {
                "key": key,
                "market": item.get("label"),
                "base_probability_hint": base_probability,
                "confidence_hint": _confidence_hint(item.get("signal"), item.get("risk_flags") or []),
                "sample_and_metrics": {
                    "signal": item.get("signal"),
                    "evidence": item.get("evidence") or [],
                    "risk_flags": item.get("risk_flags") or [],
                },
                "ai_instruction": "use este mercado apenas como ideia qualitativa se ele combinar com o roteiro do jogo.",
            }
        )
    return targets


def _base_probability_from_signal(signal: Any) -> float | None:
    normalized = _norm(signal)
    if normalized == "alto":
        return 0.68
    if normalized in {"medio", "médio"}:
        return 0.56
    if normalized == "baixo":
        return 0.43
    return None


def _confidence_hint(signal: Any, risk_flags: list[str]) -> str:
    if signal in (None, "", "indisponivel") or len(risk_flags) >= 3:
        return "baixa"
    if str(signal).lower() == "alto" and len(risk_flags) <= 1:
        return "media"
    return "baixa" if len(risk_flags) >= 2 else "media"


def _favorite_from_stats(
    home_name: str,
    away_name: str,
    home_signal: float | None,
    away_signal: float | None,
) -> dict[str, Any]:
    if home_signal is None and away_signal is None:
        return {"team": None, "signal": "baixo", "evidence": ["favorito indefinido"], "risk_flags": ["sem vantagem estatistica clara"]}
    if (home_signal or 0) >= (away_signal or 0):
        team = home_name
        diff = (home_signal or 0) - (away_signal or 0)
    else:
        team = away_name
        diff = (away_signal or 0) - (home_signal or 0)
    return {
        "team": team,
        "signal": "alto" if diff >= 0.6 else "medio" if diff >= 0.25 else "baixo",
        "evidence": [f"favorito estatistico por producao de gols: {team}"],
        "risk_flags": ["favoritismo apenas estatistico, confirmar escalacao e contexto"],
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


def _wait_signal(risk_flags: list[str], total_signal: float | None) -> str:
    if len(risk_flags) >= 3:
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
