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

# Configurações - sua chave API Football já inserida aqui
BOT_TOKEN = os.getenv("BOT_TOKEN", "8219603341:AAHsqUktaC5IIEtI8aehyPZtDrrKHWpeZOQ")
API_FOOTBALL_KEY = "cadc8d2e9944e5f78dc45bf26ab7a3fa"
API_FOOTBALL_HOST = "v3.football.api-sports.io"
HEADERS = {
    'x-apisports-key': API_FOOTBALL_KEY
}

logging.basicConfig(level=logging.INFO)

# Função para formatar data e hora em horário de São Paulo
def formatar_hora(data_str):
    dt = datetime.strptime(data_str, "%Y-%m-%dT%H:%M:%S%z")
    dt_sp = dt.astimezone(pytz.timezone("America/Sao_Paulo"))
    return dt_sp.strftime("%d/%m %H:%M")

# Busca jogos do dia atual
def obter_jogos_do_dia():
    url = f"https://{API_FOOTBALL_HOST}/fixtures?live=all&timezone=America/Sao_Paulo"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        logging.error(f"Erro API Football jogos ao vivo: {response.status_code}")
        return []
    dados = response.json()
    jogos = dados.get("response", [])
    return jogos

# Busca jogos agendados para amanhã
def obter_jogos_amanha():
    from datetime import date, timedelta
    dia_amanha = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    url = f"https://{API_FOOTBALL_HOST}/fixtures?date={dia_amanha}&timezone=America/Sao_Paulo"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        logging.error(f"Erro API Football jogos amanhã: {response.status_code}")
        return []
    dados = response.json()
    jogos = dados.get("response", [])
    return jogos

# Busca estatísticas e forma um texto de análise para apostadores
def analisar_jogo(fixture_id):
    url = f"https://{API_FOOTBALL_HOST}/fixtures/statistics?fixture={fixture_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        logging.error(f"Erro API Football estatísticas: {response.status_code}")
        return "Estatísticas indisponíveis no momento."

    dados = response.json()
    stats = dados.get("response", [])
    if not stats or len(stats) < 2:
        return "Estatísticas insuficientes para análise."

    home_stats = {item["type"]: item["value"] for item in stats[0].get("statistics", [])}
    away_stats = {item["type"]: item["value"] for item in stats[1].get("statistics", [])}

    texto = ""

    gols_casa = home_stats.get("Goals", "N/A")
    gols_fora = away_stats.get("Goals", "N/A")

    texto += f"⚽ Gols: Casa {gols_casa} x Visitante {gols_fora}\n"

    posse_casa = home_stats.get("Ball Possession", "N/A")
    posse_fora = away_stats.get("Ball Possession", "N/A")
    texto += f"🟢 Posse de bola: Casa {posse_casa} | Visitante {posse_fora}\n"

    final_casa = home_stats.get("Shots on Goal", "N/A")
    final_fora = away_stats.get("Shots on Goal", "N/A")
    texto += f"🎯 Finalizações no gol: Casa {final_casa} | Visitante {final_fora}\n"

    cart_casa = home_stats.get("Yellow Cards", 0)
    cart_fora = away_stats.get("Yellow Cards", 0)
    texto += f"🟨 Cartões amarelos: Casa {cart_casa} | Visitante {cart_fora}\n"

    texto += "\n🧠 Análise para apostas:\n"
    if posse_casa != "N/A" and posse_fora != "N/A" and final_casa != "N/A" and final_fora != "N/A":
        posse_casa_pct = int(posse_casa.strip('%'))
        posse_fora_pct = int(posse_fora.strip('%'))
        final_casa = int(final_casa)
        final_fora = int(final_fora)
        if posse_casa_pct > posse_fora_pct and final_casa > final_fora:
            texto += "- Favorito claro: time da casa controla o jogo e finaliza mais.\n"
            texto += "- Recomenda-se aposta em vitória do time da casa e over 1.5 gols.\n"
        elif posse_fora_pct > posse_casa_pct and final_fora > final_casa:
            texto += "- Favorito claro: visitante com mais posse e finalizações.\n"
            texto += "- Recomenda-se aposta em vitória do visitante e over 1.5 gols.\n"
        else:
            texto += "- Jogo equilibrado, com chances para ambos os lados.\n"
            texto += "- Recomenda-se cautela e considerar apostas em ambas marcam.\n"
    else:
        texto += "- Dados insuficientes para uma análise detalhada."

    return texto

def formatar_jogo_menu(jogo):
    data = formatar_hora(jogo["fixture"]["date"])
    casa = jogo["teams"]["home"]["name"]
    fora = jogo["teams"]["away"]["name"]
    return f"{data} - {casa} x {fora}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔝 Prognósticos do Dia", callback_data='best_tips')],
        [InlineKeyboardButton("🏆 Principais Campeonatos", callback_data='main_leagues')],
        [InlineKeyboardButton("🗓️ Jogos de Amanhã", callback_data='tomorrow_games')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "*⚽ Bem-vindo ao ProGol AI Bot!*\n\n"
        "Selecione uma opção para ver prognósticos reais baseados em dados atualizados.",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    logging.info(f"Callback recebido: {data}")

    if data == "best_tips":
        jogos = obter_jogos_do_dia()
        if not jogos:
            await query.edit_message_text("⚠️ Nenhum jogo ao vivo encontrado no momento.")
            return
        keyboard = []
        text = "*Jogos ao vivo para prognósticos:*\n"
        for jogo in jogos:
            jogo_text = formatar_jogo_menu(jogo)
            fixture_id = jogo["fixture"]["id"]
            keyboard.append([InlineKeyboardButton(jogo_text, callback_data=f"analisar_{fixture_id}")])
        keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="voltar")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "main_leagues":
        ligas = [
            "Brasileirão Série A",
            "Premier League",
            "La Liga",
            "Serie A",
            "Bundesliga"
        ]
        text = "*Principais Campeonatos:*\n\n" + "\n".join(ligas)
        keyboard = [[InlineKeyboardButton("⬅️ Voltar", callback_data="voltar")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "tomorrow_games":
        jogos = obter_jogos_amanha()
        if not jogos:
            await query.edit_message_text("⚠️ Nenhum jogo encontrado para amanhã.")
            return
        keyboard = []
        text = "*Jogos agendados para amanhã:*\n"
        for jogo in jogos:
            jogo_text = formatar_jogo_menu(jogo)
            fixture_id = jogo["fixture"]["id"]
            keyboard.append([InlineKeyboardButton(jogo_text, callback_data=f"analisar_{fixture_id}")])
        keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="voltar")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("analisar_"):
        fixture_id = int(data.split("_")[1])
        texto_analise = analisar_jogo(fixture_id)
        keyboard = [[InlineKeyboardButton("⬅️ Voltar", callback_data="best_tips")]]
        await query.edit_message_text(texto_analise, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "voltar":
        await start(update, context)

    else:
        await query.edit_message_text("⚠️ Opção não implementada.")

def iniciar_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    iniciar_bot()
