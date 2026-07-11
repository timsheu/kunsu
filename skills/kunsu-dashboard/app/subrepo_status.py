"""
subrepo_status.py — 子專案模式狀態判斷（4a Python 版）

複製 skills/kunsu-inbox/SKILL.md 步驟 4a-1 至 4a-4 的邏輯：
掃描軍師的交接文件頂層（不遞迴），對 to: 為本角色的交接文件判斷回覆狀態，
分類為「待接手」、「已回覆待確認」、「to: 不符清單」、或「異常」。

⚠️ 維護提示：本模組邏輯對齊 skills/kunsu-inbox/SKILL.md 步驟 4a。
   修改 SKILL.md 步驟 4a 時，請同步更新本模組並重跑
   skills/kunsu-dashboard/tests/test_subrepo_status.py。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml  # PyYAML — 列於 requirements.txt

# ── 回覆檔名後綴解析：-reply-YYYY-MM-DD.md 或 -reply-YYYY-MM-DD-N.md ────────
# 不可用字串降序排列：ASCII 中 '-'(45) < '.'(46)，同日多份時「無後綴」的基礎回覆
# (.md) 字串排名高於有 '-2' 後綴者，會誤取較舊的一份（見 SKILL.md 4a-3 警告）。
_REPLY_SUFFIX_RE = re.compile(r"-reply-(\d{4}-\d{2}-\d{2})(?:-(\d+))?\.md$")


# ── 資料類別 ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class HandoffInfo:
    """交接文件基本資訊與最新回覆狀態。"""

    filename: str               # basename，含 .md
    title: str
    from_role: str              # frontmatter from: 值（原角色代碼）
    to_role: str                # frontmatter to: 值（目標角色代碼）
    created: str
    latest_reply_status: Optional[str]  # None 表示無回覆
    latest_reply_date: Optional[str]    # None 表示無回覆
    raw_content: str = ""               # 檔案原始內容，供軍師沙盤展開式預覽使用
    mtime: Optional[float] = None       # 檔案最後修改時間（epoch），供時間軸排序／顯示


@dataclass(frozen=True)
class UnknownToItem:
    """to: 值不在此軍師任何已知角色代碼集合中的交接文件。"""

    filename: str
    to_value: str  # frontmatter to: 的實際值


@dataclass(frozen=True)
class ErrorItem:
    """frontmatter 缺少必要欄位或解析失敗的交接文件。"""

    filename: str
    error: str  # 錯誤描述（不中斷其餘交接文件的判斷）


@dataclass(frozen=True)
class SubrepoStatusResult:
    """子專案在此軍師底下的交接文件分類結果。

    Attributes:
        pending:          待接手（to∈our_roles，無回覆或 status: partial/blocked）
        awaiting_confirm: 已回覆待確認（to∈our_roles，最新回覆 status: submitted）
        unknown_to:       to: 不符清單（to∉all_known_roles）
        errors:           異常清單（frontmatter 缺必要欄位或解析失敗）
    """

    pending: list[HandoffInfo] = field(default_factory=list)
    awaiting_confirm: list[HandoffInfo] = field(default_factory=list)
    unknown_to: list[UnknownToItem] = field(default_factory=list)
    errors: list[ErrorItem] = field(default_factory=list)


# ── 內部輔助函式 ────────────────────────────────────────────────────────────────

def _parse_frontmatter(content: str) -> dict:
    """從 Markdown 檔案內容中提取並解析 YAML frontmatter。

    僅支援以 '---' 開頭的標準 frontmatter 格式。
    一律使用 yaml.safe_load()，嚴禁 yaml.load()。
    frontmatter 內容來自其他協作者可寫入的子專案 repo，不可信任其安全性。

    Returns:
        解析後的 dict；若無 frontmatter 或解析失敗則回傳空 dict。
    """
    # 開頭分隔符須為獨立一行（'---\n' 或整份內容恰為 '---'），
    # 避免誤判如 '---title: ...'（無換行）這類非標準開頭。
    if not (content.startswith("---\n") or content == "---"):
        return {}

    # 尋找結束分隔符：須為獨立一行（'\n---\n' 或以 '\n---' 結尾），
    # 避免 YAML 值中剛好有一行以 '---' 開頭時被誤判為結束標記，
    # 提前截斷 frontmatter、遺漏後面的必要欄位。
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
        return {}

    yaml_str = content[3:end]
    try:
        result = yaml.safe_load(yaml_str)
        return result if isinstance(result, dict) else {}
    except yaml.YAMLError:
        return {}


def _parse_reply_sort_key(filename: str) -> Optional[tuple[str, int]]:
    """從回覆檔名中提取 (date, n) 數值排序鍵。

    回覆檔名格式（由 /handoff reply 建立）：
      {原交接檔名}-reply-{YYYY-MM-DD}.md      → (date, 1)
      {原交接檔名}-reply-{YYYY-MM-DD}-{N}.md  → (date, N)

    Returns:
        (date_str, n) 若符合格式；None 若檔名不符回覆命名慣例。
    """
    m = _REPLY_SUFFIX_RE.search(filename)
    if not m:
        return None
    date_str = m.group(1)
    n = int(m.group(2)) if m.group(2) else 1
    return (date_str, n)


# ── 主函式 ──────────────────────────────────────────────────────────────────────

def get_subrepo_status(
    subrepo_path: str,
    our_roles: set[str],
    all_known_roles: set[str],
    kunsu_path: str,
) -> SubrepoStatusResult:
    """對子專案在指定軍師底下的交接文件進行分類判斷。

    複製 kunsu-inbox SKILL.md 步驟 4a-1 至 4a-4 的判斷邏輯，以 Python 實作，
    供軍師沙盤的 HTML 渲染使用（不依賴 Claude Code session）。

    Args:
        subrepo_path:    已判定為 healthy 的子專案絕對路徑（供上下文使用）。
        our_roles:       此子專案在本軍師的角色代碼集合（精確比對 handoff to:）。
        all_known_roles: 此軍師底下全部已知角色代碼的聯集（供 to: 不符清單判斷）。
        kunsu_path:      此軍師的絕對路徑。

    Returns:
        SubrepoStatusResult，含四個分類清單：
        - pending:          待接手
        - awaiting_confirm: 已回覆待確認
        - unknown_to:       to: 不符清單
        - errors:           frontmatter 缺欄位等異常（不中斷整體判斷）
    """
    handoffs_dir = Path(kunsu_path) / "docs" / "handoffs"
    replies_dir = handoffs_dir / "replies"

    pending: list[HandoffInfo] = []
    awaiting_confirm: list[HandoffInfo] = []
    unknown_to: list[UnknownToItem] = []
    errors: list[ErrorItem] = []

    # ── 若軍師無交接目錄，直接回傳空結果 ─────────────────────────────────────
    if not handoffs_dir.exists():
        return SubrepoStatusResult(
            pending=pending,
            awaiting_confirm=awaiting_confirm,
            unknown_to=unknown_to,
            errors=errors,
        )

    # ── 4a-3 前置：預先索引全部回覆（{handoff_filename: [(date, n, status)]}） ─
    # 一次性掃描，避免逐筆交接再搜尋回覆目錄造成 O(n²) 讀檔
    replies_index: dict[str, list[tuple[str, int, str]]] = {}

    if replies_dir.exists():
        for reply_file in replies_dir.glob("*.md"):
            try:
                content = reply_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            fm = _parse_frontmatter(content)
            # str() 強制轉換：YAML 可能將非預期格式的值解析為 bool/int 等
            # 非字串型別（比照 created 欄位已有的處理，見下方 4a-2 區塊），
            # 避免型別不符導致 replies_index 的 key 比對永遠失敗。
            in_reply_to = str(fm.get("in_reply_to") or "")
            status = str(fm.get("status") or "")
            if not in_reply_to:
                continue

            sort_key = _parse_reply_sort_key(reply_file.name)
            if sort_key is None:
                continue  # 不符回覆命名慣例，略過

            date_str, n = sort_key
            if in_reply_to not in replies_index:
                replies_index[in_reply_to] = []
            replies_index[in_reply_to].append((date_str, n, str(status)))

    # ── 4a-2. 掃描軍師交接文件頂層（不遞迴） ─────────────────────────────────
    # Path.glob("*.md") 僅比對頂層 .md 檔案，天然排除 replies/ 與 archive/ 子目錄
    # （Python pathlib glob 的 * 不跨越路徑分隔符，無需額外過濾）
    for handoff_file in handoffs_dir.glob("*.md"):
        filename = handoff_file.name

        try:
            content = handoff_file.read_text(encoding="utf-8")
            mtime = handoff_file.stat().st_mtime
        except (OSError, UnicodeDecodeError) as e:
            errors.append(ErrorItem(filename=filename, error=f"read error: {e}"))
            continue

        fm = _parse_frontmatter(content)

        # ── 必要欄位完整性核查 ───────────────────────────────────────────────
        missing = [k for k in ("title", "from", "to", "created") if not fm.get(k)]
        if missing:
            errors.append(
                ErrorItem(
                    filename=filename,
                    error=f"missing required frontmatter field(s): {', '.join(missing)}",
                )
            )
            continue

        title = str(fm["title"])
        from_role = str(fm["from"])
        to_role = str(fm["to"])
        # YAML 可能將 YYYY-MM-DD 解析為 datetime.date；str() 可安全轉回字串
        created = str(fm["created"])

        # ── 4a-2 步驟 3：依 to: 值分類（三路分支） ────────────────────────────
        if to_role in our_roles:
            # 納入主處理流程（4a-3）
            pass
        elif to_role not in all_known_roles:
            # 4a-4: to: 不符清單
            unknown_to.append(UnknownToItem(filename=filename, to_value=to_role))
            continue
        else:
            # to ∈ all_known_roles 但 ∉ our_roles → 屬於其他子 repo，靜默略過
            continue

        # ── 4a-3. 狀態推導：找最新回覆並分類 ────────────────────────────────
        reply_entries = replies_index.get(filename, [])
        latest_reply_status: Optional[str] = None
        latest_reply_date: Optional[str] = None

        if reply_entries:
            # 依 (date, n) 數值降序排序取最新
            # 注意：不可用檔名字串排序（見模組頂端說明與 SKILL.md 4a-3 警告）
            sorted_entries = sorted(
                reply_entries, key=lambda x: (x[0], x[1]), reverse=True
            )
            best_date, _best_n, best_status = sorted_entries[0]
            latest_reply_status = best_status
            latest_reply_date = best_date

        info = HandoffInfo(
            filename=filename,
            title=title,
            from_role=from_role,
            to_role=to_role,
            created=created,
            latest_reply_status=latest_reply_status,
            latest_reply_date=latest_reply_date,
            raw_content=content,
            mtime=mtime,
        )

        # ── 依 SKILL.md 4a-3 表格分類 ─────────────────────────────────────────
        if latest_reply_status is None or latest_reply_status in ("partial", "blocked"):
            pending.append(info)
        elif latest_reply_status == "submitted":
            awaiting_confirm.append(info)
        elif latest_reply_status == "done":
            pass  # 不列出（略過）
        else:
            # 未知 status 值 → 保守視同待接手
            pending.append(info)

    return SubrepoStatusResult(
        pending=pending,
        awaiting_confirm=awaiting_confirm,
        unknown_to=unknown_to,
        errors=errors,
    )
