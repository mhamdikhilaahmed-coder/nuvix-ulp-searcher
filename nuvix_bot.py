import os
import logging
import sqlite3
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from datetime import datetime

# Configuración
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '7413496478').split(',')]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 🗃️ BASE DE DATOS ====================
def init_db():
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS ulp_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  url TEXT NOT NULL,
                  login TEXT NOT NULL,
                  password TEXT NOT NULL,
                  source TEXT,
                  search_count INTEGER DEFAULT 0,
                  added_date DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_preferences
                 (user_id INTEGER PRIMARY KEY,
                  output_format TEXT DEFAULT 'urlloginpass',
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Datos de ejemplo
    sample_data = [
        ("alcampo.com", "usuario1", "clave123", "sample"),
        ("alcampo.es", "user@mail.com", "pass456", "sample"),
        ("carrefour.com", "cliente", "password789", "sample"),
    ]
    
    for url, login, password, source in sample_data:
        c.execute('''INSERT OR IGNORE INTO ulp_data (url, login, password, source)
                     VALUES (?, ?, ?, ?)''', (url, login, password, source))
    
    conn.commit()
    conn.close()
    print("✅ Base de datos lista")

def search_ulp(query, search_type="domain", limit=1000):
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    
    if search_type == "domain":
        c.execute('''SELECT url, login, password FROM ulp_data 
                     WHERE url LIKE ? LIMIT ?''', (f'%{query}%', limit))
    elif search_type == "login":
        c.execute('''SELECT url, login, password FROM ulp_data 
                     WHERE login LIKE ? LIMIT ?''', (f'%{query}%', limit))
    
    results = c.fetchall()
    conn.close()
    return results

# ==================== 🎯 COMANDOS PRINCIPALES ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hello, {user.first_name}!\n\n"
        f"use /info for showing all commands\n"
        f"🚀 all available @NuvixULP_Bot commands:\n\n"
        f"/search example.com\n"
        f"(free search url:login:pass)\n\n"
        f"/login mylogin\n"
        f"(free search ulp by login)\n\n"
        f"🔥 ALL COMMANDS ARE FREE & UNLIMITED!",
        parse_mode='Markdown'
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_text = (
        "🤖 **NuvixULP Bot - All Commands**\n\n"
        "🔍 **FREE SEARCH COMMANDS:**\n"
        "• `/search example.com` - Search ULP by domain\n"
        "• `/login mylogin` - Search ULP by login\n\n"
        "📊 **INFO COMMANDS:**\n"
        "• `/info` - Show this message\n\n"
        "⚡ **ALL FEATURES ARE 100% FREE!**\n"
        "🚀 **UNLIMITED SEARCHES**"
    )
    await update.message.reply_text(info_text, parse_mode='Markdown')

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please specify domain\nExample: `/search alcampo.com`", parse_mode='Markdown')
        return
    
    query = " ".join(context.args)
    
    # Mostrar selección de formato
    keyboard = [
        [InlineKeyboardButton("🌐 url:login:pass", callback_data=f"format_search_urlloginpass_{query}")],
        [InlineKeyboardButton("👤 login:pass", callback_data=f"format_search_loginpass_{query}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔍 **Search:** `{query}`\n\n"
        f"Choose strings format\n"
        f"url:login:pass     login:pass",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please specify login\nExample: `/login admin`", parse_mode='Markdown')
        return
    
    query = " ".join(context.args)
    
    keyboard = [
        [InlineKeyboardButton("🌐 url:login:pass", callback_data=f"format_login_urlloginpass_{query}")],
        [InlineKeyboardButton("👤 login:pass", callback_data=f"format_login_loginpass_{query}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔍 **Login Search:** `{query}`\n\n"
        f"Choose strings format\n"
        f"url:login:pass     login:pass",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ==================== 🔄 MANEJADOR DE FORMATOS ====================
async def format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    command_type = data_parts[1]
    format_type = data_parts[2]
    search_query = '_'.join(data_parts[3:])
    
    # Paso 1: Mostrar formato seleccionado
    position_msg = await query.edit_message_text(
        f"🔍 **{command_type.title()} Search:** `{search_query}`\n"
        f"✅ you choosed format: `{format_type.replace('loginpass', 'login:pass').replace('urlloginpass', 'url:login:pass')}`\n\n"
        f"⏳ Your request added to query. Query position: 1"
    )
    
    await asyncio.sleep(2)
    
    # Paso 2: Realizar búsqueda
    if command_type == "search":
        results = search_ulp(search_query, "domain")
    else:
        results = search_ulp(search_query, "login")
    
    total_found = len(results)
    sites_searched = random.randint(50, 200)
    
    # Paso 3: Mostrar estadísticas
    stats_msg = await position_msg.edit_text(
        f"🔍 **{command_type.title()} Search:** `{search_query}`\n"
        f"✅ you choosed format: `{format_type.replace('loginpass', 'login:pass').replace('urlloginpass', 'url:login:pass')}`\n\n"
        f"🚀 Started search: {command_type} `{search_query}`\n"
        f"was searched `{sites_searched}` times\n\n"
        f"📊 Found `{total_found:,}` uniq strings for {command_type} `{search_query}`."
    )
    
    await asyncio.sleep(1)
    
    if not results:
        await stats_msg.edit_text(
            f"🔍 **{command_type.title()} Search:** `{search_query}`\n"
            f"✅ you choosed format: `{format_type.replace('loginpass', 'login:pass').replace('urlloginpass', 'url:login:pass')}`\n\n"
            f"❌ No results found for {command_type}: `{search_query}`"
        )
        return
    
    # Crear archivo
    filename = f"{command_type}_{search_query.replace('.', '_')}_{format_type}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        for url, login, password in results:
            if format_type == 'loginpass':
                f.write(f"{login}:{password}\n")
            else:
                f.write(f"{url}:{login}:{password}\n")
    
    # Paso 4: Enviar resultados
    results_text = (
        f"🔍 **{command_type.title()} Search:** `{search_query}`\n"
        f"✅ you choosed format: `{format_type.replace('loginpass', 'login:pass').replace('urlloginpass', 'url:login:pass')}`\n\n"
        f"📁 {command_type} `{search_query}` format `{format_type.replace('loginpass', 'login:pass').replace('urlloginpass', 'url:login:pass')}`\n\n"
        f"📄 **File generated with** `{len(results):,}` **results**"
    )
    
    await stats_msg.edit_text(results_text)
    
    # Enviar archivo
    with open(filename, 'rb') as file:
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=file,
            filename=filename,
            caption=f"🔍 {search_query} | {len(results)} results | {format_type}"
        )
    
    # Limpiar
    if os.path.exists(filename):
        os.remove(filename)

# ==================== 🚀 MAIN FUNCTION ====================
def main():
    # Inicializar base de datos
    init_db()
    
    # Crear aplicación - VERSIÓN COMPATIBLE
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("login", login_command))
    
    application.add_handler(CallbackQueryHandler(format_callback, pattern="^format_"))
    
    print("🤖 NuvixULP Bot Started!")
    print("🚀 Bot is running...")
    
    # Iniciar bot
    application.run_polling()

if __name__ == "__main__":
    main()
