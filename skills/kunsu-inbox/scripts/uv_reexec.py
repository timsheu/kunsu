"""
uv_reexec.py — 當前直譯器缺 PyYAML 時，以 uv 重新執行呼叫端腳本一次

背景：handoff-graph.py 與 session_hook.py 匯入沙盤模組需要 PyYAML，而呼叫端
（SKILL.md 步驟、hook 掛載設定）寫的是裸 `python3`。同一台機器上不同 shell 的
`python3` 可能指向不同直譯器（例如 zsh 是 homebrew、fish 是 conda），其中一個沒裝
PyYAML 時依賴圖就只剩 DEP_ERROR。本模組讓腳本自救：找得到 uv 就依腳本檔頭的
PEP 723 依賴宣告，在 uv 管理的隔離環境重跑，不往任何全域環境安裝套件。

找不到 uv、或已重跑過一次仍缺模組時直接返回，由呼叫端照既有路徑降級
（DEP_ERROR／單行降級提示），行為與本模組不存在時相同。
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys

GUARD_ENV = "KUNSU_UV_REEXEC"  # 已重跑過的標記，防止 uv 環境仍缺模組時無限重跑


def reexec_with_uv_if_missing(script: str, argv: list[str], module: str = "yaml") -> None:
    """缺 `module` 且有 uv 時以 `uv run --script` 取代當前行程；其餘情況直接返回。

    須在讀取 stdin 之前呼叫——execv 會把尚未讀取的 stdin 原樣交給新行程（hook 的
    事件 JSON 由此傳入）。
    """
    if os.environ.get(GUARD_ENV) or importlib.util.find_spec(module) is not None:
        return
    uv = shutil.which("uv")
    if uv is None:
        return
    os.environ[GUARD_ENV] = "1"
    try:
        os.execv(uv, [uv, "run", "--quiet", "--script", script, *argv])
    except OSError as e:
        # fail-open：重跑失敗不得阻斷呼叫端，照原直譯器繼續走降級路徑
        print(f"uv 重新執行失敗（{e}），改以當前直譯器繼續", file=sys.stderr)
