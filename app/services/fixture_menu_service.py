from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any
import re
import unicodedata
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.bot.formatters import format_bet_advisor_response
from app.integrations.api_football_client import ApiFootballClient
from app.services.cache_service import cache_key, default_cache
from app.services.analysis_service import AnalysisService
from app.services.bet_advisor_service import BetAdvisorService
from app.services.card_service import generate_pre_match_card
from app.services.football_context_service import FootballContextService
from app.services.football_player_service import FootballPlayerService
from app.services.odds_service import OddsService
from app.services.player_advisor_service import PlayerAdvisorService, format_fixture_player_advice


try:
    SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")
except ZoneInfoNotFoundError:
    SAO_PAULO_TZ = timezone(timedelta(hours=-3))
INSUFFICIENT_DATA = "dados insuficientes"


@dataclass(frozen=True)
class LeagueConfig:
    key: str
    label: str
    league_id: int
    season: int


SUPPORTED_LEAGUES: tuple[LeagueConfig, ...] = (
    LeagueConfig("premier_league", "Premier League", 39, 2025),
    LeagueConfig("la_liga", "La Liga", 140, 2025),
    LeagueConfig("serie_a", "Serie A", 135, 2025),
    LeagueConfig("bundesliga", "Bundesliga", 78, 2025),
    LeagueConfig("ligue_1", "Ligue 1", 61, 2025),
    LeagueConfig("champions_league", "Champions League", 2, 2025),
    LeagueConfig("europa_league", "Europa League", 3, 2025),
    LeagueConfig("libertadores", "Libertadores", 13, 2026),
    LeagueConfig("sulamericana", "Copa Sul-Americana", 11, 2026),
    LeagueConfig("brasileirao", "Brasileirão", 71, 2026),
    LeagueConfig("eredivisie", "Eredivisie - Holanda 1ª Divisão", 88, 2025),
)


class FixtureMenuService:
    """Fetches real football fixtures and prepares analysis-ready data."""

    def __init__(
        self,
        client: ApiFootballClient | None = None,
        analysis_service: AnalysisService | None = None,
    ) -> None:
        self.client = client or ApiFootballClient()
        self.analysis_service = analysis_service or AnalysisService()
        self.player_service = FootballPlayerService(self.client)
        self.player_advisor = PlayerAdvisorService()
        self.football_context_service = FootballContextService()

    def get_supported_leagues(self) -> tuple[LeagueConfig, ...]:
        return SUPPORTED_LEAGUES

    def get_league(self, league_key: str) -> LeagueConfig | None:
        return next((league for league in SUPPORTED_LEAGUES if league.key == league_key), None)

    def get_today_fixtures(self, league_key: str) -> dict[str, Any]:
        return self.get_fixtures_for_day(league_key, day_offset=0)

    def get_tomorrow_fixtures(self, league_key: str) -> dict[str, Any]:
        return self.get_fixtures_for_day(league_key, day_offset=1)

    def get_fixtures_for_day(self, league_key: str, day_offset: int = 0) -> dict[str, Any]:
        league = self.get_league(league_key)
        if league is None:
            return {"ok": False, "error": "Liga não encontrada.", "fixtures": [], "league": None}

        target_date = (datetime.now(SAO_PAULO_TZ).date() + timedelta(days=day_offset)).isoformat()
        response = _cached_call(
            "api_football.fixtures_by_league_date",
            180,
            lambda: self.client.get_fixtures_by_league_date(league.league_id, target_date, league.season),
            league.league_id,
            target_date,
            league.season,
        )
        if not response.get("ok"):
            return {
                "ok": False,
                "error": _friendly_api_error(response.get("error")),
                "fixtures": [],
                "league": league,
                "date": target_date,
            }

        fixtures = [_normalize_fixture(item, fallback_league=league) for item in _as_list(response.get("data"))]
        fixtures = [fixture for fixture in fixtures if fixture.get("fixture_id")]
        return {"ok": True, "error": None, "fixtures": fixtures, "league": league, "date": target_date}

    def get_best_games_today(self, limit: int = 3) -> str:
        candidates: list[dict[str, Any]] = []
        errors = []

        for league in self.get_supported_leagues():
            result = self.get_today_fixtures(league.key)
            if not result.get("ok"):
                errors.append(f"{league.label}: {result.get('error')}")
                continue
            for fixture in (result.get("fixtures") or [])[:4]:
                payload = self.build_fixture_advisor_payload(fixture.get("fixture_id"), include_players=False)
                if payload.get("error"):
                    continue
                advice = payload.get("advice") or {}
                main = advice.get("main_recommendation") or {}
                score = _confidence_score(main.get("confidence"), main.get("risk_level"))
                candidates.append(
                    {
                        "score": score,
                        "fixture": payload.get("fixture") or fixture,
                        "main": main,
                        "context": advice.get("context_summary") or {},
                        "verdict": advice.get("final_verdict"),
                    }
                )

        if not candidates:
            detail = "\n".join(f"- {error}" for error in errors[:4])
            return (
                "⭐ Jogos com Melhor Leitura\n\n"
                "Não encontrei jogos com dados suficientes para recomendar hoje.\n\n"
                f"{detail if detail else 'Tente novamente mais tarde ou escolha uma liga em Jogos de Hoje.'}"
            )

        candidates.sort(key=lambda item: item["score"], reverse=True)
        lines = ["⭐ Jogos com Melhor Leitura", "", "Top 3 leituras do dia:"]
        for index, item in enumerate(candidates[:limit], start=1):
            fixture = item["fixture"]
            main = item["main"]
            context_lines = (item.get("context") or {}).get("summary_lines") or []
            home = fixture.get("home_team") or "Mandante"
            away = fixture.get("away_team") or "Visitante"
            lines.extend(
                [
                    "",
                    f"{index}. {home} x {away}",
                    f"Melhor aposta: {main.get('selection')} ({main.get('market')})",
                    f"Contexto: {_join_context_lines(context_lines)}",
                    f"Odd justa: {main.get('fair_odd') or 'dados insuficientes'}",
                    f"Veredito: {item.get('verdict')}",
                ]
            )
        return "\n".join(lines)

    def build_fixture_analysis_card(self, fixture_id: int | str) -> str:
        payload = self.build_fixture_advisor_payload(fixture_id)
        if payload.get("error"):
            return str(payload["error"])
        return str(payload["advisor_text"])

    def build_fixture_analysis_by_name(self, fixture_name: str) -> dict[str, Any]:
        teams = _parse_fixture_name(fixture_name)
        if teams is None:
            return {
                "error": "Digite o jogo no formato Time A x Time B. Ex: Arsenal x Chelsea.",
            }

        home_query, away_query = teams
        if not self.client.api_key:
            return {
                "error": (
                    "Para buscar jogo por nome eu preciso da API-Football configurada. "
                    "Tambem da para usar Futebol > Jogos de Hoje e escolher pela lista."
                )
            }

        home_team = _first_team(self.client.get_team_by_name(home_query))
        if not home_team:
            return {"error": f"Nao encontrei o time {home_query} na API-Football."}

        fixture = self._find_fixture_between_teams(home_team["id"], home_query, away_query)
        if not fixture:
            return {
                "error": (
                    f"Nao consegui encontrar {home_query} x {away_query} nos proximos jogos das ligas suportadas.\n\n"
                    "Caminho mais confiavel: Futebol > Jogos de Hoje/Amanha > Liga > Jogo."
                )
            }

        return self.build_fixture_advisor_payload(fixture["fixture_id"])

    def build_fixture_advisor_payload(self, fixture_id: int | str, include_players: bool = True) -> dict[str, Any]:
        fixture_response = _cached_call(
            "api_football.fixture_by_id",
            120,
            lambda: self.client.get_fixture_by_id(fixture_id),
            fixture_id,
        )
        if not fixture_response.get("ok"):
            return {"error": _friendly_api_error(fixture_response.get("error"))}

        raw_fixtures = _as_list(fixture_response.get("data"))
        if not raw_fixtures:
            return {"error": "Não encontrei esse jogo na API-Football."}

        fixture = _normalize_fixture(raw_fixtures[0])
        if not fixture.get("home_team_id") or not fixture.get("away_team_id"):
            return {"error": "Encontrei o jogo, mas faltam dados dos times para analisar."}

        home_team_data = self._build_team_data(
            team_id=fixture["home_team_id"],
            team_name=fixture["home_team"],
            league_id=fixture["league_id"],
            season=fixture["season"],
            side="home",
        )
        away_team_data = self._build_team_data(
            team_id=fixture["away_team_id"],
            team_name=fixture["away_team"],
            league_id=fixture["league_id"],
            season=fixture["season"],
            side="away",
        )

        context = {
            "textual_summary": "Contexto básico com dados disponíveis da API-Football.",
            "fatigue_risk": INSUFFICIENT_DATA,
            "rotation_risk": INSUFFICIENT_DATA,
            "motivation_level": INSUFFICIENT_DATA,
            "alerts": ["confirme escalações antes de apostar"],
        }

        football_context = self._build_football_context(fixture)
        context["football_context"] = football_context
        context["alerts"] = (football_context.get("context_alerts") or []) + context["alerts"]

        home_analysis = self.analysis_service.analyze_team(home_team_data)
        away_analysis = self.analysis_service.analyze_team(away_team_data)
        matchup = self.analysis_service.analyze_matchup(home_team_data, away_team_data, context)
        betting_read = _build_betting_read(home_team_data, away_team_data)
        matchup["betting_read"] = betting_read["scenario"]
        matchup["watch_points"] = betting_read["watch_points"]
        fixture["quick_read"] = betting_read["scenario"]
        odds_response = OddsService().find_football_fixture_odds(
            fixture.get("league_id"),
            fixture.get("home_team") or "",
            fixture.get("away_team") or "",
        )
        odds = odds_response.get("data") if odds_response.get("ok") else []
        player_advice: dict[str, Any] = {}
        player_advice_text = "Jogadores interessantes\n\nUse o botao de jogadores para buscar stats individuais deste jogo."
        injuries_text = "Desfalques\n\nUse o botao de desfalques para buscar dados atualizados deste jogo."
        predictions: dict[str, Any] = {}
        lineups_confirmed = False
        if include_players:
            player_context = self.player_service.build_fixture_player_context(fixture)
            player_advice = self.player_advisor.advise_fixture_players(player_context)
            player_advice_text = format_fixture_player_advice(player_advice)
            injuries_text = self.player_advisor.format_injuries(player_context)
            predictions = player_context.predictions
            lineups_confirmed = bool(player_advice.get("lineups_confirmed", False))

        card_text = generate_pre_match_card(
            {
                "fixture": fixture,
                "home_team_data": home_team_data,
                "away_team_data": away_team_data,
                "context": context,
                "matchup_analysis": matchup,
                "odds": odds,
                "props": player_advice.get("recommendations") or [],
                "lineups_confirmed": lineups_confirmed,
            }
        )
        fixture_data = {
            "fixture": fixture,
            "home_team_data": home_team_data,
            "away_team_data": away_team_data,
            "context": context,
            "matchup_analysis": matchup,
            "odds": odds,
            "props": player_advice.get("recommendations") or [],
            "player_advice": player_advice,
            "predictions": predictions,
            "lineups_confirmed": lineups_confirmed,
            "football_context": football_context,
        }
        advice = BetAdvisorService().advise_fixture_bets(fixture_data)
        if not odds and odds_response.get("error"):
            advice["odds_error"] = odds_response.get("error")
        advisor_text = format_bet_advisor_response(advice)
        return {
            "advisor_text": advisor_text,
            "card_text": card_text,
            "player_advice_text": player_advice_text,
            "injuries_text": injuries_text,
            "fixture": fixture,
            "advice": advice,
            "player_advice": player_advice,
        }

    def _build_football_context(self, fixture: dict[str, Any]) -> dict[str, Any]:
        league_id = fixture.get("league_id")
        season = fixture.get("season")
        standings_response = (
            _cached_call(
                "api_football.standings",
                900,
                lambda: self.client.get_standings(league_id, season),
                league_id,
                season,
            )
            if league_id and season
            else {"ok": False}
        )
        home_schedule_response = _cached_call(
            "api_football.team_next_fixtures",
            300,
            lambda: self.client.get_team_next_fixtures(fixture["home_team_id"], next_games=10),
            fixture["home_team_id"],
            10,
        )
        away_schedule_response = _cached_call(
            "api_football.team_next_fixtures",
            300,
            lambda: self.client.get_team_next_fixtures(fixture["away_team_id"], next_games=10),
            fixture["away_team_id"],
            10,
        )
        return self.football_context_service.build_context_summary(
            fixture=fixture,
            standings_response=standings_response,
            home_schedule_response=home_schedule_response,
            away_schedule_response=away_schedule_response,
        )

    def _find_fixture_between_teams(self, team_id: int, home_query: str, away_query: str) -> dict[str, Any] | None:
        for league in self.get_supported_leagues():
            response = self.client.get_team_next_fixtures(
                team_id,
                next_games=20,
                league_id=league.league_id,
                season=league.season,
            )
            if not response.get("ok"):
                continue
            for raw_fixture in _as_list(response.get("data")):
                fixture = _normalize_fixture(raw_fixture, fallback_league=league)
                home_name = str(fixture.get("home_team") or "")
                away_name = str(fixture.get("away_team") or "")
                if (
                    _team_name_matches(home_name, home_query)
                    and _team_name_matches(away_name, away_query)
                ) or (
                    _team_name_matches(home_name, away_query)
                    and _team_name_matches(away_name, home_query)
                ):
                    return fixture
        return None

    def _build_team_data(
        self,
        team_id: int,
        team_name: str,
        league_id: int,
        season: int,
        side: str,
    ) -> dict[str, Any]:
        stats_response = _cached_call(
            "api_football.team_home_away_stats",
            900,
            lambda: self.client.get_team_home_away_stats(team_id, league_id, season),
            team_id,
            league_id,
            season,
        )
        fixtures_response = _cached_call(
            "api_football.team_fixtures_last",
            300,
            lambda: self.client.get_team_fixtures(team_id, last=5, league_id=league_id, season=season),
            team_id,
            5,
            league_id,
            season,
        )

        recent_fixtures = _as_list(fixtures_response.get("data")) if fixtures_response.get("ok") else []
        recent_metrics = _recent_metrics_from_fixtures(recent_fixtures, team_id)

        stats = stats_response.get("data") if stats_response.get("ok") else {}
        if not isinstance(stats, dict):
            stats = {}

        goals = stats.get("goals") if isinstance(stats.get("goals"), dict) else {}
        goals_for = goals.get("for", {}) if isinstance(goals.get("for"), dict) else {}
        goals_against = goals.get("against", {}) if isinstance(goals.get("against"), dict) else {}

        data = {
            "id": team_id,
            "name": team_name,
            "side": side,
            "last_5_form": recent_metrics.get("last_5_form") or _last_form_chars(stats.get("form"), limit=5),
            "last_5_avg_scored": recent_metrics.get("avg_scored"),
            "last_5_avg_conceded": recent_metrics.get("avg_conceded"),
            "season_form": _last_form_chars(stats.get("form"), limit=12),
            "avg_scored": _nested_float(goals_for, "average", "total") or recent_metrics.get("avg_scored"),
            "avg_conceded": _nested_float(goals_against, "average", "total") or recent_metrics.get("avg_conceded"),
            "home_avg_scored": _nested_float(goals_for, "average", "home"),
            "home_avg_conceded": _nested_float(goals_against, "average", "home"),
            "away_avg_scored": _nested_float(goals_for, "average", "away"),
            "away_avg_conceded": _nested_float(goals_against, "average", "away"),
        }

        return data


def _normalize_fixture(raw: dict[str, Any], fallback_league: LeagueConfig | None = None) -> dict[str, Any]:
    fixture = raw.get("fixture") if isinstance(raw.get("fixture"), dict) else {}
    league = raw.get("league") if isinstance(raw.get("league"), dict) else {}
    teams = raw.get("teams") if isinstance(raw.get("teams"), dict) else {}
    home = teams.get("home") if isinstance(teams.get("home"), dict) else {}
    away = teams.get("away") if isinstance(teams.get("away"), dict) else {}

    return {
        "fixture_id": fixture.get("id") or raw.get("id"),
        "league_id": league.get("id") or (fallback_league.league_id if fallback_league else None),
        "league": league.get("name") or raw.get("league") or (fallback_league.label if fallback_league else None),
        "round": league.get("round") or raw.get("round"),
        "season": league.get("season") or (fallback_league.season if fallback_league else datetime.now().year),
        "fixture_date": fixture.get("date") or raw.get("date") or raw.get("fixture_date"),
        "status": _nested_get(fixture, "status", "short") or raw.get("status"),
        "home_team_id": home.get("id") or raw.get("home_team_id"),
        "away_team_id": away.get("id") or raw.get("away_team_id"),
        "home_team": home.get("name") or raw.get("home_team"),
        "away_team": away.get("name") or raw.get("away_team"),
    }


def _cached_call(namespace: str, ttl_seconds: int, factory, *parts: Any) -> dict[str, Any]:
    key = cache_key(namespace, *parts)
    return default_cache.get_or_set(key, ttl_seconds, factory)


def _format_selected_fixture_analysis(
    fixture: dict[str, Any],
    home_analysis: dict[str, Any],
    away_analysis: dict[str, Any],
    matchup: dict[str, Any],
    card_text: str,
) -> str:
    home = fixture.get("home_team") or "Mandante"
    away = fixture.get("away_team") or "Visitante"
    quick_read = fixture.get("quick_read") or []
    watch_points = matchup.get("watch_points") or []
    lines = [
        "ANÁLISE DO JOGO",
        f"{home} x {away}",
        f"Liga: {fixture.get('league') or INSUFFICIENT_DATA}",
        "",
        "Leitura do cenário",
        *_format_bullets(quick_read),
        "",
        "O que analisar antes de apostar",
        *_format_bullets(watch_points),
        "",
        card_text,
    ]
    return "\n".join(lines)


def _recent_metrics_from_fixtures(fixtures: list[dict[str, Any]], team_id: int) -> dict[str, Any]:
    form = []
    scored_values = []
    conceded_values = []

    for item in fixtures[:5]:
        teams = item.get("teams") if isinstance(item.get("teams"), dict) else {}
        goals = item.get("goals") if isinstance(item.get("goals"), dict) else {}
        home = teams.get("home") if isinstance(teams.get("home"), dict) else {}
        away = teams.get("away") if isinstance(teams.get("away"), dict) else {}

        is_home = str(home.get("id")) == str(team_id)
        is_away = str(away.get("id")) == str(team_id)
        if not is_home and not is_away:
            continue

        home_goals = _to_float(goals.get("home"))
        away_goals = _to_float(goals.get("away"))
        if home_goals is None or away_goals is None:
            continue

        scored = home_goals if is_home else away_goals
        conceded = away_goals if is_home else home_goals
        scored_values.append(scored)
        conceded_values.append(conceded)
        if scored > conceded:
            form.append("W")
        elif scored < conceded:
            form.append("L")
        else:
            form.append("D")

    return {
        "last_5_form": "".join(form) or None,
        "avg_scored": round(mean(scored_values), 2) if scored_values else None,
        "avg_conceded": round(mean(conceded_values), 2) if conceded_values else None,
    }


def _build_betting_read(
    home_team_data: dict[str, Any],
    away_team_data: dict[str, Any],
) -> dict[str, list[str]]:
    home_name = str(home_team_data.get("name") or "Mandante")
    away_name = str(away_team_data.get("name") or "Visitante")
    scenario = []
    watch_points = []

    home_scored = _to_float(home_team_data.get("home_avg_scored"))
    home_conceded = _to_float(home_team_data.get("home_avg_conceded"))
    away_scored = _to_float(away_team_data.get("away_avg_scored"))
    away_conceded = _to_float(away_team_data.get("away_avg_conceded"))
    home_last5_scored = _to_float(home_team_data.get("last_5_avg_scored"))
    home_last5_conceded = _to_float(home_team_data.get("last_5_avg_conceded"))
    away_last5_scored = _to_float(away_team_data.get("last_5_avg_scored"))
    away_last5_conceded = _to_float(away_team_data.get("last_5_avg_conceded"))
    home_form = _spaced_form(home_team_data.get("last_5_form"))
    away_form = _spaced_form(away_team_data.get("last_5_form"))

    if home_scored is not None and away_conceded is not None:
        combined = (home_scored + away_conceded) / 2
        if combined >= 1.6:
            scenario.append(
                f"O ponto mais claro é a produção do {home_name}: ele marca {home_scored:.2f} em casa, "
                f"enquanto o {away_name} sofre {away_conceded:.2f} fora. O jogo favorece olhar primeiro "
                "para mercados ligados ao mandante, como gol do time, empate anula/handicap ou props ofensivas."
            )
        elif combined <= 1.0:
            scenario.append(
                f"O ataque do {home_name} não mostra vantagem clara no recorte casa/fora: marca {home_scored:.2f}, "
                f"e o {away_name} sofre {away_conceded:.2f}. Esse cenário pede cautela em mercados de gols do mandante."
            )

    if away_scored is not None and home_conceded is not None:
        combined = (away_scored + home_conceded) / 2
        if combined >= 1.6:
            scenario.append(
                f"O {away_name} também tem caminho para produzir: marca {away_scored:.2f} fora e enfrenta um "
                f"{home_name} que sofre {home_conceded:.2f} em casa. Isso abre espaço para ambos marcam ou over, "
                "dependendo da odd."
            )
        elif combined <= 1.0:
            scenario.append(
                f"O ataque visitante não traz sinal forte: {away_name} marca {away_scored:.2f} fora e "
                f"{home_name} sofre {home_conceded:.2f} em casa. Evite forçar mercados pró-visitante sem confirmação."
            )

    if home_form != INSUFFICIENT_DATA or away_form != INSUFFICIENT_DATA:
        watch_points.append(
            f"Forma recente: {home_name} {home_form}; {away_name} {away_form}. Use isso como contexto, não como gatilho isolado."
        )
    if home_last5_scored is not None and home_last5_conceded is not None:
        watch_points.append(f"{home_name} nos últimos 5: média de {home_last5_scored:.2f} gols feitos e {home_last5_conceded:.2f} sofridos.")
    if away_last5_scored is not None and away_last5_conceded is not None:
        watch_points.append(f"{away_name} nos últimos 5: média de {away_last5_scored:.2f} gols feitos e {away_last5_conceded:.2f} sofridos.")
    if home_conceded is not None and home_conceded >= 1.2:
        watch_points.append(f"O {home_name} também concede em casa ({home_conceded:.2f}); cuidado com odds baixas em vitória seca.")
    if away_conceded is not None and away_conceded >= 2.0:
        watch_points.append(f"O {away_name} sofre bastante fora ({away_conceded:.2f}); confirme escalação defensiva antes de entrar contra ele.")

    watch_points.append("Compare a leitura com a odd: sem preço, não existe value; existe apenas hipótese de mercado.")
    watch_points.append("Confirme escalações, desfalques e rotação antes de transformar a análise em aposta.")

    if not scenario:
        scenario.append("Os recortes disponíveis não mostram vantagem estatística clara. Melhor esperar odds, escalações e dados de mercado.")

    return {"scenario": scenario[:3], "watch_points": watch_points[:4]}


def _format_bullets(items: list[str]) -> list[str]:
    if not items:
        return [f"- {INSUFFICIENT_DATA}"]
    return [f"- {item}" for item in items]


def _join_context_lines(lines: Any) -> str:
    if not isinstance(lines, list) or not lines:
        return "contexto indisponivel"
    cleaned = [str(line).strip() for line in lines[:2] if str(line).strip()]
    return " | ".join(cleaned) if cleaned else "contexto indisponivel"


def _parse_fixture_name(value: str) -> tuple[str, str] | None:
    match = re.search(r"(.+?)\s+x\s+(.+)", value.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    home = match.group(1).strip(" -:,.")
    away = match.group(2).strip(" -:,.")
    if not home or not away:
        return None
    return home, away


def _first_team(response: dict[str, Any]) -> dict[str, Any] | None:
    if not response.get("ok"):
        return None
    for item in _as_list(response.get("data")):
        team = item.get("team") if isinstance(item.get("team"), dict) else item
        team_id = team.get("id")
        name = team.get("name")
        if team_id and name:
            return {"id": int(team_id), "name": str(name)}
    return None


def _team_name_matches(api_name: str, query: str) -> bool:
    left = _compact_name(api_name)
    right = _compact_name(query)
    if not left or not right:
        return False
    return left == right or left in right or right in left


def _compact_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = re.sub(r"[^a-z0-9]+", " ", ascii_text.lower())
    aliases = {
        "man utd": "manchester united",
        "man united": "manchester united",
        "man city": "manchester city",
        "psg": "paris saint germain",
        "spurs": "tottenham",
        "inter": "inter milan",
    }
    compact = re.sub(r"\s+", " ", ascii_text).strip()
    return aliases.get(compact, compact)


def _confidence_score(confidence: Any, risk: Any) -> int:
    confidence_score = {"alta": 3, "média": 2, "media": 2, "baixa": 1}.get(str(confidence).lower(), 0)
    risk_penalty = {"baixo": 0, "médio": 1, "medio": 1, "alto": 2}.get(str(risk).lower(), 1)
    return confidence_score * 10 - risk_penalty


def _spaced_form(value: Any) -> str:
    form = _last_form_chars(value, limit=5)
    if not form:
        return INSUFFICIENT_DATA
    return " ".join(form)


def _as_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        nested = value.get("response")
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        return [value]
    return []


def _nested_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _nested_float(data: dict[str, Any], *keys: str) -> float | None:
    return _to_float(_nested_get(data, *keys))


def _last_form_chars(value: Any, limit: int = 5) -> str | None:
    if not isinstance(value, str):
        return None
    chars = [char.upper() for char in value if char.upper() in {"W", "D", "L", "V", "E"}]
    if not chars:
        return None
    return "".join(chars[-limit:])


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None
    return None


def _friendly_api_error(error: Any) -> str:
    detail = str(error or "").strip()
    if not detail:
        return "Não consegui buscar dados na API-Football agora. Tente novamente em instantes."

    lower = detail.lower()
    if "requests" in lower and "minute" in lower:
        return "A API-Football recusou por limite de requisições por minuto. Aguarde um pouco e tente novamente."
    if "subscription" in lower or "plan" in lower:
        return f"A API-Football recusou a requisição por plano/assinatura: {detail}"
    if "account" in lower or "key" in lower or "token" in lower or "credential" in lower:
        return f"A API-Football recusou a credencial: {detail}"
    if "http 401" in lower or "http 403" in lower:
        return f"A API-Football recusou a autorização: {detail}"
    if "http 429" in lower:
        return f"A API-Football recusou por limite de uso: {detail}"

    return f"Não consegui buscar dados na API-Football. Detalhe: {detail}"
