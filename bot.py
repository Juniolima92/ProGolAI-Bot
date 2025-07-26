import os
import asyncio
import logging
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

# Configuração básica
BOT_TOKEN = os.getenv("BOT_TOKEN", "8219603341:AAHsqUktaC5IIEtI8aehyPZtDrrKHWpeZOQ")
PORT = int(os.environ.get("PORT", 10000))

logging.basicConfig(level=logging.INFO)

# Menu principal
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔝 Prognósticos do Dia", callback_data='best_tips')],
        [InlineKeyboardButton("🏆 Principais Campeonatos", callback_data='main_leagues')],
        [InlineKeyboardButton("🌍 Ligas por Continente", callback_data='by_continent')],
        [InlineKeyboardButton("⏱️ Todos os Jogos do Dia", callback_data='all_games')],
        [InlineKeyboardButton("🗓️ Jogos de Amanhã", callback_data='tomorrow_games')],
    ]
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⚽ *Bem-vindo ao ProGol AI Bot!*\n\nEscolha uma das opções abaixo:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Trata cliques nos botões
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔧 Função ainda em desenvolvimento.")

# Flask App para manter o Render vivo
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "✅ ProGol AI Bot está rodando!"

# Função para iniciar o Flask em uma thread
def start_flask():
    flask_app.run(host="0.0.0.0", port=PORT)

# Função principal do bot
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    await app.start()
    await app.updater.start_polling()
    await app.updater.wait()

if __name__ == "__main__":
    Thread(target=start_flask).start()
    asyncio.run(main())
