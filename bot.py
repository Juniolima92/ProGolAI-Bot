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

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "SEU_BOT_TOKEN_AQUI")
API_FOOTBALL_TOKEN = os.getenv("API_FOOTBALL_TOKEN", "SUA_API_FOOTBALL_KEY")
PORT = int(os.environ.get("PORT", 10000))

API_BASE = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_FOOTBALL_TOKEN
}

# Cache simples para estados de navegação por chat_id (pode ser melhorado)
chat_state = {}

def get_time_brt(utc_time_str):
    # Converte string UTC para horário de Brasil (BRT)
    utc_dt = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%S%z")
    brt_tz = pytz.timezone("America/Sao_Paulo")
    brt_dt = utc_dt.astimezone(brt_tz)
    return brt_dt.strftime("%d/%m %H:%M")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_state[chat_id] = "start"
    keyboard = [
        [InlineKeyboardButton("🏆 Principais Campeonatos", callback_data='main_leagues')],
        [InlineKeyboardButton("🌍 Ligas por Continente", callback_data='by_continent')],
        [InlineKeyboardButton("⏱️ Todos os Jogos do Dia", callback_data='all_games')],
    ]
    await update.message.reply_text(
        "⚽ Bem-vindo ao ProGol AI Bot!\nEscolha uma opção:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat.id
    await query.answer()

    data = query.data

    # Funções auxiliares para construir botões voltar
    def botao_voltar(voltar_para):
        return [InlineKeyboardButton("🔙 Voltar", callback_data=voltar_para)]

    try:
        if data == "start":
            chat_state[chat_id] = "start"
            keyboard = [
                [InlineKeyboardButton("🏆 Principais Campeonatos", callback_data='main_leagues')],
                [InlineKeyboardButton("🌍 Ligas por Continente", callback_data='by_continent')],
                [InlineKeyboardButton("⏱️ Todos os Jogos do Dia", callback_data='all_games')],
            ]
            await query.edit_message_text(
                "⚽ Bem-vindo ao ProGol AI Bot!\nEscolha uma opção:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data == "main_leagues":
            chat_state[chat_id] = "main_leagues"
            # Buscar ligas populares (exemplo fixo, pode buscar dinamicamente)
            ligas = [
                {"league_id": 71, "name": "Brasileirão"},
                {"league_id": 39, "name": "Premier League"},
                {"league_id": 140, "name": "La Liga"},
                {"league_id": 135, "name": "Serie A"},
                {"league_id": 78, "name": "Bundesliga"},
            ]
            keyboard = [[InlineKeyboardButton(liga["name"], callback_data=f"league_{liga['league_id']}")] for liga in ligas]
            keyboard.append(botao_voltar("start"))
            await query.edit_message_text(
                "🏆 Principais Campeonatos:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data.startswith("league_"):
            league_id = int(data.split("_")[1])
            chat_state[chat_id] = f"league_{league_id}"
            # Buscar jogos do dia para a liga
            url = f"{API_BASE}/fixtures?league={league_id}&season=2023&next=10"
            res = requests.get(url, headers=HEADERS).json()
            jogos = res.get("response", [])
            if not jogos:
                await query.edit_message_text("Nenhum jogo encontrado para este campeonato.")
                return
            keyboard = []
            for jogo in jogos:
                fixture = jogo["fixture"]
                home = jogo["teams"]["home"]["name"]
                away = jogo["teams"]["away"]["name"]
                dt = get_time_brt(fixture["date"])
                cb = f"match_{fixture['id']}"
                keyboard.append([InlineKeyboardButton(f"{dt} - {home} x {away}", callback_data=cb)])
            keyboard.append(botao_voltar("main_leagues"))
            await query.edit_message_text(
                f"Jogos próximos no campeonato {league_id}:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data.startswith("match_"):
            match_id = int(data.split("_")[1])
            chat_state[chat_id] = f"match_{match_id}"
            # Buscar estatísticas da partida
            url = f"{API_BASE}/fixtures/statistics?fixture={match_id}"
            res = requests.get(url, headers=HEADERS).json()
            stats = res.get("response", [])
            if not stats:
                await query.edit_message_text("Estatísticas não encontradas para este jogo.")
                return
            texto = f"📊 Estatísticas do jogo ID {match_id}:\n\n"
            # Exemplo: estatísticas básicas de posse e finalizações
            home_stats = stats[0]["statistics"]
            away_stats = stats[1]["statistics"]
            for stat in home_stats:
                tipo = stat["type"]
                home_val = stat["value"]
                away_val = next((x["value"] for x in away_stats if x["type"] == tipo), "N/A")
                texto += f"{tipo}: {home_val} x {away_val}\n"
            keyboard = [botao_voltar(f"league_{stats[0]['league']['id']}")]
            await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "by_continent":
            chat_state[chat_id] = "by_continent"
            continentes = [
                {"name": "Europa", "code": "EU"},
                {"name": "América do Sul", "code": "SA"},
                {"name": "Ásia", "code": "AS"},
                {"name": "África", "code": "AF"},
                {"name": "América do Norte", "code": "NA"},
                {"name": "Oceania", "code": "OC"},
            ]
            keyboard = [[InlineKeyboardButton(c["name"], callback_data=f"continent_{c['code']}")] for c in continentes]
            keyboard.append(botao_voltar("start"))
            await query.edit_message_text("🌍 Escolha um continente:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("continent_"):
            cont_code = data.split("_")[1]
            chat_state[chat_id] = f"continent_{cont_code}"
            # Buscar países do continente via API Football
            url = f"{API_BASE}/countries"
            res = requests.get(url, headers=HEADERS).json()
            countries = res.get("response", [])
            countries_cont = [c for c in countries if c["continent"] == cont_code]
            if not countries_cont:
                await query.edit_message_text("Nenhum país encontrado para este continente.")
                return
            keyboard = [[InlineKeyboardButton(c["name"], callback_data=f"country_{c['name']}")] for c in countries_cont]
            keyboard.append(botao_voltar("by_continent"))
            await query.edit_message_text(f"Países em {cont_code}:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("country_"):
            country_name = data.split("_", 1)[1]
            chat_state[chat_id] = f"country_{country_name}"
            # Buscar ligas do país
            url = f"{API_BASE}/leagues?country={country_name}&season=2023"
            res = requests.get(url, headers=HEADERS).json()
            leagues = res.get("response", [])
            if not leagues:
                await query.edit_message_text(f"Nenhuma liga encontrada para {country_name}.")
                return
            keyboard = [[InlineKeyboardButton(l["league"]["name"], callback_data=f"league_{l['league']['id']}")] for l in leagues]
            keyboard.append(botao_voltar("by_continent"))
            await query.edit_message_text(f"Ligas em {country_name}:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "all_games":
            chat_state[chat_id] = "all_games"
            # Buscar jogos do dia (próximos 20)
            url = f"{API_BASE}/fixtures?date={datetime.now().strftime('%Y-%m-%d')}&next=20"
            res = requests.get(url, headers=HEADERS).json()
            jogos = res.get("response", [])
            if not jogos:
                await query.edit_message_text("Nenhum jogo encontrado para hoje.")
                return
            keyboard = []
            for jogo in jogos:
                fixture = jogo["fixture"]
                home = jogo["teams"]["home"]["name"]
                away = jogo["teams"]["away"]["name"]
                dt = get_time_brt(fixture["date"])
                cb = f"match_{fixture['id']}"
                keyboard.append([InlineKeyboardButton(f"{dt} - {home} x {away}", callback_data=cb)])
            keyboard.append(botao_voltar("start"))
            await query.edit_message_text("🕒 Jogos do dia:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "tomorrow_games":
            chat_state[chat_id] = "tomorrow_games"
            # Buscar jogos de amanhã
            from datetime import timedelta
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            url = f"{API_BASE}/fixtures?date={tomorrow}&next=20"
            res = requests.get(url, headers=HEADERS).json()
            jogos = res.get("response", [])
            if not jogos:
                await query.edit_message_text("Nenhum jogo encontrado para amanhã.")
                return
            keyboard = []
            for jogo in jogos:
                fixture = jogo["fixture"]
                home = jogo["teams"]["home"]["name"]
                away = jogo["teams"]["away"]["name"]
                dt = get_time_brt(fixture["date"])
                cb = f"match_{fixture['id']}"
                keyboard.append([InlineKeyboardButton(f"{dt} - {home} x {away}", callback_data=cb)])
            keyboard.append(botao_voltar("start"))
            await query.edit_message_text("🗓️ Jogos de amanhã:", reply_markup=InlineKeyboardMarkup(keyboard))

        else:
            await query.edit_message_text("Opção inválida ou não implementada ainda.")

    except Exception as e:
        logging.error(f"Erro no callback handler: {e}")
        await query.edit_message_text("Ocorreu um erro interno. Tente novamente.")

def iniciar_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("
