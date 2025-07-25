import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
)
from datetime import datetime, timedelta
import pytz
import logging
import threading
from flask import Flask

# 🔧 Configurações
BOT_TOKEN = os.getenv("BOT_TOKEN", "8219603341:AAHsqUktaC5IIEtI8aehyPZtDrrKHWpeZOQ")
API_KEY = os.getenv("API_KEY", "cadc8d2e9944e5f78dc45bf26ab7a3fa")
API_FOOTBALL_TOKEN = os.getenv("API_FOOTBALL_TOKEN", "cadc8d2e9944e5f78dc45bf26ab7a3fa")
PORT = int(os.environ.get("PORT", 10000))

API_BASE = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_FOOTBALL_TOKEN}

logging.basicConfig(level=logging.INFO)
flask_app = Flask(__name__)

# ⏰ Converter UTC para BRT
def get_time_brt(utc_str):
    dt = datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%S%z")
    brt = pytz.timezone("America/Sao_Paulo")
    return dt.astimezone(brt).strftime("%H:%M")

# 🔘 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔝 Prognósticos do Dia", callback_data='best_tips')],
        [InlineKeyboardButton("🏆 Principais Campeonatos", callback_data='main_leagues')],
        [InlineKeyboardButton("🌍 Ligas por Continente", callback_data='by_continent')],
        [InlineKeyboardButton("⏱️ Todos os Jogos do Dia", callback_data='all_games')],
        [InlineKeyboardButton("🗓️ Jogos de Amanhã", callback_data='tomorrow_games')],
    ]
    await update.message.reply_text(
        "*\u26bd Bem-vindo ao ProGol AI Bot!*\n\nEscolha uma opção abaixo:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ⚖️ Jogos do dia com estatísticas reais
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    try:
        if data == 'start':
            return await start(update, context)

        elif data == 'best_tips':
            today = datetime.now().strftime('%Y-%m-%d')
            url = f"{API_BASE}/fixtures?date={today}&next=3"
            res = requests.get(url, headers=HEADERS).json()
            jogos = res.get("response", [])
            if not jogos:
                await query.edit_message_text("Nenhum prognóstico disponível hoje.")
                return
            texto = "*\ud83c\udf1f Prognósticos do Dia:*\n"
            for j in jogos:
                h = j["teams"]["home"]["name"]
                a = j["teams"]["away"]["name"]
                dt = get_time_brt(j["fixture"]["date"])
                texto += f"{dt} - {h} x {a}\nSugestão: +1.5 gols ou Ambas Marcam\n\n"
            await query.edit_message_text(texto, parse_mode="Markdown")

        elif data == 'main_leagues':
            ligas = [
                {"id": 71, "nome": "Brasileirão"},
                {"id": 39, "nome": "Premier League"},
                {"id": 140, "nome": "La Liga"},
                {"id": 135, "nome": "Serie A"},
                {"id": 78, "nome": "Bundesliga"}
            ]
            keyboard = [[InlineKeyboardButton(l["nome"], callback_data=f"liga_{l['id']}")] for l in ligas]
            keyboard.append([InlineKeyboardButton("\ud83d\udd19 Voltar", callback_data='start')])
            await query.edit_message_text("\ud83c\udfc6 Selecione um campeonato:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("liga_"):
            league_id = data.split("_")[1]
            url = f"{API_BASE}/fixtures?league={league_id}&season=2023&next=5"
            res = requests.get(url, headers=HEADERS).json()
            jogos = res.get("response", [])
            if not jogos:
                await query.edit_message_text("Sem jogos neste campeonato hoje.")
                return
            texto = "*\ud83c\udf0f Jogos:*\n\n"
            for j in jogos:
                h = j["teams"]["home"]["name"]
                a = j["teams"]["away"]["name"]
                dt = get_time_brt(j["fixture"]["date"])
                texto += f"{dt} - {h} x {a}\n"
            await query.edit_message_text(texto, parse_mode="Markdown")

        elif data == 'all_games':
            today = datetime.now().strftime('%Y-%m-%d')
            url = f"{API_BASE}/fixtures?date={today}&next=10"
            res = requests.get(url, headers=HEADERS).json()
            jogos = res.get("response", [])
            if not jogos:
                await query.edit_message_text("Nenhum jogo para hoje.")
                return
            texto = "*\ud83c\udf1f Todos os Jogos de Hoje:*\n\n"
            for j in jogos:
                h = j["teams"]["home"]["name"]
                a = j["teams"]["away"]["name"]
                dt = get_time_brt(j["fixture"]["date"])
                texto += f"{dt} - {h} x {a}\n"
            await query.edit_message_text(texto, parse_mode="Markdown")

        elif data == 'tomorrow_games':
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            url = f"{API_BASE}/fixtures?date={tomorrow}&next=10"
            res = requests.get(url, headers=HEADERS).json()
            jogos = res.get("response", [])
            if not jogos:
                await query.edit_message_text("Nenhum jogo para amanhã.")
                return
            texto = "*\ud83d\udd22 Jogos de Amanhã:*\n\n"
            for j in jogos:
                h = j["teams"]["home"]["name"]
                a = j["teams"]["away"]["name"]
                dt = get_time_brt(j["fixture"]["date"])
                texto += f"{dt} - {h} x {a}\n"
            await query.edit_message_text(texto, parse_mode="Markdown")

        else:
            await query.edit_message_text("Opção não reconhecida.")

    except Exception as e:
        logging.error(f"Erro: {e}")
        await query.edit_message_text("Erro interno ao processar.")

# 🚀 Inicializador

def iniciar_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

@flask_app.route('/')
def home():
    return "ProGol AI Bot online."

if __name__ == "__main__":
    bot_thread = threading.Thread(target=iniciar_bot)
    bot_thread.start()
    flask_app.run(host="0.0.0.0", port=PORT)
