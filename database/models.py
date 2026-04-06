"""SQLiteデータベース初期化・操作モジュール"""
import sqlite3
import os
from datetime import datetime, timedelta
import config


def get_connection():
    """DB接続を取得"""
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """テーブル初期化"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            url TEXT,
            published_at DATETIME,
            fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            direction TEXT,
            impact INTEGER,
            ai_reason TEXT,
            analyzed INTEGER DEFAULT 0,
            UNIQUE(source, title, published_at)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_summary (
            date TEXT PRIMARY KEY,
            total_items INTEGER,
            yen_weak_count INTEGER,
            yen_strong_count INTEGER,
            avg_impact REAL,
            summary TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_news_fetched
        ON news_items(fetched_at)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_news_source
        ON news_items(source)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_news_analyzed
        ON news_items(analyzed)
    """)

    conn.commit()
    conn.close()
    print("[DB] データベース初期化完了")


def insert_news(source, title, content=None, url=None, published_at=None):
    """ニュースをDBに挿入（重複はスキップ）"""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO news_items
               (source, title, content, url, published_at)
               VALUES (?, ?, ?, ?, ?)""",
            (source, title, content, url, published_at),
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def get_today_news():
    """本日のニュース一覧を取得"""
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute(
        """SELECT * FROM news_items
           WHERE date(fetched_at) = ?
           ORDER BY fetched_at DESC""",
        (today,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unanalyzed_news():
    """未分析のニュースを取得"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM news_items WHERE analyzed = 0"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_analysis(news_id, direction, impact, reason):
    """分析結果を保存"""
    conn = get_connection()
    conn.execute(
        """UPDATE news_items
           SET direction = ?, impact = ?, ai_reason = ?, analyzed = 1
           WHERE id = ?""",
        (direction, impact, reason, news_id),
    )
    conn.commit()
    conn.close()


def get_daily_summary(date_str):
    """指定日のサマリーを取得"""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM daily_summary WHERE date = ?", (date_str,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_daily_summary(date_str, total, yen_weak, yen_strong, avg_impact, summary):
    """日次サマリーを保存"""
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO daily_summary
           (date, total_items, yen_weak_count, yen_strong_count, avg_impact, summary)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (date_str, total, yen_weak, yen_strong, avg_impact, summary),
    )
    conn.commit()
    conn.close()


def get_news_by_date(date_str):
    """指定日のニュース一覧を取得"""
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM news_items
           WHERE date(fetched_at) = ?
           ORDER BY fetched_at DESC""",
        (date_str,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_calendar_data(year, month):
    """指定月のカレンダー用サマリーデータを取得"""
    conn = get_connection()
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{month + 1:02d}-01"
    rows = conn.execute(
        """SELECT * FROM daily_summary
           WHERE date >= ? AND date < ?
           ORDER BY date""",
        (start, end),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cleanup_old_data():
    """古いデータを削除"""
    conn = get_connection()
    cutoff = (
        datetime.now() - timedelta(days=config.HISTORY_RETENTION_DAYS)
    ).strftime("%Y-%m-%d")
    conn.execute("DELETE FROM news_items WHERE date(fetched_at) < ?", (cutoff,))
    conn.execute("DELETE FROM daily_summary WHERE date < ?", (cutoff,))
    conn.commit()
    conn.close()
    print(f"[DB] {cutoff}より前のデータを削除しました")
