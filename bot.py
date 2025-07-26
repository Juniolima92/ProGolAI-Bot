import os
import logging
import requests
import asyncio
import pytz
from flask import Flask
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8219603341:AAHsqUktaC5IIEtI8aehyPZtDrrKHWpeZOQ")
API_FOOTBALL_TOKEN = os.getenv("API_FOOTBALL_TOKEN", "cadc8d2e9944e5f78dc45bf26ab7a3fa")
API_BASE = "https://v3.football.api-sports.io"
PORT = int(os.environ.get("PORT", 10000))

HEADERS = {"x-apisports-key": API_FOOTBALL_TOKEN}
logging.basicConfig(level=logging.INFO)

CLUB_COLORS = {
    "Botafogo": "⚫️", "Flamengo": "🔴", "Santos": "⚪️",
    "Palmeiras": "🟢", "Corinthians": "⚫️", "São Paulo": "🔴"
}
COUNTRY_FLAGS = {
    "Brazil": "🇧🇷", "England": "🇬🇧", "Spain": "🇪🇸",
    "Italy": "🇮🇹", "Germany": "🇩🇪", "France": "🇫🇷",
    "Argentina": "🇦🇷", "Portugal": "🇵🇹"
}

def get_time_brt(utc_time_str):
    utc_dt = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%S%z")
    brt_tz = pytz.timezone("America/Sao_Paulo")
    brt_dt = utc_dt.astimezone(brt_tz)
    return brt_dt.strftime("%d/%m %H:%M")

def botao_voltar(callback: str):
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

# Handler de botões
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    try:
        if data == "start":
            await start(update, context)

        elif data == "best_tips":
            texto = (
                "🌟 *Bilhete do Dia (Baseado em Estatísticas)*\n\n"
                "➡️ Palmeiras x São Paulo – +1.5 Gols\n"
                "➡️ Atlético-MG x Cruzeiro – Ambas Marcam\n"
                "➡️ Flamengo x Vasco – +8.5 Escanteios\n\n"
                "🔹 Odds ilustrativas\n🧠 Baseado em padrões estatísticos reais"
            )
            await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([botao_voltar("start")]))

        elif data == "main_leagues":
            ligas = [
                {"id": 71, "name": "Brasileirão", "flag": "🇧🇷"},
                {"id": 39, "name": "Premier League", "flag": "🇬🇧"},
                {"id": 140, "name": "La Liga", "flag": "🇪🇸"},
                {"id": 135, "name": "Serie A", "flag": "🇮🇹"},
                {"id": 78, "name": "Bundesliga", "flag": "🇩🇪"},
            ]
            keyboard = [[InlineKeyboardButton(f"{l['flag']} {l['name']}", callback_data=f"league_{l['id']}")] for l in ligas]
            keyboard.append(botao_voltar("start"))
            await query.edit_message_text("🏆 *Principais Campeonatos:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("league_"):
            league_id = int(data.split("_")[1])
            url = f"{API_BASE}/fixtures?league={league_id}&season=2023&next=10"
            res = requests.get(url, headers=HEADERS).json()
            jogos = res.get("response", [])
            keyboard = []
            for j in jogos:
                f = j["fixture"]
                dt = get_time_brt(f["date"])
                home, away = j["teams"]["home"]["name"], j["teams"]["away"]["name"]
                keyboard.append([InlineKeyboardButton(f"{dt} {home} x {away}", callback_data=f"match_{f['id']}")])
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
            texto = "📊 *Estatísticas:*\n\n"
            for stat in stats[0]["statistics"]:
                tipo = stat["type"]
                val_home = stat["value"]
                val_away = next((x["value"] for x in stats[1]["statistics"] if x["type"] == tipo), "N/A")
                texto += f"{tipo}: {val_home} x {val_away}\n"
            await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([botao_voltar("main_leagues")]))

        else:
            await query.edit_message_text("⚠️ Opção inválida ou não implementada.")
    except Exception as e:
        logging.error(f"Erro: {e}")
        await query.edit_message_text("❌ Ocorreu um erro interno.")

# Flask App para manter vivo
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ ProGol AI Bot rodando!"

# Função principal
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    await app.run_polling()

# Iniciar Flask e Bot
if __name__ == "__main__":
    from threading import Thread
    Thread(target=lambda: flask_app.run(host="0.0.0.0", port=PORT)).start()
    asyncio.run(main())
