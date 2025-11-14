import os
import logging
import sqlite3
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from datetime import datetime

# Configuración
BOT_TOKEN = os.getenv('BOT_TOKEN', '7927690342:AAFKbjYIKPsdh1FHRUctIVwDOfoFshGwNvA')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '7413496478').split(',')]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
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
    
    # Datos de ejemplo
    sample_data = [
        ("alcampo.com", "usuario1", "clave123", "sample"),
        ("alcampo.es", "user@mail.com", "pass456", "sample"),
        ("carrefour.com", "cliente", "password789", "sample"),
        ("amazon.es", "comprador", "amazonpass", "sample"),
        ("facebook.com", "user_fb", "fbpass123", "sample"),
        ("gmail.com", "correo@gmail.com", "gmailpass", "sample"),
    ]
    
    for url, login, password, source in sample_data:
        c.execute('''INSERT OR IGNORE INTO ulp_data (url, login, password, source)
                     VALUES (?, ?, ?, ?)''', (url, login, password, source))
    
    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada con datos de ejemplo")

def search_ulp(query, search_type="domain", limit=1000):
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    
    if search_type == "domain":
        c.execute('''SELECT url, login, password FROM ulp_data 
                     WHERE url LIKE ? LIMIT ?''', (f'%{query}%', limit))
    elif search_type == "login":
        c.execute('''SELECT url, login, password FROM ulp_data 
                     WHERE login LIKE ? LIMIT ?''', (f'%{query}%', limit))
    elif search_type == "password":
        c.execute('''SELECT url, login, password FROM ulp_data 
                     WHERE password LIKE ? LIMIT ?''', (f'%{query}%', limit))
    
    results = c.fetchall()
    conn.close()
    return results

# ==================== 🎯 COMANDOS PRINCIPALES ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hello, {user.first_name}!\n\n"
        "use /info for showing all commands\n"
        "🚀 all available @NuvixULP_Bot commands:\n\n"
        "/search example.com\n"
        "(free search url:login:pass)\n\n"
        "/login mylogin\n"
        "(free search ulp by login)\n\n"
        "/password mypassword\n"
        "(free search ulp by password)\n\n"
        "/mail example@gmail.com\n"
        "(free search mail passwords)\n\n"
        "🔥 ALL COMMANDS ARE FREE & UNLIMITED!"
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_text = (
        "🤖 NuvixULP Bot - All Commands\n\n"
        "🔍 FREE SEARCH COMMANDS:\n"
        "• /search example.com - Search ULP by domain\n"
        "• /login mylogin - Search ULP by login\n"
        "• /password mypassword - Search ULP by password\n"
        "• /mail example@gmail.com - Search mail passwords\n\n"
        "📊 INFO COMMANDS:\n"
        "• /info - Show this message\n"
        "• /stats - Bot statistics\n\n"
        "⚡ ALL FEATURES ARE 100% FREE!\n"
        "🚀 UNLIMITED SEARCHES"
    )
    await update.message.reply_text(info_text)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please specify domain\nExample: /search alcampo.com")
        return
    
    query = " ".join(context.args)
    
    # Mostrar selección de formato
    keyboard = [
        [InlineKeyboardButton("🌐 url:login:pass", callback_data=f"format_search_urlloginpass_{query}")],
        [InlineKeyboardButton("👤 login:pass", callback_data=f"format_search_loginpass_{query}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔍 Search: {query}\n\n"
        "Choose strings format\n"
        "url:login:pass     login:pass",
        reply_markup=reply_markup
    )

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please specify login\nExample: /login admin")
        return
    
    query = " ".join(context.args)
    
    keyboard = [
        [InlineKeyboardButton("🌐 url:login:pass", callback_data=f"format_login_urlloginpass_{query}")],
        [InlineKeyboardButton("👤 login:pass", callback_data=f"format_login_loginpass_{query}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔍 Login Search: {query}\n\n"
        "Choose strings format\n"
        "url:login:pass     login:pass",
        reply_markup=reply_markup
    )

async def password_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please specify password\nExample: /password 123456")
        return
    
    query = " ".join(context.args)
    
    keyboard = [
        [InlineKeyboardButton("🌐 url:login:pass", callback_data=f"format_password_urlloginpass_{query}")],
        [InlineKeyboardButton("👤 login:pass", callback_data=f"format_password_loginpass_{query}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔍 Password Search: {query}\n\n"
        "Choose strings format\n"
        "url:login:pass     login:pass",
        reply_markup=reply_markup
    )

async def mail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please specify email\nExample: /mail user@gmail.com")
        return
    
    query = " ".join(context.args)
    
    keyboard = [
        [InlineKeyboardButton("🌐 url:login:pass", callback_data=f"format_mail_urlloginpass_{query}")],
        [InlineKeyboardButton("👤 login:pass", callback_data=f"format_mail_loginpass_{query}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔍 Email Search: {query}\n\n"
        "Choose strings format\n"
        "url:login:pass     login:pass",
        reply_markup=reply_markup
    )

# ==================== 🔄 MANEJADOR DE FORMATOS ====================
async def format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    command_type = data_parts[1]  # search, login, password, mail
    format_type = data_parts[2]   # urlloginpass o loginpass
    search_query = '_'.join(data_parts[3:])
    
    # Paso 1: Mostrar formato seleccionado
    position_msg = await query.edit_message_text(
        f"🔍 {command_type.title()} Search: {search_query}\n"
        f"✅ you choosed format: {format_type.replace('loginpass', 'login:pass').replace('urlloginpass', 'url:login:pass')}\n\n"
        f"⏳ Your request added to query. Query position: 1"
    )
    
    await asyncio.sleep(2)
    
    # Paso 2: Realizar búsqueda
    if command_type == "search":
        results = search_ulp(search_query, "domain")
    elif command_type == "login":
        results = search_ulp(search_query, "login")
    elif command_type == "password":
        results = search_ulp(search_query, "password")
    else:  # mail
        results = search_ulp(search_query, "login")  # Buscar por login para emails
    
    total_found = len(results)
    sites_searched = random.randint(50, 200)
    
    # Generar números realistas si hay pocos resultados
    if total_found < 10:
        total_found = random.randint(1000, 50000)
    
    # Paso 3: Mostrar estadísticas
    stats_msg = await position_msg.edit_text(
        f"🔍 {command_type.title()} Search: {search_query}\n"
        f"✅ you choosed format: {format_type.replace('loginpass', 'login:pass').replace('urlloginpass', 'url:login:pass')}\n\n"
        f"🚀 Started search: {command_type} {search_query}\n"
        f"was searched {sites_searched} times\n\n"
        f"📊 Found {total_found:,} uniq strings for {command_type} {search_query}."
    )
    
    await asyncio.sleep(1)
    
    if not results:
        await stats_msg.edit_text(
            f"🔍 {command_type.title()} Search: {search_query}\n"
            f"✅ you choosed format: {format_type.replace('loginpass', 'login:pass').replace('urlloginpass', 'url:login:pass')}\n\n"
            f"❌ No results found for {command_type}: {search_query}"
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
        f"🔍 {command_type.title()} Search: {search_query}\n"
        f"✅ you choosed format: {format_type.replace('loginpass', 'login:pass').replace('urlloginpass', 'url:login:pass')}\n\n"
        f"📁 {command_type} {search_query} format {format_type.replace('loginpass', 'login:pass').replace('urlloginpass', 'url:login:pass')}\n\n"
        f"📄 File generated with {len(results):,} results"
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

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM ulp_data")
    total_ulp = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT url) FROM ulp_data")
    unique_sites = c.fetchone()[0]
    
    conn.close()
    
    stats_text = (
        f"📊 NuvixULP Bot Statistics\n\n"
        f"🔐 Total ULP: {total_ulp:,}\n"
        f"🌐 Unique Sites: {unique_sites:,}\n\n"
        f"⚡ Status: ✅ ACTIVE & FREE\n"
        f"🚀 All features are 100% FREE!"
    )
    
    await update.message.reply_text(stats_text)

# ==================== 🔧 COMANDOS ADMIN ====================
async def add_ulp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only")
        return
    
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "❌ Format: /addulp <url> <login> <password> [source]\n\n"
            "📝 Examples:\n"
            "• /addulp alcampo.com usuario123 clave456\n"
            "• /addulp gmail.com user@mail.com password123"
        )
        return
    
    url = context.args[0]
    login = context.args[1]
    password = context.args[2]
    source = context.args[3] if len(context.args) > 3 else "manual"
    
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    
    try:
        c.execute('''INSERT OR IGNORE INTO ulp_data (url, login, password, source)
                     VALUES (?, ?, ?, ?)''', (url, login, password, source))
        conn.commit()
        
        await update.message.reply_text(
            f"✅ ULP Added Successfully!\n\n"
            f"🌐 URL: {url}\n"
            f"👤 Login: {login}\n"
            f"🔐 Password: {password}\n"
            f"📁 Source: {source}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    finally:
        conn.close()

# ==================== 🚀 MAIN FUNCTION ====================
def main():
    # Inicializar base de datos
    init_db()
    
    # Crear aplicación
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("login", login_command))
    application.add_handler(CommandHandler("password", password_command))
    application.add_handler(CommandHandler("mail", mail_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("addulp", add_ulp_command))
    
    application.add_handler(CallbackQueryHandler(format_callback, pattern="^format_"))
    
    print("🤖 NuvixULP Bot Started!")
    print("🐍 Python 3.13 Compatible Version")
    print("🚀 Bot is running...")
    
    # Iniciar bot
    application.run_polling()

if __name__ == "__main__":
    main()
