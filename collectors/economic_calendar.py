"""経済イベントカレンダー取得モジュール

Investing.comから当日の経済イベントを取得。
失敗時はFinnHub APIにフォールバック。
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from database.models import insert_news

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# 重要度マッピング
IMPORTANCE_MAP = {
    "bull1": 1,  # 星1つ
    "bull2": 2,
    "bull3": 3,  # 星3つ（最重要）
}


def fetch_investing_calendar():
    """Investing.comから経済カレンダーを取得"""
    url = "https://www.investing.com/economic-calendar/"
    items = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # 経済カレンダーテーブルの行を取得
        rows = soup.select("tr.js-event-item")

        for row in rows:
            try:
                # 通貨フィルタ（USD, JPYのみ）
                currency_el = row.select_one("td.flagCur span")
                if currency_el:
                    currency = currency_el.get_text(strip=True)
                    if currency not in ("USD", "JPY"):
                        continue

                # 時刻
                time_el = row.select_one("td.time")
                time_str = time_el.get_text(strip=True) if time_el else ""

                # イベント名
                event_el = row.select_one("td.event a")
                event_name = event_el.get_text(strip=True) if event_el else ""
                event_url = ""
                if event_el and event_el.get("href"):
                    event_url = "https://www.investing.com" + event_el["href"]

                # 重要度
                importance = 0
                sentiment_el = row.select_one("td.sentiment")
                if sentiment_el:
                    icon = sentiment_el.select_one("i")
                    if icon:
                        for cls, val in IMPORTANCE_MAP.items():
                            if cls in icon.get("class", []):
                                importance = val
                                break

                # 予想値・前回値・結果
                cells = row.select("td")
                actual = ""
                forecast = ""
                previous = ""
                if len(cells) >= 7:
                    actual = cells[4].get_text(strip=True) if cells[4] else ""
                    forecast = cells[5].get_text(strip=True) if cells[5] else ""
                    previous = cells[6].get_text(strip=True) if cells[6] else ""

                if not event_name:
                    continue

                # 詳細テキスト
                detail_parts = [f"[{currency}] {event_name}"]
                if time_str:
                    detail_parts.append(f"時刻: {time_str}")
                detail_parts.append(f"重要度: {'★' * importance if importance else '−'}")
                if forecast:
                    detail_parts.append(f"予想: {forecast}")
                if previous:
                    detail_parts.append(f"前回: {previous}")
                if actual:
                    detail_parts.append(f"結果: {actual}")
                content = " | ".join(detail_parts)

                title = f"[{currency}] {event_name}"
                today = datetime.now().strftime("%Y-%m-%d")
                pub_time = f"{today} {time_str}" if time_str else today

                items.append({
                    "source": "investing_calendar",
                    "title": title,
                    "content": content,
                    "url": event_url,
                    "published_at": pub_time,
                })

            except Exception:
                continue

        print(f"[Investing] {len(items)}件の経済イベントを取得")

    except Exception as e:
        print(f"[Investing] 取得失敗: {e}")

    return items


def fetch_finnhub_calendar():
    """FinnHub APIから経済カレンダーを取得（フォールバック）
    FinnHubは無料APIキー不要で基本的なカレンダーを取得可能
    """
    items = []
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        # FinnHubの無料経済カレンダーエンドポイント
        url = f"https://finnhub.io/api/v1/calendar/economic?from={today}&to={today}"
        resp = requests.get(url, headers={"X-Finnhub-Token": "free"}, timeout=15)

        if resp.status_code == 200:
            data = resp.json()
            events = data.get("economicCalendar", [])

            for evt in events:
                country = evt.get("country", "")
                if country not in ("US", "JP"):
                    continue

                event_name = evt.get("event", "")
                impact = evt.get("impact", "")
                actual = evt.get("actual", "")
                estimate = evt.get("estimate", "")
                prev = evt.get("prev", "")
                time_str = evt.get("time", "")

                importance = {"low": 1, "medium": 2, "high": 3}.get(impact, 0)

                detail_parts = [f"[{country}] {event_name}"]
                detail_parts.append(f"重要度: {'★' * importance if importance else '−'}")
                if estimate:
                    detail_parts.append(f"予想: {estimate}")
                if prev:
                    detail_parts.append(f"前回: {prev}")
                if actual:
                    detail_parts.append(f"結果: {actual}")
                content = " | ".join(detail_parts)

                currency = "USD" if country == "US" else "JPY"
                title = f"[{currency}] {event_name}"
                pub_time = f"{today} {time_str}" if time_str else today

                items.append({
                    "source": "finnhub_calendar",
                    "title": title,
                    "content": content,
                    "url": "",
                    "published_at": pub_time,
                })

            print(f"[FinnHub] {len(items)}件の経済イベントを取得")

        else:
            print(f"[FinnHub] APIエラー: {resp.status_code}")

    except Exception as e:
        print(f"[FinnHub] 取得失敗: {e}")

    return items


def fetch_economic_events():
    """経済イベントを取得してDBに保存（Investing優先、失敗時FinnHub）"""
    items = fetch_investing_calendar()

    if not items:
        print("[Economic] Investingから取得できず、FinnHubにフォールバック")
        items = fetch_finnhub_calendar()

    saved = 0
    for item in items:
        inserted = insert_news(
            source=item["source"],
            title=item["title"],
            content=item["content"],
            url=item["url"],
            published_at=item["published_at"],
        )
        if inserted:
            saved += 1

    print(f"[Economic] {saved}件を新規保存（合計{len(items)}件取得）")
    return items


if __name__ == "__main__":
    from database.models import init_db
    init_db()
    events = fetch_economic_events()
    for e in events[:5]:
        print(f"  {e['title']}")
