from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.bot.keyboards import (
    BTN_AVOID,
    BTN_BACK,
    BTN_BEST_GAMES,
    BTN_FOOTBALL,
    BTN_HELP,
    BTN_MY_BETS,
    BTN_NBA,
    BTN_NBA_BEST,
    BTN_SEARCH_GAME,
    BTN_SEARCH_PLAYER,
    BTN_SETTINGS,
    BTN_TODAY,
    BTN_TOMORROW,
    football_menu_keyboard,
    main_menu_keyboard,
    nba_menu_keyboard,
)
from app.services.recommendation_service import RecommendationService


CALLBACK_PREFIX = "rec:"
LEAGUE_PREFIX = "recleague:"


def _service(context: ContextTypes.DEFAULT_TYPE) -> RecommendationService:
    service = context.application.bot_data.get("recommendation_service")
    if service is None:
        service = RecommendationService()
        context.application.bot_data["recommendation_service"] = service
    return service


async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.message.text is None:
        return
    text = update.message.text
    if text == BTN_FOOTBALL:
        context.user_data["sport_menu"] = "football"
        await update.message.reply_text("Menu Futebol", reply_markup=football_menu_keyboard())
    elif text == BTN_NBA:
        context.user_data["sport_menu"] = "nba"
        await update.message.reply_text("Menu NBA", reply_markup=nba_menu_keyboard())
    elif text == BTN_BACK:
        context.user_data["sport_menu"] = None
        await update.message.reply_text("Menu principal.", reply_markup=main_menu_keyboard())
    elif text == BTN_TODAY:
        await _show_games(update, context, "today")
    elif text == BTN_TOMORROW:
        await _show_games(update, context, "tomorrow")
    elif text in {BTN_BEST_GAMES, BTN_NBA_BEST}:
        await _show_best(update, context)
    elif text == BTN_AVOID:
        await _show_avoid(update, context)
    elif text == BTN_SEARCH_GAME:
        await update.message.reply_text("Use Jogos de Hoje/Amanhã e escolha o jogo na lista.")
    elif text == BTN_SEARCH_PLAYER:
        await update.message.reply_text("Busca de jogador entra pela análise do jogo para evitar leitura fora de contexto.")
    elif text in {BTN_HELP, BTN_SETTINGS, BTN_MY_BETS}:
        await update.message.reply_text("Use /help, /status, /apostas, /roi e /resultado para essas ações.", reply_markup=main_menu_keyboard())


async def fixture_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return
    await query.answer()
    if query.data.startswith(LEAGUE_PREFIX):
        _, sport, when, league_name = query.data.split(":", 3)
        await _show_games_by_league(query, context, sport, when, league_name)
        return

    _, sport, when, fixture_id = query.data.split(":")
    fixtures = _service(context).list_games(sport, when)
    fixture = next((f for f in fixtures if str(f.get("fixture_id")) == str(fixture_id)), None)
    if not fixture:
        await query.edit_message_text("Não consegui localizar esse jogo.")
        return
    analysis = _service(context).analyze_fixture(sport, fixture)
    await query.edit_message_text(analysis["text"])


async def _show_games(update: Update, context: ContextTypes.DEFAULT_TYPE, when: str) -> None:
    if update.message is None:
        return
    sport = context.user_data.get("sport_menu", "football")
    fixtures = _service(context).list_games(sport, when)
    if not fixtures:
        await update.message.reply_text("Sem jogos para esse período.")
        return
    if sport == "football":
        leagues = sorted({str(f.get("league") or "Outras") for f in fixtures})
        rows = [[InlineKeyboardButton(lg, callback_data=f"{LEAGUE_PREFIX}{sport}:{when}:{lg}")] for lg in leagues[:20]]
        await update.message.reply_text("Escolha a liga/competição:", reply_markup=InlineKeyboardMarkup(rows))
        return
    rows = [
        [InlineKeyboardButton(f"{f.get('home_team')} x {f.get('away_team')}", callback_data=f"{CALLBACK_PREFIX}{sport}:{when}:{f.get('fixture_id')}")]
        for f in fixtures[:15]
    ]
    await update.message.reply_text("Escolha o jogo para análise completa:", reply_markup=InlineKeyboardMarkup(rows))


async def _show_games_by_league(query, context: ContextTypes.DEFAULT_TYPE, sport: str, when: str, league_name: str) -> None:
    fixtures = _service(context).list_games(sport, when)
    selected = [f for f in fixtures if str(f.get("league") or "") == league_name]
    if not selected:
        await query.edit_message_text(f"Sem jogos para {league_name} nesse período.")
        return
    rows = [
        [InlineKeyboardButton(f"{f.get('home_team')} x {f.get('away_team')}", callback_data=f"{CALLBACK_PREFIX}{sport}:{when}:{f.get('fixture_id')}")]
        for f in selected[:20]
    ]
    await query.edit_message_text(f"{league_name}\n\nEscolha o jogo para análise completa:", reply_markup=InlineKeyboardMarkup(rows))


async def _show_best(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    sport = context.user_data.get("sport_menu", "football")
    rows = _service(context).get_best_readings_today(sport, limit=5)
    if not rows:
        await update.message.reply_text("Sem leitura forte hoje.")
        return
    lines = ["🔥 Melhores leituras de hoje", ""]
    for idx, row in enumerate(rows, start=1):
        fixture = row["fixture"]
        rec = row["recommendation"]["main_recommendation"]
        lines.append(f"{idx}. {fixture.get('home_team')} x {fixture.get('away_team')}")
        lines.append(f"Leitura: {rec.get('selection')}")
        lines.append(f"Confiança: {row.get('confidence')} | Risco: {row.get('risk')}")
        lines.append("")
    await update.message.reply_text("\n".join(lines))


async def _show_avoid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    sport = context.user_data.get("sport_menu", "football")
    avoids = _service(context).get_games_to_avoid_today(sport, limit=5)
    if not avoids:
        await update.message.reply_text("Nenhum jogo crítico para evitar no momento.")
        return
    lines = ["🚫 Jogos que eu evitaria pré-jogo", ""]
    for idx, item in enumerate(avoids, start=1):
        fixture = item["fixture"]
        lines.append(f"{idx}. {fixture.get('home_team')} x {fixture.get('away_team')}")
        lines.append(f"Motivo: {item.get('reason')}")
        lines.append("")
    await update.message.reply_text("\n".join(lines))
