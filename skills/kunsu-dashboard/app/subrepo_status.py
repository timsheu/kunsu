"""
subrepo_status.py — 子專案模式狀態判斷（4a Python 版）

複製 skills/kunsu-inbox/SKILL.md 步驟 4a-1 至 4a-4 的邏輯：
掃描軍師的交接文件頂層（不遞迴），對 to: 為本角色的交接文件判斷回覆狀態，
分類為「未接手」、「部分完成」、「已回覆待確認」、「to: 不符清單」、或「異常」，
並帶出最新回覆的選填欄位 verify（驗收方式，ADR 011，display-only）與最新回覆首句摘錄
（latest_reply_excerpt，沙盤與 SessionStart hook 顯示專用，非分類依據；分類分支零改動）。

⚠️ 維護提示：本模組邏輯對齊 skills/kunsu-inbox/SKILL.md 步驟 4a。
   修改 SKILL.md 步驟 4a 時，請同步更新本模組並重跑
   skills/kunsu-dashboard/tests/test_subrepo_status.py。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple, Optional

import yaml  # PyYAML — 列於 requirements.txt

# ── 回覆檔名後綴解析：-reply-YYYY-MM-DD.md 或 -reply-YYYY-MM-DD-N.md ────────
# 不可用字串降序排列：ASCII 中 '-'(45) < '.'(46)，同日多份時「無後綴」的基礎回覆
# (.md) 字串排名高於有 '-2' 後綴者，會誤取較舊的一份（見 SKILL.md 4a-3 警告）。
_REPLY_SUFFIX_RE = re.compile(r"-reply-(\d{4}-\d{2}-\d{2})(?:-(\d+))?\.md$")


# ── 資料類別 ────────────────────────────────────────────────────────────────────

class _ReplyEntry(NamedTuple):
    """回覆索引的一筆：以 (date, n) 數值排序取最新；body 供勝出者萃取首句。"""

    date: str
    n: int
    status: str
    verify: Optional[str]
    body: str
    filename: str


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
    latest_reply_verify: Optional[str] = None  # 最新回覆的 verify 欄位；None 表示無回覆或缺省
    latest_reply_excerpt: Optional[str] = None  # 最新回覆首句摘錄（display-only）；None 表示無回覆或無可用文字段
    raw_content: str = ""               # 檔案原始內容，供軍師沙盤展開式預覽使用
    mtime: Optional[float] = None       # 檔案最後修改時間（epoch），供時間軸排序／顯示
    series: Optional[str] = None        # 線別（display-only，str 正規化；缺省／空白為 None）
    latest_reply_filename: Optional[str] = None  # 最新回覆檔名（display-only，供看板展開全文）；None 表示無回覆


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
        not_picked_up:    未接手（to∈our_roles，無任何回覆）
        partial_done:     部分完成（to∈our_roles，最新回覆 status: partial/blocked
                          或未知值——有回覆就不是未接手，未知值保守列出不略過）
        awaiting_confirm: 已回覆待確認（to∈our_roles，最新回覆 status: submitted）
        unknown_to:       to: 不符清單（to∉all_known_roles）
        errors:           異常清單（frontmatter 缺必要欄位或解析失敗）
    """

    not_picked_up: list[HandoffInfo] = field(default_factory=list)
    partial_done: list[HandoffInfo] = field(default_factory=list)
    awaiting_confirm: list[HandoffInfo] = field(default_factory=list)
    unknown_to: list[UnknownToItem] = field(default_factory=list)
    errors: list[ErrorItem] = field(default_factory=list)


# ── 內部輔助函式 ────────────────────────────────────────────────────────────────

def _find_frontmatter_end(content: str) -> Optional[int]:
    """回傳 frontmatter 結束分隔符的位置（'\n---' 的起點）；無 frontmatter 時為 None。

    分隔符判定只此一處（parse_frontmatter 與 _split_frontmatter 共用），
    避免兩套邊界規則各切一次。
    """
    # 開頭分隔符須為獨立一行（'---\n' 或整份內容恰為 '---'），
    # 避免誤判如 '---title: ...'（無換行）這類非標準開頭。
    if not (content.startswith("---\n") or content == "---"):
        return None

    # 尋找結束分隔符：須為獨立一行（'\n---\n' 或以 '\n---' 結尾），
    # 避免 YAML 值中剛好有一行以 '---' 開頭時被誤判為結束標記，
    # 提前截斷 frontmatter、遺漏後面的必要欄位。
    search_from = 3
    while True:
        candidate = content.find("\n---", search_from)
        if candidate == -1:
            return None
        after = candidate + len("\n---")
        if after == len(content) or content[after] == "\n":
            return candidate
        search_from = after


def parse_frontmatter(content: str) -> dict:
    """從 Markdown 檔案內容中提取並解析 YAML frontmatter。

    僅支援以 '---' 開頭的標準 frontmatter 格式。
    一律使用 yaml.safe_load()，嚴禁 yaml.load()。
    frontmatter 內容來自其他協作者可寫入的子專案 repo，不可信任其安全性。

    Returns:
        解析後的 dict；若無 frontmatter 或解析失敗則回傳空 dict。
    """
    end = _find_frontmatter_end(content)
    if end is None:
        return {}
    try:
        result = yaml.safe_load(content[3:end])
        return result if isinstance(result, dict) else {}
    except yaml.YAMLError:
        return {}


def _split_frontmatter(content: str) -> tuple[dict, str]:
    """拆出 frontmatter dict 與其後的本文（只有需要本文的呼叫端才付切片成本）。"""
    end = _find_frontmatter_end(content)
    if end is None:
        return {}, content
    body = content[end + len("\n---"):]
    if body.startswith("\n"):
        body = body[1:]
    return parse_frontmatter(content), body


def split_frontmatter(content: str) -> tuple[dict, str]:
    """公開介面：拆出 frontmatter dict 與本文（全文頁 Markdown 渲染用，見 markdown_render.py）。"""
    return _split_frontmatter(content)


# ── 最新回覆首句摘錄（display-only；規則見計畫 R4）────────────────────────────
_EXCERPT_MAX_CHARS = 60
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")
_FENCE_RE = re.compile(r"^\s{0,3}(```|~~~)")
_TABLE_ROW_RE = re.compile(r"^\s*\|")
_HTML_LINE_RE = re.compile(r"^\s*<[A-Za-z/!]")
# 水平線（---／***／___）與 Setext 標題底線（===／---）：前者是段落邊界，
# 後者使其上一行（單行段落）成為標題而非內文。
_HR_RE = re.compile(r"^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$")
_SETEXT_UNDERLINE_RE = re.compile(r"^\s{0,3}(?:=+|-+)\s*$")
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_BLOCKQUOTE_RE = re.compile(r"^\s*>\s?")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_BACKTICK_RE = re.compile(r"`+")
# 粗體／斜體：只去除成對且緊貼文字兩端、外側不緊鄰 ASCII 英數字的標記，
# 識別字內的單一底線（client_ref、_lang=zh-TW）原樣保留。lookaround 用
# ASCII 集合而非 \w：Python 的 \w 含漢字，「但**尚未鎖定**，」會因前接「但」
# 而不被視為粗體邊界（code review #6）。
_ASCII_WORD = r"[A-Za-z0-9_]"
_STRONG_RE = re.compile(rf"(?<!{_ASCII_WORD})(\*\*|__)(?=\S)(.+?)(?<=\S)\1(?!{_ASCII_WORD})")
# 斜體內文不得含同一標記字元，否則 `_lang=zh-TW，_重要_` 會被跨識別字配對。
_EM_STAR_RE = re.compile(rf"(?<!{_ASCII_WORD})\*(?=\S)([^*]+?)(?<=\S)\*(?!{_ASCII_WORD})")
# 底線斜體依 CommonMark 不可在字中（含漢字）開閉，故維持 Unicode \w 邊界，
# 否則 `_lang=zh-TW，_重要_` 會被 `_lang…，_` 跨識別字配對。
_EM_UNDERSCORE_RE = re.compile(r"(?<!\w)_(?=\S)([^_]+?)(?<=\S)_(?!\w)")
# 句尾：CJK 標點一律；ASCII 標點僅在後接空白或行尾時（版本號 1.30.7 不切）。
_SENTENCE_END_RE = re.compile(r"[。！？]|[.!?](?=\s|$)")
_ASCII_ALNUM_RE = re.compile(r"[A-Za-z0-9]")


def _extract_reply_excerpt(body: str) -> Optional[str]:
    """取回覆本文第一個文字段的首句（純函式，唯讀擷取，不做任何判斷）。

    跳過標題行（含 Setext）、空行、水平線、程式碼圍欄內容、表格列與 HTML 標籤行；
    連續非空行先併為一段（英數字相鄰處補空白）再切句；清單每一項各自成段、只取
    第一項；去清單標記、反引號、連結語法（保留連結文字）與成對強調符號；以第一個
    句尾標點截斷，超過 _EXCERPT_MAX_CHARS 字元截斷加「…」。無可用文字段回傳 None。
    """
    paragraph: list[str] = []
    fence_marker: Optional[str] = None
    for raw in body.splitlines():
        fence = _FENCE_RE.match(raw)
        if fence:
            marker = fence.group(1)
            if fence_marker is None:
                fence_marker = marker
            elif marker == fence_marker:
                fence_marker = None
            continue
        if fence_marker is not None:
            continue
        line = raw.strip()
        if not line:
            if paragraph:
                break
            continue
        if len(paragraph) == 1 and _SETEXT_UNDERLINE_RE.match(raw):
            paragraph = []  # 上一行是 Setext 標題，不是內文
            continue
        if (
            _HEADING_RE.match(raw)
            or _HR_RE.match(raw)
            or _TABLE_ROW_RE.match(raw)
            or _HTML_LINE_RE.match(raw)
        ):
            if paragraph:
                break
            continue
        is_list_item = bool(_LIST_MARKER_RE.match(line))
        if is_list_item and paragraph:
            break  # 清單第二項起各自成段，只取第一項（code review #7）
        line = _BLOCKQUOTE_RE.sub("", line, count=1)
        line = _LIST_MARKER_RE.sub("", line, count=1)
        if line:
            paragraph.append(line)

    if not paragraph:
        return None

    text = ""
    for part in paragraph:
        if text and _ASCII_ALNUM_RE.match(text[-1]) and _ASCII_ALNUM_RE.match(part[0]):
            text += " "  # 英數字硬換行併段補空白，CJK 不補（code review #5）
        text += part
    text = _IMAGE_RE.sub(r"\1", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _BACKTICK_RE.sub("", text)
    text = _STRONG_RE.sub(r"\2", text)
    text = _EM_STAR_RE.sub(r"\1", text)
    text = _EM_UNDERSCORE_RE.sub(r"\1", text)
    text = text.strip()

    m = _SENTENCE_END_RE.search(text)
    if m:
        text = text[: m.end()]
    if len(text) > _EXCERPT_MAX_CHARS:
        text = text[:_EXCERPT_MAX_CHARS] + "…"
    return text or None


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


def reply_sort_key(filename: str) -> Optional[tuple[str, int]]:
    """公開介面：回覆檔名的 (date, n) 排序鍵（全文頁列出回覆序列用，見 handoff_detail.py）。"""
    return _parse_reply_sort_key(filename)


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
        SubrepoStatusResult，含五個分類清單：
        - not_picked_up:    未接手
        - partial_done:     部分完成
        - awaiting_confirm: 已回覆待確認
        - unknown_to:       to: 不符清單
        - errors:           frontmatter 缺欄位等異常（不中斷整體判斷）
    """
    handoffs_dir = Path(kunsu_path) / "docs" / "handoffs"
    replies_dir = handoffs_dir / "replies"

    not_picked_up: list[HandoffInfo] = []
    partial_done: list[HandoffInfo] = []
    awaiting_confirm: list[HandoffInfo] = []
    unknown_to: list[UnknownToItem] = []
    errors: list[ErrorItem] = []

    # ── 若軍師無交接目錄，直接回傳空結果 ─────────────────────────────────────
    if not handoffs_dir.exists():
        return SubrepoStatusResult(
            not_picked_up=not_picked_up,
            partial_done=partial_done,
            awaiting_confirm=awaiting_confirm,
            unknown_to=unknown_to,
            errors=errors,
        )

    # ── 4a-3 前置：預先索引全部回覆 ─────────────────────────────────────────
    # {handoff_filename: [_ReplyEntry]}
    # 一次性掃描，避免逐筆交接再搜尋回覆目錄造成 O(n²) 讀檔
    replies_index: dict[str, list[_ReplyEntry]] = {}

    if replies_dir.exists():
        for reply_file in replies_dir.glob("*.md"):
            try:
                content = reply_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            fm, reply_body = _split_frontmatter(content)
            # str() 強制轉換：YAML 可能將非預期格式的值解析為 bool/int 等
            # 非字串型別（比照 created 欄位已有的處理，見下方 4a-2 區塊），
            # 避免型別不符導致 replies_index 的 key 比對永遠失敗。
            in_reply_to = str(fm.get("in_reply_to") or "")
            status = str(fm.get("status") or "")
            # verify 為選填欄位（驗收方式，ADR 011）：缺省／空值／純空白字串
            # （如 verify: "   "）一律正規化為 None，避免顯示端出現空白標籤
            verify_raw = fm.get("verify")
            verify_str = str(verify_raw).strip() if verify_raw is not None else ""
            verify: Optional[str] = verify_str or None
            if not in_reply_to:
                continue

            sort_key = _parse_reply_sort_key(reply_file.name)
            if sort_key is None:
                continue  # 不符回覆命名慣例，略過

            date_str, n = sort_key
            if in_reply_to not in replies_index:
                replies_index[in_reply_to] = []
            # 本文留在索引內供勝出（最新）回覆萃取首句：同一次讀取、不第二次讀檔，
            # 讀檔失敗維持上方 continue（KTD1）；未勝出的回覆不付萃取成本。
            replies_index[in_reply_to].append(
                _ReplyEntry(date_str, n, str(status), verify, reply_body, reply_file.name)
            )

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

        fm = parse_frontmatter(content)

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
        # series 為選填線別（display-only）：YAML 可能轉型為 bool／int，一律 str()；
        # 缺省、空值與純空白正規化為 None
        series_raw = fm.get("series")
        series = (str(series_raw).strip() or None) if series_raw is not None else None

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
        latest_reply_verify: Optional[str] = None
        latest_reply_excerpt: Optional[str] = None
        latest_reply_filename: Optional[str] = None

        if reply_entries:
            # 依 (date, n) 數值取最大者為最新（等價於降序排序取首筆）
            # 注意：不可用檔名字串排序（見模組頂端說明與 SKILL.md 4a-3 警告）
            best = max(reply_entries, key=lambda e: (e.date, e.n))
            latest_reply_status = best.status
            latest_reply_date = best.date
            latest_reply_verify = best.verify
            latest_reply_excerpt = _extract_reply_excerpt(best.body)
            latest_reply_filename = best.filename

        info = HandoffInfo(
            filename=filename,
            title=title,
            from_role=from_role,
            to_role=to_role,
            created=created,
            latest_reply_status=latest_reply_status,
            latest_reply_date=latest_reply_date,
            latest_reply_verify=latest_reply_verify,
            latest_reply_excerpt=latest_reply_excerpt,
            raw_content=content,
            mtime=mtime,
            series=series,
            latest_reply_filename=latest_reply_filename,
        )

        # ── 依 SKILL.md 4a-3 表格分類 ─────────────────────────────────────────
        # 判準是「有無回覆」：有回覆就不是未接手（ADR 011）
        if latest_reply_status is None:
            not_picked_up.append(info)
        elif latest_reply_status == "submitted":
            awaiting_confirm.append(info)
        elif latest_reply_status == "done":
            pass  # 不列出（略過）
        else:
            # partial／blocked，以及未知 status 值（保守列出不略過，
            # 顯示端原樣呈現該 status）→ 部分完成
            partial_done.append(info)

    return SubrepoStatusResult(
        not_picked_up=not_picked_up,
        partial_done=partial_done,
        awaiting_confirm=awaiting_confirm,
        unknown_to=unknown_to,
        errors=errors,
    )
