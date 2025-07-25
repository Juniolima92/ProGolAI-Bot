import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN") or "SEU_TOKEN_AQUI"
API_KEY = os.getenv("API_KEY") or "SUA_API_KEY_AQUI"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔝 Melhores Prognósticos do Dia", callback_data='best_tips')],
        [InlineKeyboardButton("🌍 Principais Ligas", callback_data='main_leagues')],
        [InlineKeyboardButton("🗓️ Jogos de Amanhã", callback_data='tomorrow_games')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Olá! Escolha uma opção:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'best_tips':
        await query.edit_message_text("Aqui estão os melhores prognósticos do dia com odds reais...")
    elif query.data == 'main_leagues':
        leagues = ["🇧🇷 Brasileirão", "🇪🇸 La Liga", "🇩🇪 Bundesliga", "🇬🇧 Premier League", "🇮🇹 Serie A"]
        text = "Principais ligas do mundo:\n" + "\n".join(leagues)
        await query.edit_message_text(text)
    elif query.data == 'tomorrow_games':
        await query.edit_message_text("Jogos de amanhã...")

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()

if __name__
