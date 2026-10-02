"""
html_common.py — 軍師沙盤各頁面共用的 HTML 輔助函式

main.py（原彙整頁 /overview 與路由組裝）與 board_html.py（看板 / 與 archive 頁）
都從本模組匯入。board_html.py 不得匯入 app.main：main.py 頂層會匯入 board_html，
反向匯入會造成循環匯入而使沙盤無法啟動（看板化計畫 KTD5，比照
handoff_graph_html.py 不匯入 main 的先例）。
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

PAGE_TITLE = "軍師沙盤（kunsu dashboard）"

# verify 建議代碼 → (中文標籤, 原彙整頁 CSS class)。看板頁另以 kb- 前綴對應樣式。
VERIFY_LABELS: dict[str, tuple[str, str]] = {
    "needs-deploy": ("需上線測試 🚀", "badge-deploy"),
    "testable-now": ("馬上可測 ⚡", "badge-now"),
    "needs-device": ("需實機測試 📱", "badge-device"),
}


# 主題切換：唯一的頁面 JS。<head> 內先讀 localStorage 設定 html[data-kb-theme]（避免
# 先畫預設再閃一下），再以事件委派接 [data-kb-set] 按鈕。localStorage 不可用（隱私
# 視窗、被封鎖）時 try/catch 吞掉，頁面照常以預設主題顯示；伺服器不持有任何主題狀態。
THEME_STORAGE_KEY = "kunsu-dashboard-theme"
THEME_CODES = ("a", "b", "c", "d")
THEME_SCRIPT = (
    "<script>(function(){"
    f"var K={THEME_STORAGE_KEY!r},V={list(THEME_CODES)!r},d=document.documentElement;"
    "function apply(t){if(V.indexOf(t)<0)return;if(t==='d'){d.removeAttribute('data-kb-theme')}"
    "else{d.setAttribute('data-kb-theme',t)}}"
    "try{apply(localStorage.getItem(K))}catch(e){}"
    "document.addEventListener('click',function(ev){"
    "var b=ev.target.closest&&ev.target.closest('[data-kb-set]');if(!b)return;"
    "var t=b.getAttribute('data-kb-set');apply(t);"
    "try{localStorage.setItem(K,t)}catch(e){}});"
    "})();</script>"
)


def page_shell(body: str, css: str) -> str:
    """以 body 內容與頁面 CSS 組裝完整 HTML 頁面骨架（含主題切換 script）。"""
    return (
        '<!DOCTYPE html><html lang="zh-Hant"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{PAGE_TITLE}</title>'
        f'<style>{css}</style>'
        f'{THEME_SCRIPT}'
        '</head><body>'
        f'<h1>{PAGE_TITLE}</h1>'
        f'{body}'
        '<p style="color:var(--kb-faint,#6b7280);font-size:.8em;margin-top:3em">'
        '重新整理瀏覽器頁面觸發全新掃描。</p>'
        '</body></html>'
    )


def read_related_file(base_path: str, rel_path: str) -> tuple[str, Optional[float]]:
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


def format_mtime(mtime: Optional[float]) -> str:
    """將檔案最後修改時間（epoch）格式化為可讀字串；None 時回傳空字串。"""
    if mtime is None:
        return ""
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")


def days_since(value: Optional[str]) -> Optional[int]:
    """value（YYYY-MM-DD 開頭）距今天數；缺失、無效或未來日期回傳 None。

    未來日期回傳 None 而非 0：基準日在未來代表時鐘或資料異常，顯示端應降級為
    「日期不明」，而不是假裝「今天」。原彙整頁的 _days_waiting_label 另有其
    clamp 規則，不經過本函式的未來日期分支。
    """
    if not value:
        return None
    try:
        d = date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
    days = (date.today() - d).days
    return days if days >= 0 else None


def nav_anchor_id(kunsu_path: str, sub_path: Optional[str] = None) -> str:
    """快速導覽錨點 id：`nav-<軍師目錄名>[--<子專案目錄名>]-<6 碼雜湊>`。

    目錄名只保留 `[A-Za-z0-9_-]`（其餘字元折成 `-`）供肉眼辨識；唯一性由
    完整路徑雜湊保證——同一軍師底下兩個同名 basename 子專案、或巢狀拓撲
    同一路徑在不同軍師分組各渲染一次，都不會撞 id。
    """
    key = f"{kunsu_path}\0{sub_path or ''}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:6]
    parts = [Path(kunsu_path).name or "root"]
    if sub_path is not None:
        parts.append(Path(sub_path).name or "root")
    slug = "--".join(re.sub(r"[^A-Za-z0-9_-]+", "-", n) for n in parts)
    return f"nav-{slug}-{digest}"
