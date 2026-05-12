from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.intents import UserIntent
from app.bot.keyboards import main_menu_keyboard
from app.bot.state import clear_user_state, get_user_state
from app.services.fixture_menu_service import FixtureMenuService
from app.services.intent_service import Intent, IntentService


async def free_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free text after a user selected an intent or typed naturally."""
    if update.effective_user is None or update.effective_chat is None or update.message is None or update.message.text is None:
        return

    telegram_user_id = update.effective_user.id
    state = get_user_state(telegram_user_id)
    if state is None:
        await _handle_natural_language(update)
        return

    response = _build_intent_response(state.intent, update.message.text)
    clear_user_state(telegram_user_id)
    await _reply_long(update, response)


async def _handle_natural_language(update: Update) -> None:
    text = update.message.text or ""
    service = IntentService()
    intent = service.detect_intent(text)
    entities = service.extract_entities(text)
    route = service.route_intent(intent, entities, update.effective_user)

    if intent == Intent.ANALYZE_FIXTURE:
        fixture = entities.get("fixture") or text
        await _reply_long(update, _analyze_fixture_text(str(fixture)))
        return

    if intent == Intent.PRE_MATCH_CARD:
        await _reply_long(
            update,
            "O card foi integrado na analise inteligente do jogo. Envie o confronto no formato Time A x Time B ou use Futebol > Jogos de Hoje.",
        )
        return

    if intent == Intent.TOP_PROPS or intent == Intent.ANALYZE_PLAYER:
        await _reply_long(
            update,
            "Para jogadores, escolha Futebol > Jogadores do Jogo. Assim a leitura considera jogo, titulares, desfalques e matchup.",
        )
        return

    if intent in {Intent.ODDS, Intent.VALUE_BETTING, Intent.REGISTER_BET, Intent.LIST_BETS}:
        await _reply_long(
            update,
            "Essa versao agora e um analisador de futebol com IA. Envie Time A x Time B para receber roteiro do jogo, riscos e ideias qualitativas de mercados.",
        )
        return

    await update.message.reply_text(route.message, reply_markup=main_menu_keyboard())


def _build_intent_response(intent: UserIntent, text: str) -> str:
    if intent == UserIntent.ANALYZE_GAME:
        return _analyze_fixture_text(text)
    if intent == UserIntent.ANALYZE_TEAM:
        return "Analise isolada de time foi removida. A leitura mais util e pelo jogo: escolha Futebol > Jogos de Hoje/Amanha ou envie Time A x Time B."
    if intent == UserIntent.PRE_GAME_CARD:
        return _analyze_fixture_text(text)
    if intent == UserIntent.ANALYZE_PLAYER:
        return "Para jogador, escolha um jogo em Futebol > Jogadores do Jogo. Assim a analise considera matchup e provavel participacao."
    if intent == UserIntent.TOP_PROPS:
        return "Para ideias individuais, use Futebol > Jogadores do Jogo e escolha o confronto."

    return "Recebi sua mensagem. Escolha uma funcao no teclado para continuar."


def _analyze_fixture_text(text: str) -> str:
    payload = FixtureMenuService().build_fixture_analysis_by_name(text)
    if payload.get("error"):
        return str(payload["error"])
    return str(payload.get("advisor_text") or "Nao consegui gerar analise para esse jogo.")


async def _reply_long(update: Update, text: str, limit: int = 3800) -> None:
    if update.message is None:
        return
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
    chunks = chunks or [text]
    for index, chunk in enumerate(chunks):
        await update.message.reply_text(
            chunk,
            reply_markup=main_menu_keyboard() if index == len(chunks) - 1 else None,
        )
