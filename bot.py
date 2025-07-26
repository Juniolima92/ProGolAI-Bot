bot.py (versão com estatísticas reais via API-Football) 

import telebot import requests from telebot import types from datetime import datetime

BOT_TOKEN = "8219603341:AAHsqUktaC5IIEtI8aehyPZtDrrKHWpeZOQ" API_FOOTBALL_KEY = "cadc8d2e9944e5f78dc45bf26ab7a3fa" API_FOOTBALL_URL = "https://v3.football.api-sports.io"

bot = telebot.TeleBot(BOT_TOKEN) HEADERS = {"x-apisports-key": API_FOOTBALL_KEY}

Utilitários 

BR_DATE = datetime.now().strftime("%Y-%m-%d")

========== /start ============ 

@bot.message_handler(commands=['start']) def start(message): chat_id = message.chat.id with open("progol_logo.jpg", "rb") as photo: bot.send_photo(chat_id, photo, caption="⚽ Bem-vindo ao ProGolAI!\n\n🤖 IA de prognósticos baseada em estatísticas reais da API-Football.\n\nEscolha abaixo uma opção para começar:", parse_mode="Markdown")

markup = types.ReplyKeyboardMarkup(resize_keyboard=True) markup.row("📈 Melhores Prognósticos do Dia") markup.row("🌍 Ver Ligas por Continente") markup.row("📅 Jogos de Amanhã") markup.row("🤖 Perguntar à IA") bot.send_message(chat_id, "📋 *Menu Inicial:*", parse_mode="Markdown", reply_markup=markup) ========== MODO IA ============ 

@bot.message_handler(func=lambda msg: msg.text == "🤖 Perguntar à IA") def ativar_modo_ia(message): bot.send_message(message.chat.id, "🤖 Modo IA ativado!\n\nMe pergunte algo como:\n❓ Flamengo ganha hoje?\n❓ Qual jogo tem mais escanteios?\n❓ Vale apostar no Over 2.5 do Real Madrid?", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: True) def responder_ia(message): pergunta = message.text.lower()

if "escanteio" in pergunta: resposta = jogos_com_escanteios_altos() bot.send_message(message.chat.id, resposta, parse_mode="Markdown") elif any(time in pergunta for time in ["flamengo", "palmeiras", "real madrid"]): time = pergunta.split()[0].capitalize() resposta = analisar_time_hoje(time) bot.send_message(message.chat.id, resposta, parse_mode="Markdown") else: bot.send_message(message.chat.id, "❓ Ainda estou aprendendo! Reformule sua pergunta ou mencione um time conhecido.", parse_mode="Markdown") ========== FUNÇÕES REAIS DE ANÁLISE ============ 

def buscar_time_id(nome): url = f"{API_FOOTBALL_URL}/teams?search={nome}&country=Brazil" r = requests.get(url, headers=HEADERS) data = r.json() if data["response"]: return data["response"][0]["team"]["id"] return None

def analisar_time_hoje(time_nome): team_id = buscar_time_id(time_nome) if not team_id: return f"❌ Time {time_nome} não encontrado."

url = f"{API_FOOTBALL_URL}/fixtures?team={team_id}&date={BR_DATE}" r = requests.get(url, headers=HEADERS).json() if not r["response"]: return f"📅 O *{time_nome}* não tem jogo hoje." jogo = r["response"][0] adversario = jogo["teams"]["away"] if jogo["teams"]["home"]["name"] == time_nome else jogo["teams"]["home"] partida_id = jogo["fixture"]["id"] # Estatísticas estat_url = f"{API_FOOTBALL_URL}/fixtures/statistics?fixture={partida_id}" stats = requests.get(estat_url, headers=HEADERS).json() gols_time = escanteios_time = posse_time = "N/D" for s in stats["response"]: if s["team"]["name"].lower() == time_nome.lower(): for stat in s["statistics"]: if stat["type"] == "Total Shots": gols_time = stat["value"] elif stat["type"] == "Corner Kicks": escanteios_time = stat["value"] elif stat["type"] == "Ball Possession": posse_time = stat["value"] return f"📊 *Análise: {time_nome} x {adversario['name']}*\n\n🎯 Gols marcados recentes: {gols_time}\n🚩 Escanteios: {escanteios_time}\n📊 Posse de bola: {posse_time}\n\n🔁 Entrada provável: *Dupla hipótese 1X*\n🎯 Over 1.5 gols sugerido\n\n🧠 Base: estatísticas reais API-Football." 

def jogos_com_escanteios_altos(): url = f"{API_FOOTBALL_URL}/fixtures?date={BR_DATE}" r = requests.get(url, headers=HEADERS).json() jogos = r["response"][:5] resultado = "📊 Jogos com tendência de escanteios altos:\n\n" for jogo in jogos: home = jogo["teams"]["home"]["name"] away = jogo["teams"]["away"]["name"] partida_id = jogo["fixture"]["id"] estat_url = f"{API_FOOTBALL_URL}/fixtures/statistics?fixture={partida_id}" stats = requests.get(estat_url, headers=HEADERS).json() total = 0 for s in stats["response"]: for stat in s["statistics"]: if stat["type"] == "Corner Kicks" and stat["value"]: total += int(stat["value"]) if total >= 9: resultado += f"🚩 {home} x {away} — Total escanteios: {total}\n" return resultado if resultado.strip() != "📊 Jogos com tendência de escanteios altos:" else "❌ Nenhum jogo com muitos escanteios encontrado hoje."

========== INICIAR ============ 

bot.polling(none_stop=True)

