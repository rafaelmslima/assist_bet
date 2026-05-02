from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from app.bot.keyboards import nba_menu_keyboard
from app.services.nba_game_menu_service import NbaGameMenuService


NBA_GAMES = "nba_games"
NBA_TOMORROW_GAMES = "nba_tomorrow_games"
NBA_PLAYERS = "nba_players"
NBA_GAME_PREFIX = "nba_game_"
NBA_PLAYER_GAME_PREFIX = "nba_player_game_"
NBA_LIST_PREFIX = "nba_list_"


async def show_nba_games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_games(update, context, title="Jogos de hoje - NBA", day_offset=0)


async def show_nba_tomorrow_games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_games(update, context, title="Jogos de amanhã - NBA", day_offset=1)


async def show_nba_players_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_games(update, context, title="Jogadores do dia - NBA", day_offset=0)


async def nba_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return

    await query.answer()
    if query.data == NBA_GAMES:
        await show_nba_games_menu(update, context)
        return
    if query.data == NBA_TOMORROW_GAMES:
        await show_nba_tomorrow_games_menu(update, context)
        return
    if query.data == NBA_PLAYERS:
        await show_nba_players_menu(update, context)
        return
    if query.data.startswith(NBA_LIST_PREFIX):
        day_offset = int(query.data.removeprefix(NBA_LIST_PREFIX) or 0)
        title = "Jogos de amanhã - NBA" if day_offset == 1 else "Jogos de hoje - NBA"
        await _show_games(update, context, title=title, day_offset=day_offset)
        return
    if query.data.startswith(NBA_PLAYER_GAME_PREFIX):
        await _show_game_props(update, context, query.data.removeprefix(NBA_PLAYER_GAME_PREFIX))
        return
    if query.data.startswith(NBA_GAME_PREFIX):
        await _show_game_context(update, context, query.data.removeprefix(NBA_GAME_PREFIX))


async def _show_games(update: Update, context: ContextTypes.DEFAULT_TYPE, title: str, day_offset: int) -> None:
    service = _get_service(context)
    result = service.get_games_for_day(day_offset=day_offset)
    retry_callback = NBA_TOMORROW_GAMES if day_offset == 1 else NBA_GAMES

    is_player_flow = "Jogadores" in title
    text = f"{title}\n\nEscolha um jogo para eu analisar:"
    if not result.get("ok"):
        text = str(result.get("error"))
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Tentar de novo", callback_data=retry_callback)]])
    else:
        games = result.get("games") or []
        if not games:
            day_label = "amanhã" if day_offset == 1 else "hoje"
            text = f"Não encontrei jogos da NBA {day_label}."
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Tentar de novo", callback_data=retry_callback)]])
        else:
            rows = []
            callback_prefix = NBA_PLAYER_GAME_PREFIX if is_player_flow else NBA_GAME_PREFIX
            for game in games[:12]:
                _cache_nba_navigation(context, game.get("game_id"), day_offset, is_player_flow)
                rows.append(
                    [
                        InlineKeyboardButton(
                            f"{game.get('visitor_team')} @ {game.get('home_team')}",
                            callback_data=f"{callback_prefix}{game.get('game_id')}",
                        )
                    ]
                )
            keyboard = InlineKeyboardMarkup(rows)

    if update.callback_query is not None and update.callback_query.message is not None:
        await _safe_edit_text(update.callback_query.message, text, reply_markup=keyboard)
        return
    if update.message is not None:
        await update.message.reply_text(text, reply_markup=keyboard)


async def _show_game_context(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id: str) -> None:
    query = update.callback_query
    if query is None or query.message is None:
        return

    await _safe_edit_text(query.message, "Analisando contexto do jogo...")
    service = _get_service(context)
    payload = service.build_game_context_payload(game_id)
    text = payload.get("advisor_text") if not payload.get("error") else payload.get("error")
    day_offset = _nba_navigation(context, game_id).get("day_offset", 0)
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Ver jogadores interessantes", callback_data=f"{NBA_PLAYER_GAME_PREFIX}{game_id}")],
            [InlineKeyboardButton("Voltar para escolher outro jogo", callback_data=f"{NBA_LIST_PREFIX}{day_offset}")],
        ]
    )
    await _send_long_text(update, str(text), final_reply_markup=keyboard)


async def _show_game_props(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id: str) -> None:
    query = update.callback_query
    if query is None or query.message is None:
        return

    await _safe_edit_text(query.message, "Analisando props da NBA...")
    service = _get_service(context)
    payload = service.build_game_advisor_payload(game_id)
    text = payload.get("advisor_text") if not payload.get("error") else payload.get("error")
    day_offset = _nba_navigation(context, game_id).get("day_offset", 0)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Voltar para escolher outro jogo", callback_data=f"{NBA_LIST_PREFIX}{day_offset}")]])
    await _send_long_text(update, str(text), final_reply_markup=keyboard)


async def _send_long_text(
    update: Update,
    text: str,
    limit: int = 3800,
    final_reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    chunks = _split_telegram_text(text, limit)
    for index, chunk in enumerate(chunks):
        reply_markup = None
        if index == len(chunks) - 1:
            reply_markup = final_reply_markup or nba_menu_keyboard()
        await chat.send_message(chunk, reply_markup=reply_markup)


def _split_telegram_text(text: str, limit: int) -> list[str]:
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


def _get_service(context: ContextTypes.DEFAULT_TYPE) -> NbaGameMenuService:
    service = context.application.bot_data.get("nba_game_menu_service")
    if service is None:
        service = NbaGameMenuService()
        context.application.bot_data["nba_game_menu_service"] = service
    return service


def _cache_nba_navigation(
    context: ContextTypes.DEFAULT_TYPE,
    game_id: str | int | None,
    day_offset: int,
    is_player_flow: bool,
) -> None:
    if game_id in (None, ""):
        return
    context.application.bot_data.setdefault("nba_navigation", {})[str(game_id)] = {
        "day_offset": day_offset,
        "is_player_flow": is_player_flow,
    }


def _nba_navigation(context: ContextTypes.DEFAULT_TYPE, game_id: str | int) -> dict:
    return context.application.bot_data.get("nba_navigation", {}).get(str(game_id), {})
