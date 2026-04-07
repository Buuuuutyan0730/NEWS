"""X（旧Twitter）投稿取得モジュール

RSSHub / Nitter経由でX投稿をRSSとして取得。
複数インスタンスを順番に試してフォールバック。
"""
import requests
import atoma
from bs4 import BeautifulSoup
from datetime import datetime
from database.models import insert_news
import config

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Nitter公開インスタンス（生存状況により変動）
NITTER_INSTANCES = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.1d4.us",
    "https://nitter.kavin.rocks",
]


def _try_rsshub(account):
    """RSSHub経由でX投稿を取得"""
    for base_url in config.RSSHUB_INSTANCES:
        url = f"{base_url}/twitter/user/{account}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                items = _parse_feed(resp.content, account)
                if items:
                    print(f"[X/RSSHub] @{account}: {len(items)}件取得 ({base_url})")
                    return items
        except Exception as e:
            print(f"[X/RSSHub] {base_url} 失敗: {e}")
            continue

    return []


def _try_nitter(account):
    """Nitter経由でX投稿をRSSとして取得"""
    for instance in NITTER_INSTANCES:
        url = f"{instance}/{account}/rss"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                items = _parse_feed(resp.content, account)
                if items:
                    print(f"[X/Nitter] @{account}: {len(items)}件取得 ({instance})")
                    return items
        except Exception as e:
            print(f"[X/Nitter] {instance} 失敗: {e}")
            continue

    return []


def _parse_feed(content, account):
    """RSS/Atomフィードをパースして投稿リストに変換"""
    items = []

    # Atom形式
    try:
        feed = atoma.parse_atom_bytes(content)
        for entry in feed.entries:
            title = entry.title.value if hasattr(entry.title, "value") else str(entry.title)
            body = ""
            if entry.content:
                body = entry.content[0].value
            elif entry.summary:
                body = entry.summary.value if hasattr(entry.summary, "value") else str(entry.summary)
            link = entry.links[0].href if entry.links else ""
            pub = entry.updated or entry.published
            pub_str = pub.strftime("%Y-%m-%d %H:%M:%S") if pub else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # HTMLタグ除去
            clean_text = BeautifulSoup(body, "html.parser").get_text() if body else title

            items.append({
                "title": clean_text[:200],
                "content": clean_text,
                "url": link,
                "published_at": pub_str,
            })
        return items
    except Exception:
        pass

    # RSS 2.0形式
    try:
        feed = atoma.parse_rss_bytes(content)
        for entry in feed.items:
            title = entry.title or ""
            body = entry.description or ""
            link = entry.link or ""
            pub = entry.pub_date
            pub_str = pub.strftime("%Y-%m-%d %H:%M:%S") if pub else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            clean_text = BeautifulSoup(body, "html.parser").get_text() if body else title

            items.append({
                "title": clean_text[:200],
                "content": clean_text,
                "url": link,
                "published_at": pub_str,
            })
        return items
    except Exception:
        pass

    return items


def fetch_x_posts():
    """全監視アカウントのX投稿を取得してDBに保存"""
    all_items = []
    saved = 0

    for account in config.X_ACCOUNTS:
        source_id = f"x_{account}"

        # RSSHub → Nitter の順で試行
        items = _try_rsshub(account)
        if not items:
            items = _try_nitter(account)

        if not items:
            print(f"[X] @{account}: 取得できませんでした（全インスタンス失敗）")
            continue

        for item in items:
            inserted = insert_news(
                source=source_id,
                title=item["title"],
                content=item["content"],
                url=item["url"],
                published_at=item["published_at"],
            )
            if inserted:
                saved += 1

            all_items.append({
                "source": source_id,
                **item,
            })

    print(f"[X] 合計: {len(all_items)}件取得、{saved}件新規保存")
    return all_items


if __name__ == "__main__":
    from database.models import init_db
    init_db()
    posts = fetch_x_posts()
    for p in posts[:5]:
        print(f"  [@{p['source']}] {p['title'][:80]}")
