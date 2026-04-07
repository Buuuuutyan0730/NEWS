# FX分析ツール 引き継ぎ資料

## プロジェクト概要
ドル円（USD/JPY）に関する経済イベント・金融ニュース・X投稿を自動収集し、
Gemini AIで「円安/円高」方向と影響度（1〜5）を判定、Webブラウザで一覧表示するツール。

## リポジトリ
- GitHub: `buuuuutyan0730/news`
- 開発ブランチ: `claude/fx-analysis-tool-UbfaC`

## ユーザー環境
- **OS**: Windows 10 (Version 10.0.26200.8039)
- **Python**: 3.13（Microsoft Store版）
- **PCユーザー名**: Hayashi Ibuki
- **ダウンロード先**: `C:\Users\Hayashi Ibuki\Downloads\`
- **gitは未インストール**（インストール推奨済み、次回対応予定）

## Gemini APIキー
- キー: `AIzaSyBe6wR7lDRtQZQObPmsSQvIeTwrEIS-Rco`
- **GitHubには絶対にアップしないこと**（.gitignoreでstart.batを除外済み）
- start.bat内に環境変数として設定する運用

## 技術スタック
| 項目 | 技術 |
|------|------|
| バックエンド | Python 3.13 + Flask |
| フロントエンド | HTML + Bootstrap 5 + vanilla JS |
| DB | SQLite |
| AI分析 | Google Gemini API (gemini-2.5-flash) |
| スケジューラ | APScheduler (1分間隔) |
| RSSパーサー | atoma (feedparserはsgmllib3kビルド失敗のため使用不可) |

## ファイル構成
```
NEWS/
├── app.py                      # Flask本体 + スケジューラ + 全APIエンドポイント
├── config.py                   # 設定（APIキー、フィード、キーワード等）
├── requirements.txt            # 依存パッケージ
├── start.bat                   # 起動用（.gitignore対象、ユーザーが手動作成）
├── PLAN.md                     # 開発計画書
├── HANDOFF.md                  # 本資料
├── .gitignore
├── collectors/
│   ├── economic_calendar.py    # 経済イベント取得（Investing.com → ForexFactory）
│   ├── rss_news.py             # RSSニュース取得（Yahoo, Reuters, NHK）
│   └── x_fetcher.py            # X投稿取得（RSSHub → Nitter）
├── analyzer/
│   └── gemini_analyzer.py      # Gemini AI分析（方向+影響度判定）
├── database/
│   ├── models.py               # SQLiteテーブル定義・CRUD
│   └── fx_data.db              # DBファイル（自動生成、.gitignore対象）
├── templates/
│   ├── base.html               # 共通レイアウト（ナビバー）
│   ├── dashboard.html          # メインダッシュボード
│   └── calendar.html           # カレンダー履歴画面
└── static/
    ├── css/style.css           # ダークテーマCSS
    └── js/dashboard.js         # ダッシュボードJS（自動更新、ゲージ等）
```

## 現在の動作状況

### 動いているもの
| 機能 | 状態 | 備考 |
|------|------|------|
| 経済イベント (ForexFactory) | OK | 11件取得成功 |
| RSS (Yahoo/Reuters) | OK | 28件取得→1件FX関連抽出 |
| X投稿 (RSSHub) | OK | 37件取得成功（rsshub.pseudoyu.com経由） |
| Gemini AI分析 | 部分的 | 503エラー多発（一時的混雑）、リトライ機能あり |
| ダッシュボード画面 | OK | http://localhost:5000 で表示確認済み |
| カレンダー画面 | 未確認 | コード実装済みだが実環境での確認はまだ |

### 問題・改善が必要なもの
1. **Investing.comスクレイピング**: 0件取得（JSレンダリングが必要な可能性）→ ForexFactoryで代替中
2. **NHK RSS**: 404エラー（URLが間違っている可能性）→ 要修正
3. **RSSキーワードフィルタ**: 28件中1件しか通らない → キーワード追加orフィルタ緩和の余地あり
4. **Gemini 503エラー**: 一時的だがリトライで全件処理しきれない → リトライ回数やモデル(gemini-2.5-flash-lite等)の検討
5. **ダッシュボード画面の表示確認**: ユーザーからの画面キャプチャはまだもらっていない

## start.bat の内容（ユーザーが手動作成）
```bat
@echo off
cd /d "%~dp0"
pip install -r requirements.txt
set GEMINI_API_KEY=AIzaSyBe6wR7lDRtQZQObPmsSQvIeTwrEIS-Rco
python app.py
pause
```

## 開発環境の注意点
- この開発環境（Claude Code）は**外部通信がプロキシでブロック**されている
- そのためAPI呼び出し・スクレイピングの実テストは**ユーザーのPC上でしかできない**
- ユーザーにターミナル出力をコピペしてもらって問題を特定する運用

## 次にやるべきこと
1. **gitインストールの案内** → ZIPダウンロード地獄から脱却
2. **NHK RSS URLの修正**（404エラー）
3. **Gemini分析の安定化**（503対策の強化 or モデル変更）
4. **ダッシュボード画面のキャプチャ確認** → UIの微調整
5. **RSSフィルタの改善** → より多くのFX関連ニュースを拾えるように
