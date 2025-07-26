import os
import requests
import logging
import threading
import pytz
from datetime import datetime, timedelta
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

# 🔧 Configuração de variáveis
BOT_TOKEN = os.getenv("BOT_TOKEN", "8219603341:AAHsqUktaC5IIEtI8aehyPZtDrrKHWpeZOQ")
API_KEY = os.getenv("API_KEY", "cadc8d2e9944e5f78dc45bf26ab7a3fa")
PORT = int(os.environ.get("PORT", 10000))
API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# 📊 Emojis por clube
CLUB_COLORS = {
    "Botafogo": "⚫️", "Flamengo": "🔴", "Santos": "⚪️", "Palmeiras": "🟢",
    "Corinthians": "⚫️", "São Paulo": "🔴"
}

# 🌍 Emojis por país
COUNTRY_FLAGS = {
    "Brazil": "🇧🇷", "England": "🇬🇧", "Spain": "🇪🇸", "Italy": "🇮🇹",
    "Germany": "🇩🇪", "France": "🇫🇷", "Argentina": "🇦🇷", "Portugal": "🇵🇹"
}

# ⏰ Conversão de horário
def get_time_brt(utc_time_str):
    utc_dt = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%S%z")
    brt_tz = pytz.timezone("America/Sao_Paulo")
    return utc_dt.astimezone(brt_tz).strftime("%H:%M")

# 🔙 Botão voltar
def botao_voltar(callback):
    return [InlineKeyboardButton("🔙 Voltar", callback_data=callback)]

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔝 Prognósticos do Dia", callback_data='best_tips')],
        [InlineKeyboardButton("🏆 Principais Campeonatos", callback_data='main_leagues')],
        [InlineKeyboardButton("🌍 Ligas por Continente", callback_data='by_continent')],
        [InlineKeyboardButton("⏱️ Todos os Jogos do Dia", callback_data='all_games')],
        [InlineKeyboardButton("🗓️ Jogos de Amanhã", callback_data='tomorrow_games')],
    ]
    await update.message.reply_text(
        "⚽ *Bem-vindo ao ProGol AI Bot!*\n\nEscolha uma das opções abaixo:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# 🔘 Botões do menu
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    try:
        if data == "start":
            await start(update, context)

        elif data == "best_tips":
            texto = "🌟 *Bilhete do Dia (Baseado em Estatísticas)*\n\n"
            texto += "➡️ Palmeiras x São Paulo – +1.5 Gols\n"
            texto += "➡️ Atlético-MG x Cruzeiro – Ambas Marcam\n"
            texto += "➡️ Flamengo x Vasco – +8.5 Escanteios\n\n"
            texto += "🔹 Odds ilustrativas\n🧠 Baseado em padrões estatísticos reais"
            await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([botao_voltar("start")]))

        elif data == "main_leagues":
            ligas = [
                {"id": 71, "name": "Brasileirão", "flag": "🇧🇷"},
                {"id": 39, "name": "Premier League", "flag": "🇬🇧"},
                {"id": 140, "name": "La Liga", "flag": "🇪🇸"},
                {"id": 135, "name": "Serie A", "flag": "🇮🇹"},
                {"id": 78, "name": "Bundesliga", "flag": "🇩🇪"},
            ]
            keyboard = [[InlineKeyboardButton(f"{liga['flag']} {liga['name']}", callback_data=f"league_{liga['id']}")] for liga in ligas]
            keyboard.append(botao_voltar("start"))
            await query.edit_message_text("🏆 *Principais Campeonatos:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("league_"):
            league_id = int(data.split("_")[1])
            url = f"{API_BASE}/fixtures?league={league_id}&season=2023&next=10"
            res = requests.get(url, headers=HEADERS).json()
            jogos = res.get("response", [])
            keyboard = []
            for j in jogos:
                dt = get_time_brt(j["fixture"]["date"])
                home = j["teams"]["home"]["name"]
                away = j["teams"]["away"]["name"]
                emoji_home = CLUB_COLORS.get(home, "")
                emoji_away = CLUB_COLORS.get(away, "")
                keyboard.append([InlineKeyboardButton(f"{dt} {emoji_home} {home} x {away} {emoji_away}", callback_data=f"match_{j['fixture']['id']}")])
            keyboard.append(botao_voltar("main_leagues"))
            await query.edit_message_text("🕹️ *Jogos Próximos:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("match_"):
            match_id = int(data.split("_")[1])
            url = f"{API_BASE}/fixtures/statistics?fixture={match_id}"
            res = requests.get(url, headers=HEADERS).json()
            stats = res.get("response", [])
            if not stats:
                await query.edit_message_text("Sem estatísticas para esta partida.")
                return
            home_stats = stats[0]["statistics"]
            away_stats = stats[1]["statistics"]
            texto = "📊 *Estatísticas:*\n\n"
            for stat in home_stats:
                tipo = stat["type"]
                val_home = stat["value"]
                val_away = next((x["value"] for x in away_stats if x["type"] == tipo), "N/A")
                texto += f"{tipo}: {val_home} x {val_away}\n"
            await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([botao_voltar("main_leagues")]))

        elif data == "all_games":
            hoje = datetime.now().strftime('%Y-%m-%d')
            url = f"{API_BASE}/fixtures?date={hoje}&next=20"
            res = requests.get(url, headers=HEADERS).json()
            jogos = res.get("response", [])
            keyboard = []
            for j in jogos:
                dt = get_time_brt(j["fixture"]["date"])
                home = j["teams"]["home"]["name"]
                away = j["teams"]["away"]["name"]
                keyboard.append([InlineKeyboardButton(f"{dt} - {home} x {away}", callback_data=f"match_{j['fixture']['id']}")])
            keyboard.append(botao_voltar("start"))
            await query.edit_message_text("📅 Jogos de hoje:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "tomorrow_games":
            dia = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            url = f"{API_BASE}/fixtures?date={dia}&next=20"
            res = requests.get(url, headers=HEADERS).json()
            jogos = res.get("response", [])
            keyboard = []
            for j in jogos:
                dt = get_time_brt(j["fixture"]["date"])
                home = j["teams"]["home"]["name"]
                away = j["teams"]["away"]["name"]
                keyboard.append([InlineKeyboardButton(f"{dt} - {home} x {away}", callback_data=f"match_{j['fixture']['id']}")])
            keyboard.append(botao_voltar("start"))
            await query.edit_message_text("🗓️ Jogos de amanhã:", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        logging.error(f"Erro interno: {e}")
        await query.edit_message_text("❌ Erro interno ao processar sua solicitação.")

# 🌐 Webserver para manter online no Render
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ ProGol AI Bot rodando com sucesso!"

# 🚀 Inicializador
def rodar_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()

if __name__ == "__main__":
    threading.Thread(target=rodar_bot).start()
    flask_app.run(host="0.0.0.0", port=PORT)
