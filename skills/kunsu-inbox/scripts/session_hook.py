#!/usr/bin/env python3
"""
session_hook.py — SessionStart hook：session 啟動時自動回報 kunsu 信箱狀態

ADR 002 Decision 3 預留的「第二階段」正式啟用（ADR 014）：startup／resume／
clear／compact／fork 等 session 啟動事件觸發時，依當前 repo 在全域反向註冊表
的身分（子專案／軍師／巢狀）將信箱摘要注入開場 context。只告知不開工
（ADR 002 Decision 5），事件驅動非輪詢，全程唯讀、不呼叫 LLM。

分類邏輯零重寫：子專案模式複用軍師沙盤 app/subrepo_status.py（= kunsu-inbox
SKILL.md 步驟 4a），軍師模式複用 app/kunsu_scan.py（= 三支 scan-*.sh 包裝）。

掛載與解除（機器層級設定，見 SKILL.md「SessionStart hook」節）：
  Claude Code ~/.claude/settings.json → hooks.SessionStart；Codex ~/.codex/hooks.json → hooks.SessionStart
  （各指向自己部署位置的本腳本，ADR 019）；移除該條目即停用。

失敗策略 fail-open：任何錯誤一律 exit 0，絕不阻斷 session 啟動。
未登記 repo 與身分確認前的錯誤（如註冊表毀損）靜默零輸出；
身分確認後的錯誤（如沙盤模組／PyYAML 缺失）輸出單行降級提示。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REGISTRY_PATH = Path.home() / ".claude" / "kunsu-registry.json"

# skill 版號變動提示的狀態檔（機器層級，不進任何 repo）：只記「上次看到的版號」
# 這一項告知性事實。測試以 monkeypatch 指向 tmp_path，不觸真實 home。
STATE_PATH = Path.home() / ".claude" / "kunsu-hook-state.json"

# handoff SKILL.md 於部署樹的相對位置：本腳本 → scripts/ → kunsu-inbox/ →
# skills/ → handoff/SKILL.md。resolve() 跟隨 symlink，copy／symlink 兩種部署
# 模式與 repo 內直跑測試皆可解析（比照 _DASHBOARD_ROOT 註解）。
_HANDOFF_SKILL_PATH = Path(__file__).resolve().parents[2] / "handoff" / "SKILL.md"

# 每分類最多列出筆數，超出以「另有 N 筆」收尾（需求 R5）
MAX_ITEMS_PER_CATEGORY = 5

# 軍師沙盤根目錄：本腳本 → scripts/ → kunsu-inbox/ → skills/ → kunsu-dashboard/。
# resolve() 跟隨 symlink，copy／symlink 兩種部署模式下推算結果一致
# （比照 kunsu_scan.py 的 _SCRIPTS_DIR 註解）。
_DASHBOARD_ROOT = Path(__file__).resolve().parents[2] / "kunsu-dashboard"


def _read_cwd_from_stdin() -> str:
    """讀取 hook stdin JSON 的 cwd；缺欄位或讀取失敗時退回程序當前目錄。"""
    try:
        data = json.loads(sys.stdin.read() or "{}")
        cwd = data.get("cwd") if isinstance(data, dict) else None
        if isinstance(cwd, str) and cwd:
            return cwd
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        pass
    return os.getcwd()


def _git_root(cwd: str) -> str | None:
    """取 cwd 所在 git repo 的根路徑；非 repo 或 git 不可用時回傳 None。"""
    try:
        proc = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _load_raw_registry(path: Path) -> dict:
    """容錯讀取註冊表；任何錯誤回傳 {}。

    hook 對註冊表錯誤保持安靜——錯誤呈現由 kunsu-list skill 與軍師沙盤負責，
    hook 的職責是機會性提示，不是診斷面。
    """
    try:
        content = path.read_text(encoding="utf-8").strip()
        data = json.loads(content) if content else {}
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _kunsu_paths_of(raw: dict) -> set[str]:
    """註冊表全部條目中出現過的軍師路徑集合（軍師身分判斷用）。"""
    paths: set[str] = set()
    for entries in raw.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and entry.get("kunsu"):
                paths.add(str(entry["kunsu"]))
    return paths


def _all_known_roles(raw: dict, kunsu_path: str) -> set[str]:
    """同一軍師底下全部已登記角色代碼的聯集（to: 不符清單判斷用）。"""
    roles: set[str] = set()
    for entries in raw.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("kunsu") or "") == kunsu_path:
                roles.update(str(r) for r in (entry.get("roles") or []) if str(r))
    return roles


def _ensure_dashboard_on_path() -> None:
    """把軍師沙盤根目錄加入 sys.path，供 `from app.X import` 匯入。"""
    p = str(_DASHBOARD_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)


def _capped(items: list[str], indent: str = "  ") -> list[str]:
    lines = [f"{indent}• {s}" for s in items[:MAX_ITEMS_PER_CATEGORY]]
    extra = len(items) - MAX_ITEMS_PER_CATEGORY
    if extra > 0:
        lines.append(f"{indent}…另有 {extra} 筆")
    return lines


def _reply_annotated(info) -> str:
    """帶最新回覆狀態的交接摘要行（部分完成／已回覆待確認共用）。"""
    status = info.latest_reply_status or ""
    label = f"⛔ {status}" if status == "blocked" else status
    verify = f"，verify: {info.latest_reply_verify}" if info.latest_reply_verify else ""
    return f"{info.filename}（{label} {info.latest_reply_date}{verify}）"


def _sub_mode_lines(root: str, raw: dict) -> list[str]:
    # 延遲匯入：未登記 repo 的快退路徑不付沙盤模組（含 PyYAML）的匯入成本
    from app.subrepo_status import get_subrepo_status

    lines: list[str] = []
    for entry in raw.get(root) or []:
        if not isinstance(entry, dict):
            continue
        kunsu = str(entry.get("kunsu") or "")
        roles = {str(r) for r in (entry.get("roles") or []) if str(r)}
        if not kunsu or not roles:
            continue
        kunsu_name = Path(kunsu).name
        role_label = "、".join(sorted(roles))

        if not os.path.isdir(kunsu):
            lines.append(f"⚠ 軍師 {kunsu_name} 路徑失聯（{kunsu}），略過掃描")
            continue

        result = get_subrepo_status(root, roles, _all_known_roles(raw, kunsu), kunsu)

        section: list[str] = []
        if result.not_picked_up:
            items = sorted(result.not_picked_up, key=lambda h: h.created)
            section.append(f"⚠ 未接手 {len(items)}：")
            section += _capped([f"{h.filename}（created {h.created}）" for h in items])
        if result.partial_done:
            items = sorted(result.partial_done, key=lambda h: h.latest_reply_date or "")
            section.append(f"部分完成 {len(items)}：")
            section += _capped([_reply_annotated(h) for h in items])
        if result.awaiting_confirm:
            items = sorted(result.awaiting_confirm, key=lambda h: h.latest_reply_date or "")
            section.append(f"已回覆待確認 {len(items)}：")
            section += _capped([_reply_annotated(h) for h in items])
        if result.unknown_to:
            section.append(f"⚠ to: 不符清單 {len(result.unknown_to)} 筆（詳 kunsu-inbox skill）")
        if result.errors:
            section.append(f"⚠ frontmatter 異常 {len(result.errors)} 筆（詳 kunsu-inbox skill）")

        if section:
            lines.append(f"[{role_label} @ 軍師 {kunsu_name}]")
            lines += section
    return lines


def _kunsu_mode_lines(root: str) -> list[str]:
    from app.kunsu_scan import scan_kunsu

    result = scan_kunsu(root)

    body: list[str] = []
    if result.tripwire_lines:
        body.append(f"🚨 tripwire 異常 {len(result.tripwire_lines)}：")
        body += _capped(result.tripwire_lines)
    if result.script_error:
        body.append(f"⚠ 掃描腳本異常：{result.script_error}")
    for label, items in (
        ("新回覆", result.new_replies),
        ("新申請", result.new_applications),
        ("新上報", result.new_reports),
    ):
        if items:
            body.append(f"{label} {len(items)}：")
            body += _capped(items)

    if not body:
        return []
    return [f"[軍師模式 @ {Path(root).name}]"] + body


def _handoff_version_notice() -> list[str]:
    """比對部署 handoff SKILL.md 版號與狀態檔，變動時回傳單行提示。

    首次執行（無狀態檔）靜默記錄當前版號、不提示——避免每台機器首個
    session 收到無意義提示；狀態檔損壞視同首次重建。任何失敗 fail-open
    回傳空清單，不阻斷 hook 既有輸出。僅於身分確認後呼叫（ADR 002
    未登記快退零輸出不受影響）。
    """
    try:
        current: str | None = None
        for line in _HANDOFF_SKILL_PATH.read_text(encoding="utf-8").splitlines()[:10]:
            if line.startswith("version:"):
                current = line.split(":", 1)[1].strip()
                break
        if not current:
            return []

        state: dict = {}
        try:
            loaded = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                state = loaded
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            state = {}  # 缺檔或損壞：視同首次

        last = state.get("handoff_version")
        if last == current:
            return []

        state["handoff_version"] = current
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        if last is None:
            return []  # 首次：靜默建檔不提示
        return [
            f"📌 handoff skill 已更新至 v{current}（自 v{last}），流程指引有變——"
            "本輪 add／done 建議經 handoff skill 執行或回讀 SKILL.md 對應段"
        ]
    except Exception:
        return []  # fail-open：版號提示屬告知層，任何失敗靜默跳過


def main() -> int:
    identity_established = False
    try:
        cwd = _read_cwd_from_stdin()
        raw = _load_raw_registry(REGISTRY_PATH)
        if not raw:
            return 0
        root = _git_root(cwd)
        if root is None:
            return 0

        # ADR 002 Decision 2：以 repo 根路徑為唯一基準，獨立評估雙重身分
        is_sub = root in raw
        is_kunsu = root in _kunsu_paths_of(raw)
        if not (is_sub or is_kunsu):
            return 0
        identity_established = True

        for notice in _handoff_version_notice():
            print(notice)

        _ensure_dashboard_on_path()
        lines: list[str] = []
        if is_sub:
            lines += _sub_mode_lines(root, raw)
        if is_kunsu:
            lines += _kunsu_mode_lines(root)

        if lines:
            print("📬 kunsu 信箱")
            print("\n".join(lines))
            print("→ 接手／查核請執行 kunsu-inbox skill 或直接指名檔案；本提示僅告知，不構成任何動工授權")
        else:
            print("📬 kunsu 信箱：無待辦")
        return 0
    except Exception as e:  # fail-open：hook 絕不阻斷 session 啟動（需求 R7）
        if identity_established:
            print(
                f"📬 kunsu session hook 降級（{type(e).__name__}: {e}），"
                "不影響 session；信箱請手動執行 kunsu-inbox skill"
            )
        return 0


if __name__ == "__main__":
    sys.exit(main())
