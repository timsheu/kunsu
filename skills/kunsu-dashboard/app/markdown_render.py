"""
markdown_render.py — 交接／回覆／信箱檔的 Markdown 伺服器端渲染（全文頁用）

輸入是來自軍師 repo 的 Markdown 原文（frontmatter＋本文），輸出為可直接嵌入
text/html 頁面的 HTML 片段。渲染在伺服器端以 Python 完成，頁面除主題切換外
無 JS、端點仍只回 text/html（ADR 010 Decision 1.5 零改動）。

安全邊界：原文由子專案 session 寫入、不可信任。
- `html=False`：原文中的任何 HTML 標籤一律轉義為文字，不會成為 DOM。
- markdown-it-py 預設 validateLink 拒絕 `javascript:`／`vbscript:`／`file:` 等
  連結協定（會以純文字輸出），`data:` 僅允許圖片。
- frontmatter 以 yaml.safe_load 解析後逐值 escape，不經 Markdown 渲染。

markdown-it-py 為選用依賴（requirements.txt 已列）：匯入失敗時降級為
`<pre>` 轉義全文並附一行提示，不讓全文頁 500。
"""

from __future__ import annotations

import re
from html import escape
from typing import Optional

from app.subrepo_status import split_frontmatter

try:  # 選用依賴：缺席時降級為純文字
    from markdown_it import MarkdownIt as _MarkdownIt
except ImportError:  # pragma: no cover - 由測試以 monkeypatch 模擬
    _MarkdownIt = None  # type: ignore[assignment]

MARKDOWN_UNAVAILABLE_NOTICE = (
    "未安裝 markdown-it-py，以純文字顯示；"
    "請執行 pip install -r requirements.txt 後重啟沙盤。"
)

_md: Optional[object] = None


def _get_renderer():
    """惰性建立單一 MarkdownIt 實例；不可用時回傳 None。"""
    global _md
    if _MarkdownIt is None:
        return None
    if _md is None:
        # js-default 預設集＝CommonMark＋表格＋刪除線；html=False 關閉原始 HTML，
        # linkify=False 不自動把裸網址變連結（避免路徑類字串被誤判）。
        _md = _MarkdownIt("js-default", {"html": False, "linkify": False})
    return _md


def markdown_available() -> bool:
    return _get_renderer() is not None


def render_markdown(text: str) -> str:
    """把 Markdown 本文渲染為 HTML 片段；渲染器不可用時降級為轉義 <pre>。"""
    md = _get_renderer()
    if md is None:
        return (
            f'<p class="kb-md-notice">{MARKDOWN_UNAVAILABLE_NOTICE}</p>'
            f"<pre>{escape(text)}</pre>"
        )
    return f'<div class="kb-md">{md.render(text)}</div>'


def _format_value(value) -> str:
    if isinstance(value, (list, tuple)):
        return "、".join(_format_value(v) for v in value)
    if isinstance(value, dict):
        return "；".join(f"{k}: {_format_value(v)}" for k, v in value.items())
    return str(value)


def render_frontmatter_table(fm: dict, omit: tuple[str, ...] = ()) -> str:
    """frontmatter 以鍵值表呈現（值一律 escape，不經 Markdown）。空 dict 回空字串。

    omit 列出不入表的鍵（例如頁首已以標題呈現的 title），全部被略過時亦回空字串。
    """
    rows = "".join(
        f"<tr><th>{escape(str(k))}</th><td>{escape(_format_value(v))}</td></tr>"
        for k, v in fm.items()
        if k not in omit
    )
    if not rows:
        return ""
    return f'<table class="kb-fm">{rows}</table>'


_LEADING_H1_RE = re.compile(r"^\s*#\s+(.+?)\s*#*\s*$", re.M)


def _drop_leading_h1(body: str, title: str) -> str:
    """本文第一個非空行若是與 title 同文的 `# 標題`，去掉它（頁首已顯示標題）。"""
    stripped = body.lstrip("\n")
    first_line, _, rest = stripped.partition("\n")
    m = _LEADING_H1_RE.match(first_line)
    if m and m.group(1).strip() == title.strip():
        return rest
    return body


def render_document(content: str, *, title: Optional[str] = None) -> tuple[dict, str]:
    """拆 frontmatter 後渲染整份文件；回傳 (frontmatter dict, HTML 片段)。

    frontmatter 解析失敗時 split_frontmatter 回傳空 dict 與完整原文，
    此時整份內容交由 Markdown 渲染，不會遺失文字。給了 title 時，frontmatter
    表略過 title 列、本文開頭與之同文的 `# 標題` 行不重複渲染（頁首已顯示）。
    """
    fm, body = split_frontmatter(content)
    omit: tuple[str, ...] = ()
    if title:
        omit = ("title",)
        body = _drop_leading_h1(body, title)
    return fm, render_frontmatter_table(fm, omit) + render_markdown(body)
