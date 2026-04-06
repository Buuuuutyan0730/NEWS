/**
 * FX ドル円 分析ダッシュボード - メインJavaScript
 */

const REFRESH_INTERVAL = 60 * 1000; // 1分
let autoRefreshTimer = null;
let nextRefreshTime = null;

// ソース名の表示マッピング
const SOURCE_LABELS = {
    investing_calendar: { label: "経済指標", cls: "source-investing" },
    finnhub_calendar:   { label: "経済指標", cls: "source-investing" },
    rss_yahoo:          { label: "Yahoo",    cls: "source-rss" },
    rss_reuters:        { label: "Reuters",  cls: "source-rss" },
    rss_nikkei:         { label: "日経",     cls: "source-rss" },
    x_financialjuice:   { label: "X",        cls: "source-x" },
    x_yahoojpfinance:   { label: "X",        cls: "source-x" },
};

/**
 * データ取得・画面更新
 */
async function fetchAndRender() {
    try {
        const resp = await fetch("/api/today");
        const data = await resp.json();
        renderStats(data.stats);
        renderGauge(data.stats.overall_score);
        renderEvents(data.news);
        renderNews(data.news);
        document.getElementById("lastUpdated").textContent = data.last_updated;
    } catch (e) {
        console.error("データ取得エラー:", e);
    }
}

/**
 * 統計サマリー更新
 */
function renderStats(stats) {
    document.getElementById("yenWeakCount").textContent = stats.yen_weak;
    document.getElementById("yenStrongCount").textContent = stats.yen_strong;
    document.getElementById("totalCount").textContent = stats.total;
}

/**
 * 総合ゲージ更新
 * score: -5(円高) ～ 0(中立) ～ +5(円安)
 */
function renderGauge(score) {
    const marker = document.getElementById("gaugeMarker");
    const badge = document.getElementById("overallBadge");

    // スコアを 0%~100% に変換 (-5=0%, 0=50%, +5=100%)
    const pct = Math.max(0, Math.min(100, (score + 5) / 10 * 100));
    marker.style.left = pct + "%";

    let label, cls;
    if (score > 1) {
        label = "円安傾向";
        cls = "bg-danger";
    } else if (score > 0.3) {
        label = "やや円安";
        cls = "bg-warning text-dark";
    } else if (score < -1) {
        label = "円高傾向";
        cls = "bg-info text-dark";
    } else if (score < -0.3) {
        label = "やや円高";
        cls = "bg-info text-dark";
    } else {
        label = "中立";
        cls = "bg-secondary";
    }

    if (score === 0 && document.getElementById("totalCount").textContent === "0") {
        label = "データなし";
        cls = "bg-secondary";
    }

    badge.textContent = `${label} (${score >= 0 ? "+" : ""}${score.toFixed(2)})`;
    badge.className = `badge fs-6 ${cls}`;
}

/**
 * 経済イベント一覧
 */
function renderEvents(news) {
    const tbody = document.getElementById("eventsBody");
    const events = news.filter(n =>
        n.source === "investing_calendar" || n.source === "finnhub_calendar"
    );

    document.getElementById("eventCount").textContent = events.length + "件";

    if (events.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">本日の経済イベントはありません</td></tr>';
        return;
    }

    tbody.innerHTML = events.map(e => {
        const time = extractTime(e.published_at);
        const dir = renderDirection(e.direction);
        const impact = renderImpactBar(e.impact);
        const title = e.url
            ? `<a href="${e.url}" target="_blank" class="news-link">${escHtml(e.title)}</a>`
            : escHtml(e.title);
        const reason = e.ai_reason || '<span class="text-muted">-</span>';
        return `<tr>
            <td>${time}</td>
            <td>${title}</td>
            <td class="text-center">${dir}</td>
            <td class="text-center">${impact}</td>
            <td class="d-none d-md-table-cell small">${escHtml(reason)}</td>
        </tr>`;
    }).join("");
}

/**
 * ニュース＆X投稿一覧
 */
function renderNews(news) {
    const tbody = document.getElementById("newsBody");
    const items = news.filter(n =>
        n.source !== "investing_calendar" && n.source !== "finnhub_calendar"
    );

    document.getElementById("newsCount").textContent = items.length + "件";

    if (items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">ニュースはまだありません</td></tr>';
        return;
    }

    tbody.innerHTML = items.map(n => {
        const time = extractTime(n.published_at || n.fetched_at);
        const src = SOURCE_LABELS[n.source] || { label: n.source, cls: "source-rss" };
        const dir = renderDirection(n.direction);
        const impact = renderImpactBar(n.impact);
        const title = n.url
            ? `<a href="${n.url}" target="_blank" class="news-link">${escHtml(n.title)}</a>`
            : escHtml(n.title);
        const reason = n.ai_reason || '<span class="text-muted">-</span>';
        return `<tr>
            <td>${time}</td>
            <td><span class="source-badge ${src.cls}">${src.label}</span></td>
            <td>${title}</td>
            <td class="text-center">${dir}</td>
            <td class="text-center">${impact}</td>
            <td class="d-none d-md-table-cell small">${escHtml(reason)}</td>
        </tr>`;
    }).join("");
}

/**
 * 方向バッジ生成
 */
function renderDirection(direction) {
    if (!direction || direction === "中立") {
        return '<span class="direction-badge direction-neutral">中立</span>';
    } else if (direction === "円安") {
        return '<span class="direction-badge direction-yen-weak">円安↗</span>';
    } else if (direction === "円高") {
        return '<span class="direction-badge direction-yen-strong">円高↘</span>';
    }
    return '<span class="direction-badge direction-neutral">-</span>';
}

/**
 * 影響度バー生成 (1-5)
 */
function renderImpactBar(impact) {
    if (!impact) return '<span class="text-muted">-</span>';
    let html = '<div class="impact-bar">';
    for (let i = 1; i <= 5; i++) {
        let cls = "";
        if (i <= impact) {
            if (impact <= 2) cls = "active-low";
            else if (impact <= 3) cls = "active-mid";
            else cls = "active-high";
        }
        html += `<div class="bar-segment ${cls}"></div>`;
    }
    html += "</div>";
    return html;
}

/**
 * 時刻抽出 (HH:MM)
 */
function extractTime(dateStr) {
    if (!dateStr) return "-";
    const match = dateStr.match(/(\d{2}):(\d{2})/);
    return match ? `${match[1]}:${match[2]}` : dateStr.substring(11, 16) || "-";
}

/**
 * HTMLエスケープ
 */
function escHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

/**
 * 手動更新
 */
async function manualRefresh() {
    const btn = document.getElementById("refreshBtn");
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> 更新中...';

    try {
        // サーバー側の手動取得APIを呼ぶ
        await fetch("/api/fetch", { method: "POST" });
        await fetchAndRender();
    } catch (e) {
        console.error("手動更新エラー:", e);
    }

    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> 手動更新';
    resetAutoRefresh();
}

/**
 * 自動更新タイマー
 */
function resetAutoRefresh() {
    if (autoRefreshTimer) clearInterval(autoRefreshTimer);
    nextRefreshTime = Date.now() + REFRESH_INTERVAL;

    autoRefreshTimer = setInterval(() => {
        const remaining = Math.max(0, Math.ceil((nextRefreshTime - Date.now()) / 1000));
        document.getElementById("nextUpdate").textContent = remaining + "秒後";

        if (remaining <= 0) {
            fetchAndRender();
            nextRefreshTime = Date.now() + REFRESH_INTERVAL;
        }
    }, 1000);
}

// 初期化
document.addEventListener("DOMContentLoaded", () => {
    fetchAndRender();
    resetAutoRefresh();
});
