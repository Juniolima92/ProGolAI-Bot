import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes
)
from flask import Flask
from threading import Thread

BOT_TOKEN = "8219603341:AAHsqUktaC5IIEtI8aehyPZtDrrKHWpeZOQ"
API_KEY = "cadc8d2e9944e5f78dc45bf26ab7a3fa"

app = Flask(__name__)

@app.route('/ping')
def ping():
    return "OK", 200

def run_flask():
    app.run(host="0.0.0.0", port=5000)

HEADERS = {
    "x-apisports-key": API_KEY
}

BASE_URL = "https://api-football-v1.p.rapidapi.com/v3"

def get_fixtures_today():
    from datetime import datetime
    date_today = datetime.utcnow().strftime('%Y-%m-%d')
    url = f"{BASE_URL}/fixtures?date={date_today}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        return data.get("response", [])
    return []

def get_fixture_stats(fixture_id):
    url = f"{BASE_URL}/fixtures/statistics?fixture={fixture_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        return data.get("response", [])
    return []

def calculate_probabilities(stats):
    if not stats:
        return 0.33, 0.34, 0.33
    try:
        home_stats = stats[0]
        away_stats = stats[1]
        home_shots = next((s['value'] for s in home_stats['statistics'] if s['type'] == 'Shots on Goal'), 0)
        away_shots = next((s['value'] for s in away_stats['statistics'] if s['type'] == 'Shots on Goal'), 0)
        total = home_shots + away_shots
        if total == 0:
            return 0.33, 0.34, 0.33
        p1 = home_shots / total
        p2 = away_shots / total
        px = 1 - p1 - p2
        if px < 0: px = 0
        soma = p1 + px + p2
        return p1 / soma, px / soma, p2 / soma
    except Exception:
        return 0.33, 0.34, 0.33

def calcular_dupla_hipotese(p1, px, p2):
    return p1 + px, p1 + p2, px + p2

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔝 Prognósticos do Dia", callback_data='prog')],
        [InlineKeyboardButton("🏆 Principais Campeonatos", callback_data='campeonatos')],
        [InlineKeyboardButton("🌍 Ligas por Continente", callback_data='ligas')],
        [InlineKeyboardButton("⏱️ Todos os Jogos do Dia", callback_data='jogos_hoje')],
        [InlineKeyboardButton("🗓️ Jogos de Amanhã", callback_data='jogos_amanha')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Bem-vindo ao ProGolAI!\nEscolha uma opção no menu abaixo:",
        reply_markup=reply_markup
    )

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    print(f"Callback recebido: {data}")

    if data == 'prog':
        fixtures = get_fixtures_today()
        if not fixtures:
            await query.edit_message_text("❌ Nenhum jogo encontrado para hoje.",
                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data='menu')]]))
            return

        msg = "🎯 *Prognósticos do Dia*\n\n"
        count = 0
        for f in fixtures:
            home = f['teams']['home']['name']
            away = f['teams']['away']['name']
            fixture_id = f['fixture']['id']
            stats = get_fixture_stats(fixture_id)
            p1, px, p2 = calculate_probabilities(stats)
            dupla_1X, dupla_12, dupla_X2 = calcular_dupla_hipotese(p1, px, p2)
            msg += (f"➡️ {home} x {away}\n"
                    f"Probabilidades:\n"
                    f"🏠 Casa: {p1*100:.1f}%\n"
                    f"🤝 Empate: {px*100:.1f}%\n"
                    f"🚩 Visitante: {p2*100:.1f}%\n"
                    f"Dupla hipótese:\n"
                    f"1X: {dupla_1X*100:.1f}%, 12: {dupla_12*100:.1f}%, X2: {dupla_X2*100:.1f}%\n\n")
            count += 1
            if count >= 5:
                break
        await query.edit_message_text(msg, parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data='menu')]]))
    elif data == 'menu':
        keyboard = [
            [InlineKeyboardButton("🔝 Prognósticos do Dia", callback_data='prog')],
            [InlineKeyboardButton("🏆 Principais Campeonatos", callback_data='campeonatos')],
            [InlineKeyboardButton("🌍 Ligas por Continente", callback_data='ligas')],
            [InlineKeyboardButton("⏱️ Todos os Jogos do Dia", callback_data='jogos_hoje')],
            [InlineKeyboardButton("🗓️ Jogos de Amanhã", callback_data='jogos_amanha')],
        ]
        await query.edit_message_text("👋 Menu Inicial:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text("Opção desconhecida.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data='menu')]]))

async def chat_simulacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if 'x' in texto.lower():
        fixtures = get_fixtures_today()
        jogo_encontrado = None
        for f in fixtures:
            home = f['teams']['home']['name'].lower()
            away = f['teams']['away']['name'].lower()
            if home in texto.lower() and away in texto.lower():
                jogo_encontrado = f
                break
        if not jogo_encontrado:
            await update.message.reply_text("❌ Jogo não encontrado para hoje. Tente outro jogo ou verifique o nome.")
            return

        fixture_id = jogo_encontrado['fixture']['id']
        stats = get_fixture_stats(fixture_id)
        p1, px, p2 = calculate_probabilities(stats)
        dupla_1X, dupla_12, dupla_X2 = calcular_dupla_hipotese(p1, px, p2)

        resposta = (
            f"🎲 *Simulação do jogo:* {jogo_encontrado['teams']['home']['name']} x {jogo_encontrado['teams']['away']['name']}\n\n"
            f"🏠 Vitória time da casa: {p1*100:.1f}%\n"
            f"🤝 Empate: {px*100:.1f}%\n"
            f"🚩 Vitória time visitante: {p2*100:.1f}%\n\n"
            f"🔢 *Dupla hipótese:*\n"
            f"1X (Casa ou empate): {dupla_1X*100:.1f}%\n"
            f"12 (Casa ou visitante): {dupla_12*100:.1f}%\n"
            f"X2 (Empate ou visitante): {dupla_X2*100:.1f}%"
        )
        await update.message.reply_text(resposta, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "❓ Para simular, envie o jogo no formato: 'Time A x Time B'\n"
            "Exemplo: Palmeiras x Corinthians"
        )

def main():
    Thread(target=run_flask).start()
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CallbackQueryHandler(handle_menu))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_simulacao))
    print("🤖 Bot ProGolAI rodando...")
    app_bot.run_polling()

if __name__ == "__main__":
    main()
