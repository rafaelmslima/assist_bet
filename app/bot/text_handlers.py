from __future__ import annotations

from pydantic import ValidationError
from telegram import Update
from telegram.ext import ContextTypes

from app.bot.betting_handlers import build_betting_dashboard_message
from app.bot.intents import UserIntent
from app.bot.keyboards import main_menu_keyboard
from app.bot.state import clear_user_state, get_user_state
from app.database.repository import get_or_create_user
from app.database.session import SessionLocal
from app.schemas.bet import BetCreate
from app.services.betting_service import BettingService
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

    if state.intent == UserIntent.REGISTER_BET:
        registered = await _handle_register_bet(update)
        if registered:
            clear_user_state(telegram_user_id)
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

    if intent == Intent.LIST_BETS:
        await update.message.reply_text(
            build_betting_dashboard_message(update),
            reply_markup=main_menu_keyboard(),
        )
        return

    if intent == Intent.ANALYZE_FIXTURE:
        fixture = entities.get("fixture") or text
        await _reply_long(update, _analyze_fixture_text(str(fixture)))
        return

    if intent == Intent.PRE_MATCH_CARD:
        await _reply_long(
            update,
            "O card separado foi unificado na analise do jogo. Envie o confronto no formato Time A x Time B ou use Futebol > Jogos de Hoje.",
        )
        return

    if intent == Intent.TOP_PROPS:
        await _reply_long(
            update,
            "Para props reais, use Futebol > Jogadores do Dia ou NBA > Jogadores do Dia. Assim eu uso o jogo escolhido e evito inventar linha.",
        )
        return

    if intent == Intent.ODDS:
        await _reply_long(
            update,
            "Odds agora entram dentro da analise do jogo. Envie Time A x Time B ou escolha o jogo pelo menu para eu comparar leitura esportiva com preco.",
        )
        return

    if intent == Intent.VALUE_BETTING:
        await _reply_long(
            update,
            "Value betting foi integrado na analise completa. Sem jogo e mercado reais, o calculo vira chute. Escolha um jogo pelo menu ou envie Time A x Time B.",
        )
        return

    if intent == Intent.ANALYZE_PLAYER:
        await _reply_long(
            update,
            "Analise de jogador agora depende do jogo e da provavel participacao. Use Futebol > Jogadores do Dia ou NBA > Jogadores do Dia.",
        )
        return

    if intent == Intent.REGISTER_BET:
        if "|" in text:
            registered = await _handle_register_bet(update)
            if registered:
                return
        await update.message.reply_text(
            route.message,
            reply_markup=main_menu_keyboard(),
        )
        return

    await update.message.reply_text(route.message, reply_markup=main_menu_keyboard())


async def _handle_register_bet(update: Update) -> bool:
    if update.effective_user is None or update.effective_chat is None:
        return False

    text = update.message.text or ""
    parts = [part.strip() for part in text.split("|")]

    if len(parts) != 6:
        await update.message.reply_text(
            "Formato invalido. Envie assim:\n"
            "jogo | mercado | selecao | odd | stake | motivo",
            reply_markup=main_menu_keyboard(),
        )
        return False

    fixture_name, market, selection, odd_text, stake_text, reason = parts
    try:
        odd = float(odd_text.replace(",", "."))
        stake = float(stake_text.replace(",", "."))
    except (ValueError, ValidationError):
        await update.message.reply_text(
            "Odd e stake precisam ser numeros. Ex: Arsenal x Chelsea | vencedor | Arsenal | 1.80 | 50 | motivo",
            reply_markup=main_menu_keyboard(),
        )
        return False

    with SessionLocal() as db:
        user = get_or_create_user(
            db,
            telegram_user_id=update.effective_user.id,
            chat_id=update.effective_chat.id,
            first_name=update.effective_user.first_name,
            username=update.effective_user.username,
        )
        try:
            payload = BetCreate(
                user_id=user.id,
                sport="unknown",
                league=None,
                fixture_name=fixture_name,
                market=market,
                selection=selection,
                odd=odd,
                stake=stake,
                reason=reason,
                status="open",
            )
        except ValidationError:
            await update.message.reply_text(
                "Odd deve ser maior que 1 e stake maior que 0.",
                reply_markup=main_menu_keyboard(),
            )
            return False

        BettingService(db).track_bet(payload)

    await update.message.reply_text(
        "Aposta registrada com sucesso.",
        reply_markup=main_menu_keyboard(),
    )
    return True


def _build_intent_response(intent: UserIntent, text: str) -> str:
    if intent == UserIntent.ANALYZE_GAME:
        return _analyze_fixture_text(text)
    if intent == UserIntent.ANALYZE_TEAM:
        return "Analise isolada de time foi removida. A leitura mais util e pelo jogo: escolha Futebol > Jogos de Hoje/Amanha ou envie Time A x Time B."
    if intent == UserIntent.PRE_GAME_CARD:
        return "Card pre-jogo foi unificado na analise completa. Envie o jogo no formato Time A x Time B."
    if intent == UserIntent.ANALYZE_PLAYER:
        return "Para jogador, escolha um jogo em Futebol > Jogadores do Dia ou NBA > Jogadores do Dia. Assim a analise considera matchup e minutos."
    if intent == UserIntent.TOP_PROPS:
        return "Para props reais, use Futebol > Jogadores do Dia ou NBA > Jogadores do Dia e escolha o jogo."
    if intent == UserIntent.VIEW_ODDS:
        return "Odds agora aparecem dentro da analise completa do jogo. Envie Time A x Time B ou escolha pelo menu."
    if intent == UserIntent.VALUE_BETTING:
        return "Value betting foi integrado na analise do jogo. Primeiro escolha um confronto para eu estimar probabilidade, odd justa e edge."

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
