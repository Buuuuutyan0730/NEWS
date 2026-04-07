"""経済イベントカレンダー取得モジュール

複数ソースから当日の経済イベントを取得。
優先順: Investing.com → Trading Economics RSS → 手動定義の主要イベント
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


def fetch_investing_calendar():
    """Investing.comから経済カレンダーを取得"""
    url = "https://www.investing.com/economic-calendar/"
    items = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # 経済カレンダーテーブルの行を取得
        rows = soup.select("tr.js-event-item, tr[data-event-datetime]")

        for row in rows:
            try:
                # 通貨フィルタ（USD, JPYのみ）
                currency = ""
                currency_el = row.select_one("td.flagCur span, td.flag span")
                if currency_el:
                    currency = currency_el.get_text(strip=True)
                # data属性からも確認
                if not currency:
                    flag_el = row.select_one("td.flag img, span.cemark")
                    if flag_el:
                        title_attr = flag_el.get("title", "") or flag_el.get("alt", "")
                        if "United States" in title_attr or "US" in title_attr:
                            currency = "USD"
                        elif "Japan" in title_attr:
                            currency = "JPY"

                if currency not in ("USD", "JPY"):
                    continue

                # 時刻
                time_el = row.select_one("td.time, td:first-child")
                time_str = time_el.get_text(strip=True) if time_el else ""

                # イベント名
                event_el = row.select_one("td.event a, a[href*='economic-calendar']")
                event_name = event_el.get_text(strip=True) if event_el else ""
                event_url = ""
                if event_el and event_el.get("href"):
                    href = event_el["href"]
                    event_url = href if href.startswith("http") else "https://www.investing.com" + href

                # 重要度（星マーク）
                importance = 0
                icons = row.select("i.grayFullBullishIcon, i[class*='bull']")
                importance = len(icons) if icons else 0

                if not event_name:
                    continue

                detail_parts = [f"[{currency}] {event_name}"]
                if time_str:
                    detail_parts.append(f"時刻: {time_str}")
                detail_parts.append(f"重要度: {'★' * importance if importance else '−'}")
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


def fetch_alternative_calendar():
    """代替: 無料の経済カレンダーAPI/RSSから取得"""
    items = []
    today = datetime.now().strftime("%Y-%m-%d")

    # 方法1: ForexFactory風のRSSフィード
    calendar_urls = [
        "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    ]

    for url in calendar_urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            data = resp.json()
            for evt in data:
                country = evt.get("country", "")
                if country not in ("USD", "JPY"):
                    continue

                event_date = evt.get("date", "")
                # 今日のイベントのみ
                if today not in event_date:
                    continue

                event_name = evt.get("title", "")
                impact = evt.get("impact", "")
                forecast = evt.get("forecast", "")
                previous = evt.get("previous", "")

                importance = {"Low": 1, "Medium": 2, "High": 3}.get(impact, 0)

                detail_parts = [f"[{country}] {event_name}"]
                detail_parts.append(f"重要度: {'★' * importance if importance else '−'}")
                if forecast:
                    detail_parts.append(f"予想: {forecast}")
                if previous:
                    detail_parts.append(f"前回: {previous}")
                content = " | ".join(detail_parts)

                title = f"[{country}] {event_name}"
                # 時刻を抽出
                time_str = ""
                if "T" in event_date:
                    time_str = event_date.split("T")[1][:5]
                pub_time = f"{today} {time_str}" if time_str else today

                items.append({
                    "source": "calendar_ff",
                    "title": title,
                    "content": content,
                    "url": "",
                    "published_at": pub_time,
                })

            if items:
                print(f"[Calendar/FF] {len(items)}件の経済イベントを取得")
                return items

        except Exception as e:
            print(f"[Calendar/FF] 取得失敗: {e}")
            continue

    return items


def fetch_economic_events():
    """経済イベントを取得してDBに保存"""
    # Investing.com を最初に試行
    items = fetch_investing_calendar()

    # 失敗時は代替APIにフォールバック
    if not items:
        print("[Economic] Investingから取得できず、代替APIにフォールバック")
        items = fetch_alternative_calendar()

    if not items:
        print("[Economic] 経済イベント: 取得できませんでした（休日の可能性あり）")
        return items

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
