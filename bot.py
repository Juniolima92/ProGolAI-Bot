import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
)
from datetime import datetime
import pytz
import logging
import threading
from flask import Flask

# 🔧 Configuração
BOT_TOKEN = os.getenv("BOT_TOKEN", "8219603341:AAHsqUktaC5IIEtI8aehyPZtDrrKHWpeZOQ")
API_KEY = os.getenv("API_KEY", "cadc8d2e9944e5f78dc45bf26ab7a3fa")
PORT = int(os.environ.get("PORT", 10000))

logging.basicConfig(level=logging.INFO)

# 🟡 Dicionário de cores por time
CLUB_COLORS = {
    "Botafogo": "⚫️", "Flamengo": "🔴",
    "Santos": "⚪️", "Palmeiras": "🟢",
    "Corinthians": "⚫️", "São Paulo": "🔴",
}

# 🟡 Traduções de nomes de clubes
def traduzir_nome(nome):
    traducoes = {
        "Flamengo RJ": "Flamengo",
        "Botafogo RJ": "Botafogo",
        "Palmeiras SP": "Palmeiras",
        "Santos SP": "Santos",
    }
    return traducoes.get(nome, nome)

# 🟡 Formatação dos jogos
def formatar_jogo(jogo):
    horario = datetime.fromtimestamp(jogo["timestamp"], pytz.timezone("America/Sao_Paulo")).strftime("%H:%M")
    home = traduzir_nome(jogo["home"])
    away = traduzir_nome(jogo["away"])
    emoji_home = CLUB_COLORS.get(home, "")
    emoji_away = CLUB_COLORS.get(away, "")
    return f"{horario} {emoji_home} {home} x {away} {emoji_away}"

# 🔵 Buscar jogos ao vivo
def obter_jogos_do_dia():
    url = f"https://api.b365api.com/v3/events/inplay?sport_id=1&token={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        jogos = response.json().get("results", [])
        jogos_ordenados = sorted(jogos, key=lambda x: x["time"])
        return jogos_ordenados
    else:
        return []

# 🔵 Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔝 Prognósticos do Dia", callback_data='best_tips')],
        [InlineKeyboardButton("🏆 Principais Campeonatos", callback_data='main_leagues')],
        [InlineKeyboardButton("🌍 Ligas por Continente", callback_data='by_continent')],
        [InlineKeyboardButton("⏱️ Todos os Jogos do Dia", callback_data='all_games')],
        [InlineKeyboardButton("🗓️ Jogos de Amanhã", callback_data='tomorrow_games')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "*⚽ Bem-vindo ao ProGol AI Bot!*\n\n"
        "Escolha uma das opções abaixo para ver os prognósticos e jogos com odds reais 👇",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# 🔵 Resposta aos botões
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'best_tips':
        await query.edit_message_text("🔝 Em breve: bilhetes com odds reais e análise por IA 🤖⚽")

    elif query.data == 'main_leagues':
        ligas = ["🇧🇷 Brasileirão", "🇬🇧 Premier League", "🇪🇸 La Liga", "🇮🇹 Serie A", "🇩🇪 Bundesliga"]
        texto = "*Principais Campeonatos:*\n" + "\n".join(ligas)
        await query.edit_message_text(texto, parse_mode="Markdown")

    elif query.data == 'by_continent':
        continentes = [
            [InlineKeyboardButton("🌍 Europa", callback_data='continent_europe')],
            [InlineKeyboardButton("🌎 América do Sul", callback_data='continent_south_america')],
            [InlineKeyboardButton("🌏 Ásia", callback_data='continent_asia')],
            [InlineKeyboardButton("🌍 África", callback_data='continent_africa')],
            [InlineKeyboardButton("🌎 América do Norte", callback_data='continent_north_america')],
            [InlineKeyboardButton("🌍 Oceania", callback_data='continent_oceania')],
        ]
        await query.edit_message_text("Escolha um continente:", reply_markup=InlineKeyboardMarkup(continentes))

    elif query.data == 'all_games':
        jogos = obter_jogos_do_dia()
        if not jogos:
            await query.edit_message_text("⚠️ Nenhum jogo encontrado no momento.")
        else:
            texto = "*🎯 Jogos de Hoje:*\n\n"
            for jogo in jogos[:20]:
                texto += formatar_jogo(jogo) + "\n"
            await query.edit_message_text(texto, parse_mode="Markdown")

    elif query.data == 'tomorrow_games':
        await query.edit_message_text("📅 Em breve: jogos de amanhã com IA!")

    else:
        await query.edit_message_text("⚠️ Opção ainda não implementada.")

# 🔄 Inicializador do bot (em thread separada)
def iniciar_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

# 🔌 Servidor Flask apenas para manter porta aberta no Render
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "✅ ProGol AI Bot está rodando!"

# 🔁 Executa o bot + servidor Flask
if __name__ == "__main__":
    bot_thread = threading.Thread(target=iniciar_bot)
    bot_thread.start()
    flask_app.run(host="0.0.0.0", port=PORT)
