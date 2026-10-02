"""
board_html.py — 軍師沙盤看板頁（/）與 archive 頁（/archive）的 HTML 渲染

輸入為 board_model.Board 與 handoff_graph 結果，輸出完整 HTML 頁面字串；
不讀 registry、不呼叫掃描。卡片與 archive 列表只放連結，全文由獨立全文頁
（/handoff）伺服器端渲染 Markdown 呈現。頁面唯一的 JS 是主題切換（html_common.
THEME_SCRIPT）：選擇存於瀏覽器 localStorage，伺服器不持有主題狀態。

CSS class 一律用 `kb-` 前綴，避開原彙整頁負向測試針對的 badge／chip／tlabel／
dlabel／reply-excerpt 字面（看板化計畫 KTD5）。本模組不得匯入 app.main，
共用輔助一律取自 app.html_common（避免循環匯入）。
"""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import quote

from app.board_model import (
    CARD_APPLICATION,
    CARD_HANDOFF,
    CARD_REPORT,
    COLUMN_LABELS,
    COLUMNS,
    LANE_KUNSU,
    Board,
    Card,
)
from app.handoff_detail import KIND_LABELS, HandoffDetail
from app.handoff_graph import LOCATION_ARCHIVE, HandoffGraphResult
from app.html_common import (
    VERIFY_LABELS,
    days_since,
    nav_anchor_id,
    page_shell,
)
from app.markdown_render import render_document

# 單一格子常態顯示的卡片上限，其餘收進「另有 N 筆」（KTD6）
CELL_VISIBLE_LIMIT = 8
# HTML 屬性用的軍師泳道識別：@ 不屬於角色代碼字元集，不與任何角色同名
_KUNSU_ATTR = "@kunsu"

_KIND_TAGS = {CARD_APPLICATION: "申請", CARD_REPORT: "上報"}

_VERIFY_CSS = {
    "needs-deploy": "kb-tag-deploy",
    "testable-now": "kb-tag-now",
    "needs-device": "kb-tag-device",
}

BOARD_CSS = (
    # 色票：:root 為預設主題「墨與朱」；html[data-kb-theme] 覆寫為另三個主題
    # （沙盤／青瓷／夜戰）。切換存在瀏覽器 localStorage，伺服器不持有任何主題狀態
    # （ADR 010 第 1 條零改動）。欄位色一律綁狀態（等待中／待辦／進行中／待驗收）。
    ":root{--kb-ink:#17191c;--kb-muted:#4f5560;--kb-faint:#767c86;"
    "--kb-line:#e1e3e7;--kb-line-strong:#c3c7cd;--kb-canvas:#fff;--kb-card:#fff;"
    "--kb-surface:#f6f6f7;--kb-surface-2:#ededf0;--kb-accent:#1d4ed8;--kb-kunsu:#c2410c;"
    "--kb-col-wait:#f1f2f4;--kb-col-wait-ink:#555b66;--kb-col-todo:#e0ecff;--kb-col-todo-ink:#1d4ed8;"
    "--kb-col-doing:#fff0d6;--kb-col-doing-ink:#b45309;--kb-col-review:#dcfce7;--kb-col-review-ink:#15803d;"
    "--kb-cell-wait:#f8f8f9;--kb-cell-todo:#f6f9ff;--kb-cell-doing:#fffaf0;--kb-cell-review:#f4fcf6;"
    "--kb-mail-bg:#fff7ed;--kb-mail-line:#fdba74;--kb-tag-bg:#ededf0;--kb-tag-ink:#4f5560;"
    "--kb-tag-kind-bg:#ffedd5;--kb-tag-kind-ink:#c2410c;--kb-deploy-bg:#ffedd5;--kb-deploy-ink:#9a3412;"
    "--kb-now-bg:#dcfce7;--kb-now-ink:#15803d;--kb-device-bg:#ede9fe;--kb-device-ink:#6d28d9;"
    "--kb-status-bg:#fae8ff;--kb-status-ink:#86198f;--kb-days:#b45309;--kb-wait-ink:#78350f;"
    "--kb-warn-bg:#fff6e0;--kb-warn-line:#f0c36d;--kb-warn-ink:#8a5a00;"
    "--kb-danger-bg:#fff1f1;--kb-danger-line:#fca5a5;--kb-danger-ink:#b91c1c;"
    "--kb-selection:#dbe7fb;--kb-card-shadow:none;--kb-radius:6px;--kb-lane-kunsu-line:var(--kb-kunsu)}"
    # 沙盤：作戰地圖的沙色與硃砂
    "html[data-kb-theme=a]{--kb-ink:#2a2420;--kb-muted:#5f564e;--kb-faint:#7a716a;"
    "--kb-line:#dcd3c4;--kb-line-strong:#c4b89f;--kb-canvas:#f4efe4;--kb-card:#fffdf8;"
    "--kb-surface:#ebe4d4;--kb-surface-2:#e3dbc8;--kb-accent:#8a3a1c;--kb-kunsu:#b3261e;"
    "--kb-col-wait:#e3dfd6;--kb-col-wait-ink:#5f5a52;--kb-col-todo:#e9dcb8;--kb-col-todo-ink:#5a4a14;"
    "--kb-col-doing:#e8cfa6;--kb-col-doing-ink:#7a4306;--kb-col-review:#cfdcc6;--kb-col-review-ink:#2f5a2a;"
    "--kb-cell-wait:#ece8df;--kb-cell-todo:#f1ead6;--kb-cell-doing:#f3e5d0;--kb-cell-review:#e6ede0;"
    "--kb-mail-bg:#e9e6dc;--kb-mail-line:#c9c2ad;--kb-tag-bg:#e8e1d2;--kb-tag-ink:#5f564e;"
    "--kb-tag-kind-bg:#d9d3c3;--kb-tag-kind-ink:#4a4234;--kb-deploy-bg:#f1d9b3;--kb-deploy-ink:#7a4306;"
    "--kb-now-bg:#d5e3c7;--kb-now-ink:#2f5a2a;--kb-device-bg:#e1d6e6;--kb-device-ink:#5a3a6e;"
    "--kb-status-bg:#e6dcd0;--kb-status-ink:#6b4a2b;--kb-days:#8a3a1c;--kb-wait-ink:#6b4a2b;"
    "--kb-warn-bg:#f3e6c4;--kb-warn-line:#d9bd7a;--kb-warn-ink:#6b4a00;"
    "--kb-danger-bg:#f7dcd6;--kb-danger-line:#e7a79b;--kb-danger-ink:#8d2416;"
    "--kb-selection:#e9d7c2;--kb-radius:8px;--kb-lane-kunsu-line:var(--kb-line-strong)}"
    # 青瓷：冷色作業台，欄首為色帶
    "html[data-kb-theme=b]{--kb-ink:#1b2730;--kb-muted:#4f6270;--kb-faint:#6f8290;"
    "--kb-line:#d5dee3;--kb-line-strong:#b4c4cc;--kb-canvas:#f3f6f7;--kb-card:#fff;"
    "--kb-surface:#e9eff1;--kb-surface-2:#dfe8eb;--kb-accent:#0f6e8c;--kb-kunsu:#2b3a8f;"
    "--kb-col-wait:#c9d3d9;--kb-col-wait-ink:#2f3f49;--kb-col-todo:#bcd9ea;--kb-col-todo-ink:#0f4d6b;"
    "--kb-col-doing:#f2d9a6;--kb-col-doing-ink:#6b4500;--kb-col-review:#b9e3d4;--kb-col-review-ink:#115c45;"
    "--kb-cell-wait:#eceff2;--kb-cell-todo:#e6f1f7;--kb-cell-doing:#f9f1e1;--kb-cell-review:#e4f3ee;"
    "--kb-mail-bg:#e8eefb;--kb-mail-line:#bfcdee;--kb-tag-bg:#e2e9ed;--kb-tag-ink:#4f6270;"
    "--kb-tag-kind-bg:#d6def6;--kb-tag-kind-ink:#2b3a8f;--kb-deploy-bg:#f6dfb8;--kb-deploy-ink:#7a4e00;"
    "--kb-now-bg:#cfeadf;--kb-now-ink:#115c45;--kb-device-bg:#dcdcf3;--kb-device-ink:#3b3b9c;"
    "--kb-status-bg:#e6dff2;--kb-status-ink:#5b3f8a;--kb-days:#9a4a00;--kb-wait-ink:#5b4a3a;"
    "--kb-danger-bg:#fbe3e3;--kb-danger-line:#efb0b0;--kb-danger-ink:#9b2c2c;"
    "--kb-selection:#cfe3ee;--kb-card-shadow:0 1px 2px rgba(27,39,48,.08);--kb-radius:10px;"
    "--kb-lane-kunsu-line:var(--kb-line-strong)}"
    # 夜戰：深色作戰室，狀態色發光
    "html[data-kb-theme=c]{color-scheme:dark;--kb-ink:#e6eaef;--kb-muted:#a7b1bd;--kb-faint:#8b95a1;"
    "--kb-line:#2c343d;--kb-line-strong:#3a4450;--kb-canvas:#14181d;--kb-card:#1e242c;"
    "--kb-surface:#1b2027;--kb-surface-2:#232a33;--kb-accent:#7fb4ff;--kb-kunsu:#f2c66d;"
    "--kb-col-wait:#2a3038;--kb-col-wait-ink:#b7bfc9;--kb-col-todo:#1d3a52;--kb-col-todo-ink:#9fd1ff;"
    "--kb-col-doing:#4a3416;--kb-col-doing-ink:#ffcf7a;--kb-col-review:#173a2e;--kb-col-review-ink:#8fe3b9;"
    "--kb-cell-wait:#191d23;--kb-cell-todo:#171f27;--kb-cell-doing:#1f1b16;--kb-cell-review:#16201c;"
    "--kb-mail-bg:#1c2535;--kb-mail-line:#34507a;--kb-tag-bg:#2a313a;--kb-tag-ink:#b7bfc9;"
    "--kb-tag-kind-bg:#263552;--kb-tag-kind-ink:#a9c6ff;--kb-deploy-bg:#4a3416;--kb-deploy-ink:#ffcf7a;"
    "--kb-now-bg:#173a2e;--kb-now-ink:#8fe3b9;--kb-device-bg:#302a4a;--kb-device-ink:#cbb9ff;"
    "--kb-status-bg:#3a2a44;--kb-status-ink:#e3b6ff;--kb-days:#ffb067;--kb-wait-ink:#d6b38f;"
    "--kb-warn-bg:#3a2f14;--kb-warn-line:#7a6428;--kb-warn-ink:#ffd98a;"
    "--kb-danger-bg:#3a1c1c;--kb-danger-line:#7a3434;--kb-danger-ink:#ff9e9e;"
    "--kb-selection:#2c4a6e;--kb-radius:10px;--kb-lane-kunsu-line:var(--kb-line-strong)}"
    "*{box-sizing:border-box}"
    "::selection{background:var(--kb-selection);color:var(--kb-ink)}"
    ":focus-visible{outline:2px solid var(--kb-accent);outline-offset:2px;border-radius:3px}"
    "body{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;color:var(--kb-ink);"
    "background:var(--kb-canvas);max-width:1400px;margin:1.25em auto;padding:0 1em;line-height:1.5;"
    "font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}"
    "h1{font-size:1.3em;font-weight:700;letter-spacing:-.01em;margin:0 0 .5em;"
    "padding-bottom:.45em;border-bottom:1px solid var(--kb-line)}"
    "a{color:var(--kb-accent);text-decoration:none;text-underline-offset:.18em}"
    "a:hover{text-decoration:underline}"
    "code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.9em}"
    "pre{white-space:pre-wrap;word-break:break-all;background:var(--kb-surface);"
    "padding:.6em .8em;border-radius:6px;font-size:.82em;margin:.3em 0;"
    "max-height:24em;overflow:auto;border:1px solid var(--kb-line)}"
    "details{margin:.25em 0}"
    "summary{cursor:pointer;color:var(--kb-accent);font-size:.85em}"
    # 頁首導覽
    ".kb-nav{display:flex;flex-wrap:wrap;gap:.4em 1.1em;align-items:center;"
    "margin:.4em 0 1.1em;font-size:.9em}"
    ".kb-switch{display:inline-flex;gap:.25em;padding:.15em;background:var(--kb-surface-2);"
    "border-radius:8px}"
    ".kb-switch a,.kb-switch span{padding:.15em .65em;border-radius:6px}"
    ".kb-switch a:hover{background:var(--kb-card);text-decoration:none}"
    ".kb-switch-current{font-weight:600;color:var(--kb-ink);background:var(--kb-card);"
    "box-shadow:0 1px 2px rgba(31,41,51,.12)}"
    ".kb-scan-time{color:var(--kb-faint);font-size:.85em;margin-left:auto}"
    ".kb-notice{background:var(--kb-warn-bg);border:1px solid var(--kb-warn-line);"
    "color:var(--kb-warn-ink);padding:.45em .8em;border-radius:6px;margin:.5em 0}"
    ".kb-alert{background:var(--kb-danger-bg);border:1px solid var(--kb-danger-line);"
    "padding:.45em .8em;border-radius:6px;margin:.5em 0;color:var(--kb-danger-ink)}"
    ".kb-alert a{color:var(--kb-danger-ink);margin-right:.8em;text-decoration:underline}"
    ".kb-empty{color:var(--kb-muted);margin:2em 0}"
    # 看板格線
    ".kb-board{overflow-x:auto;padding-bottom:.5em}"
    ".kb-grid{display:grid;grid-template-columns:7.5em repeat(4,minmax(13em,1fr));"
    "gap:.5em;align-items:start;min-width:62em}"
    ".kb-colhead{font-weight:600;font-size:.9em;background:var(--kb-surface-2);"
    "padding:.35em .5em;border-radius:6px;text-align:center;position:sticky;top:0}"
    ".kb-colhead b{font-weight:600;opacity:.75;margin-left:.3em}"
    ".kb-colhead[data-col=waiting]{background:var(--kb-col-wait);color:var(--kb-col-wait-ink)}"
    ".kb-colhead[data-col=todo]{background:var(--kb-col-todo);color:var(--kb-col-todo-ink)}"
    ".kb-colhead[data-col=doing]{background:var(--kb-col-doing);color:var(--kb-col-doing-ink)}"
    ".kb-colhead[data-col=review]{background:var(--kb-col-review);color:var(--kb-col-review-ink)}"
    ".kb-lane{font-weight:600;font-size:.9em;padding:.5em .3em;"
    "border-top:1px solid var(--kb-line-strong);word-break:break-all;color:var(--kb-muted)}"
    ".kb-lane-kunsu{color:var(--kb-kunsu);border-top-color:var(--kb-lane-kunsu-line)}"
    ".kb-cell{border-top:1px solid var(--kb-line-strong);padding:.5em .35em 0;min-height:2.6em;"
    "border-radius:0 0 6px 6px}"
    ".kb-cell[data-col=waiting]{background:var(--kb-cell-wait)}"
    ".kb-cell[data-col=todo]{background:var(--kb-cell-todo)}"
    ".kb-cell[data-col=doing]{background:var(--kb-cell-doing)}"
    ".kb-cell[data-col=review]{background:var(--kb-cell-review)}"
    # 卡片
    ".kb-card{border:1px solid var(--kb-line);border-radius:var(--kb-radius);padding:.55em .7em .6em;"
    "margin:0 0 .5em;background:var(--kb-card);box-shadow:var(--kb-card-shadow);"
    "transition:border-color .15s ease-out}"
    ".kb-card:hover{border-color:var(--kb-line-strong)}"
    ".kb-card-blocked{background:var(--kb-danger-bg);border-color:var(--kb-danger-line)}"
    ".kb-card-mail{background:var(--kb-mail-bg);border-color:var(--kb-mail-line)}"
    ".kb-title{font-weight:600;font-size:.92em;line-height:1.35;display:-webkit-box;"
    "-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;"
    "text-wrap:balance}"
    ".kb-meta{font-size:.78em;color:var(--kb-muted);margin-top:.35em;display:flex;"
    "flex-wrap:wrap;gap:.2em .55em;align-items:center}"
    ".kb-tag{display:inline-block;padding:.05em .5em;border-radius:999px;"
    "background:var(--kb-tag-bg);color:var(--kb-tag-ink);white-space:nowrap;line-height:1.5}"
    ".kb-tag-kind{background:var(--kb-tag-kind-bg);color:var(--kb-tag-kind-ink)}"
    ".kb-tag-blocked{background:var(--kb-danger-line);color:var(--kb-danger-ink);font-weight:600}"
    ".kb-tag-deploy{background:var(--kb-deploy-bg);color:var(--kb-deploy-ink)}"
    ".kb-tag-now{background:var(--kb-now-bg);color:var(--kb-now-ink)}"
    ".kb-tag-device{background:var(--kb-device-bg);color:var(--kb-device-ink)}"
    ".kb-tag-status{background:var(--kb-status-bg);color:var(--kb-status-ink)}"
    ".kb-days{color:var(--kb-days)}"
    ".kb-wait{font-size:.78em;color:var(--kb-wait-ink);margin-top:.25em}"
    ".kb-excerpt{font-size:.78em;color:var(--kb-muted);margin-top:.25em;line-height:1.45}"
    ".kb-more>summary{color:var(--kb-muted)}"
    ".kb-open{font-size:.78em;white-space:nowrap;margin-left:auto;font-weight:500}"
    # archive 頁
    ".kb-archive{padding-left:0;list-style:none;margin:.5em 0}"
    ".kb-archive li{margin:0;padding:.5em 0;border-top:1px solid var(--kb-line)}"
    ".kb-archive li:last-child{border-bottom:1px solid var(--kb-line)}"
    ".kb-archive a{color:var(--kb-ink)}"
    ".kb-archive a:hover{color:var(--kb-accent)}"
    ".kb-archive-meta{font-size:.82em;color:var(--kb-muted)}"
    ".kb-path{font-size:.8em;color:var(--kb-faint);font-family:ui-monospace,SFMono-Regular,"
    "Menlo,monospace;word-break:break-all}"
    # 全文頁
    ".kb-doc{max-width:860px}"
    ".kb-doc>h2{font-size:1.35em;line-height:1.3;letter-spacing:-.01em;margin:.4em 0 .2em;"
    "text-wrap:balance}"
    ".kb-doc-meta{font-size:.85em;color:var(--kb-muted);margin:.2em 0 1em;display:flex;"
    "flex-wrap:wrap;gap:.2em .6em;align-items:baseline}"
    ".kb-fm{border-collapse:collapse;font-size:.82em;margin:0 0 1.4em;"
    "background:var(--kb-surface);border-radius:8px;padding:.3em .8em;display:table;"
    "border:1px solid var(--kb-line)}"
    ".kb-fm th{text-align:left;color:var(--kb-faint);font-weight:500;"
    "padding:.3em 1.2em .3em .8em;vertical-align:top;white-space:nowrap}"
    ".kb-fm td{padding:.3em .8em .3em 0;word-break:break-all}"
    ".kb-fm tr+tr th,.kb-fm tr+tr td{border-top:1px solid var(--kb-line)}"
    ".kb-md{font-size:.95em;line-height:1.65}"
    ".kb-md>:first-child{margin-top:0}"
    ".kb-md h1{font-size:1.2em;border:0;padding:0;margin:1.4em 0 .4em}"
    ".kb-md h2{font-size:1.1em;margin:1.4em 0 .4em;padding-bottom:.2em;"
    "border-bottom:1px solid var(--kb-line)}"
    ".kb-md h3{font-size:1em;margin:1.2em 0 .3em}"
    ".kb-md h4,.kb-md h5,.kb-md h6{font-size:.95em;margin:1em 0 .3em}"
    ".kb-md p,.kb-md ul,.kb-md ol{margin:.5em 0}"
    ".kb-md li{margin:.15em 0}"
    ".kb-md table{border-collapse:collapse;margin:.6em 0;font-size:.9em;display:block;"
    "overflow-x:auto;max-width:100%}"
    ".kb-md th,.kb-md td{border:1px solid var(--kb-line);padding:.25em .6em;vertical-align:top}"
    ".kb-md th{background:var(--kb-surface-2);font-weight:600}"
    ".kb-md blockquote{border-left:1px solid var(--kb-line-strong);margin:.6em 0;"
    "padding:.1em .9em;color:var(--kb-muted)}"
    ".kb-md code{background:var(--kb-surface-2);padding:.05em .3em;border-radius:4px}"
    ".kb-md pre{max-height:none;font-size:.85em}"
    ".kb-md pre code{background:none;padding:0;font-size:inherit}"
    ".kb-md img{max-width:100%;height:auto}"
    ".kb-md hr{border:0;border-top:1px solid var(--kb-line);margin:1.2em 0}"
    ".kb-md-notice{background:var(--kb-warn-bg);border:1px solid var(--kb-warn-line);"
    "color:var(--kb-warn-ink);padding:.35em .7em;border-radius:6px;font-size:.85em}"
    ".kb-doc-section{font-weight:600;margin:1.6em 0 .4em;color:var(--kb-muted);"
    "font-size:.85em;text-transform:none;letter-spacing:.02em}"
    ".kb-reply{border:1px solid var(--kb-line);border-radius:var(--kb-radius);padding:.7em .9em;"
    "margin:.6em 0;background:var(--kb-card)}"
    ".kb-reply-head{font-size:.82em;color:var(--kb-muted);margin-bottom:.5em;display:flex;"
    "flex-wrap:wrap;gap:.2em .6em;align-items:center}"
    ".kb-reply-head strong{color:var(--kb-ink)}"
    ".kb-deps{margin:.3em 0;padding-left:1.2em}"
    ".kb-deps li{margin:.2em 0}"
    # 主題切換器
    ".kb-theme{display:inline-flex;gap:.2em;align-items:center;font-size:.8em;color:var(--kb-faint)}"
    ".kb-theme button{font:inherit;color:var(--kb-muted);background:none;border:1px solid transparent;"
    "border-radius:999px;padding:.05em .55em;cursor:pointer;line-height:1.6}"
    ".kb-theme button:hover{border-color:var(--kb-line-strong)}"
    ".kb-theme button i{display:inline-block;width:.6em;height:.6em;border-radius:50%;margin-right:.3em;"
    "vertical-align:baseline;border:1px solid rgba(0,0,0,.15)}"
    ":root:not([data-kb-theme]) .kb-theme button[data-kb-set=d],"
    "html[data-kb-theme=a] .kb-theme button[data-kb-set=a],"
    "html[data-kb-theme=b] .kb-theme button[data-kb-set=b],"
    "html[data-kb-theme=c] .kb-theme button[data-kb-set=c],"
    "html[data-kb-theme=d] .kb-theme button[data-kb-set=d]"
    "{color:var(--kb-ink);border-color:var(--kb-line-strong);background:var(--kb-card)}"
    "@media (max-width:640px){body{margin:.75em auto}.kb-nav{font-size:.85em}"
    ".kb-scan-time{margin-left:0;flex-basis:100%}.kb-grid{grid-template-columns:6em "
    "repeat(4,minmax(12em,1fr))}}"
)


# ── 共用片段 ────────────────────────────────────────────────────────────────────

def kunsu_label(kunsu_path: str) -> str:
    """軍師顯示名稱＝目錄名（亦為查詢參數 k 的值）。"""
    return Path(kunsu_path).name or kunsu_path


def _lane_attr(lane: str) -> str:
    return _KUNSU_ATTR if lane == LANE_KUNSU else lane


def _days_text(card: Card) -> str:
    days = days_since(card.base_date)
    if days is None:
        return "日期不明"
    if days == 0:
        return f"今天（{card.base_label}）"
    return f"已等 {days} 天（{card.base_label}）"


def _verify_tag(verify: Optional[str]) -> str:
    if not verify:
        return ""
    key = verify.lower()
    known = VERIFY_LABELS.get(key)
    if known:
        return f'<span class="kb-tag {_VERIFY_CSS.get(key, "")}">{known[0]}</span>'
    return f'<span class="kb-tag">{escape(verify)}</span>'


def handoff_href(kunsu_path: str, rel_path: str) -> str:
    """全文頁連結：`/handoff?k=<軍師目錄名>&f=<相對路徑>`（兩值皆 URL 編碼）。"""
    return f"/handoff?k={quote(kunsu_label(kunsu_path))}&f={quote(rel_path)}"


def _open_link(kunsu_path: str, rel_path: str, text: str = "全文") -> str:
    return f'<a class="kb-open" href="{escape(handoff_href(kunsu_path, rel_path))}">{text}</a>'


# 主題代碼 → (顯示名, 切換鈕色點)。代碼即 html[data-kb-theme] 的值，CSS 與 JS 共用。
THEMES: tuple[tuple[str, str, str], ...] = (
    ("d", "墨與朱", "#c2410c"),
    ("a", "沙盤", "#b3261e"),
    ("b", "青瓷", "#0f6e8c"),
    ("c", "夜戰", "#f2c66d"),
)


def _theme_switch() -> str:
    """主題切換鈕列；點擊由 page_shell 注入的 script 處理，選擇存於 localStorage。"""
    buttons = "".join(
        f'<button type="button" data-kb-set="{code}" aria-label="主題：{name}">'
        f'<i style="background:{dot}"></i>{name}</button>'
        for code, name, dot in THEMES
    )
    return f'<span class="kb-theme" role="group" aria-label="配色主題">{buttons}</span>'


def _nav(
    kunsus: Sequence[str],
    selected: Optional[str],
    page: str,
    todo_count: Optional[int] = None,
) -> str:
    """頁首：軍師切換、技術債、archive、原彙整頁連結與掃描時間（KTD9）。"""
    links: list[str] = []
    for kp in kunsus:
        name = kunsu_label(kp)
        href = f"{page}?k={quote(name)}"
        if kp == selected:
            links.append(f'<span class="kb-switch-current">{escape(name)}</span>')
        else:
            links.append(f'<a href="{escape(href)}">{escape(name)}</a>')
    parts = [f'<span class="kb-switch">{"".join(links)}</span>']
    if selected is not None:
        k = quote(kunsu_label(selected))
        anchor = nav_anchor_id(selected)
        if page == "/":
            parts.append(f'<a href="/archive?k={escape(k)}">已完成（archive）</a>')
        else:
            parts.append(f'<a href="/?k={escape(k)}">← 看板</a>')
        if todo_count is not None:
            parts.append(
                f'<a href="/overview#{escape(anchor)}">技術債 {todo_count} 筆</a>'
            )
    parts.append('<a href="/overview">完整彙整頁</a>')
    parts.append(_theme_switch())
    note = "；看板不掃回覆信箱，回覆側 tripwire 見完整彙整頁" if page == "/" else ""
    parts.append(
        f'<span class="kb-scan-time">掃描時間 {datetime.now().strftime("%H:%M:%S")}{note}</span>'
    )
    return f'<nav class="kb-nav">{"".join(parts)}</nav>'


def _notice(not_found: Optional[str]) -> str:
    if not_found is None:
        return ""
    return f'<p class="kb-notice">找不到軍師「{escape(not_found)}」，改顯示第一個軍師。</p>'


# ── 看板頁 ──────────────────────────────────────────────────────────────────────

def _alert(board: Board, kunsu_path: str) -> str:
    """異常警示列：有異常才出現，逐類連到原彙整頁該軍師錨點（KTD11）。"""
    if not board.anomalies:
        return ""
    href = f"/overview#{nav_anchor_id(kunsu_path)}"
    items = "".join(
        f'<a href="{escape(href)}">{escape(a.label)} {a.count}</a>' for a in board.anomalies
    )
    extra = (
        "（新申請／新上報清單可能不完整）" if board.mailbox_incomplete else ""
    )
    return f'<div class="kb-alert">⚠ 異常：{items}{extra}</div>'


def _card_html(card: Card, kunsu_path: str) -> str:
    classes = ["kb-card"]
    if card.blocked:
        classes.append("kb-card-blocked")
    if card.kind != CARD_HANDOFF:
        classes.append("kb-card-mail")

    meta: list[str] = []
    if card.kind in _KIND_TAGS:
        meta.append(f'<span class="kb-tag kb-tag-kind">{_KIND_TAGS[card.kind]}</span>')
    if card.blocked:
        meta.append('<span class="kb-tag kb-tag-blocked">⛔ 卡關</span>')
    if card.unknown_status:
        meta.append(
            f'<span class="kb-tag kb-tag-status">status: {escape(card.unknown_status)}</span>'
        )
    meta.append(_verify_tag(card.verify))
    if card.to_role and card.lane == LANE_KUNSU:
        meta.append(f"<span>收件：{escape(card.to_role)}</span>")
    meta.append(f'<span class="kb-days">{escape(_days_text(card))}</span>')
    if card.series:
        meta.append(f"<span>線：{escape(card.series)}</span>")

    wait = ""
    if card.waiting_titles or card.unresolved_waiting:
        items = [escape(t) for t in card.waiting_titles]
        if card.unresolved_waiting:
            items.append("無法解析的依賴")
        wait = f'<div class="kb-wait">等：{"、".join(items)}</div>'

    excerpt = (
        f'<div class="kb-excerpt">回覆摘錄：「{escape(card.excerpt)}」</div>'
        if card.excerpt
        else ""
    )

    meta.append(_open_link(kunsu_path, card.body_rel_path))

    return (
        f'<div class="{" ".join(classes)}">'
        f'<div class="kb-title">{escape(card.title)}</div>'
        f'<div class="kb-meta">{"".join(meta)}</div>'
        f"{wait}{excerpt}"
        "</div>"
    )


def _cell_html(lane: str, column: str, cards: Sequence[Card], kunsu_path: str) -> str:
    cls = "kb-cell" if cards else "kb-cell kb-cell-empty"
    visible = "".join(_card_html(c, kunsu_path) for c in cards[:CELL_VISIBLE_LIMIT])
    rest = cards[CELL_VISIBLE_LIMIT:]
    more = (
        f'<details class="kb-more"><summary>另有 {len(rest)} 筆</summary>'
        f'{"".join(_card_html(c, kunsu_path) for c in rest)}</details>'
        if rest
        else ""
    )
    return (
        f'<div class="{cls}" data-col="{column}" data-cell="{escape(_lane_attr(lane))}|{column}">'
        f"{visible}{more}</div><!--cell-->"
    )


def _grid(board: Board, kunsu_path: str) -> str:
    head = ['<div></div>']
    for col in COLUMNS:
        n = sum(len(board.cells.get((lane, col), ())) for lane, _ in board.lanes)
        head.append(f'<div class="kb-colhead" data-col="{col}">{COLUMN_LABELS[col]}<b>{n}</b></div>')
    rows: list[str] = []
    for lane, label in board.lanes:
        lane_cls = "kb-lane kb-lane-kunsu" if lane == LANE_KUNSU else "kb-lane"
        rows.append(
            f'<div class="{lane_cls}" data-lane="{escape(_lane_attr(lane))}">'
            f"{escape(label)}</div>"
        )
        for col in COLUMNS:
            rows.append(_cell_html(lane, col, board.cells.get((lane, col), ()), kunsu_path))
    return (
        f'<div class="kb-board"><div class="kb-grid">{"".join(head)}{"".join(rows)}</div></div>'
    )


def render_board_page(
    *,
    kunsus: Sequence[str],
    selected: str,
    board: Board,
    not_found: Optional[str] = None,
) -> str:
    """看板頁完整 HTML。"""
    parts = [_nav(kunsus, selected, "/", board.todo_count), _notice(not_found)]
    if board.stale:
        parts.append(
            '<div class="kb-alert">⚠ 軍師路徑失聯：'
            f"<code>{escape(selected)}</code>（路徑不存在或非有效 git repo）。"
            '<a href="/overview">到完整彙整頁查看</a></div>'
        )
        return page_shell("".join(parts), BOARD_CSS)
    parts.append(_alert(board, selected))
    if board.card_count == 0:
        parts.append('<p class="kb-empty">目前沒有待處理的項目。</p>')
    else:
        parts.append(_grid(board, selected))
    return page_shell("".join(parts), BOARD_CSS)


def render_no_kunsu_page() -> str:
    """registry 無任何軍師時的頁面。"""
    body = (
        _nav((), None, "/")
        + '<p class="kb-empty">尚無已登記的軍師。請先以 kunsu-init 建立軍師，'
        "或以 kunsu-list 確認註冊表。</p>"
    )
    return page_shell(body, BOARD_CSS)


def render_error_page(message: str) -> str:
    """registry 讀取錯誤頁（仍回 HTTP 200）。"""
    body = (
        _nav((), None, "/")
        + f'<div class="kb-alert">Registry 讀取錯誤</div><pre>{escape(message)}</pre>'
    )
    return page_shell(body, BOARD_CSS)


# ── archive 頁 ──────────────────────────────────────────────────────────────────

def render_archive_page(
    *,
    kunsus: Sequence[str],
    selected: str,
    graph: HandoffGraphResult,
    not_found: Optional[str] = None,
    stale: bool = False,
) -> str:
    """archive 頁：依檔名日期新到舊列出已歸檔交接，每筆連結至全文頁。

    軍師路徑失聯時無法讀取 archive，顯示失聯說明而非「沒有已歸檔的交接」，
    避免把無法判定的狀態誤呈現為歷史資料不存在。
    """
    nodes = sorted(
        (n for n in graph.nodes.values() if n.location == LOCATION_ARCHIVE),
        key=lambda n: n.filename,
        reverse=True,
    )
    parts = [_nav(kunsus, selected, "/archive"), _notice(not_found)]
    parts.append(f"<h2>已完成（archive）：{escape(kunsu_label(selected))}</h2>")
    if stale:
        parts.append(
            '<div class="kb-alert">⚠ 軍師路徑失聯：'
            f"<code>{escape(selected)}</code>（路徑不存在或非有效 git repo），"
            '無法讀取已歸檔的交接。<a href="/overview">到完整彙整頁查看</a></div>'
        )
        return page_shell("".join(parts), BOARD_CSS)
    if not nodes:
        parts.append('<p class="kb-empty">沒有已歸檔的交接。</p>')
        return page_shell("".join(parts), BOARD_CSS)

    items: list[str] = []
    for node in nodes:
        rel = f"docs/handoffs/archive/{node.filename}"
        meta = [f"收件：{escape(node.to_role or '（未知）')}"]
        if not node.is_done:
            meta.append('<span class="kb-tag kb-tag-status">已歸檔未標 done</span>')
        if node.corrected_by:
            meta.append(f"已由 {escape('、'.join(node.corrected_by))} 更正")
        title_link = (
            f'<a href="{escape(handoff_href(selected, rel))}">'
            f"<strong>{escape(node.title or node.filename)}</strong></a>"
        )
        items.append(
            f'<li>{title_link} <span class="kb-archive-meta">{" ・ ".join(meta)}</span></li>'
        )
    parts.append(f'<p class="kb-archive-meta">共 {len(nodes)} 份，點標題開啟全文。</p>')
    parts.append(f'<ul class="kb-archive">{"".join(items)}</ul>')
    return page_shell("".join(parts), BOARD_CSS)


# ── 全文頁 ──────────────────────────────────────────────────────────────────────

def _back_links(kunsu_path: str, detail: HandoffDetail) -> str:
    k = quote(kunsu_label(kunsu_path))
    links = [f'<a href="/?k={escape(k)}">← 看板</a>']
    if detail.location == LOCATION_ARCHIVE:
        links.append(f'<a href="/archive?k={escape(k)}">已完成（archive）</a>')
    links.append('<a href="/overview">完整彙整頁</a>')
    links.append(_theme_switch())
    return f'<nav class="kb-nav">{"".join(links)}</nav>'


def _deps_section(detail: HandoffDetail, graph: Optional[HandoffGraphResult]) -> str:
    """依賴區塊：宣告的 depends_on、尚未滿足者與 corrected_by；全無則不渲染。"""
    if graph is None or detail.kind != "handoff":
        return ""
    node = graph.nodes.get(detail.filename)
    if node is None:
        return ""
    waiting = set(graph.waiting_on.get(detail.filename, ()))
    items: list[str] = []
    for dep in node.depends_on:
        target = graph.nodes.get(dep)
        if target is None:
            items.append(f"<li>{escape(dep)}（無法解析）</li>")
            continue
        state = "等待中" if dep in waiting else ("已完成" if target.is_done else "未完成")
        items.append(
            f"<li>{escape(target.title or dep)}（{state}）"
            f' <span class="kb-path">{escape(dep)}</span></li>'
        )
    if node.corrected_by:
        items.append(f"<li>已由 {escape('、'.join(node.corrected_by))} 更正</li>")
    if not items:
        return ""
    return f'<div class="kb-doc-section">依賴</div><ul class="kb-deps">{"".join(items)}</ul>'


def render_handoff_page(
    *,
    kunsu_path: str,
    detail: HandoffDetail,
    graph: Optional[HandoffGraphResult] = None,
) -> str:
    """全文頁：frontmatter 鍵值表、本體 Markdown、同串回覆（舊→新）。

    Markdown 渲染與 frontmatter 表由 markdown_render 負責（html=False，
    原文 HTML 一律轉義）；graph 可省略，省略時不渲染依賴區塊。
    """
    kind_label = KIND_LABELS.get(detail.kind, detail.kind)
    parts = [_back_links(kunsu_path, detail), '<div class="kb-doc">']
    parts.append(f"<h2>{escape(detail.title)}</h2>")
    meta = [kind_label, escape(kunsu_label(kunsu_path))]
    if detail.location == LOCATION_ARCHIVE:
        meta.append("已歸檔")
    meta.append(f'<span class="kb-path">{escape(detail.rel_path)}</span>')
    parts.append(f'<div class="kb-doc-meta">{" ・ ".join(meta)}</div>')
    if detail.read_error:
        parts.append(f'<div class="kb-alert">{escape(detail.read_error)}</div>')
    else:
        _, html = render_document(detail.content, title=detail.title)
        parts.append(html)
    parts.append(_deps_section(detail, graph))

    if detail.kind == "handoff":
        if detail.replies:
            parts.append(f'<div class="kb-doc-section">回覆（{len(detail.replies)} 份，舊→新）</div>')
        else:
            parts.append('<div class="kb-doc-section">尚無回覆</div>')
        for i, reply in enumerate(detail.replies, start=1):
            head = [f"<strong>第 {i} 份</strong>"]
            if reply.status:
                head.append(
                    f'<span class="kb-tag kb-tag-status">status: {escape(reply.status)}</span>'
                )
            head.append(_verify_tag(reply.verify))
            if reply.created:
                head.append(f"<span>{escape(reply.created)}</span>")
            head.append(f'<span class="kb-path">{escape(reply.filename)}</span>')
            _, reply_html = render_document(reply.content)
            parts.append(
                f'<div class="kb-reply" id="reply-{i}">'
                f'<div class="kb-reply-head">{"".join(head)}</div>{reply_html}</div>'
            )
    parts.append("</div>")
    return page_shell("".join(parts), BOARD_CSS)


def render_handoff_stale_page(kunsu_path: str) -> str:
    """全文頁：軍師路徑失聯時的說明頁（HTTP 200，比照看板與 archive 頁）。"""
    k = quote(kunsu_label(kunsu_path))
    body = (
        f'<nav class="kb-nav"><a href="/?k={escape(k)}">← 看板</a></nav>'
        '<div class="kb-alert">⚠ 軍師路徑失聯：'
        f"<code>{escape(kunsu_path)}</code>（路徑不存在或非有效 git repo），"
        '無法讀取文件。<a href="/overview">到完整彙整頁查看</a></div>'
    )
    return page_shell(body, BOARD_CSS)


def render_handoff_not_found_page(kunsu_path: Optional[str], f: Optional[str]) -> str:
    """全文頁 404：不回顯原始 f 以外的任何路徑資訊（f 經轉義）。"""
    k = quote(kunsu_label(kunsu_path)) if kunsu_path else ""
    back = f'<a href="/?k={escape(k)}">← 看板</a>' if kunsu_path else '<a href="/">← 看板</a>'
    body = (
        f'<nav class="kb-nav">{back}</nav>'
        '<div class="kb-alert">找不到這份文件。</div>'
        f'<p class="kb-path">f={escape(f or "")}</p>'
    )
    return page_shell(body, BOARD_CSS)
