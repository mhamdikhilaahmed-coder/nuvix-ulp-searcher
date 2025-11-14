from flask import Flask, jsonify
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Estadísticas globales
BOT_STATS = {
    "total_ulp": 0,
    "last_update": datetime.now().strftime('%Y-%m-%d %H:%M'),
    "last_added": 0
}

def get_stats():
    conn = sqlite3.connect('nuvixlogs.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM ulp_data")
    total_ulp = c.fetchone()[0]
    conn.close()
    
    BOT_STATS["total_ulp"] = total_ulp
    return BOT_STATS

@app.route('/')
def home():
    stats = get_stats()
    return f"""
    <html>
        <head><title>🤖 NuvixULP Bot</title></head>
        <body>
            <h1>🤖 NuvixULP Bot</h1>
            <p>✅ Bot is running and active</p>
            <p>Total ULP: <strong>{stats['total_ulp']:,}</strong></p>
            <a href="https://t.me/NuvixULP_Bot" target="_blank">📲 Open Bot</a>
        </body>
    </html>
    """

@app.route('/health')
def health():
    stats = get_stats()
    return jsonify({
        "status": "healthy", 
        "bot": "running",
        "total_ulp": stats["total_ulp"]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
