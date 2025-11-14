from flask import Flask, jsonify
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# Configuración
BOT_TOKEN = os.getenv('BOT_TOKEN', '7927690342:AAFKbjYIKPsdh1FHRUctIVwDOfoFshGwNvA')

def init_db():
    """Inicializar base de datos solo para la web"""
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    
    # Solo crear tablas si no existen
    c.execute('''CREATE TABLE IF NOT EXISTS ulp_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  url TEXT NOT NULL,
                  login TEXT NOT NULL,
                  password TEXT NOT NULL,
                  source TEXT,
                  search_count INTEGER DEFAULT 0,
                  added_date DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

def get_stats():
    """Obtener estadísticas para la web"""
    try:
        conn = sqlite3.connect('nuvixlogs.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM ulp_data")
        total_ulp = c.fetchone()[0]
        conn.close()
        return total_ulp
    except:
        return 0

@app.route('/')
def home():
    """Página principal"""
    init_db()
    total_ulp = get_stats()
    
    return f"""
    <html>
        <head>
            <title>🤖 NuvixULP Bot</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 40px; 
                    background: #f0f2f5; 
                    text-align: center;
                }}
                .container {{ 
                    max-width: 800px; 
                    margin: 0 auto; 
                    background: white; 
                    padding: 30px; 
                    border-radius: 10px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
                }}
                h1 {{ color: #2c3e50; }}
                .status {{ 
                    background: #27ae60; 
                    color: white; 
                    padding: 10px; 
                    border-radius: 5px; 
                    margin: 20px 0;
                }}
                .bot-link {{ 
                    display: inline-block; 
                    background: #3498db; 
                    color: white; 
                    padding: 15px 25px; 
                    text-decoration: none; 
                    border-radius: 5px; 
                    margin: 10px 0; 
                    font-size: 18px;
                }}
                .stats {{ 
                    background: #f8f9fa; 
                    padding: 15px; 
                    border-radius: 5px; 
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 NuvixULP Bot</h1>
                <div class="status">✅ Bot is running and active</div>
                
                <div class="stats">
                    <h2>📊 Live Statistics</h2>
                    <p>Total ULP in database: <strong>{total_ulp:,}</strong></p>
                    <p>Last update: <strong>{datetime.now().strftime('%Y-%m-%d %H:%M')}</strong></p>
                </div>
                
                <h2>🚀 Bot Features</h2>
                <ul style="text-align: left; display: inline-block;">
                    <li>🔍 Free ULP searches</li>
                    <li>🌐 Domain, login, password searches</li>
                    <li>📊 Advanced statistics</li>
                    <li>⚡ Unlimited usage</li>
                </ul>
                
                <h2>🔗 Access the Bot</h2>
                <a href="https://t.me/NuvixULP_Bot" class="bot-link" target="_blank">
                    📲 Open in Telegram
                </a>
                
                <p style="margin-top: 30px; color: #666;">
                    <em>🤖 Advanced ULP Search Engine - Always Online!</em>
                </p>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health():
    """Endpoint de salud para Render"""
    return jsonify({
        "status": "healthy", 
        "service": "nuvix-ulp-bot",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/stats')
def stats():
    """Endpoint de estadísticas"""
    total_ulp = get_stats()
    return jsonify({
        "total_ulp": total_ulp,
        "last_update": datetime.now().strftime('%Y-%m-%d %H:%M'),
        "status": "online"
    })

if __name__ == '__main__':
    # Inicializar base de datos
    init_db()
    
    # Iniciar servidor Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
