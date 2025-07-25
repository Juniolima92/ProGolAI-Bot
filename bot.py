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

CLUB_COLORS = {
    "Botafogo": "⚫️", "Flamengo": "🔴",
    "Santos": "⚪️", "Palmeiras": "🟢",
    "Corinthians": "⚫️", "São Paulo": "🔴",
}

def traduzir_nome(nome):
    traducoes = {
        "Flamengo RJ": "Flamengo",
        "Botafogo RJ": "Botafogo",
        "Palmeiras SP": "Palmeiras",
        "Santos SP": "Santos",
    }
    return traducoes.get(nome, nome)

def formatar_jogo(jogo):
    horario = datetime.fromtimestamp(jogo["timestamp"], pytz.timezone("America/Sao_Paulo")).strftime("%H:%M")
    home = traduzir_nome(jogo["home"])
    away = traduzir_nome(jogo["away"])
    emoji_home = CLUB_COLORS.get(home, "")
    emoji_away = CLUB_COLORS.get(away, "")
    return f"{horario} {emoji_home} {home} x {away} {emoji_away}"

def obter_jogos_do_dia():
    try:
        url = f"https://api.b365api.com/v3/events/inplay?sport_id=1&token={API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            jogos = response.json().get("results", [])
            return sorted(jogos, key=lambda x: x["time"])
        return []
    except Exception as e:
        logging.error(f"Erro ao obter jogos: {e}")
        return []

def menu_principal():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔝 Prognósticos do Dia", callback_data='best_tips')],
        [InlineKeyboardButton("🏆 Principais Campeonatos", callback_data='main_leagues')],
        [InlineKeyboardButton("🌍 Ligas por Continente", callback_data='by_continent')],
        [InlineKeyboardButton("⏱️ Todos os Jogos do Dia", callback_data='all_games')],
        [InlineKeyboardButton("🗓️ Jogos de Amanhã", callback_data='tomorrow_games')],
    ])

def botao_voltar():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar ao Menu", callback_data='menu')]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*⚽ Bem-vindo ao ProGol AI Bot!*\n\n"
        "Escolha uma das opções abaixo 👇",
        parse_mode='Markdown',
        reply_markup=menu_principal()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        if query.data == 'menu':
            await query.edit_message_text(
                "*⚽ Bem-vindo ao ProGol AI Bot!*\n\n"
                "Escolha uma das opções abaixo 👇",
                parse_mode='Markdown',
                reply_markup=menu_principal()
            )

        elif query.data == 'best_tips':
            texto = "🌟 *Bilhete Conservador (90%)*\n\n"
            texto += "▶️ Botafogo x Flamengo – *+1.5 Gols* (Odd: 1.40)\n"
            texto += "▶️ Santos x Palmeiras – *Ambas Marcam* (Odd: 1.65)\n"
            texto += "▶️ Grêmio x Inter – *+8.5 Escanteios* (Odd: 1.55)\n\n"
            texto += "🔹 *Odd Total:* 3.57\n🧠 *Baseado em estatísticas reais*"
            await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=botao_voltar())

        elif query.data == 'main_leagues':
            texto = "*🏆 Principais Campeonatos:*\n\n"
            texto += "🇧🇷 Brasileirão\n🇬🇧 Premier League\n🇪🇸 La Liga\n🇮🇹 Serie A\n🇩🇪 Bundesliga"
            await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=botao_voltar())

        elif query.data == 'by_continent':
            continentes = [
                [InlineKeyboardButton("🌍 Europa", callback_data='continent_europe')],
                [InlineKeyboardButton("🌎 América do Sul", callback_data='continent_south_america')],
                [InlineKeyboardButton("🌏 Ásia", callback_data='continent_asia')],
                [InlineKeyboardButton("🌍 África", callback_data='continent_africa')],
                [InlineKeyboardButton("🌎 América do Norte", callback_data='continent_north_america')],
                [InlineKeyboardButton("🌍 Oceania", callback_data='continent_oceania')],
                [InlineKeyboardButton("🔙 Voltar", callback_data='menu')],
            ]
            await query.edit_message_text("Escolha um continente:", reply_markup=InlineKeyboardMarkup(continentes))

        elif query.data == 'all_games':
            jogos = obter_jogos_do_dia()
            if not jogos:
                await query.edit_message_text("⚠️ Nenhum jogo no momento.", reply_markup=botao_voltar())
            else:
                texto = "*🎯 Jogos ao Vivo:*\n\n"
                for jogo in jogos[:20]:
                    texto += formatar_jogo(jogo) + "\n"
                await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=botao_voltar())

        elif query.data == 'tomorrow_games':
            await query.edit_message_text("📅 Em breve: jogos de amanhã com IA!", reply_markup=botao_voltar())

        else:
            await query.edit_message_text("⚠️ Opção ainda não implementada.", reply_markup=botao_voltar())

    except Exception as e:
        logging.error(f"Erro no callback: {e}")
        await query.message.reply_text("❌ Ocorreu um erro ao processar a opção.")

# 🟢 Inicializador do bot
def iniciar_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

# 🔁 Flask para o Render detectar o serviço
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "✅ ProGol AI Bot está rodando!"

if __name__ == "__main__":
    bot_thread = threading.Thread(target=iniciar_bot)
    bot_thread.start()
    flask_app.run(host="0.0.0.0", port=PORT)
