"""FX（ドル円）情報収集・分析ツール メインアプリケーション"""
from flask import Flask, render_template, jsonify, request
from database.models import (
    init_db, get_today_news, get_news_by_date,
    get_daily_summary, get_calendar_data, cleanup_old_data,
    save_daily_summary,
)
from collectors.economic_calendar import fetch_economic_events
from collectors.rss_news import fetch_rss_news
from collectors.x_fetcher import fetch_x_posts
from analyzer.gemini_analyzer import analyze_unprocessed, generate_daily_summary
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import config

app = Flask(__name__)
scheduler = BackgroundScheduler()


# === 定期実行タスク ===

def scheduled_fetch():
    """定期実行: 全ソースからデータ取得 + AI分析"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] === 定期取得開始 ===")
    try:
        fetch_economic_events()
    except Exception as e:
        print(f"[Error] 経済イベント取得: {e}")
    try:
        fetch_rss_news()
    except Exception as e:
        print(f"[Error] RSSニュース取得: {e}")
    try:
        fetch_x_posts()
    except Exception as e:
        print(f"[Error] X投稿取得: {e}")
    try:
        analyze_unprocessed()
    except Exception as e:
        print(f"[Error] AI分析: {e}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] === 定期取得完了 ===\n")


def daily_maintenance():
    """日次メンテナンス: サマリー生成 + 古いデータ削除"""
    yesterday = datetime.now().strftime("%Y-%m-%d")
    news = get_today_news()
    if news:
        summary_text = generate_daily_summary(news)
        yen_weak = sum(1 for n in news if n.get("direction") == "円安")
        yen_strong = sum(1 for n in news if n.get("direction") == "円高")
        analyzed = [n for n in news if n.get("impact")]
        avg_imp = sum(n["impact"] for n in analyzed) / len(analyzed) if analyzed else 0
        save_daily_summary(yesterday, len(news), yen_weak, yen_strong, round(avg_imp, 1), summary_text)
        print(f"[Daily] サマリー保存完了: {yesterday}")
    cleanup_old_data()


# === APIエンドポイント ===

@app.route("/")
def dashboard():
    """メインダッシュボード"""
    return render_template("dashboard.html")


@app.route("/api/today")
def api_today():
    """本日のニュース一覧API"""
    news = get_today_news()
    yen_weak = sum(1 for n in news if n.get("direction") == "円安")
    yen_strong = sum(1 for n in news if n.get("direction") == "円高")
    analyzed = [n for n in news if n.get("analyzed")]
    avg_impact = (
        sum(n["impact"] for n in analyzed if n.get("impact"))
        / len(analyzed)
        if analyzed
        else 0
    )

    total_score = 0
    score_count = 0
    for n in analyzed:
        if n.get("impact") and n.get("direction"):
            if n["direction"] == "円安":
                total_score += n["impact"]
            elif n["direction"] == "円高":
                total_score -= n["impact"]
            score_count += 1
    overall_score = total_score / score_count if score_count else 0

    return jsonify({
        "news": news,
        "stats": {
            "total": len(news),
            "yen_weak": yen_weak,
            "yen_strong": yen_strong,
            "avg_impact": round(avg_impact, 1),
            "overall_score": round(overall_score, 2),
        },
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/api/fetch", methods=["POST"])
def api_manual_fetch():
    """手動でデータ取得・分析を実行"""
    scheduled_fetch()
    return jsonify({"status": "ok", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})


@app.route("/calendar")
def calendar_view():
    """カレンダー履歴画面"""
    return render_template("calendar.html")


@app.route("/api/calendar/<int:year>/<int:month>")
def api_calendar(year, month):
    """カレンダーデータAPI"""
    data = get_calendar_data(year, month)
    return jsonify(data)


@app.route("/api/daily/<date_str>")
def api_daily(date_str):
    """指定日の詳細API"""
    news = get_news_by_date(date_str)
    summary = get_daily_summary(date_str)
    return jsonify({"news": news, "summary": summary})


if __name__ == "__main__":
    init_db()

    # スケジューラ設定
    scheduler.add_job(
        scheduled_fetch,
        "interval",
        minutes=config.FETCH_INTERVAL_MINUTES,
        id="fetch_job",
        next_run_time=datetime.now(),  # 起動直後に1回実行
    )
    scheduler.add_job(
        daily_maintenance,
        "cron",
        hour=23, minute=55,
        id="daily_job",
    )
    scheduler.start()

    print("=" * 50)
    print(" FX ドル円 分析ツール 起動中...")
    print(f" http://localhost:{config.FLASK_PORT}")
    print(f" 自動取得間隔: {config.FETCH_INTERVAL_MINUTES}分")
    print("=" * 50)

    try:
        app.run(
            host=config.FLASK_HOST,
            port=config.FLASK_PORT,
            debug=False,  # APSchedulerとの競合を避けるためdebug=False
        )
    finally:
        scheduler.shutdown()
