"""
todo_status.py — 軍師自身 docs/todos/ 技術債掃描與分類

唯讀解析軍師自己 repo 的 docs/todos/ 頂層 frontmatter（status/date/source/severity），
供軍師沙盤的「待辦技術債」區塊使用。與 subrepo_status.py 是同一資料夾底下的獨立
資料來源（docs/todos/ vs docs/handoffs/），彼此無依賴，各自持一份頂層 frontmatter
解析邏輯（比照既有 kunsu_scan.py／subrepo_status.py 互不共用 util 的既定慣例）。

分類規則（ADR 011 verify 欄位的「建議代碼＋開放值域」模式移植）：
  - status ∈ {"已解決", "已封存"} 且仍在頂層（未歸檔）→ orphaned_done（看似完成但未歸檔），
    不計入未處理總數。
  - 其餘一切 status 值（含 "未處理" 與任何自由字串）→ pending（未處理），計入總數；
    "未處理" 為已知值，其餘自由字串原樣顯示，顯示層樣式差異由呼叫端（main.py）決定，
    本模組只負責分類與排序。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml  # PyYAML — 列於 requirements.txt


# ── 資料類別 ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TodoInfo:
    """單一待辦技術債的基本資訊。"""

    filename: str               # basename，含 .md
    title: str                  # 內文首個 H1；找不到時為檔名還原字串
    status: str                 # frontmatter status 原始值（已 str() 轉型）
    date: Optional[str] = None
    source: Optional[str] = None
    severity: Optional[str] = None
    mtime: Optional[float] = None
    raw_content: str = ""


@dataclass(frozen=True)
class ErrorItem:
    """frontmatter 缺必要欄位或解析失敗的待辦檔案。"""

    filename: str
    error: str


@dataclass(frozen=True)
class TodoStatusResult:
    """軍師 docs/todos/ 的分類結果。

    Attributes:
        pending:        未處理（status 不在 {已解決,已封存} 的所有值，含未知自由字串）。
        orphaned_done:  看似完成但未歸檔（status ∈ {已解決,已封存} 但仍在頂層）。
        archive_count:  docs/todos/archive/ 底下的 .md 檔案數，不讀取其內容。
        errors:         frontmatter 缺 status 欄位或讀取失敗的檔案。
    """

    pending: list[TodoInfo] = field(default_factory=list)
    orphaned_done: list[TodoInfo] = field(default_factory=list)
    archive_count: int = 0
    errors: list[ErrorItem] = field(default_factory=list)


# ── 內部輔助函式 ────────────────────────────────────────────────────────────────

# 顯示層可能需要區分「已知值」與自由字串（見 main.py _html_todo_item），
# 這裡匯出常數避免跨模組的裸字串同步問題。
KNOWN_PENDING_STATUS = "未處理"
_CLOSED_STATUSES = frozenset({"已解決", "已封存"})
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
_SEVERITY_UNKNOWN_WEIGHT = 3


def _parse_frontmatter_and_body(content: str) -> tuple[dict, str]:
    """從 Markdown 檔案內容中提取 YAML frontmatter 與其後的內文。

    比照 subrepo_status.py `_parse_frontmatter` 的分隔符偵測邏輯（開頭須為
    獨立一行 '---'，結束分隔符須為獨立一行，避免 YAML 值中剛好有一行以
    '---' 開頭時被誤判為結束標記）；一律使用 yaml.safe_load()。

    Returns:
        (frontmatter dict，找不到或解析失敗時為 {}；內文字串，找不到 frontmatter
        時為整份原始內容)。
    """
    if not (content.startswith("---\n") or content == "---"):
        return {}, content

    search_from = 3
    end = -1
    while True:
        candidate = content.find("\n---", search_from)
        if candidate == -1:
            break
        after = candidate + len("\n---")
        if after == len(content) or content[after] == "\n":
            end = candidate
            break
        search_from = after

    if end == -1:
        return {}, content

    yaml_str = content[3:end]
    body = content[end + len("\n---"):]

    try:
        result = yaml.safe_load(yaml_str)
    except yaml.YAMLError:
        return {}, body

    return (result if isinstance(result, dict) else {}), body


def _extract_title(body: str, filename: str) -> str:
    """取內文第一個以 '# ' 開頭的行作為標題；找不到時以檔名還原字串為 fallback。

    `/todo` skill 產出的 frontmatter 刻意不含 title 欄位（避免與 Dataview
    File 欄位重複），標題語意只存在於內文 H1。
    """
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return Path(filename).stem.replace("-", " ")


def _severity_sort_key(t: TodoInfo) -> tuple:
    """未處理清單排序鍵：severity 升冪（high→low→未知），同 severity 依 mtime 降冪。"""
    weight = _SEVERITY_ORDER.get((t.severity or "").lower(), _SEVERITY_UNKNOWN_WEIGHT)
    return (weight, -(t.mtime or 0.0))


# ── 主函式 ──────────────────────────────────────────────────────────────────────

def get_todo_status(kunsu_path: str) -> TodoStatusResult:
    """對軍師自己 repo 的 docs/todos/ 做唯讀掃描與分類。

    Args:
        kunsu_path: 軍師根目錄的絕對路徑。

    Returns:
        TodoStatusResult。`docs/todos/` 不存在時回傳空結果，不報錯
        （比照 subrepo_status.py 對 docs/handoffs/ 不存在的既有處理）。
    """
    todos_dir = Path(kunsu_path) / "docs" / "todos"

    if not todos_dir.exists():
        return TodoStatusResult()

    pending: list[TodoInfo] = []
    orphaned_done: list[TodoInfo] = []
    errors: list[ErrorItem] = []

    # Path.glob("*.md") 僅比對頂層 .md 檔案，天然排除 archive/ 子目錄
    # （* 不跨越路徑分隔符），比照 subrepo_status.py 對 handoffs_dir 的既有慣例。
    for todo_file in todos_dir.glob("*.md"):
        filename = todo_file.name

        try:
            content = todo_file.read_text(encoding="utf-8")
            mtime = todo_file.stat().st_mtime
        except (OSError, UnicodeDecodeError) as e:
            errors.append(ErrorItem(filename=filename, error=f"read error: {e}"))
            continue

        fm, body = _parse_frontmatter_and_body(content)

        status_raw = fm.get("status")
        # 用 is None 而非真值判斷：YAML 可能把 status 解析為 False/0 等
        # falsy 值，這仍是「欄位存在」（雖然是無意義的值），若誤判為缺欄位
        # 會讓該筆待辦從清單裡靜默消失，比顯示一個奇怪的 status 字串更糟。
        if status_raw is None:
            errors.append(
                ErrorItem(filename=filename, error="missing required frontmatter field: status")
            )
            continue

        status = str(status_raw)
        date = str(fm["date"]) if fm.get("date") is not None else None
        source = str(fm["source"]) if fm.get("source") is not None else None
        severity = str(fm["severity"]) if fm.get("severity") is not None else None

        info = TodoInfo(
            filename=filename,
            title=_extract_title(body, filename),
            status=status,
            date=date,
            source=source,
            severity=severity,
            mtime=mtime,
            raw_content=content,
        )

        if status in _CLOSED_STATUSES:
            orphaned_done.append(info)
        else:
            pending.append(info)

    pending.sort(key=_severity_sort_key)

    # archive_count：只計數，不讀取內容
    archive_dir = todos_dir / "archive"
    archive_count = sum(1 for _ in archive_dir.glob("*.md")) if archive_dir.exists() else 0

    return TodoStatusResult(
        pending=pending,
        orphaned_done=orphaned_done,
        archive_count=archive_count,
        errors=errors,
    )
