from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.integrations.balldontlie_client import BalldontlieClient
from app.services.nba_player_advisor_service import NbaPlayerAdvisorService, format_nba_prop_advice
from app.services.nba_player_service import NbaPlayerService
from app.services.odds_service import OddsService


try:
    SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")
except ZoneInfoNotFoundError:
    SAO_PAULO_TZ = timezone(timedelta(hours=-3))


class NbaGameMenuService:
    """Lists NBA games and builds props-first advisor payloads."""

    def __init__(
        self,
        client: BalldontlieClient | None = None,
        player_service: NbaPlayerService | None = None,
        advisor_service: NbaPlayerAdvisorService | None = None,
    ) -> None:
        self.client = client or BalldontlieClient()
        self.player_service = player_service or NbaPlayerService(self.client)
        self.advisor_service = advisor_service or NbaPlayerAdvisorService()

    def get_today_games(self) -> dict[str, Any]:
        return self.get_games_for_day(day_offset=0)

    def get_tomorrow_games(self) -> dict[str, Any]:
        return self.get_games_for_day(day_offset=1)

    def get_games_for_day(self, day_offset: int = 0) -> dict[str, Any]:
        target_date = (datetime.now(SAO_PAULO_TZ).date() + timedelta(days=day_offset)).isoformat()
        response = self.client.get_games_by_date(target_date)
        if not response.get("ok"):
            return {"ok": False, "error": _friendly_error(response.get("error")), "games": [], "date": target_date}

        games = [_normalize_game(item) for item in _as_list(response.get("data"))]
        games = [game for game in games if game.get("game_id")]
        return {"ok": True, "error": None, "games": games, "date": target_date}

    def build_game_advisor_payload(self, game_id: int | str) -> dict[str, Any]:
        game_response = self.client.get_game(game_id)
        if not game_response.get("ok"):
            return {"error": _friendly_error(game_response.get("error"))}

        raw = game_response.get("data")
        game = _normalize_game(raw if isinstance(raw, dict) else (_as_list(raw)[0] if _as_list(raw) else {}))
        if not game.get("game_id"):
            return {"error": "Nao encontrei esse jogo na balldontlie."}

        context = self.player_service.build_game_player_context(game)
        odds = self._find_nba_prop_odds(game)
        advice = self.advisor_service.advise_game_props(context, odds=odds)
        return {
            "game": game,
            "advice": advice,
            "advisor_text": format_nba_prop_advice(advice),
        }

    def build_game_context_payload(self, game_id: int | str) -> dict[str, Any]:
        game_response = self.client.get_game(game_id)
        if not game_response.get("ok"):
            return {"error": _friendly_error(game_response.get("error"))}

        raw = game_response.get("data")
        game = _normalize_game(raw if isinstance(raw, dict) else (_as_list(raw)[0] if _as_list(raw) else {}))
        if not game.get("game_id"):
            return {"error": "Nao encontrei esse jogo na balldontlie."}

        home_context = self.client.get_team_home_away_stats(int(game["home_team_id"]))
        away_context = self.client.get_team_home_away_stats(int(game["visitor_team_id"]))
        home_stats = home_context.get("data") if home_context.get("ok") and isinstance(home_context.get("data"), dict) else {}
        away_stats = away_context.get("data") if away_context.get("ok") and isinstance(away_context.get("data"), dict) else {}
        text = _format_nba_game_context(game, home_stats, away_stats)
        return {"game": game, "advisor_text": text}

    def get_best_games_today(self, limit: int = 3) -> str:
        result = self.get_today_games()
        if not result.get("ok"):
            return f"🏀 Jogos com Melhor Leitura\n\n{result.get('error')}"

        candidates = []
        for game in (result.get("games") or [])[:8]:
            payload = self.build_game_advisor_payload(game["game_id"])
            if payload.get("error"):
                continue
            advice = payload.get("advice") or {}
            best = advice.get("best") or {}
            score = _confidence_score(best.get("confidence"), best.get("risk_level"))
            candidates.append({"score": score, "game": game, "best": best, "verdict": advice.get("final_verdict")})

        if not candidates:
            return "🏀 Jogos com Melhor Leitura\n\nNao encontrei props com dados suficientes hoje."

        candidates.sort(key=lambda item: item["score"], reverse=True)
        lines = ["🏀 Jogos com Melhor Leitura", "", "Top leituras de props do dia:"]
        for index, item in enumerate(candidates[:limit], start=1):
            game = item["game"]
            best = item["best"]
            lines.extend(
                [
                    "",
                    f"{index}. {game.get('visitor_team')} @ {game.get('home_team')}",
                    f"Melhor prop: {best.get('player')} - {best.get('selection')}",
                    f"Confiança: {best.get('confidence')} | Risco: {best.get('risk_level')}",
                    f"Veredito: {item.get('verdict')}",
                ]
            )
        return "\n".join(lines)

    def _find_nba_prop_odds(self, game: dict[str, Any]) -> list[dict[str, Any]]:
        response = OddsService().find_nba_game_odds(
            game.get("home_team") or "",
            game.get("visitor_team") or "",
            markets="player_points,player_rebounds,player_assists,player_threes",
        )
        return response.get("data") if response.get("ok") else []


def _normalize_game(raw: dict[str, Any]) -> dict[str, Any]:
    home = raw.get("home_team") if isinstance(raw.get("home_team"), dict) else {}
    visitor = raw.get("visitor_team") if isinstance(raw.get("visitor_team"), dict) else {}
    return {
        "game_id": raw.get("id") or raw.get("game_id"),
        "date": raw.get("date"),
        "status": raw.get("status"),
        "home_team_id": home.get("id") or raw.get("home_team_id"),
        "visitor_team_id": visitor.get("id") or raw.get("visitor_team_id"),
        "home_team": home.get("full_name") or home.get("name") or raw.get("home_team"),
        "visitor_team": visitor.get("full_name") or visitor.get("name") or raw.get("visitor_team") or raw.get("away_team"),
        "home_team_score": raw.get("home_team_score"),
        "visitor_team_score": raw.get("visitor_team_score"),
    }


def _format_nba_game_context(game: dict[str, Any], home: dict[str, Any], away: dict[str, Any]) -> str:
    home_name = game.get("home_team") or "Mandante"
    away_name = game.get("visitor_team") or "Visitante"
    home_pf = _to_float(home.get("points_for_avg"))
    home_pa = _to_float(home.get("points_against_avg"))
    away_pf = _to_float(away.get("points_for_avg"))
    away_pa = _to_float(away.get("points_against_avg"))
    home_total = _to_float(home.get("game_total_avg"))
    away_total = _to_float(away.get("game_total_avg"))
    combined_total = _avg([value for value in (home_total, away_total) if value is not None])

    best_market = "sem entrada clara pré-jogo"
    reason = "os dados disponíveis ainda não apontam vantagem forte em total, spread ou lado."
    risks = ["confirmar status dos principais jogadores", "verificar linha e odds antes de entrar"]
    alternatives = ["esperar props após status dos titulares", "observar live nos primeiros minutos"]
    avoid = "moneyline/spread se a odd estiver espremida ou houver status indefinido."

    if combined_total is not None and combined_total >= 225:
        best_market = "Total de pontos - olhar over se a linha não estiver esticada"
        reason = "os recortes recentes sugerem ambiente de pontuação mais alto."
        alternatives = ["team total do ataque mais confiável", "props de pontos/bolas de 3 dos titulares"]
    elif combined_total is not None and combined_total <= 215:
        best_market = "Total de pontos - olhar under se a linha vier alta"
        reason = "os recortes recentes sugerem jogo mais controlado."
        alternatives = ["rebotes de pivôs/alas", "assistências de armadores com minutos seguros"]

    if home_pf is not None and away_pa is not None and (home_pf + away_pa) / 2 >= 116:
        alternatives.insert(0, f"team total do {home_name}")
    if away_pf is not None and home_pa is not None and (away_pf + home_pa) / 2 >= 116:
        alternatives.insert(0, f"team total do {away_name}")

    lines = [
        f"🏀 Contexto do jogo - {away_name} @ {home_name}",
        "",
        f"Melhor leitura: {best_market}",
        "",
        "Explicação:",
        f"- {reason}",
        f"- {home_name}: marca {_fmt(home_pf)} e sofre {_fmt(home_pa)} pontos no recorte recente.",
        f"- {away_name}: marca {_fmt(away_pf)} e sofre {_fmt(away_pa)} pontos no recorte recente.",
        "",
        "Riscos:",
        *[f"- {item}" for item in risks],
        "",
        "Alternativas:",
        *[f"- {item}" for item in alternatives[:3]],
        "",
        "Eu evitaria:",
        f"- {avoid}",
        "",
        "Veredito:",
        "Eu usaria essa leitura como direção inicial do jogo. Para entrada, preciso comparar com a linha real e status dos jogadores.",
        "",
        "Use como apoio de análise, não como garantia. Aposte com gestão de banca.",
    ]
    return "\n".join(lines)


def _as_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None
    return None


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _fmt(value: float | None) -> str:
    return f"{value:.1f}" if value is not None else "dados insuficientes"


def _friendly_error(error: Any) -> str:
    detail = str(error or "").strip()
    if not detail:
        return "Nao consegui buscar dados da NBA agora. Tente novamente em instantes."
    if "401" in detail or "403" in detail:
        return f"A balldontlie recusou a credencial/plano: {detail}"
    if "429" in detail:
        return f"A balldontlie recusou por limite de uso: {detail}"
    return f"Nao consegui buscar dados da NBA. Detalhe: {detail}"


def _confidence_score(confidence: Any, risk: Any) -> int:
    confidence_score = {"alta": 3, "media": 2, "média": 2, "baixa": 1}.get(str(confidence).lower(), 0)
    risk_penalty = {"baixo": 0, "medio": 1, "médio": 1, "alto": 2}.get(str(risk).lower(), 1)
    return confidence_score * 10 - risk_penalty
