import os
import logging
import sqlite3
import asyncio
import random
import re
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

# Estadísticas globales
BOT_STATS = {
    "total_ulp": 0,
    "last_update": datetime.now().strftime('%Y-%m-%d %H:%M'),
    "last_added": 0
}

# ==================== 🗃️ BASE DE DATOS COMPLETA ====================
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_activity_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  command TEXT NOT NULL,
                  query TEXT,
                  results_count INTEGER DEFAULT 0,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Datos de ejemplo
    sample_data = [
        ("alcampo.com", "usuario1", "clave123", "sample"),
        ("alcampo.es", "user@mail.com", "pass456", "sample"),
        ("carrefour.com", "cliente", "password789", "sample"),
        ("amazon.es", "comprador", "amazonpass", "sample"),
        ("facebook.com", "user_fb", "fbpass123", "sample"),
        ("gmail.com", "correo@gmail.com", "gmailpass", "sample"),
        ("twitter.com", "user_tw", "twpass456", "sample"),
        ("instagram.com", "user_ig", "igpass789", "sample"),
        ("netflix.com", "user_nf", "nfpass123", "sample"),
        ("spotify.com", "user_sp", "sppass456", "sample"),
    ]
    
    for url, login, password, source in sample_data:
        c.execute('''INSERT OR IGNORE INTO ulp_data (url, login, password, source)
                     VALUES (?, ?, ?, ?)''', (url, login, password, source))
    
    conn.commit()
    
    # Actualizar estadísticas
    c.execute("SELECT COUNT(*) FROM ulp_data")
    BOT_STATS["total_ulp"] = c.fetchone()[0]
    
    conn.close()
    logger.info("✅ Base de datos inicializada con datos de ejemplo")

def log_user_activity(update: Update, command: str, query: str = "", results_count: int = 0):
    user = update.effective_user
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    
    c.execute('''INSERT INTO user_activity_logs 
                 (user_id, username, first_name, last_name, command, query, results_count)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (user.id, user.username, user.first_name, user.last_name, command, query, results_count))
    
    conn.commit()
    conn.close()

def get_user_format(user_id):
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    c.execute("SELECT output_format FROM user_preferences WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 'urlloginpass'

def set_user_format(user_id, format_type):
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO user_preferences (user_id, output_format) 
                 VALUES (?, ?)''', (user_id, format_type))
    conn.commit()
    conn.close()

def search_ulp(query, search_type="domain", limit=1000):
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    
    if search_type == "domain":
        c.execute('''SELECT url, login, password FROM ulp_data 
                     WHERE url LIKE ? ORDER BY search_count DESC LIMIT ?''',
                  (f'%{query}%', limit))
    elif search_type == "login":
        c.execute('''SELECT url, login, password FROM ulp_data 
                     WHERE login LIKE ? ORDER BY search_count DESC LIMIT ?''',
                  (f'%{query}%', limit))
    elif search_type == "password":
        c.execute('''SELECT url, login, password FROM ulp_data 
                     WHERE password LIKE ? ORDER BY search_count DESC LIMIT ?''',
                  (f'%{query}%', limit))
    elif search_type == "email":
        c.execute('''SELECT url, login, password FROM ulp_data 
                     WHERE login LIKE ? ORDER BY search_count DESC LIMIT ?''',
                  (f'%{query}%', limit))
    
    results = c.fetchall()
    
    # Actualizar contador de búsquedas
    for url, login, password in results:
        c.execute('''UPDATE ulp_data SET search_count = search_count + 1 
                     WHERE url = ? AND login = ? AND password = ?''',
                  (url, login, password))
    
    conn.commit()
    conn.close()
    return results

def get_search_stats(query, search_type="domain"):
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    
    if search_type == "domain":
        c.execute('''SELECT COUNT(*) FROM ulp_data WHERE url LIKE ?''', (f'%{query}%',))
    elif search_type == "login":
        c.execute('''SELECT COUNT(*) FROM ulp_data WHERE login LIKE ?''', (f'%{query}%',))
    
    total_found = c.fetchone()[0]
    
    c.execute('''SELECT COUNT(DISTINCT url) FROM ulp_data WHERE url LIKE ?''', (f'%{query}%',))
    sites_searched = c.fetchone()[0]
    
    conn.close()
    return total_found, sites_searched

# ==================== 🎯 COMANDOS USUARIOS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_user_activity(update, "start")
    user = update.effective_user
    
    await update.message.reply_text(
        f"Hello, {user.first_name}!\n\n"
        f"use /info for showing all commands\n"
        f"🚀 all available @NuvixULP_Bot commands:\n\n"
        f"/search example.com\n"
        f"(free search url:login:pass, limit 500k lines)\n\n"
        f"/login mylogin\n"
        f"(free search ulp by login)\n\n"
        f"/password mypassword\n"
        f"(free search ulp by password)\n\n"
        f"/mail example@gmail.com\n"
        f"(free search mail passwords)\n\n"
        f"🔥 ALL COMMANDS ARE FREE & UNLIMITED!\n"
        f"🎯 Identical to TTMlogsBot but 100% FREE!"
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log_user_activity(update, "info")
    
    info_text = (
        "🤖 NuvixULP Bot - All Commands\n\n"
        "🔍 FREE SEARCH COMMANDS:\n"
        "• /search example.com - Search ULP by domain\n"
        "• /login mylogin - Search ULP by login\n"
        "• /password mypassword - Search ULP by password\n"
        "• /mail example@gmail.com - Search mail passwords\n\n"
        "📊 INFO COMMANDS:\n"
        "• /stats - Bot statistics\n"
        "• /info - Show this message\n\n"
        "⚡ ALL FEATURES ARE 100% FREE!\n"
        "🚀 UNLIMITED SEARCHES\n\n"
        "🎯 Identical to TTMlogsBot but FREE!"
    )
    
    await update.message.reply_text(info_text)

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please specify domain\nExample: /search alcampo.com")
        return
    
    query = " ".join(context.args)
    log_user_activity(update, "search", query, 0)
    
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
    log_user_activity(update, "login", query, 0)
    
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
    log_user_activity(update, "password", query, 0)
    
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
    log_user_activity(update, "mail", query, 0)
    
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
    
    user_id = query.from_user.id
    set_user_format(user_id, format_type)
    
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
        total_found, sites_searched = get_search_stats(search_query, "domain")
    elif command_type == "login":
        results = search_ulp(search_query, "login")
        total_found, sites_searched = len(results), random.randint(10, 100)
    elif command_type == "password":
        results = search_ulp(search_query, "password")
        total_found, sites_searched = len(results), random.randint(5, 50)
    elif command_type == "mail":
        results = search_ulp(search_query, "email")
        total_found, sites_searched = len(results), random.randint(20, 150)
    
    # Generar números realistas si no hay suficientes datos
    if total_found < 100:
        total_found = random.randint(1000, 50000)
        sites_searched = random.randint(10, 200)
    
    # Paso 3: Mostrar estadísticas
    stats_msg = await position_msg.edit_text(
        f"🔍 {command_type.title()} Search: {search_query}\n"
        f"✅ you choosed format: {format_type.replace('loginpass', 'login:pass').replace('urlloginpass', 'url:login:pass')}\n\n"
        f"🚀 Started search: {command_type} {search_query}\n"
        f"was searched {sites_searched} times\n\n"
        f"📊 Found {total_found:,} uniq strings for {command_type} {search_query}."
    )
    
    await asyncio.sleep(1)
    
    # Actualizar log con resultados reales
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    c.execute('''UPDATE user_activity_logs SET results_count = ? 
                 WHERE user_id = ? AND command = ? AND query = ? 
                 ORDER BY id DESC LIMIT 1''',
              (len(results), user_id, command_type, search_query))
    conn.commit()
    conn.close()
    
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
    log_user_activity(update, "stats")
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM ulp_data")
    total_ulp = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT url) FROM ulp_data")
    unique_sites = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT user_id) FROM user_activity_logs")
    total_users = c.fetchone()[0]
    
    conn.close()
    
    stats_text = (
        f"📊 NuvixULP Bot Statistics\n\n"
        f"🔐 Total ULP: {total_ulp:,}\n"
        f"🌐 Unique Sites: {unique_sites:,}\n"
        f"👥 Total Users: {total_users:,}\n\n"
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
            "• /addulp gmail.com user@mail.com password123 email_leak"
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
        
        # Actualizar estadísticas
        c.execute("SELECT COUNT(*) FROM ulp_data")
        BOT_STATS["total_ulp"] = c.fetchone()[0]
        BOT_STATS["last_update"] = datetime.now().strftime('%Y-%m-%d %H:%M')
        BOT_STATS["last_added"] = 1
        
        await update.message.reply_text(
            f"✅ ULP Added Successfully!\n\n"
            f"🌐 URL: {url}\n"
            f"👤 Login: {login}\n"
            f"🔐 Password: {password}\n"
            f"📁 Source: {source}\n\n"
            f"💾 Total in database: {BOT_STATS['total_ulp']:,} ULP"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    finally:
        conn.close()

async def upload_ulp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only")
        return
    
    if not update.message.document:
        await update.message.reply_text(
            "📁 Send me a .txt file with ULP data\n\n"
            "📝 Format:\n"
            "url:login:password\n"
            "alcampo.com:user1:pass123\n"
            "gmail.com:user@mail.com:pass456\n\n"
            "Supports: : ; | , tab\n"
            "⚡ Max file size: 50MB"
        )
        return
    
    # Verificar tamaño del archivo
    if update.message.document.file_size > 50 * 1024 * 1024:
        await update.message.reply_text("❌ File too large. Maximum size is 50MB")
        return
    
    processing_msg = await update.message.reply_text("📥 Downloading file...")
    
    # Descargar archivo
    file = await update.message.document.get_file()
    filename = f"upload_{user_id}.txt"
    await file.download_to_drive(filename)
    
    try:
        ulp_list = []
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                for delimiter in [':', ';', '|', ',', '\t']:
                    if delimiter in line:
                        parts = line.split(delimiter)
                        if len(parts) >= 3:
                            url, login, password = parts[0], parts[1], parts[2]
                            ulp_list.append((url.strip(), login.strip(), password.strip(), "file_upload"))
                            break
        
        conn = sqlite3.connect('nuvixlogs.db')
        c = conn.cursor()
        added_count = 0
        
        for url, login, password, source in ulp_list:
            c.execute('''INSERT OR IGNORE INTO ulp_data (url, login, password, source)
                         VALUES (?, ?, ?, ?)''', (url, login, password, source))
            if c.rowcount > 0:
                added_count += 1
        
        conn.commit()
        
        # Actualizar estadísticas
        c.execute("SELECT COUNT(*) FROM ulp_data")
        total_ulp_in_db = c.fetchone()[0]
        BOT_STATS["total_ulp"] = total_ulp_in_db
        BOT_STATS["last_update"] = datetime.now().strftime('%Y-%m-%d %H:%M')
        BOT_STATS["last_added"] = added_count
        
        conn.close()
        
        await processing_msg.edit_text(
            f"✅ File Processed!\n\n"
            f"📁 File: {update.message.document.file_name}\n"
            f"📊 Lines: {len(ulp_list):,}\n"
            f"🆕 Added: {added_count:,} ULP\n"
            f"🔄 Duplicates skipped: {len(ulp_list) - added_count:,}\n"
            f"💾 Total in database: {total_ulp_in_db:,}"
        )
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error: {str(e)}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

async def admin_activity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only")
        return
    
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    c.execute('''SELECT username, first_name, last_name, command, query, results_count, timestamp 
                 FROM user_activity_logs ORDER BY timestamp DESC LIMIT 15''')
    activities = c.fetchall()
    conn.close()
    
    if not activities:
        await update.message.reply_text("📊 No user activity recorded yet")
        return
    
    activity_text = "📊 Recent User Activity\n\n"
    for username, first_name, last_name, command, query, results_count, timestamp in activities:
        user_display = f"@{username}" if username else f"{first_name} {last_name}".strip()
        if not user_display:
            user_display = f"UserID: ...{str(user_id)[-4:]}"
        
        activity_text += f"👤 User: {user_display}\n"
        activity_text += f"📝 Command: /{command}\n"
        if query:
            activity_text += f"🔍 Query: {query}\n"
        if results_count > 0:
            activity_text += f"✅ Results: {results_count}\n"
        activity_text += f"🕐 Time: {timestamp}\n"
        activity_text += "─" * 25 + "\n\n"
    
    await update.message.reply_text(activity_text)

async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only")
        return
    
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM ulp_data")
    total_ulp = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT user_id) FROM user_activity_logs")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM user_activity_logs")
    total_commands = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM user_activity_logs WHERE DATE(timestamp) = DATE('now')")
    today_commands = c.fetchone()[0]
    
    c.execute("SELECT command, COUNT(*) FROM user_activity_logs GROUP BY command ORDER BY COUNT(*) DESC")
    popular_commands = c.fetchall()
    
    conn.close()
    
    stats_text = (
        f"📊 Admin Statistics - NuvixULP\n\n"
        f"🔐 Total ULP: {total_ulp:,}\n"
        f"👥 Total Users: {total_users:,}\n"
        f"📝 Total Commands: {total_commands:,}\n"
        f"📈 Today's Commands: {today_commands:,}\n\n"
        f"🏆 Popular Commands:\n"
    )
    
    for command, count in popular_commands:
        stats_text += f"• /{command}: {count:,}\n"
    
    await update.message.reply_text(stats_text)

async def admin_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only")
        return
    
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    
    # Get unique users
    c.execute('''SELECT DISTINCT user_id, username, first_name, last_name,
                 (SELECT COUNT(*) FROM user_activity_logs u2 WHERE u2.user_id = user_activity_logs.user_id) as usage_count,
                 (SELECT MAX(timestamp) FROM user_activity_logs u3 WHERE u3.user_id = user_activity_logs.user_id) as last_activity
                 FROM user_activity_logs 
                 ORDER BY last_activity DESC LIMIT 50''')
    
    users = c.fetchall()
    conn.close()
    
    if not users:
        await update.message.reply_text("👥 No users found in activity logs")
        return
    
    users_text = f"👥 Bot Users List\n\nTotal Users: {len(users)}\n\n"
    for user_id, username, first_name, last_name, usage_count, last_activity in users:
        user_display = f"@{username}" if username else f"{first_name} {last_name}".strip()
        if not user_display:
            user_display = f"UserID: ...{str(user_id)[-4:]}"
        
        users_text += f"👤 User: {user_display}\n"
        users_text += f"📊 Usage: {usage_count} commands\n"
        users_text += f"🕐 Last seen: {last_activity}\n"
        users_text += "─" * 20 + "\n\n"
    
    await update.message.reply_text(users_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text.startswith('/') and len(text) > 3:
        await update.message.reply_text(
            f"🔍 Quick Search Detected: {text}\n\n"
            f"Use commands for better results:\n"
            f"• /search {text} - Search by domain\n"
            f"• /login {text} - Search by login\n"
            f"• /mail {text} - Search by email\n\n"
            f"Type /info for all commands"
        )

# ==================== 🚀 MAIN FUNCTION ====================
def main():
    # Inicializar base de datos
    init_db()
    
    # Crear aplicación
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ==================== HANDLERS ====================
    # Comandos usuarios
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("login", login_command))
    application.add_handler(CommandHandler("password", password_command))
    application.add_handler(CommandHandler("mail", mail_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Comandos admin
    application.add_handler(CommandHandler("addulp", add_ulp_command))
    application.add_handler(CommandHandler("upload", upload_ulp_command))
    application.add_handler(CommandHandler("activity", admin_activity_command))
    application.add_handler(CommandHandler("adminstats", admin_stats_command))
    application.add_handler(CommandHandler("users", admin_users_command))
    
    # Handlers de formato
    application.add_handler(CallbackQueryHandler(format_callback, pattern="^format_"))
    
    # Handler para mensajes de texto
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Iniciar bot CORREGIDO
    print("🤖 NuvixULP Bot Started!")
    print("🎯 Complete Version with All Features")
    print("🚀 Bot is running...")
    
    # SOLUCIÓN: Agregar drop_pending_updates para evitar conflictos
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    main()
