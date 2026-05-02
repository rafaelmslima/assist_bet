from __future__ import annotations

from dataclasses import dataclass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.bot.keyboards import main_menu_keyboard


FIRST_STEP = 1
FINAL_STEP = 9
_TUTORIAL_PROGRESS: dict[int, int] = {}


@dataclass(frozen=True)
class TutorialStep:
    title: str
    body: str
    example: str | None = None


TUTORIAL_STEPS: dict[int, TutorialStep] = {
    1: TutorialStep(
        "Boas-vindas",
        "Bem-vindo ao Assistente de Apostas.\n\n"
        "Este bot te ajuda a analisar jogos, jogadores e encontrar apostas com mais valor.\n\n"
        "Você pode usar os botões ou digitar comandos.",
    ),
    2: TutorialStep(
        "Analisar Jogo",
        "O botão 📊 Analisar Jogo permite avaliar um confronto completo entre dois times.\n\n"
        "O bot analisa:\n"
        "- forma recente\n"
        "- casa vs fora\n"
        "- matchup\n"
        "- contexto do jogo",
        "Arsenal x Chelsea",
    ),
    3: TutorialStep(
        "Analisar Time",
        "O botão 🏟️ Analisar Time mostra o desempenho geral de um time.\n\n"
        "Inclui:\n"
        "- últimos jogos\n"
        "- força ofensiva\n"
        "- força defensiva\n"
        "- desempenho em casa e fora",
        "Arsenal",
    ),
    4: TutorialStep(
        "Jogadores e Props",
        "Você pode analisar jogadores para mercados específicos.\n\n"
        "Botões:\n"
        "👤 Analisar Jogador\n"
        "🔥 Top Props\n\n"
        "Mostra média, tendência, consistência e risco.",
        "Arsenal finalizações",
    ),
    5: TutorialStep(
        "Odds e Value Betting",
        "O bot te ajuda a identificar apostas com valor.\n\n"
        "Botões:\n"
        "💰 Ver Odds\n"
        "🧠 Value Betting\n\n"
        "Explica probabilidade implícita, probabilidade estimada e edge.",
        "Odd 1.80 -> 55% implícito\nEstimado 62% -> VALUE",
    ),
    6: TutorialStep(
        "Card Pré-Jogo",
        "O 🧾 Card Pré-Jogo reúne a análise em um só lugar.\n\n"
        "Inclui forma, casa/fora, contexto, odds, sugestões e alertas.",
        "Arsenal x Chelsea",
    ),
    7: TutorialStep(
        "Registrar Apostas",
        "Você pode registrar e acompanhar suas apostas.\n\n"
        "Botão:\n"
        "➕ Registrar Aposta\n\n"
        "Formato:\n"
        "jogo | mercado | seleção | odd | stake | motivo",
        "Arsenal x Chelsea | finalizações | Saka over 2.5 | 1.85 | 50 | bom matchup",
    ),
    8: TutorialStep(
        "Acompanhamento",
        "Veja seu desempenho com 📈 Minhas Apostas.\n\n"
        "Inclui histórico, lucro/prejuízo e ROI.",
    ),
    9: TutorialStep(
        "Pronto",
        "Você está pronto para usar o bot.\n\n"
        "Dica: sempre analise contexto e odds antes de apostar.",
    ),
}


async def start_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else None
    if user_id is not None:
        _TUTORIAL_PROGRESS[user_id] = FIRST_STEP

    text, keyboard = render_tutorial_step(FIRST_STEP)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
        return

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)


async def tutorial_step_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    user_id = update.effective_user.id if update.effective_user else None
    data = query.data or ""

    if data == "tutorial_exit":
        if user_id is not None:
            _TUTORIAL_PROGRESS.pop(user_id, None)
        await query.edit_message_text(
            "Tutorial encerrado. Use o menu abaixo para continuar.",
            reply_markup=None,
        )
        if query.message:
            await query.message.reply_text("Menu principal:", reply_markup=main_menu_keyboard())
        return

    if data == "tutorial_menu":
        if user_id is not None:
            _TUTORIAL_PROGRESS.pop(user_id, None)
        await query.edit_message_text("Perfeito. Menu principal liberado.", reply_markup=None)
        if query.message:
            await query.message.reply_text("Escolha uma função:", reply_markup=main_menu_keyboard())
        return

    if data == "tutorial_restart":
        step = FIRST_STEP
    else:
        try:
            step = int(data.replace("tutorial_step_", ""))
        except ValueError:
            step = FIRST_STEP

    step = max(FIRST_STEP, min(FINAL_STEP, step))
    if user_id is not None:
        _TUTORIAL_PROGRESS[user_id] = step

    text, keyboard = render_tutorial_step(step)
    await query.edit_message_text(text, reply_markup=keyboard)


def render_tutorial_step(step: int) -> tuple[str, InlineKeyboardMarkup]:
    step_data = TUTORIAL_STEPS.get(step, TUTORIAL_STEPS[FIRST_STEP])
    text = f"{step}/{FINAL_STEP} - {step_data.title}\n\n{step_data.body}"
    if step_data.example:
        text += f"\n\nExemplo:\n{step_data.example}"

    return text, _tutorial_keyboard(step)


def start_tutorial_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Sim", callback_data="tutorial_step_1")],
            [InlineKeyboardButton("Não", callback_data="tutorial_menu")],
        ]
    )


def _tutorial_keyboard(step: int) -> InlineKeyboardMarkup:
    if step == FIRST_STEP:
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Próximo", callback_data="tutorial_step_2")],
                [InlineKeyboardButton("Sair", callback_data="tutorial_exit")],
            ]
        )

    if step == FINAL_STEP:
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Ir para Menu", callback_data="tutorial_menu")],
                [InlineKeyboardButton("Reiniciar Tutorial", callback_data="tutorial_restart")],
            ]
        )

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Voltar", callback_data=f"tutorial_step_{step - 1}"),
                InlineKeyboardButton("Próximo", callback_data=f"tutorial_step_{step + 1}"),
            ],
            [InlineKeyboardButton("Sair", callback_data="tutorial_exit")],
        ]
    )
