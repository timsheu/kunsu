"""
kunsu_scan.py — 軍師模式掃描整合

對 U1 判為 healthy 的軍師路徑，依序呼叫既有三支掃描腳本，
解析輸出並分類回覆、申請、上報與 tripwire 異常。
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# 腳本目錄：以本模組位置往上推算至 skills/ 層，再定位 kunsu-inbox/scripts/
#
# 層次：skills/kunsu-dashboard/app/kunsu_scan.py
#   Path(__file__).resolve() = .../skills/kunsu-dashboard/app/kunsu_scan.py
#   parents[0]               = .../skills/kunsu-dashboard/app/
#   parents[1]               = .../skills/kunsu-dashboard/
#   parents[2]               = .../skills/
#   parents[2] / "kunsu-inbox" / "scripts" = .../skills/kunsu-inbox/scripts/
#
# install.sh 的 --link 模式以目錄 symlink 部署；resolve() 跟隨 symlink
# 回到源碼目錄，兩種部署模式（copy/symlink）下路徑計算結果一致。
_SCRIPTS_DIR: Path = (
    Path(__file__).resolve().parents[2] / "kunsu-inbox" / "scripts"
)

# 腳本清單：(腳本檔名, 對應的 stdout 前綴)
# 順序與 /kunsu-inbox SKILL.md 的呈現順序一致（replies → applications → reports）
_SCRIPTS: list[tuple[str, str]] = [
    ("scan-replies.sh",      "NEW_REPLY:"),
    ("scan-applications.sh", "NEW_APPLICATION:"),
    ("scan-reports.sh",      "NEW_REPORT:"),
]


@dataclass(frozen=True)
class KunsuScanResult:
    """單一軍師的掃描結果。

    Attributes:
        kunsu_path:       被掃描的軍師絕對路徑。
        new_replies:      新回覆相對路徑清單（scan-replies.sh NEW_REPLY: 前綴行）。
        new_applications: 新申請相對路徑清單（scan-applications.sh NEW_APPLICATION: 前綴行）。
        new_reports:      新上報相對路徑清單（scan-reports.sh NEW_REPORT: 前綴行）。
        tripwire_lines:   tripwire 行完整字串清單（含 TRIPWIRE:<XY>... 格式）；
                          非空表示某支腳本 exit 2，掃描在此中止。
        script_error:     非預期 exit code 時的錯誤描述字串，格式：
                          "<script_name> exited with code <N>: <stderr>"；
                          None 表示無腳本錯誤。

    與 tripwire 的明確區分：
        - tripwire 狀態：tripwire_lines 非空（安全邊界觸發，由腳本 exit 2 回報）
        - 腳本錯誤狀態：script_error 非 None（腳本自身異常，exit code 非 0 非 2）
        兩者語義不同，不可以單一布林值混用。
    """

    kunsu_path: str
    new_replies: list[str] = field(default_factory=list)
    new_applications: list[str] = field(default_factory=list)
    new_reports: list[str] = field(default_factory=list)
    tripwire_lines: list[str] = field(default_factory=list)
    script_error: Optional[str] = None


def scan_kunsu(kunsu_path: str) -> KunsuScanResult:
    """對單一軍師路徑依序呼叫三支掃描腳本，解析輸出並回傳結構化結果。

    Args:
        kunsu_path: 軍師根目錄的絕對路徑（U1 load_registry 判定為 healthy 者）。
                    呼叫前提：路徑存在且為有效 git repo 根，由呼叫端（U4）保證。
                    腳本內部亦會自行核驗；若不符則腳本以 exit 1 結束，
                    scan_kunsu 會將其歸類為 script_error。

    Returns:
        KunsuScanResult，含新回覆／新申請／新上報清單，以及 tripwire 與腳本錯誤狀態。

    Exit code 語意（依 scan-*.sh 規格）：
        0  — 正常完成，解析 NEW_*: 前綴行加入對應清單。
        2  — tripwire 觸發，收集所有 TRIPWIRE: 行後立即停止後續腳本
             （比照 SKILL.md 4b-3「立即停止」）。
        其他 — 腳本本身異常，記錄 script_error（含 stderr 摘要），停止後續腳本。

    Subprocess 呼叫規格：
        ["bash", <script_path>, kunsu_path]，timeout=15 秒。
        以 bash 明確呼叫腳本，不依賴腳本執行位元（chmod）。
    """
    # 用於累積各清單的本地變數（KunsuScanResult 為 frozen，只能在建構時傳入）
    new_replies: list[str] = []
    new_applications: list[str] = []
    new_reports: list[str] = []

    # 前綴 → 對應清單的映射，供 exit 0 時逐行解析使用
    _prefix_to_list: dict[str, list[str]] = {
        "NEW_REPLY:":       new_replies,
        "NEW_APPLICATION:": new_applications,
        "NEW_REPORT:":      new_reports,
    }

    for script_name, expected_prefix in _SCRIPTS:
        script_path = _SCRIPTS_DIR / script_name

        try:
            proc = subprocess.run(
                ["bash", str(script_path), kunsu_path],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except subprocess.TimeoutExpired:
            return KunsuScanResult(
                kunsu_path=kunsu_path,
                new_replies=list(new_replies),
                new_applications=list(new_applications),
                new_reports=list(new_reports),
                script_error=f"{script_name} timed out after 15s",
            )
        except OSError as e:
            # bash 執行檔本身不存在等情況（FileNotFoundError 為 OSError 子類）；
            # 比照 timeout，回報為腳本錯誤而非讓例外穿透到 FastAPI 路由層。
            return KunsuScanResult(
                kunsu_path=kunsu_path,
                new_replies=list(new_replies),
                new_applications=list(new_applications),
                new_reports=list(new_reports),
                script_error=f"{script_name} failed to run: {e}",
            )

        if proc.returncode == 2:
            # tripwire 觸發：收集所有 TRIPWIRE: 行，立即回傳，不再執行後續腳本。
            # 即使 stdout 中沒有任何 TRIPWIRE: 前綴行（如診斷輸出寫到 stderr），
            # tripwire_lines 仍必須非空，否則呼叫端會誤判為「正常、無新訊息」
            # ——exit code 2 本身就是安全邊界訊號，不能因為找不到明細行而消失。
            tripwire_lines = [
                line
                for line in proc.stdout.splitlines()
                if line.startswith("TRIPWIRE:")
            ] or [f"TRIPWIRE: {script_name} exited 2 (no TRIPWIRE: line in stdout)"]
            return KunsuScanResult(
                kunsu_path=kunsu_path,
                new_replies=list(new_replies),
                new_applications=list(new_applications),
                new_reports=list(new_reports),
                tripwire_lines=tripwire_lines,
            )

        if proc.returncode != 0:
            # 非預期 exit code：腳本本身異常（如參數錯誤 exit 1），停止後續腳本
            stderr_excerpt = proc.stderr.strip()
            error_msg = f"{script_name} exited with code {proc.returncode}"
            if stderr_excerpt:
                error_msg += f": {stderr_excerpt}"
            return KunsuScanResult(
                kunsu_path=kunsu_path,
                new_replies=list(new_replies),
                new_applications=list(new_applications),
                new_reports=list(new_reports),
                script_error=error_msg,
            )

        # exit 0：逐行解析 stdout，只比對「這支腳本自己該有的前綴」
        # （不可用全部三個前綴逐一嘗試——那樣任何一支腳本輸出剛好以另一支
        # 腳本的前綴開頭的行，會被誤植到錯誤的清單）。
        dest = _prefix_to_list[expected_prefix]
        for line in proc.stdout.splitlines():
            if line.startswith(expected_prefix):
                dest.append(line[len(expected_prefix):])

    return KunsuScanResult(
        kunsu_path=kunsu_path,
        new_replies=new_replies,
        new_applications=new_applications,
        new_reports=new_reports,
    )
