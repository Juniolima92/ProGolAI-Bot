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
API_FOOTBALL_TOKEN = os.getenv("API_FOOTBALL_TOKEN", "cadc8d2e9944e5f78dc45bf26ab7a3fa")
PORT = int(os.environ.get("PORT", 10000))
API_BASE = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_FOOTBALL_TOKEN
}

logging.basicConfig(level=logging.INFO)

# ⚽ Emojis por clube (parcial)
CLUB_COLORS = {
    "Botafogo": "⚫️", "Flamengo": "🔴",
    "Santos": "⚪️", "Palmeiras": "🟢",
    "Corinthians": "⚫️", "São Paulo": "🔴"
}

# 🌍 Emojis por país (parcial)
COUNTRY_FLAGS = {
    "Brazil": "🇧🇷", "England": "🇬🇧",
    "Spain": "🇪🇸", "Italy": "🇮🇹",
    "Germany": "🇩🇪", "France": "🇫🇷",
    "Argentina": "🇦🇷", "Portugal": "🇵🇹"
}

chat_state = {}

def get_time_brt(utc_time_str):
    utc_dt = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%S%z")
    brt_tz = pytz.timezone("America/Sao_Paulo")
    brt_dt = utc_dt.astimezone(brt_tz)
    return brt_dt.strftime("%d/%m %H:%M")

def botao_voltar(voltar_para):
    return [InlineKeyboardButton("🔙 Voltar", callback_data=voltar_para)]

# ✅ Função corrigida
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔝 Prognósticos do Dia", callback_data='best_tips')],
        [InlineKeyboardButton("🏆 Principais Campeonatos", callback_data='main_leagues')],
        [InlineKeyboardButton("🌍 Ligas por Continente", callback_data='by_continent')],
        [InlineKeyboardButton("⏱️ Todos os Jogos do Dia", callback_data='all_games')],
        [InlineKeyboardButton("🗓️ Jogos de Amanhã", callback_data='tomorrow_games')],
    ]

    mensagem = "⚽ *Bem-vindo ao ProGol AI Bot!*\n\nEscolha uma das opções abaixo para ver os jogos e prognósticos:"

    if update.message:
        await update.message.reply_text(
            mensagem,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            mensagem,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat.id

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
            if not jogos:
                await query.edit_message_text("Nenhum jogo encontrado.")
                return
            keyboard = []
            for j in jogos:
                fixture = j["fixture"]
                dt = get_time_brt(fixture["date"])
                home = j["teams"]["home"]["name"]
                away = j["teams"]["away"]["name"]
                emoji_home = CLUB_COLORS.get(home, "")
                emoji_away = CLUB_COLORS.get(away, "")
                keyboard.append([InlineKeyboardButton(f"{dt} {emoji_home} {home} x {away} {emoji_away}", callback_data=f"match_{fixture['id']}")])
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

        elif data == "by_continent":
            continentes = [
                ("Europa", "EU"), ("América do Sul", "SA"),
                ("Ásia", "AS"), ("África", "AF"),
                ("América do Norte", "NA"), ("Oceania", "OC")
            ]
            keyboard = [[InlineKeyboardButton(c[0], callback_data=f"continent_{c[1]}")] for c in continentes]
            keyboard.append(botao_voltar("start"))
            await query.edit_message_text("🌍 Escolha um continente:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("continent_"):
            cont = data.split("_")[1]
            url = f"{API_BASE}/countries"
            res = requests.get(url, headers=HEADERS).json()
            countries = [c for c in res.get("response", []) if c["continent"] == cont]
            keyboard = [[InlineKeyboardButton(f"{COUNTRY_FLAGS.get(c['name'], '')} {c['name']}", callback_data=f"country_{c['name']}")] for c in countries]
            keyboard.append(botao_voltar("by_continent"))
            await query.edit_message_text("🌐 Escolha um país:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("country_"):
            country = data.split("_", 1)[1]
            url = f"{API_BASE}/leagues?country={country}&season=2023"
            res = requests.get(url, headers=HEADERS).json()
            leagues = res.get("response", [])
            keyboard = [[InlineKeyboardButton(l["league"]["name"], callback_data=f"league_{l['league']['id']}")] for l in leagues]
            keyboard.append(botao_voltar("by_continent"))
            await query.edit_message_text(f"Ligas em {country}:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "all_games":
            hoje = datetime.now().strftime('%Y-%m-%d')
            url = f"{API_BASE}/fixtures?date={hoje}&next=20"
            res = requests.get(url, headers=HEADERS).json()
            jogos = res.get("response", [])
            keyboard = []
            for j in jogos:
                fixture = j["fixture"]
                dt = get_time_brt(fixture["date"])
                home = j["teams"]["home"]["name"]
                away = j["teams"]["away"]["name"]
                keyboard.append([InlineKeyboardButton(f"{dt} - {home} x {away}", callback_data=f"match_{fixture['id']}")])
            keyboard.append(botao_voltar("start"))
            await query.edit_message_text("📅 Jogos de hoje:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "tomorrow_games":
            dia = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            url = f"{API_BASE}/fixtures?date={dia}&next=20"
            res = requests.get(url, headers=HEADERS).json()
            jogos = res.get("response", [])
            keyboard = []
            for j in jogos:
                fixture = j["fixture"]
                dt = get_time_brt(fixture["date"])
                home = j["teams"]["home"]["name"]
                away = j["teams"]["away"]["name"]
                keyboard.append([InlineKeyboardButton(f"{dt} - {home} x {away}", callback_data=f"match_{fixture['id']}")])
            keyboard.append(botao_voltar("start"))
            await query.edit_message_text("🗓️ Jogos de amanhã:", reply_markup=InlineKeyboardMarkup(keyboard))

        else:
            await query.edit_message_text("⚠️ Opção inválida ou não implementada.")

    except Exception as e:
        logging.error(f"Erro: {e}")
        await query.edit_message_text("❌ Ocorreu um erro interno.")

# 🚀 Inicialização
def iniciar_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

# 🌐 Web para render
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "✅ ProGol AI Bot está rodando!"

if __name__ == "__main__":
    threading.Thread(target=iniciar_bot).start()
    flask_app.run(host="0.0.0.0", port=PORT)
