"""RSSニュース取得モジュール

Yahoo Finance JP、Reuters JPなどのRSSフィードからFX関連ニュースを取得。
feedparserの代わりにatomaを使用。
"""
import requests
import atoma
from datetime import datetime
from database.models import insert_news
import config

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def _matches_keywords(text):
    """FX関連キーワードにマッチするか判定"""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in config.FX_KEYWORDS)


def _parse_rss(url):
    """RSSフィードをパースして記事リストを返す"""
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        content = resp.content

        # Atom形式を試す
        try:
            feed = atoma.parse_atom_bytes(content)
            for entry in feed.entries:
                title = entry.title.value if hasattr(entry.title, "value") else str(entry.title)
                # コンテンツ取得
                body = ""
                if entry.content:
                    body = entry.content[0].value
                elif entry.summary:
                    body = entry.summary.value if hasattr(entry.summary, "value") else str(entry.summary)
                # URL
                link = ""
                if entry.links:
                    link = entry.links[0].href
                elif entry.id_:
                    link = entry.id_
                # 日時
                pub = entry.updated or entry.published
                pub_str = pub.strftime("%Y-%m-%d %H:%M:%S") if pub else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                items.append({
                    "title": title,
                    "content": body,
                    "url": link,
                    "published_at": pub_str,
                })
            return items
        except Exception:
            pass

        # RSS 2.0形式を試す
        try:
            feed = atoma.parse_rss_bytes(content)
            for entry in feed.items:
                title = entry.title or ""
                body = entry.description or ""
                link = entry.link or ""
                pub = entry.pub_date
                pub_str = pub.strftime("%Y-%m-%d %H:%M:%S") if pub else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                items.append({
                    "title": title,
                    "content": body,
                    "url": link,
                    "published_at": pub_str,
                })
            return items
        except Exception:
            pass

        # RDF形式（RSS 1.0）を試す
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "lxml-xml")
            for item in soup.find_all("item"):
                title = item.find("title").get_text(strip=True) if item.find("title") else ""
                body = item.find("description").get_text(strip=True) if item.find("description") else ""
                link = item.find("link").get_text(strip=True) if item.find("link") else ""
                pub_el = item.find("dc:date") or item.find("pubDate")
                pub_str = pub_el.get_text(strip=True) if pub_el else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                items.append({
                    "title": title,
                    "content": body,
                    "url": link,
                    "published_at": pub_str,
                })
            return items
        except Exception:
            pass

    except Exception as e:
        print(f"[RSS] フィード取得失敗 ({url}): {e}")

    return items


def fetch_rss_news():
    """全RSSフィードからFX関連ニュースを取得してDBに保存"""
    total_items = []
    saved = 0

    for feed_conf in config.RSS_FEEDS:
        name = feed_conf["name"]
        url = feed_conf["url"]
        source_id = feed_conf["source_id"]
        needs_filter = feed_conf.get("filter", True)

        items = _parse_rss(url)
        print(f"[RSS] {name}: {len(items)}件取得")

        for item in items:
            if needs_filter:
                combined_text = f"{item['title']} {item['content']}"
                if not _matches_keywords(combined_text):
                    continue

            # HTMLタグ除去（簡易）
            from bs4 import BeautifulSoup
            clean_content = BeautifulSoup(item["content"], "html.parser").get_text() if item["content"] else ""

            inserted = insert_news(
                source=source_id,
                title=item["title"],
                content=clean_content[:1000],
                url=item["url"],
                published_at=item["published_at"],
            )
            if inserted:
                saved += 1

            total_items.append({
                "source": source_id,
                "title": item["title"],
                "content": clean_content[:1000],
                "url": item["url"],
                "published_at": item["published_at"],
            })

    print(f"[RSS] FX関連ニュース: {len(total_items)}件抽出、{saved}件新規保存")
    return total_items


if __name__ == "__main__":
    from database.models import init_db
    init_db()
    news = fetch_rss_news()
    for n in news[:5]:
        print(f"  [{n['source']}] {n['title']}")
