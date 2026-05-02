from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Return the fixed main reply keyboard."""
    keyboard = [
        [KeyboardButton("⚽ Futebol"), KeyboardButton("🏀 NBA")],
        [KeyboardButton("📈 Minhas Apostas"), KeyboardButton("⚙️ Configurações")],
        [KeyboardButton("❓ Ajuda")],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Escolha um esporte",
    )


def football_menu_keyboard() -> ReplyKeyboardMarkup:
    """Return football-focused navigation."""
    keyboard = [
        [KeyboardButton("📅 Jogos de Hoje"), KeyboardButton("📆 Jogos de Amanhã")],
        [KeyboardButton("🔎 Buscar Jogo")],
        [KeyboardButton("⭐ Jogos com Melhor Leitura"), KeyboardButton("👟 Jogadores do Dia")],
        [KeyboardButton("⬅️ Voltar")],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Escolha uma opção de futebol",
    )


def nba_menu_keyboard() -> ReplyKeyboardMarkup:
    """Return NBA-focused navigation."""
    keyboard = [
        [KeyboardButton("🏀 Jogos de Hoje"), KeyboardButton("🏀 Jogos de Amanhã")],
        [KeyboardButton("🏀 Jogadores do Dia")],
        [KeyboardButton("🏀 Jogos com Melhor Leitura")],
        [KeyboardButton("⬅️ Voltar")],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Escolha uma opção de NBA",
    )
