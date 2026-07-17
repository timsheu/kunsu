"""
main.py — 軍師沙盤（kunsu dashboard）FastAPI 應用

GET / 路由彙整全域反向註冊表所有軍師與子專案的訊息狀態，渲染為單頁 HTML。

ADR 010 Decision 1.5：所有端點僅回傳 text/html，不提供任何 JSON／XML
等結構化格式端點，確保本工具不構成機器對機器介面。

啟動方式（從 skills/kunsu-dashboard/ 目錄執行）：
    python app/main.py --port 8000
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from itertools import groupby
from pathlib import Path
from typing import Optional

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
    "h5{margin:.6em 0 .1em;font-size:.88em;color:#555}"
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
    ".kunsu-group{margin:1.5em 0}"
    ".kunsu-group>summary{font-weight:700;font-size:1.05em;margin-bottom:.3em}"
    ".subrepo-nested{margin-left:1.75em;padding-left:1em;"
    "border-left:3px solid #e0e0e0}"
    ".lbl-tripwire{color:#b71c1c;font-weight:700}"
    ".hint-uncommitted{color:#1565c0;font-size:.85em;display:inline-block;"
    "margin-top:.15em}"
    ".lbl-script-error{color:#e65100;font-weight:700}"
    ".lbl-stale{color:#616161}"
    ".lbl-warn{color:#f57c00;font-weight:700}"
    ".lbl-error{color:#b71c1c;font-weight:700}"
    ".empty{color:#888;font-style:italic}"
    ".filename{color:#777;font-size:.85em}"
    ".unknown-to-item{color:#7b1fa2}"
    ".mtime{color:#999;font-size:.82em}"
    ".badge{display:inline-block;padding:0 .45em;border-radius:9px;"
    "font-size:.8em;font-weight:600;margin-left:.35em;white-space:nowrap}"
    ".badge-deploy{background:#fff3e0;color:#e65100}"
    ".badge-now{background:#e8f5e9;color:#2e7d32}"
    ".badge-device{background:#ede7f6;color:#4527a0}"
    ".badge-other{background:#f0f0f0;color:#555}"
    ".badge-blocked{background:#ffebee;color:#b71c1c}"
    ".badge-status-unknown{background:#f3e5f5;color:#7b1fa2}"
    ".overview{border-color:#90caf9;background:#f7fbff;display:flex;"
    "flex-wrap:wrap;gap:.4em;align-items:center}"
    ".chip{display:inline-block;padding:.15em .6em;border-radius:12px;"
    "font-size:.9em;font-weight:600;white-space:nowrap}"
    ".chip-alert{background:#ffebee;color:#b71c1c}"
    ".chip-now{background:#e8f5e9;color:#2e7d32}"
    ".chip-other{background:#f0f0f0;color:#555}"
    ".chip-msg{background:#e3f2fd;color:#1565c0}"
    ".hint-next-step{color:#2e7d32;font-size:.85em;margin:0 0 .35em 1.5em}"
    ".days-waiting{color:#e65100;font-weight:600;margin-left:.5em}"
    ".detail-name{display:inline-block;padding-left:1.5em;margin-top:.15em}"
    "pre{white-space:pre-wrap;word-break:break-all;background:#f8f8f8;"
    "padding:.5em;border-radius:3px;font-size:.85em;margin:.3em 0}"
    "details{margin:.3em 0}"
    "summary{cursor:pointer;color:#1565c0}"
    "summary:hover{text-decoration:underline}"
)


# ── HTML 渲染輔助 ─────────────────────────────────────────────────────────────

def _page(body: str) -> str:
    """以 body 內容組裝完整 HTML 頁面骨架。"""
    return (
        '<!DOCTYPE html><html lang="zh-Hant"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>軍師沙盤（kunsu dashboard）</title>'
        f'<style>{_CSS}</style>'
        '</head><body>'
        '<h1>軍師沙盤（kunsu dashboard）</h1>'
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


def _html_subrepo_kunsu_unreachable(path: str, kunsu_path: str) -> str:
    """子專案所屬軍師為 stale 時的卡片：明確標示軍師不可達，

    不呼叫 get_subrepo_status（該函式對不存在的路徑會靜默回傳空結果，
    容易被誤讀為「無待處理交接文件」）。
    """
    return (
        '<div class="card card-subrepo card-stale">'
        f'<h3>子專案：<code>{escape(path)}</code></h3>'
        '<p class="lbl-stale">⚠ 所屬軍師不可達：'
        f'<code>{escape(kunsu_path)}</code>'
        '（路徑不存在或非有效 git repo，無法判斷待處理交接文件）</p>'
        '</div>'
    )


def _read_related_file(base_path: str, rel_path: str) -> tuple[str, Optional[float]]:
    """讀取 base_path 底下 rel_path 檔案內容與最後修改時間，供展開式預覽使用。

    讀取失敗（檔案在掃描與渲染之間被搬移／歸檔，或權限問題等競態）不拋例外，
    回傳錯誤提示字串與 None，避免單一檔案讀取失敗導致整頁渲染中斷。
    """
    full_path = Path(base_path) / rel_path
    try:
        content = full_path.read_text(encoding="utf-8")
        mtime = full_path.stat().st_mtime
    except (OSError, UnicodeDecodeError) as e:
        return f"（無法讀取檔案內容：{e}）", None
    return content, mtime


def _format_mtime(mtime: Optional[float]) -> str:
    """將檔案最後修改時間（epoch）格式化為可讀字串；None 時回傳空字串。"""
    if mtime is None:
        return ""
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")


def _html_detail(summary_html: str, content: str) -> str:
    """展開式預覽卡片（原生 <details>/<summary>，無需 JS）。

    summary_html 須為呼叫端已組好、必要字串已 escape() 的 HTML 片段；
    content 為原始檔案內容，本函式負責 escape() 後包入 <pre>。
    """
    return (
        f'<details><summary>{summary_html}</summary>'
        f'<pre>{escape(content)}</pre></details>'
    )


def _html_summary_line(mtime_str: str, name_html: str) -> str:
    """組出「時間在前、換行縮排接檔名」的 <summary> 內容。

    name_html 須為呼叫端已組好、必要字串已 escape() 的 HTML 片段。
    mtime_str 為空字串時（讀取失敗等情境找不到 mtime）僅顯示檔名，不留空行。
    """
    name_line = f'<span class="detail-name">{name_html}</span>'
    if not mtime_str:
        return name_line
    return f'<span class="mtime">{escape(mtime_str)}</span><br>{name_line}'


def _html_latest_badge(mtime: Optional[float]) -> str:
    """分類標題列的「最新」時間標示；mtime 為 None 時回傳空字串。"""
    s = _format_mtime(mtime)
    return f' <span class="mtime">最新 {escape(s)}</span>' if s else ""


def _render_kunsu_category(
    base_path: str, rel_paths: list[str]
) -> tuple[str, Optional[float]]:
    """渲染軍師單一訊息分類（新回覆／新申請／新上報）的展開式清單。

    回傳 (該分類全部項目的展開式 HTML, 分類中最新的檔案修改時間)，
    後者供標題列「最新」標示使用，讓使用者不必逐一展開即可掌握時間流。
    """
    items_html: list[str] = []
    mtimes: list[float] = []
    for rel_path in rel_paths:
        content, mtime = _read_related_file(base_path, rel_path)
        if mtime is not None:
            mtimes.append(mtime)
        mtime_str = _format_mtime(mtime)
        summary = _html_summary_line(mtime_str, f'<code>{escape(rel_path)}</code>')
        items_html.append(_html_detail(summary, content))
    latest = max(mtimes) if mtimes else None
    return "".join(items_html), latest


# ── verify 標籤對照（ADR 011）──────────────────────────────────────────────
# 建議代碼 → (中文標籤, CSS class)；其他非空字串原樣顯示為一般標籤（badge-other）
_VERIFY_LABELS: dict[str, tuple[str, str]] = {
    "needs-deploy": ("需上線測試 🚀", "badge-deploy"),
    "testable-now": ("馬上可測 ⚡", "badge-now"),
    "needs-device": ("需實機測試 📱", "badge-device"),
}


def _html_status_badges(h: HandoffInfo) -> str:
    """組出摘要列的狀態標籤區（blocked／未知 status＋verify 驗收方式）。

    - `status: blocked` → ⛔ 卡關（partial／submitted 由所屬分類標題傳達，不重複）
    - 未知 status 值 → 原樣顯示（分類端已保守歸入部分完成）
    - verify 建議代碼 → 中文彩色標籤；其他非空字串 → 原樣一般標籤；缺省 → 不顯示
    """
    badges: list[str] = []
    status = h.latest_reply_status
    if status == "blocked":
        badges.append('<span class="badge badge-blocked">⛔ 卡關</span>')
    elif status is not None and status not in ("partial", "submitted"):
        badges.append(
            f'<span class="badge badge-status-unknown">'
            f'status: {escape(status)}</span>'
        )
    verify = h.latest_reply_verify
    if verify:
        # 建議代碼為全小寫 kebab-case；查找前正規化為小寫（ADR 011），
        # 大小寫變體（Needs-Deploy 等）仍命中彩色標籤，不靜默降格。
        # 未命中的自由字串一律原樣顯示「原始值」，不顯示正規化後的字串。
        known = _VERIFY_LABELS.get(verify.lower())
        if known:
            label, css = known
            badges.append(f'<span class="badge {css}">{label}</span>')
        else:
            badges.append(
                f'<span class="badge badge-other">{escape(verify)}</span>'
            )
    return "".join(badges)


def _verify_sort_key(h: HandoffInfo) -> tuple:
    """分類內 verify 聚合排序鍵（ADR 011 Decision 2）。

    已知建議代碼在前、自由字串次之、缺省最後；同 verify 值相鄰，
    組內依檔案修改時間降序——讓相同驗收方式的項目相鄰，支撐批次排程。
    僅用於未接手／部分完成兩分類；已回覆待確認改以 _awaiting_sort_key
    做顯式子分組（見下方）。
    """
    verify = h.latest_reply_verify
    if verify and verify.lower() in _VERIFY_LABELS:
        group, value = 0, verify.lower()
    elif verify:
        group, value = 1, verify
    else:
        group, value = 2, ""
    return (group, value, -(h.mtime or 0.0))


# ── 已回覆待確認 verify 子分組 ────────────────────────────────────────────────
# 建議代碼 → (子分組權重, 子分組標題)；權重順序＝可動性優先，愈接近「能收尾
# （/handoff done）」愈前。自由字串各 distinct 值自成一組（字典序）、缺省最後。
_AWAITING_SUBGROUPS: dict[str, tuple[int, str]] = {
    "testable-now": (0, "⚡ 馬上可測"),
    "needs-device": (1, "📱 需實機測試"),
    "needs-deploy": (2, "🚀 需上線測試"),
}
_SUBGROUP_FREE_WEIGHT = 3   # 自由字串 verify
_SUBGROUP_NONE_WEIGHT = 4   # verify 缺省
_SUBGROUP_NONE_LABEL = "未標示驗收方式"


def _awaiting_subgroup(h: HandoffInfo) -> tuple[int, str]:
    """回傳 (權重, 子分組標題)——同鍵項目屬同一子分組，權重決定子分組順序。

    自由字串子分組的標題即 verify 原始值，渲染端負責 escape()。
    """
    verify = h.latest_reply_verify
    if verify and verify.lower() in _AWAITING_SUBGROUPS:
        return _AWAITING_SUBGROUPS[verify.lower()]
    if verify:
        return (_SUBGROUP_FREE_WEIGHT, verify)
    return (_SUBGROUP_NONE_WEIGHT, _SUBGROUP_NONE_LABEL)


def _awaiting_sort_key(h: HandoffInfo) -> tuple:
    """已回覆待確認排序鍵：子分組順序＋組內最新回覆日期升冪（等最久排最前，

    讓陳年件浮頂；此分類必有回覆，latest_reply_date 為 YYYY-MM-DD 可字典序比較），
    同日再依檔案修改時間升冪。
    """
    weight, label = _awaiting_subgroup(h)
    return (weight, label, h.latest_reply_date or "", h.mtime or 0.0)


def _html_handoff_detail(h: HandoffInfo) -> str:
    """單一交接文件的展開式預覽卡片，摘要列含標題、檔名、狀態標籤與最後修改時間。"""
    mtime_str = _format_mtime(h.mtime)
    name_html = (
        f'{escape(h.title)} '
        f'<span class="filename">({escape(h.filename)})</span>'
        f'{_html_status_badges(h)}'
    )
    summary = _html_summary_line(mtime_str, name_html)
    return _html_detail(summary, h.raw_content)


# ── 下一步提示對照（「已回覆待確認」分類專用）──────────────────────────────────
# verify 建議代碼 → 白話下一步文案；缺省與自由字串使用通用文案
_NEXT_STEP_HINTS: dict[str, str] = {
    "needs-deploy": "等上線部署後驗收，通過後請軍師執行 /handoff done",
    "testable-now": "可立即驗收，確認無誤即執行 /handoff done",
    "needs-device": "等實機測試後，確認即執行 /handoff done",
}
_NEXT_STEP_HINT_DEFAULT = "開軍師 session 查核回覆，確認無誤後以 /handoff done 收尾歸檔"


def _days_waiting_label(reply_date: Optional[str]) -> str:
    """最新回覆至今的停留天數標籤；日期缺失或無效時降級為空字串。

    latest_reply_date 來自回覆檔名 regex，格式必為 YYYY-MM-DD 但無語意驗證
    （如 2026-13-01 可通過 regex），fromisoformat 失敗時不顯示天數、不中斷渲染。
    未來日期（時鐘異常）clamp 為 0，與當日回覆同以「今天回覆」呈現。
    """
    if not reply_date:
        return ""
    try:
        d = date.fromisoformat(reply_date)
    except ValueError:
        return ""
    days = max(0, (date.today() - d).days)
    return "今天回覆" if days == 0 else f"已等 {days} 天"


def _html_awaiting_confirm_item(h: HandoffInfo) -> str:
    """「已回覆待確認」專屬卡片：展開式預覽下方常態顯示下一步提示與停留天數。

    提示置於 <details> 之外，收合狀態下仍一眼可見；未接手／部分完成兩分類
    沿用 _html_handoff_detail，不帶提示與天數（其下一步在接手方，非使用者）。
    """
    verify = (h.latest_reply_verify or "").lower()
    hint = _NEXT_STEP_HINTS.get(verify, _NEXT_STEP_HINT_DEFAULT)
    days = _days_waiting_label(h.latest_reply_date)
    days_html = f'<span class="days-waiting">（{escape(days)}）</span>' if days else ""
    return (
        f"{_html_handoff_detail(h)}"
        f'<div class="hint-next-step">→ {escape(hint)}{days_html}</div>'
    )


@dataclass(frozen=True)
class PendingAggregate:
    """子專案分類結果的聚合計數，供軍師分組摘要列與頁首全域總覽共用。

    blocked／testable_now 分別是 partial_done／awaiting_confirm 的子集
    （前者計 status: blocked，後者計 verify 正規化後為 testable-now 者），
    僅供全域總覽列細分呈現。
    """

    not_picked_up: int = 0
    partial_done: int = 0
    awaiting_confirm: int = 0
    blocked: int = 0
    testable_now: int = 0
    anomalies: int = 0  # frontmatter 異常 ＋ to: 不符清單


def _aggregate_pending(results: list[SubrepoStatusResult]) -> PendingAggregate:
    """聚合多個子專案的分類結果為計數。"""
    npu = partial = awaiting = blocked = testable = anomalies = 0
    for r in results:
        npu += len(r.not_picked_up)
        partial += len(r.partial_done)
        awaiting += len(r.awaiting_confirm)
        blocked += sum(
            1 for h in r.partial_done if h.latest_reply_status == "blocked"
        )
        testable += sum(
            1 for h in r.awaiting_confirm
            if (h.latest_reply_verify or "").lower() == "testable-now"
        )
        anomalies += len(r.errors) + len(r.unknown_to)
    return PendingAggregate(
        not_picked_up=npu,
        partial_done=partial,
        awaiting_confirm=awaiting,
        blocked=blocked,
        testable_now=testable,
        anomalies=anomalies,
    )


def _pending_suffix(pending: Optional[PendingAggregate]) -> str:
    """分組摘要列的待處理計數尾註；僅列非零項，全零回傳空字串。"""
    if pending is None:
        return ""
    parts: list[str] = []
    if pending.not_picked_up:
        parts.append(f"⚠ 未接手 {pending.not_picked_up}")
    if pending.partial_done:
        parts.append(f"部分完成 {pending.partial_done}")
    if pending.awaiting_confirm:
        parts.append(f"待確認 {pending.awaiting_confirm}")
    if pending.anomalies:
        parts.append(f"異常 {pending.anomalies}")
    if not parts:
        return ""
    return "｜" + "・".join(parts)


def _kunsu_group_open_and_label(
    path: str,
    is_stale: bool,
    scan: Optional[KunsuScanResult],
    pending: Optional[PendingAggregate] = None,
) -> tuple[bool, str]:
    """判斷軍師分組預設是否展開，並組出摘要列文字。

    有進度（新訊息／tripwire／腳本錯誤）或 stale 者預設展開；
    子專案有未接手或異常件時同樣強制展開——未接手／異常不得藏在收合分組裡。
    摘要列尾註帶出子專案待處理計數，收合狀態下即可掌握全貌；
    健康、無新訊息且無未接手／異常的軍師預設折疊，避免軍師一多列表就過長。
    """
    esc = escape(path)
    if is_stale:
        return True, f'⚠ 軍師：<code>{esc}</code>（stale）'
    suffix = _pending_suffix(pending)
    force_open = bool(pending and (pending.not_picked_up or pending.anomalies))
    if scan is None:
        return True, f'軍師：<code>{esc}</code>{suffix}'
    if scan.tripwire_lines:
        return True, f'⛔ 軍師：<code>{esc}</code>（tripwire 異常）{suffix}'
    if scan.script_error:
        return True, f'⚠ 軍師：<code>{esc}</code>（腳本錯誤）{suffix}'
    total = len(scan.new_replies) + len(scan.new_applications) + len(scan.new_reports)
    if total == 0:
        return force_open, f'軍師：<code>{esc}</code>（無新訊息）{suffix}'
    return True, f'軍師：<code>{esc}</code>（{total} 則新訊息）{suffix}'


def _html_overview(
    pending: PendingAggregate,
    new_messages: int,
    tripwire_kunsus: int,
    script_error_kunsus: int,
) -> str:
    """頁首全域總覽列；全部計數為零時回傳空字串（不渲染）。

    刻意使用 .chip 而非 .badge class——既有測試以「頁面不含
    <span class="badge」斷言 verify 標籤缺席，總覽列不得共用同一 class。
    """
    chips: list[str] = []
    if tripwire_kunsus:
        chips.append(
            f'<span class="chip chip-alert">⛔ tripwire 異常軍師 {tripwire_kunsus}</span>'
        )
    if script_error_kunsus:
        chips.append(
            f'<span class="chip chip-alert">⚠ 腳本錯誤軍師 {script_error_kunsus}</span>'
        )
    if pending.not_picked_up:
        chips.append(
            f'<span class="chip chip-alert">⚠ 未接手 {pending.not_picked_up}</span>'
        )
    if pending.blocked:
        chips.append(f'<span class="chip chip-alert">⛔ 卡關 {pending.blocked}</span>')
    if pending.testable_now:
        chips.append(
            f'<span class="chip chip-now">⚡ 馬上可測 {pending.testable_now}</span>'
        )
    other_awaiting = pending.awaiting_confirm - pending.testable_now
    if other_awaiting:
        chips.append(
            f'<span class="chip chip-other">其餘待確認 {other_awaiting}</span>'
        )
    if pending.anomalies:
        chips.append(
            f'<span class="chip chip-alert">異常 {pending.anomalies}</span>'
        )
    if new_messages:
        chips.append(f'<span class="chip chip-msg">📨 新訊息 {new_messages}</span>')
    if not chips:
        return ""
    return f'<div class="card overview"><strong>全域總覽</strong>{"".join(chips)}</div>'


def _html_kunsu_stale(path: str) -> str:
    """Stale 軍師卡片（路徑不存在或非有效 git repo），標籤與純子專案 stale 卡片區分。"""
    return (
        '<div class="card card-stale">'
        f'<h3>軍師：<code>{escape(path)}</code></h3>'
        '<span class="lbl-stale">⚠ stale（路徑不存在或非有效 git repo）</span>'
        '</div>'
    )


def _html_subrepo_stale(path: str, kunsu_path: str) -> str:
    """Stale 子專案卡片，巢狀呈現於所屬軍師分組底下。"""
    return (
        '<div class="card card-subrepo card-stale">'
        f'<h3>子專案：<code>{escape(path)}</code></h3>'
        f'<p>所屬軍師：<code>{escape(kunsu_path)}</code></p>'
        '<span class="lbl-stale">⚠ stale（路徑不存在或非有效 git repo）</span>'
        '</div>'
    )


# scan-replies.sh 分類規則第 3 條：docs/handoffs/ 頂層 .md 檔案只要有任何未
# commit 狀態變更即觸發 tripwire，不論成因是「未經授權的跨 repo 寫入」或
# 「軍師 session 自己漏做 /handoff add 尾端確認 commit」。這兩種成因在
# git status 上完全同形，腳本本身無法（也不該）代為判斷，只能由人工核實。
# 這裡只針對其中最常見、最無歧義的一種形狀（檔案剛建立、尚未進 commit：
# untracked「??」或已 git add 但未 commit「A 」）附加白話提示，縮短使用者
# 從「看到異常」到「猜到可能是漏 commit」的判讀距離；其餘形狀（修改、刪除、
# 非法搬移等）維持原樣顯示——那些無法用同一套啟發式安全歸類為「僅是忘記
# commit」，仍需人工完整判讀。
_UNCOMMITTED_HANDOFF_RE = re.compile(
    r'^TRIPWIRE:(?:\?\?|A )\s(docs/handoffs/[^/\s]+\.md)$'
)


def _annotate_tripwire_line(line: str) -> str:
    """為「交接檔已建立但尚未 commit」這種最常見的 tripwire 形狀附加白話提示。"""
    esc = escape(line)
    if not _UNCOMMITTED_HANDOFF_RE.match(line):
        return esc
    return (
        f'{esc}<br><span class="hint-uncommitted">'
        '💡 疑似交接文件已建立但尚未 commit（漏做 /handoff add 尾端確認 commit '
        '步驟）。確認內容無誤後於軍師 repo 執行 git add + commit 即可清除此異常。'
        '</span>'
    )


def _html_kunsu(path: str, result: KunsuScanResult) -> str:
    """軍師卡片：tripwire／腳本錯誤／正常三種樣式。

    所有插入 HTML 的字串（路徑、腳本輸出行）一律先 escape() 再拼接。
    """
    esc = escape(path)

    if result.tripwire_lines:
        lines_html = "".join(
            f'<li>{_annotate_tripwire_line(line)}</li>'
            for line in result.tripwire_lines
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
            items, latest = _render_kunsu_category(path, result.new_replies)
            badge = _html_latest_badge(latest)
            parts.append(
                f'<h4>新回覆（{len(result.new_replies)}）{badge}</h4>{items}'
            )
        if result.new_applications:
            items, latest = _render_kunsu_category(path, result.new_applications)
            badge = _html_latest_badge(latest)
            parts.append(
                f'<h4>新申請（{len(result.new_applications)}）{badge}</h4>{items}'
            )
        if result.new_reports:
            items, latest = _render_kunsu_category(path, result.new_reports)
            badge = _html_latest_badge(latest)
            parts.append(
                f'<h4>新上報（{len(result.new_reports)}）{badge}</h4>{items}'
            )
        inner = "".join(parts)

    return (
        '<div class="card card-normal">'
        f'<h3>軍師：<code>{esc}</code></h3>'
        f'{inner}'
        '</div>'
    )


def _html_subrepo(path: str, kunsu_path: str, result: SubrepoStatusResult) -> str:
    """子專案卡片：未接手／部分完成／已回覆待確認／to 不符清單／異常五類。

    所有 frontmatter 字串（title、filename 等）一律 escape() 後再拼接。
    """
    esc_path = escape(path)
    esc_kunsu = escape(kunsu_path)
    parts: list[str] = [
        '<div class="card card-subrepo">',
        f'<h3>子專案：<code>{esc_path}</code></h3>',
        f'<p>所屬軍師：<code>{esc_kunsu}</code></p>',
    ]

    if result.not_picked_up:
        items = "".join(
            _html_handoff_detail(h)
            for h in sorted(result.not_picked_up, key=_verify_sort_key)
        )
        parts.append(
            f'<h4 class="lbl-warn">⚠ 未接手（{len(result.not_picked_up)}）</h4>{items}'
        )

    if result.partial_done:
        items = "".join(
            _html_handoff_detail(h)
            for h in sorted(result.partial_done, key=_verify_sort_key)
        )
        parts.append(f'<h4>部分完成（{len(result.partial_done)}）</h4>{items}')

    if result.awaiting_confirm:
        # 依 verify 拆顯式子分組（h5 標題）：馬上可測 → 需實機 → 需上線 →
        # 自由字串 → 未標示，讓「哪幾筆現在就能收尾」一眼可辨
        sorted_awaiting = sorted(result.awaiting_confirm, key=_awaiting_sort_key)
        sub_parts: list[str] = []
        for (_weight, label), grouped in groupby(
            sorted_awaiting, key=_awaiting_subgroup
        ):
            group_items = list(grouped)
            items = "".join(
                _html_awaiting_confirm_item(h) for h in group_items
            )
            sub_parts.append(
                f'<h5>{escape(label)}（{len(group_items)}）</h5>{items}'
            )
        parts.append(
            f'<h4>已回覆待確認（{len(result.awaiting_confirm)}）</h4>'
            f'{"".join(sub_parts)}'
        )

    if result.unknown_to:
        # 以獨立警示列呈現，不歸入未接手／部分完成／已回覆待確認
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
        result.not_picked_up
        or result.partial_done
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

    # ── 身分判斷（軍師 vs 子專案） ─────────────────────────────────────────
    # reg.raw 是 load_registry 內部已解析的同一份資料，不再次開檔讀取——
    # 避免兩次獨立讀檔之間的競態（registry 在兩次讀取之間被覆寫，導致健康
    # 檢查結果與身分判斷結果基於不同版本的資料，見 U4 code review 修正）。
    data = reg.raw
    kunsu_paths = _build_kunsu_paths(data)
    healthy_set = set(reg.healthy)
    stale_set = set(reg.stale)

    # ── 軍師 → 所屬子專案 對照表（供分組巢狀渲染） ─────────────────────────
    kunsu_to_subrepos: dict[str, set[str]] = {}
    for sub_path, entries in data.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            kunsu_p = entry.get("kunsu", "")
            if kunsu_p:
                kunsu_to_subrepos.setdefault(kunsu_p, set()).add(sub_path)

    # ── 依軍師分組：每個軍師卡片底下巢狀顯示其所屬子專案 ───────────────────
    # 巢狀拓撲（同一路徑同時是軍師與子專案）：該路徑既會以自己的分組出現，
    # 也會巢狀出現在「上游軍師」的分組底下——兩處各自獨立渲染，不合併。
    group_parts: list[str] = []
    covered: set[str] = set()

    # 全域總覽累計（頁首總覽列用）
    all_sub_results: list[SubrepoStatusResult] = []
    total_new_messages = 0
    tripwire_kunsus = 0
    script_error_kunsus = 0

    for kunsu_path in sorted(kunsu_paths):
        if kunsu_path not in healthy_set and kunsu_path not in stale_set:
            continue  # raw 與健康檢查結果不一致，理論上不應發生
        covered.add(kunsu_path)

        sub_paths = sorted(kunsu_to_subrepos.get(kunsu_path, ()))
        nested_parts: list[str] = []
        is_stale = kunsu_path in stale_set
        scan: Optional[KunsuScanResult] = None
        pending: Optional[PendingAggregate] = None

        if is_stale:
            kunsu_card = _html_kunsu_stale(kunsu_path)
            for sp in sub_paths:
                covered.add(sp)
                # 所屬軍師本身 stale，呼叫 get_subrepo_status 只會靜默回傳
                # 空結果，誤導使用者以為「無待處理交接文件」——改為明確告知
                # 軍師不可達，不呼叫 get_subrepo_status。
                nested_parts.append(_html_subrepo_kunsu_unreachable(sp, kunsu_path))
        else:
            scan = scan_kunsu(kunsu_path)
            kunsu_card = _html_kunsu(kunsu_path, scan)
            if scan.tripwire_lines:
                tripwire_kunsus += 1
            if scan.script_error:
                script_error_kunsus += 1
            total_new_messages += (
                len(scan.new_replies)
                + len(scan.new_applications)
                + len(scan.new_reports)
            )
            sub_results: list[SubrepoStatusResult] = []
            for sp in sub_paths:
                covered.add(sp)
                if sp in stale_set:
                    nested_parts.append(_html_subrepo_stale(sp, kunsu_path))
                    continue
                our_roles = _get_our_roles(data, sp, kunsu_path)
                all_known = _get_all_known_roles(data, kunsu_path)
                status = get_subrepo_status(sp, our_roles, all_known, kunsu_path)
                sub_results.append(status)
                nested_parts.append(_html_subrepo(sp, kunsu_path, status))
            pending = _aggregate_pending(sub_results)
            all_sub_results.extend(sub_results)

        is_open, summary_label = _kunsu_group_open_and_label(
            kunsu_path, is_stale, scan, pending
        )
        nested_html = (
            f'<div class="subrepo-nested">{"".join(nested_parts)}</div>'
            if nested_parts
            else ""
        )
        open_attr = " open" if is_open else ""
        group_parts.append(
            f'<details class="kunsu-group"{open_attr}>'
            f'<summary>{summary_label}</summary>'
            f'{kunsu_card}{nested_html}'
            '</details>'
        )

    # ── 未歸類的殘留路徑（理論上不應發生，防禦性 fallback） ───────────────
    leftover_stale = [
        p for p in sorted((healthy_set | stale_set) - covered) if p in stale_set
    ]

    # ── 組裝頁面 ───────────────────────────────────────────────────────────
    body_sections: list[str] = []
    overview = _html_overview(
        _aggregate_pending(all_sub_results),
        total_new_messages,
        tripwire_kunsus,
        script_error_kunsus,
    )
    if overview:
        body_sections.append(overview)
    if group_parts:
        body_sections.append(
            f'<section><h2>軍師與子專案</h2>{"".join(group_parts)}</section>'
        )
    if leftover_stale:
        body_sections.append(
            '<section><h2>Stale 路徑</h2>'
            f'{"".join(_html_stale(p) for p in leftover_stale)}</section>'
        )
    if not body_sections:
        # healthy/stale 非空但身分未能識別（理論上不應發生）
        body_sections.append(_html_empty())

    return HTMLResponse(content=_page("".join(body_sections)))


# ── 程式化啟動 ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="軍師沙盤（kunsu dashboard）本機服務")
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="監聽 port（預設 8000）",
    )
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port, reload=False, workers=1)
