import sqlite3
import os
from datetime import datetime, timedelta
import calendar

DB_PATH = os.path.join(os.path.dirname(__file__), "tokens.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            provider TEXT,
            model TEXT,
            request_tokens INTEGER,
            response_tokens INTEGER,
            total_tokens INTEGER
        )
    """)
    conn.commit()
    conn.close()

def insert_usage(provider: str, model: str, request_tokens: int, response_tokens: int):
    # Fallback für leere Werte
    if not request_tokens: request_tokens = 0
    if not response_tokens: response_tokens = 0
    total_tokens = request_tokens + response_tokens

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO token_usage (timestamp, provider, model, request_tokens, response_tokens, total_tokens)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), provider, model, request_tokens, response_tokens, total_tokens))
    conn.commit()
    conn.close()

def get_usage_stats(timeframe='all'):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    where_clause = ""
    if timeframe == 'day':
        where_clause = "WHERE timestamp >= datetime('now', '-1 day')"
    elif timeframe == 'week':
        where_clause = "WHERE timestamp >= datetime('now', '-7 days')"
    elif timeframe == 'month':
        where_clause = "WHERE timestamp >= datetime('now', '-30 days')"
        
    query = f"""
        SELECT provider, model, SUM(request_tokens), SUM(response_tokens), SUM(total_tokens)
        FROM token_usage
        {where_clause}
        GROUP BY provider, model
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    stats = []
    for row in rows:
        stats.append({
            "provider": row[0],
            "model": row[1],
            "request_tokens": row[2] or 0,
            "response_tokens": row[3] or 0,
            "total_tokens": row[4] or 0
        })
    return stats

def get_usage_timeline(unit='week', offset=0):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now()
    
    start_date = None
    end_date = None
    time_format = "%Y-%m-%d"
    
    if unit == 'day':
        target_date = now - timedelta(days=offset)
        start_date = target_date.replace(hour=0, minute=0, second=0).isoformat()
        end_date = target_date.replace(hour=23, minute=59, second=59).isoformat()
        time_format = "%Y-%m-%d %H:00"
    elif unit == 'week':
        # Woche startet Montag (0)
        start_of_week = now - timedelta(days=now.weekday())
        target_week_start = start_of_week - timedelta(weeks=offset)
        target_week_start = target_week_start.replace(hour=0, minute=0, second=0)
        start_date = target_week_start.isoformat()
        end_date = (target_week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)).isoformat()
    elif unit == 'month':
        # Relativ komplexer Monatsoffset
        m = now.month - offset - 1
        y = now.year + m // 12
        m = m % 12 + 1
        last_day = calendar.monthrange(y, m)[1]
        start_date = datetime(y, m, 1, 0, 0, 0).isoformat()
        end_date = datetime(y, m, last_day, 23, 59, 59).isoformat()
    elif unit == 'all':
        time_format = "%Y-%m" # Gruppiere nach Monat für all-time
        
    where_clause = ""
    params = []
    if start_date and end_date:
        where_clause = "WHERE timestamp >= ? AND timestamp <= ?"
        params = [start_date, end_date]
        
    query = f"""
        SELECT strftime('{time_format}', timestamp) as time_bucket, provider, model, SUM(request_tokens), SUM(response_tokens), SUM(total_tokens)
        FROM token_usage
        {where_clause}
        GROUP BY time_bucket, provider, model
        ORDER BY time_bucket ASC
    """
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    stats = []
    for row in rows:
        stats.append({
            "time_bucket": row[0],
            "provider": row[1],
            "model": row[2],
            "request_tokens": row[3] or 0,
            "response_tokens": row[4] or 0,
            "total_tokens": row[5] or 0
        })
    return stats

# Initialisiere die DB beim Import
init_db()
