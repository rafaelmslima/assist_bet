from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from app.bot.keyboards import main_menu_keyboard
from app.services.fixture_menu_service import FixtureMenuService


LEAGUE_PREFIX = "fixtures_league_"
TOMORROW_LEAGUE_PREFIX = "fixtures_tomorrow_league_"
ANALYZE_PREFIX = "fixture_analyze_"
CARD_PREFIX = "fixture_card_"
CARD_SKIP_PREFIX = "fixture_card_skip_"
PLAYERS_PREFIX = "fixture_players_"
INJURIES_PREFIX = "fixture_injuries_"
PLAYER_LEAGUE_PREFIX = "players_league_"
PLAYER_FIXTURE_PREFIX = "players_fixture_"
LIST_PREFIX = "fixtures_list:"
BACK_TO_LEAGUES = "fixtures_back"
BACK_TO_TOMORROW_LEAGUES = "fixtures_tomorrow_back"
BACK_TO_PLAYER_LEAGUES = "players_back"


async def show_leagues_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show supported football leagues for today's real fixture menu."""
    service = _get_service(context)
    text = (
        "Escolha uma liga para ver os jogos de hoje.\n\n"
        "Depois, selecione um jogo para gerar a analise principal."
    )
    keyboard = _build_league_keyboard(service, prefix=LEAGUE_PREFIX, day_offset=0)
    if keyboard is None:
        await _render_menu(update, "Nao encontrei jogos nas ligas suportadas para hoje.", None)
        return
    await _render_menu(update, text, keyboard)


async def show_tomorrow_leagues_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show supported football leagues for tomorrow's fixture menu."""
    service = _get_service(context)
    text = (
        "Escolha uma liga para ver os jogos de amanhã.\n\n"
        "Depois, selecione um jogo para gerar a analise principal."
    )
    keyboard = _build_league_keyboard(service, prefix=TOMORROW_LEAGUE_PREFIX, day_offset=1)
    if keyboard is None:
        await _render_menu(update, "Nao encontrei jogos nas ligas suportadas para amanha.", None)
        return
    await _render_menu(update, text, keyboard)


async def show_player_leagues_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show supported leagues for player shortlist flow."""
    service = _get_service(context)
    text = (
        "Escolha uma liga para ver os jogos de hoje.\n\n"
        "Depois, selecione um jogo para buscar jogadores interessantes com stats reais."
    )
    keyboard = _build_league_keyboard(service, prefix=PLAYER_LEAGUE_PREFIX, day_offset=0)
    if keyboard is None:
        await _render_menu(update, "Nao encontrei jogos nas ligas suportadas para hoje.", None)
        return
    await _render_menu(update, text, keyboard)


async def fixture_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle fixture league, analysis, player, injury and card callbacks."""
    query = update.callback_query
    if query is None or query.data is None:
        return

    await query.answer()
    data = query.data

    if data == BACK_TO_LEAGUES:
        await show_leagues_menu(update, context)
        return

    if data == BACK_TO_TOMORROW_LEAGUES:
        await show_tomorrow_leagues_menu(update, context)
        return

    if data == BACK_TO_PLAYER_LEAGUES:
        await show_player_leagues_menu(update, context)
        return

    if data.startswith(LIST_PREFIX):
        await _show_saved_fixture_list(update, context, data.removeprefix(LIST_PREFIX))
        return

    if data.startswith(LEAGUE_PREFIX):
        await _show_league_fixtures(update, context, data.removeprefix(LEAGUE_PREFIX), mode="analysis", day_offset=0)
        return

    if data.startswith(TOMORROW_LEAGUE_PREFIX):
        await _show_league_fixtures(
            update,
            context,
            data.removeprefix(TOMORROW_LEAGUE_PREFIX),
            mode="tomorrow_analysis",
            day_offset=1,
        )
        return

    if data.startswith(PLAYER_LEAGUE_PREFIX):
        await _show_league_fixtures(update, context, data.removeprefix(PLAYER_LEAGUE_PREFIX), mode="players", day_offset=0)
        return

    if data.startswith(ANALYZE_PREFIX):
        await _show_fixture_analysis(update, context, data.removeprefix(ANALYZE_PREFIX))
        return

    if data.startswith(PLAYER_FIXTURE_PREFIX):
        await _show_fixture_players(update, context, data.removeprefix(PLAYER_FIXTURE_PREFIX))
        return

    if data.startswith(PLAYERS_PREFIX):
        await _show_fixture_players(update, context, data.removeprefix(PLAYERS_PREFIX))
        return

    if data.startswith(INJURIES_PREFIX):
        await _show_fixture_injuries(update, context, data.removeprefix(INJURIES_PREFIX))
        return

    if data.startswith(CARD_SKIP_PREFIX):
        if query.message is not None:
            await _safe_edit_reply_markup(query.message, reply_markup=None)
        return

    if data.startswith(CARD_PREFIX):
        await _show_pre_match_card(update, context, data.removeprefix(CARD_PREFIX))
        return


async def _render_menu(update: Update, text: str, keyboard: InlineKeyboardMarkup | None) -> None:
    if update.callback_query is not None and update.callback_query.message is not None:
        await _safe_edit_text(update.callback_query.message, text, reply_markup=keyboard)
        return

    if update.message is not None:
        await update.message.reply_text(text, reply_markup=keyboard)


async def _show_league_fixtures(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    league_key: str,
    mode: str,
    day_offset: int = 0,
) -> None:
    query = update.callback_query
    if query is None or query.message is None:
        return

    service = _get_service(context)
    result = service.get_fixtures_for_day(league_key, day_offset=day_offset)
    league = result.get("league")
    league_label = getattr(league, "label", "liga selecionada")
    day_label = "amanhã" if day_offset == 1 else "hoje"

    if not result.get("ok"):
        await _safe_edit_text(
            query.message,
            f"{result.get('error')}\n\nLiga: {league_label}",
            reply_markup=_back_keyboard(mode),
        )
        return

    fixtures = result.get("fixtures") or []
    if not fixtures:
        await _safe_edit_text(
            query.message,
            f"Nao ha jogos de {day_label} para {league_label}.",
            reply_markup=_back_keyboard(mode),
        )
        return

    callback_prefix = ANALYZE_PREFIX if mode in {"analysis", "tomorrow_analysis"} else PLAYER_FIXTURE_PREFIX
    rows = []
    for fixture in fixtures[:12]:
        home = fixture.get("home_team") or "Mandante"
        away = fixture.get("away_team") or "Visitante"
        fixture_id = fixture.get("fixture_id")
        _cache_fixture_navigation(context, fixture_id, league_key, mode, day_offset)
        rows.append([InlineKeyboardButton(f"{home} x {away}", callback_data=f"{callback_prefix}{fixture_id}")])
    back_callback = _back_callback(mode)
    rows.append([InlineKeyboardButton("Voltar para ligas", callback_data=back_callback)])

    await _safe_edit_text(
        query.message,
        f"Jogos de {day_label} - {league_label}\n\nEscolha um jogo:",
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def _show_fixture_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, fixture_id: str) -> None:
    query = update.callback_query
    if query is None or query.message is None:
        return

    await _safe_edit_text(query.message, "Analisando jogo...")
    service = _get_service(context)
    payload = service.build_fixture_advisor_payload(fixture_id)
    if payload.get("error"):
        await _send_long_text(update, str(payload["error"]))
        return

    _cache_fixture_payload(context, fixture_id, payload)
    navigation = _fixture_navigation(context, fixture_id)
    back_button = _fixture_back_button(navigation)
    rows = [
        [InlineKeyboardButton("Ver jogadores interessantes", callback_data=f"{PLAYERS_PREFIX}{fixture_id}")],
        [InlineKeyboardButton("Ver desfalques", callback_data=f"{INJURIES_PREFIX}{fixture_id}")],
        [InlineKeyboardButton("Ver card completo", callback_data=f"{CARD_PREFIX}{fixture_id}")],
    ]
    if back_button:
        rows.append([back_button])
    rows.append([InlineKeyboardButton("Nao precisa", callback_data=f"{CARD_SKIP_PREFIX}{fixture_id}")])
    keyboard = InlineKeyboardMarkup(rows)
    await _send_long_text(update, str(payload["advisor_text"]), final_reply_markup=keyboard)


async def _show_fixture_players(update: Update, context: ContextTypes.DEFAULT_TYPE, fixture_id: str) -> None:
    cached = context.application.bot_data.get("fixture_players", {})
    player_text = cached.get(str(fixture_id))
    if not player_text:
        service = _get_service(context)
        payload = service.build_fixture_advisor_payload(fixture_id)
        if payload.get("error"):
            player_text = payload.get("error")
        else:
            _cache_fixture_payload(context, fixture_id, payload)
            player_text = payload.get("player_advice_text")
    await _send_long_text(update, str(player_text))


async def _show_fixture_injuries(update: Update, context: ContextTypes.DEFAULT_TYPE, fixture_id: str) -> None:
    cached = context.application.bot_data.get("fixture_injuries", {})
    injury_text = cached.get(str(fixture_id))
    if not injury_text:
        service = _get_service(context)
        payload = service.build_fixture_advisor_payload(fixture_id)
        if payload.get("error"):
            injury_text = payload.get("error")
        else:
            _cache_fixture_payload(context, fixture_id, payload)
            injury_text = payload.get("injuries_text")
    await _send_long_text(update, str(injury_text))


async def _show_pre_match_card(update: Update, context: ContextTypes.DEFAULT_TYPE, fixture_id: str) -> None:
    cached = context.application.bot_data.get("fixture_cards", {})
    card_text = cached.get(str(fixture_id))
    if not card_text:
        service = _get_service(context)
        payload = service.build_fixture_advisor_payload(fixture_id)
        if payload.get("error"):
            card_text = payload.get("error")
        else:
            _cache_fixture_payload(context, fixture_id, payload)
            card_text = payload.get("card_text")
    await _send_long_text(update, str(card_text))


async def _send_long_text(
    update: Update,
    text: str,
    final_reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    chat = update.effective_chat
    if chat is None:
        return

    chunks = _split_telegram_text(text)
    for index, chunk in enumerate(chunks):
        reply_markup = None
        if index == len(chunks) - 1:
            reply_markup = final_reply_markup or main_menu_keyboard()
        await chat.send_message(chunk, reply_markup=reply_markup)


def _cache_fixture_payload(context: ContextTypes.DEFAULT_TYPE, fixture_id: str, payload: dict) -> None:
    context.application.bot_data.setdefault("fixture_cards", {})[str(fixture_id)] = payload.get("card_text", "")
    context.application.bot_data.setdefault("fixture_players", {})[str(fixture_id)] = payload.get("player_advice_text", "")
    context.application.bot_data.setdefault("fixture_injuries", {})[str(fixture_id)] = payload.get("injuries_text", "")


def _cache_fixture_navigation(
    context: ContextTypes.DEFAULT_TYPE,
    fixture_id: str | int | None,
    league_key: str,
    mode: str,
    day_offset: int,
) -> None:
    if fixture_id in (None, ""):
        return
    context.application.bot_data.setdefault("fixture_navigation", {})[str(fixture_id)] = {
        "league_key": league_key,
        "mode": mode,
        "day_offset": day_offset,
    }


def _fixture_navigation(context: ContextTypes.DEFAULT_TYPE, fixture_id: str | int) -> dict | None:
    return context.application.bot_data.get("fixture_navigation", {}).get(str(fixture_id))


def _fixture_back_button(navigation: dict | None) -> InlineKeyboardButton | None:
    if not navigation:
        return None
    callback_data = f"{LIST_PREFIX}{navigation['mode']}:{navigation['day_offset']}:{navigation['league_key']}"
    return InlineKeyboardButton("Voltar para escolher outro jogo", callback_data=callback_data)


async def _show_saved_fixture_list(update: Update, context: ContextTypes.DEFAULT_TYPE, payload: str) -> None:
    try:
        mode, day_offset_text, league_key = payload.split(":", 2)
        day_offset = int(day_offset_text)
    except ValueError:
        await show_leagues_menu(update, context)
        return
    await _show_league_fixtures(update, context, league_key, mode=mode, day_offset=day_offset)


def _build_league_keyboard(
    service: FixtureMenuService,
    prefix: str,
    day_offset: int,
) -> InlineKeyboardMarkup | None:
    rows = []
    leagues = service.get_leagues_with_fixtures(day_offset=day_offset)
    if not leagues:
        return None
    for index in range(0, len(leagues), 2):
        row = [
            InlineKeyboardButton(league.label, callback_data=f"{prefix}{league.key}")
            for league in leagues[index : index + 2]
        ]
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def _back_keyboard(mode: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Voltar para ligas", callback_data=_back_callback(mode))]])


def _back_callback(mode: str) -> str:
    if mode == "players":
        return BACK_TO_PLAYER_LEAGUES
    if mode == "tomorrow_analysis":
        return BACK_TO_TOMORROW_LEAGUES
    return BACK_TO_LEAGUES


def _split_telegram_text(text: str, limit: int = 3800) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks = []
    current = []
    current_length = 0
    for line in text.splitlines():
        line_length = len(line) + 1
        if current and current_length + line_length > limit:
            chunks.append("\n".join(current))
            current = []
            current_length = 0
        current.append(line)
        current_length += line_length
    if current:
        chunks.append("\n".join(current))
    return chunks


async def _safe_edit_text(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except BadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


async def _safe_edit_reply_markup(
    message: Message,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    try:
        await message.edit_reply_markup(reply_markup=reply_markup)
    except BadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


def _get_service(context: ContextTypes.DEFAULT_TYPE) -> FixtureMenuService:
    service = context.application.bot_data.get("fixture_menu_service")
    if service is None:
        service = FixtureMenuService()
        context.application.bot_data["fixture_menu_service"] = service
    return service
