"""
main.py — kunsu Dashboard FastAPI 應用

GET / 路由彙整全域反向註冊表所有軍師與子專案的訊息狀態，渲染為單頁 HTML。

ADR 010 Decision 1.5：所有端點僅回傳 text/html，不提供任何 JSON／XML
等結構化格式端點，確保本工具不構成機器對機器介面。

啟動方式（從 skills/kunsu-dashboard/ 目錄執行）：
    python app/main.py --port 8000
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from html import escape
from pathlib import Path

# ── 確保 skills/kunsu-dashboard/ 在 sys.path 中 ──────────────────────────────
# 讓 `from app.xxx import ...` 在直接執行（python app/main.py）時也能解析。
# 匯入（from app.main import app）情境下，conftest.py 已設好 sys.path，
# 此區塊為 no-op。
_DASHBOARD_ROOT = str(Path(__file__).resolve().parent.parent)
if _DASHBOARD_ROOT not in sys.path:
    sys.path.insert(0, _DASHBOARD_ROOT)

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.registry import RegistryResult, load_registry
from app.kunsu_scan import KunsuScanResult, scan_kunsu
from app.subrepo_status import (
    ErrorItem,
    HandoffInfo,
    SubrepoStatusResult,
    UnknownToItem,
    get_subrepo_status,
)

# ── FastAPI app ───────────────────────────────────────────────────────────────
# 禁用 OpenAPI、Docs、ReDoc 端點，確保 app 內無任何 JSON 端點存在
# （ADR 010 Decision 1.5 可程式碼驗證的技術條件）。
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

_DEFAULT_REGISTRY = os.path.expanduser("~/.claude/kunsu-registry.json")


# ── Registry 路徑解析 ─────────────────────────────────────────────────────────

def _get_registry_path() -> str:
    """取得 registry 路徑。

    優先讀取環境變數 KUNSU_REGISTRY_PATH（測試覆寫用途），
    未設定時使用預設路徑 ~/.claude/kunsu-registry.json。
    在 request 時呼叫（非模組匯入時），確保測試透過 monkeypatch.setenv 覆寫有效。
    """
    return os.environ.get("KUNSU_REGISTRY_PATH", _DEFAULT_REGISTRY)


def _load_raw_registry(registry_path: str) -> dict:
    """讀取 registry JSON 原始資料，用於身分判斷。

    RegistryResult 只含路徑清單，身分判斷（軍師 vs 子專案）需要原始 JSON 結構。
    任何例外（檔案不存在、JSON 損壞等）靜默回傳空 dict；
    錯誤情境已由 load_registry 處理，此函式無需重複回報。
    """
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.loads(f.read())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# ── 身分判斷輔助 ──────────────────────────────────────────────────────────────

def _build_kunsu_paths(data: dict) -> set[str]:
    """提取所有軍師路徑——出現在任一條目 kunsu 欄位的路徑集合。"""
    result: set[str] = set()
    for entries in data.values():
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    k = entry.get("kunsu", "")
                    if k:
                        result.add(k)
    return result


def _build_subrepo_paths(data: dict) -> set[str]:
    """提取所有子專案路徑——registry 頂層鍵集合。"""
    return set(data.keys())


def _get_our_roles(data: dict, subrepo_path: str, kunsu_path: str) -> set[str]:
    """取得子專案在指定軍師底下的角色代碼集合。"""
    roles: set[str] = set()
    for entry in data.get(subrepo_path) or []:
        if isinstance(entry, dict) and entry.get("kunsu") == kunsu_path:
            for role in entry.get("roles") or []:
                if role:
                    roles.add(str(role))
    return roles


def _get_all_known_roles(data: dict, kunsu_path: str) -> set[str]:
    """取得指定軍師底下所有子專案角色代碼的聯集。"""
    roles: set[str] = set()
    for entries in data.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and entry.get("kunsu") == kunsu_path:
                for role in entry.get("roles") or []:
                    if role:
                        roles.add(str(role))
    return roles


# ── CSS ──────────────────────────────────────────────────────────────────────

_CSS = (
    "body{font-family:system-ui,sans-serif;max-width:900px;"
    "margin:2em auto;padding:0 1em;line-height:1.5}"
    "h1{border-bottom:2px solid #333;padding-bottom:.4em}"
    "h2{margin-top:2em;color:#444}"
    "h3{margin:.5em 0;font-size:1em}"
    "h4{margin:.4em 0 .2em;font-size:.95em}"
    "ul{margin:.2em 0;padding-left:1.5em}"
    "code{background:#f0f0f0;padding:.1em .3em;border-radius:3px;"
    "font-size:.88em;word-break:break-all}"
    ".card{border:1px solid #ddd;border-radius:6px;padding:.8em 1em;margin:.6em 0}"
    ".card-normal{border-color:#4caf50}"
    ".card-tripwire{border-color:#e53935;background:#fff5f5}"
    ".card-script-error{border-color:#fb8c00;background:#fff8f0}"
    ".card-stale{border-color:#9e9e9e;background:#f9f9f9}"
    ".card-subrepo{border-color:#1e88e5}"
    ".card-error-state{border-color:#e53935;background:#fff5f5}"
    ".lbl-tripwire{color:#b71c1c;font-weight:700}"
    ".lbl-script-error{color:#e65100;font-weight:700}"
    ".lbl-stale{color:#616161}"
    ".lbl-warn{color:#f57c00;font-weight:700}"
    ".lbl-error{color:#b71c1c;font-weight:700}"
    ".empty{color:#888;font-style:italic}"
    ".filename{color:#777;font-size:.85em}"
    ".unknown-to-item{color:#7b1fa2}"
    "pre{white-space:pre-wrap;word-break:break-all;background:#f8f8f8;"
    "padding:.5em;border-radius:3px;font-size:.85em;margin:.3em 0}"
)


# ── HTML 渲染輔助 ─────────────────────────────────────────────────────────────

def _page(body: str) -> str:
    """以 body 內容組裝完整 HTML 頁面骨架。"""
    return (
        '<!DOCTYPE html><html lang="zh-Hant"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>kunsu Dashboard</title>'
        f'<style>{_CSS}</style>'
        '</head><body>'
        '<h1>kunsu Dashboard</h1>'
        f'{body}'
        '<p style="color:#aaa;font-size:.8em;margin-top:3em">'
        '刷新瀏覽器頁面觸發全新掃描。</p>'
        '</body></html>'
    )


def _html_error(msg: str) -> str:
    """Registry 讀取錯誤頁（仍 HTTP 200，避免瀏覽器顯示通用錯誤頁）。"""
    return (
        '<div class="card card-error-state">'
        '<h2>Registry 讀取錯誤</h2>'
        f'<pre>{escape(msg)}</pre>'
        '</div>'
    )


def _html_empty() -> str:
    """空登記狀態（非錯誤，顯示提示訊息）。"""
    return '<p class="empty">目前沒有任何已登記的軍師或子專案。</p>'


def _html_stale(path: str) -> str:
    """Stale 路徑卡片（路徑不存在或非有效 git repo）。"""
    return (
        '<div class="card card-stale">'
        '<span class="lbl-stale">⚠ stale：</span>'
        f'<code>{escape(path)}</code>'
        '（路徑不存在或非有效 git repo）'
        '</div>'
    )


def _html_kunsu(path: str, result: KunsuScanResult) -> str:
    """軍師卡片：tripwire／腳本錯誤／正常三種樣式。

    所有插入 HTML 的字串（路徑、腳本輸出行）一律先 escape() 再拼接。
    """
    esc = escape(path)

    if result.tripwire_lines:
        lines_html = "".join(
            f'<li>{escape(line)}</li>' for line in result.tripwire_lines
        )
        return (
            '<div class="card card-tripwire">'
            f'<h3>軍師：<code>{esc}</code></h3>'
            '<p class="lbl-tripwire">⛔ tripwire 異常</p>'
            f'<ul>{lines_html}</ul>'
            '</div>'
        )

    if result.script_error:
        return (
            '<div class="card card-script-error">'
            f'<h3>軍師：<code>{esc}</code></h3>'
            '<p class="lbl-script-error">⚠ 腳本錯誤</p>'
            f'<pre>{escape(result.script_error)}</pre>'
            '</div>'
        )

    # 正常狀態：彙整各項新訊息
    total = (
        len(result.new_replies)
        + len(result.new_applications)
        + len(result.new_reports)
    )
    if total == 0:
        inner = '<p class="empty">無新訊息</p>'
    else:
        parts: list[str] = []
        if result.new_replies:
            items = "".join(f'<li>{escape(r)}</li>' for r in result.new_replies)
            parts.append(
                f'<h4>新回覆（{len(result.new_replies)}）</h4><ul>{items}</ul>'
            )
        if result.new_applications:
            items = "".join(f'<li>{escape(a)}</li>' for a in result.new_applications)
            parts.append(
                f'<h4>新申請（{len(result.new_applications)}）</h4><ul>{items}</ul>'
            )
        if result.new_reports:
            items = "".join(f'<li>{escape(r)}</li>' for r in result.new_reports)
            parts.append(
                f'<h4>新上報（{len(result.new_reports)}）</h4><ul>{items}</ul>'
            )
        inner = "".join(parts)

    return (
        '<div class="card card-normal">'
        f'<h3>軍師：<code>{esc}</code></h3>'
        f'{inner}'
        '</div>'
    )


def _html_subrepo(path: str, kunsu_path: str, result: SubrepoStatusResult) -> str:
    """子專案卡片：待接手／已回覆待確認／to 不符清單／異常四類。

    所有 frontmatter 字串（title、filename 等）一律 escape() 後再拼接。
    """
    esc_path = escape(path)
    esc_kunsu = escape(kunsu_path)
    parts: list[str] = [
        '<div class="card card-subrepo">',
        f'<h3>子專案：<code>{esc_path}</code></h3>',
        f'<p>所屬軍師：<code>{esc_kunsu}</code></p>',
    ]

    if result.pending:
        items = "".join(
            f'<li>{escape(h.title)}'
            f' <span class="filename">({escape(h.filename)})</span></li>'
            for h in result.pending
        )
        parts.append(
            f'<h4>待接手（{len(result.pending)}）</h4><ul>{items}</ul>'
        )

    if result.awaiting_confirm:
        items = "".join(
            f'<li>{escape(h.title)}'
            f' <span class="filename">({escape(h.filename)})</span></li>'
            for h in result.awaiting_confirm
        )
        parts.append(
            f'<h4>已回覆待確認（{len(result.awaiting_confirm)}）</h4><ul>{items}</ul>'
        )

    if result.unknown_to:
        # 以獨立警示列呈現，不歸入待接手或已回覆待確認
        items = "".join(
            f'<li class="unknown-to-item">{escape(u.filename)}'
            f' <span class="lbl-warn">to: {escape(u.to_value)}</span></li>'
            for u in result.unknown_to
        )
        parts.append(
            f'<h4 class="lbl-warn">to: 不符清單（{len(result.unknown_to)}）</h4>'
            f'<ul>{items}</ul>'
        )

    if result.errors:
        items = "".join(
            f'<li class="lbl-error">{escape(e.filename)}：{escape(e.error)}</li>'
            for e in result.errors
        )
        parts.append(
            f'<h4 class="lbl-error">異常（{len(result.errors)}）</h4><ul>{items}</ul>'
        )

    if not (
        result.pending
        or result.awaiting_confirm
        or result.unknown_to
        or result.errors
    ):
        parts.append('<p class="empty">無待處理交接文件</p>')

    parts.append('</div>')
    return "".join(parts)


# ── 路由（唯一端點） ──────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """彙整全部軍師與子專案訊息狀態，渲染為 text/html。

    遵守 ADR 010 Decision 1.5：本函式及 app 內所有路由僅回傳 text/html。
    registry 讀取失敗時仍回傳 HTTP 200（計畫明確要求），
    避免瀏覽器顯示通用錯誤頁面。
    """
    registry_path = _get_registry_path()
    reg = load_registry(registry_path)

    # ── 錯誤狀態：registry 無法讀取 ─────────────────────────────────────────
    if reg.registry_error:
        return HTMLResponse(content=_page(_html_error(reg.registry_error)))

    # ── 空登記狀態：healthy 與 stale 皆空 ─────────────────────────────────
    if not reg.healthy and not reg.stale:
        return HTMLResponse(content=_page(_html_empty()))

    # ── 讀原始 JSON 做身分判斷（軍師 vs 子專案） ──────────────────────────
    # RegistryResult 只含路徑清單，身分判斷需要原始 JSON 結構。
    data = _load_raw_registry(registry_path)
    kunsu_paths = _build_kunsu_paths(data)
    subrepo_paths = _build_subrepo_paths(data)
    healthy_set = set(reg.healthy)
    stale_set = set(reg.stale)

    stale_parts: list[str] = []
    kunsu_parts: list[str] = []
    subrepo_parts: list[str] = []

    for path in sorted(healthy_set | stale_set):
        # Stale 路徑：顯示警示卡片後跳過後續判斷
        if path in stale_set:
            stale_parts.append(_html_stale(path))
            continue

        # 軍師身分：呼叫 scan_kunsu 取得新訊息狀態
        # 兩個 if 皆可能為真（巢狀拓撲），各自獨立渲染，不合併
        if path in kunsu_paths:
            scan = scan_kunsu(path)
            kunsu_parts.append(_html_kunsu(path, scan))

        # 子專案身分：對每個所屬軍師呼叫 get_subrepo_status
        if path in subrepo_paths:
            entries = data.get(path) or []
            seen_kunsu: set[str] = set()
            if isinstance(entries, list):
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    kunsu_p = entry.get("kunsu", "")
                    if not kunsu_p or kunsu_p in seen_kunsu:
                        continue
                    seen_kunsu.add(kunsu_p)
                    our_roles = _get_our_roles(data, path, kunsu_p)
                    all_known = _get_all_known_roles(data, kunsu_p)
                    status = get_subrepo_status(path, our_roles, all_known, kunsu_p)
                    subrepo_parts.append(_html_subrepo(path, kunsu_p, status))

    # ── 組裝頁面（軍師分組與子專案分組獨立呈現） ─────────────────────────
    body_sections: list[str] = []
    if stale_parts:
        body_sections.append(
            f'<section><h2>Stale 路徑</h2>{"".join(stale_parts)}</section>'
        )
    if kunsu_parts:
        body_sections.append(
            f'<section><h2>軍師</h2>{"".join(kunsu_parts)}</section>'
        )
    if subrepo_parts:
        body_sections.append(
            f'<section><h2>子專案</h2>{"".join(subrepo_parts)}</section>'
        )
    if not body_sections:
        # healthy/stale 非空但身分未能識別（理論上不應發生）
        body_sections.append(_html_empty())

    return HTMLResponse(content=_page("".join(body_sections)))


# ── 程式化啟動 ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="kunsu Dashboard 本機服務")
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="監聽 port（預設 8000）",
    )
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port, reload=False, workers=1)
