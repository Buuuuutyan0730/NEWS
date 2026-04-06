"""FX分析ツール 設定ファイル"""
import os

# --- Gemini API ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")

# --- データベース ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "fx_data.db")

# --- 取得間隔（分） ---
FETCH_INTERVAL_MINUTES = 1

# --- 監視するXアカウント ---
X_ACCOUNTS = ["financialjuice", "yahoojpfinance"]

# --- RSSHub設定 ---
RSSHUB_INSTANCES = [
    "https://rsshub.app",
    "https://rsshub.rssforever.com",
    "https://rsshub.moeyy.cn",
]

# --- RSSニュースフィード ---
RSS_FEEDS = [
    {
        "name": "Yahoo Finance JP",
        "url": "https://news.yahoo.co.jp/rss/topics/business.xml",
        "source_id": "rss_yahoo",
    },
    {
        "name": "Reuters JP",
        "url": "https://assets.wor.jp/rss/rdf/reuters/top.rdf",
        "source_id": "rss_reuters",
    },
]

# --- FXフィルタキーワード ---
FX_KEYWORDS = [
    "ドル円", "ドル/円", "USD/JPY", "USDJPY",
    "為替", "円安", "円高", "外国為替",
    "FRB", "FOMC", "米連邦", "パウエル",
    "日銀", "日本銀行", "植田", "金融政策",
    "金利", "利上げ", "利下げ",
    "雇用統計", "CPI", "消費者物価",
    "GDP", "ISM", "PCE",
    "dollar", "yen", "forex", "Fed",
    "BOJ", "rate hike", "rate cut",
    "inflation", "employment", "payroll",
]

# --- 履歴保持日数 ---
HISTORY_RETENTION_DAYS = 365

# --- Flask ---
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = True
