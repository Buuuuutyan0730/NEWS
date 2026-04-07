"""Gemini AI分析モジュール

ニュース・投稿文章を読み解き、ドル円への影響（方向・大きさ）を判定。
"""
import json
import time
from google import genai
from database.models import get_unanalyzed_news, update_analysis
import config

# 分析プロンプト
ANALYSIS_PROMPT = """あなたはFX（ドル円 USD/JPY）の専門アナリストです。
以下のニュースまたは投稿を読み、ドル円相場への影響を分析してください。

【ニュース本文】
{text}

【回答ルール】
- 必ず以下のJSON形式のみで回答してください。説明文は不要です。
- directionは「円安」「円高」「中立」のいずれか。
  - 円安 = ドル高/円安方向（USD/JPYが上昇する要因）
  - 円高 = ドル安/円高方向（USD/JPYが下落する要因）
- impactは1〜5の整数（1=ほぼ影響なし, 2=小さい, 3=中程度, 4=大きい, 5=極めて大きい）
- reasonは判定理由を日本語50文字以内で。

【回答形式】
{{"direction": "円安", "impact": 3, "reason": "理由をここに"}}"""


def _init_client():
    """Gemini APIクライアントを初期化"""
    if config.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        print("[Gemini] APIキーが未設定です。config.pyのGEMINI_API_KEYを設定してください。")
        return None
    return genai.Client(api_key=config.GEMINI_API_KEY)


def analyze_single(text, client=None):
    """単一のテキストを分析"""
    if client is None:
        client = _init_client()
    if client is None:
        return None

    prompt = ANALYSIS_PROMPT.format(text=text[:2000])

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        # レスポンスからJSONを抽出
        result_text = response.text.strip()
        # コードブロックで囲まれている場合の処理
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            result_text = "\n".join(lines[1:-1])

        result = json.loads(result_text)

        # バリデーション
        direction = result.get("direction", "中立")
        if direction not in ("円安", "円高", "中立"):
            direction = "中立"

        impact = result.get("impact", 1)
        if not isinstance(impact, int) or impact < 1 or impact > 5:
            impact = max(1, min(5, int(impact)))

        reason = result.get("reason", "")[:100]

        return {
            "direction": direction,
            "impact": impact,
            "reason": reason,
        }

    except json.JSONDecodeError as e:
        print(f"[Gemini] JSON解析エラー: {e}")
        return None
    except Exception as e:
        print(f"[Gemini] 分析エラー: {e}")
        return None


def analyze_unprocessed():
    """未分析のニュースを一括分析してDB更新"""
    items = get_unanalyzed_news()
    if not items:
        print("[Gemini] 未分析のニュースはありません")
        return 0

    client = _init_client()
    if client is None:
        return 0

    analyzed_count = 0
    for item in items:
        text = f"{item['title']}\n{item.get('content', '')}"
        result = analyze_single(text, client)

        if result:
            update_analysis(
                item["id"],
                result["direction"],
                result["impact"],
                result["reason"],
            )
            analyzed_count += 1
            print(f"  [{result['direction']}|{result['impact']}] {item['title'][:50]}")
        else:
            # 分析失敗時は中立・影響1としてマーク（再試行防止）
            update_analysis(item["id"], "中立", 1, "分析失敗")
            analyzed_count += 1

        # レートリミット対策（無料枠: 15 RPM）
        time.sleep(4.5)

    print(f"[Gemini] {analyzed_count}/{len(items)}件を分析完了")
    return analyzed_count


def generate_daily_summary(news_items):
    """その日のニュースから日次サマリーを生成"""
    client = _init_client()
    if client is None:
        return "APIキー未設定のためサマリー生成不可"

    if not news_items:
        return "本日のニュースはありませんでした。"

    # ニュース一覧を整形
    news_texts = []
    for n in news_items[:30]:  # 最大30件
        direction = n.get("direction", "未分析")
        impact = n.get("impact", "-")
        news_texts.append(f"- [{direction}|影響{impact}] {n['title']}")

    news_list = "\n".join(news_texts)

    prompt = f"""あなたはFX（ドル円）の専門アナリストです。
以下は本日のFX関連ニュース一覧です。これらを総合的に分析し、
本日のドル円相場の動向を200文字以内の日本語で簡潔に要約してください。

【本日のニュース】
{news_list}

【回答】要約のみを出力してください。"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()[:500]
    except Exception as e:
        print(f"[Gemini] サマリー生成エラー: {e}")
        return "サマリー生成に失敗しました。"


if __name__ == "__main__":
    # テスト実行
    print("=== Gemini分析テスト ===")
    test_text = "米FRBが0.25%の利上げを決定。パウエル議長はインフレ抑制の姿勢を強調。"
    result = analyze_single(test_text)
    if result:
        print(f"方向: {result['direction']}, 影響度: {result['impact']}, 理由: {result['reason']}")
    else:
        print("APIキー未設定またはAPI接続エラー（実環境で動作確認してください）")
