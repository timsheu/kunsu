"""
handoff_detail.py — 全文頁（/handoff）的資料模型：路徑守門、讀檔與回覆序列

輸入是看板／archive 頁連結帶來的查詢參數 `f`（相對軍師根目錄的檔案路徑），
輸出是渲染端需要的文件內容與同串回覆清單。純讀檔，不呼叫掃描腳本
（scan-replies.sh 會推進歷史夾帶基線並寫統計檔，全文頁不得觸發）。

路徑守門（比照看板 `k` 的白名單精神）：`f` 只接受「允許目錄 + 單層檔名 + .md」
四種形狀，拒絕任何含 `..`、反斜線、多層或指向允許目錄之外的值；最後再以
resolve() 核對實體位置確實落在該允許目錄之下（symlink 逃逸亦擋）。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.handoff_graph import LOCATION_ARCHIVE, LOCATION_TOP
from app.subrepo_status import parse_frontmatter, reply_sort_key, split_frontmatter

# 允許的目錄（相對軍師根目錄）→ 文件類別
ALLOWED_DIRS: dict[str, str] = {
    "docs/handoffs": "handoff",
    "docs/handoffs/archive": "handoff",
    "docs/applications": "application",
    "docs/reports": "report",
}

KIND_LABELS = {"handoff": "交接", "application": "申請", "report": "上報"}


@dataclass(frozen=True)
class ReplyDoc:
    filename: str
    rel_path: str
    status: Optional[str]
    verify: Optional[str]
    created: Optional[str]
    content: str


@dataclass(frozen=True)
class HandoffDetail:
    rel_path: str
    filename: str
    kind: str                       # handoff／application／report
    location: Optional[str]         # 交接：LOCATION_TOP／LOCATION_ARCHIVE；信箱件 None
    title: str
    frontmatter: dict
    content: str                    # 原文（含 frontmatter）
    replies: tuple[ReplyDoc, ...]   # 同串回覆，舊→新
    read_error: Optional[str] = None


def resolve_rel_path(kunsu_path: str, rel: Optional[str]) -> Optional[tuple[str, str]]:
    """核對 `f` 是否為允許形狀且實際存在；回傳 (正規化相對路徑, 類別) 或 None。"""
    if not rel:
        return None
    rel = rel.strip().strip("/")
    if "\\" in rel or ".." in rel.split("/") or not rel.endswith(".md"):
        return None
    parent, _, name = rel.rpartition("/")
    kind = ALLOWED_DIRS.get(parent)
    if kind is None or not name or name.startswith("."):
        return None
    base = Path(kunsu_path)
    try:
        target = (base / parent / name).resolve()
        allowed_dir = (base / parent).resolve()
        if target.parent != allowed_dir or not target.is_file():
            return None
    except OSError:
        return None
    return f"{parent}/{name}", kind


def _replies_dir(kunsu_path: str, parent: str) -> Path:
    # 頂層交接的回覆在 docs/handoffs/replies/，已歸檔者在 docs/handoffs/archive/replies/
    return Path(kunsu_path) / parent / "replies"


def _collect_replies(kunsu_path: str, parent: str, filename: str) -> tuple[ReplyDoc, ...]:
    """列出 in_reply_to 指向本交接的回覆，依檔名 (date, n) 升冪（舊→新）。"""
    rdir = _replies_dir(kunsu_path, parent)
    if not rdir.is_dir():
        return ()
    found: list[tuple[tuple[str, int], ReplyDoc]] = []
    for f in rdir.glob("*.md"):
        key = reply_sort_key(f.name)
        if key is None:
            continue
        try:
            content = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        fm = parse_frontmatter(content)
        if str(fm.get("in_reply_to") or "") != filename:
            continue

        def _opt(k: str) -> Optional[str]:
            v = fm.get(k)
            s = str(v).strip() if v is not None else ""
            return s or None

        found.append((key, ReplyDoc(
            filename=f.name,
            rel_path=f"{parent}/replies/{f.name}",
            status=_opt("status"),
            verify=_opt("verify"),
            created=_opt("created"),
            content=content,
        )))
    found.sort(key=lambda item: item[0])
    return tuple(doc for _, doc in found)


def load_handoff_detail(kunsu_path: str, rel: Optional[str]) -> Optional[HandoffDetail]:
    """讀取全文頁所需資料；`f` 不合法或檔案不存在回傳 None。"""
    resolved = resolve_rel_path(kunsu_path, rel)
    if resolved is None:
        return None
    rel_path, kind = resolved
    parent, _, filename = rel_path.rpartition("/")
    location: Optional[str] = None
    if kind == "handoff":
        location = LOCATION_ARCHIVE if parent.endswith("/archive") else LOCATION_TOP

    try:
        content = (Path(kunsu_path) / rel_path).read_text(encoding="utf-8")
        read_error = None
    except (OSError, UnicodeDecodeError) as e:
        content, read_error = "", f"（無法讀取檔案內容：{e}）"

    fm, _ = split_frontmatter(content) if content else ({}, "")
    title_raw = fm.get("title")
    title = str(title_raw).strip() if title_raw is not None else ""
    replies = _collect_replies(kunsu_path, parent, filename) if kind == "handoff" else ()
    return HandoffDetail(
        rel_path=rel_path,
        filename=filename,
        kind=kind,
        location=location,
        title=title or Path(filename).stem,
        frontmatter=fm,
        content=content,
        replies=replies,
        read_error=read_error,
    )
