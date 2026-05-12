from __future__ import annotations

from dataclasses import dataclass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.bot.keyboards import main_menu_keyboard


FIRST_STEP = 1
FINAL_STEP = 5
_TUTORIAL_PROGRESS: dict[int, int] = {}


@dataclass(frozen=True)
class TutorialStep:
    title: str
    body: str
    example: str | None = None


TUTORIAL_STEPS: dict[int, TutorialStep] = {
    1: TutorialStep(
        "Boas-vindas",
        "Bem-vindo ao Analisador Inteligente de Futebol.\n\n"
        "O bot usa dados da API-Football e IA para explicar como um jogo tende a acontecer.",
    ),
    2: TutorialStep(
        "Escolher jogo",
        "Fluxo recomendado:\n"
        "- Futebol\n"
        "- Jogos de Hoje ou Jogos de Amanha\n"
        "- Liga\n"
        "- Jogo\n\n"
        "Voce tambem pode digitar um confronto diretamente.",
        "Arsenal x Chelsea",
    ),
    3: TutorialStep(
        "O que a IA entrega",
        "A analise vem em formato de roteiro:\n"
        "- ideia geral\n"
        "- como o jogo deve comecar\n"
        "- como muda com gol cedo\n"
        "- matchups importantes\n"
        "- riscos da leitura",
    ),
    4: TutorialStep(
        "Ideias de apostas",
        "As apostas agora aparecem como ideias qualitativas de mercado.\n\n"
        "O bot pode apontar gols, gol de um time, ambas marcam, escanteios, cartoes ou mercados a evitar, mas sem tratar isso como certeza.",
    ),
    5: TutorialStep(
        "Pronto",
        "Use a analise como apoio: confirme escalacoes, desfalques e contexto final antes de apostar.\n\n"
        "A melhor leitura e aquela que entende o jogo, nao apenas um numero solto.",
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
        await query.edit_message_text("Tutorial encerrado. Use o menu abaixo para continuar.", reply_markup=None)
        if query.message:
            await query.message.reply_text("Menu principal:", reply_markup=main_menu_keyboard())
        return

    if data == "tutorial_menu":
        if user_id is not None:
            _TUTORIAL_PROGRESS.pop(user_id, None)
        await query.edit_message_text("Perfeito. Menu principal liberado.", reply_markup=None)
        if query.message:
            await query.message.reply_text("Escolha uma funcao:", reply_markup=main_menu_keyboard())
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
            [InlineKeyboardButton("Nao", callback_data="tutorial_menu")],
        ]
    )


def _tutorial_keyboard(step: int) -> InlineKeyboardMarkup:
    if step == FIRST_STEP:
        return InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Proximo", callback_data="tutorial_step_2")],
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
                InlineKeyboardButton("Proximo", callback_data=f"tutorial_step_{step + 1}"),
            ],
            [InlineKeyboardButton("Sair", callback_data="tutorial_exit")],
        ]
    )
