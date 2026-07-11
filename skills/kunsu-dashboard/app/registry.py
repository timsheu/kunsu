"""
registry.py — 全域反向註冊表讀取與路徑健康檢查

移植自 skills/kunsu-list/scripts/registry-list.sh 的 JSON 讀取邏輯，
改為結構化回傳，供 U2（軍師掃描）、U3（子專案狀態）、U4（HTML 渲染）呼叫。
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class RegistryResult:
    """Registry 讀取與路徑健康檢查的結構化結果。

    Attributes:
        healthy:        路徑存在且為有效 git repo 根目錄的絕對路徑清單。
        stale:          路徑不存在、存在但不是 git repo、或存在但非 repo 根目錄
                        的絕對路徑清單。
        registry_error: 檔案不存在或 JSON 格式損壞時的錯誤描述；
                        None 表示 registry 本身無讀取錯誤。
        raw:            成功解析的 registry 原始 JSON 結構（`{}` 表示無資料或
                        讀取失敗）。呼叫端（如 U4 的身分判斷）用這份資料，不需
                        要再次開檔讀取——避免與本函式的健康檢查讀取產生競態，
                        兩者對同一次呼叫永遠讀到同一份內容。
    """

    healthy: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    registry_error: Optional[str] = None
    raw: dict = field(default_factory=dict)


def load_registry(registry_path: str | Path) -> RegistryResult:
    """讀取全域反向註冊表，對每個登記路徑做存在性與 git repo 有效性檢查。

    Args:
        registry_path: 全域反向註冊表檔案路徑
                       （通常為 ~/.claude/kunsu-registry.json）。

    Returns:
        RegistryResult，含 healthy 清單、stale 清單、registry_error、raw。
        三種 registry 本身的錯誤情境均以 registry_error 字串回傳，不拋例外：

        - 檔案不存在      → registry_error 說明「not found」
        - JSON 格式損壞   → registry_error 說明「malformed」（訊息與前者不同）
        - 無法讀取（權限等）→ registry_error 說明「unreadable」
        - 合法空物件 {}   → registry_error 為 None，healthy 與 stale 皆空

    Health-check 規則（對聯集路徑逐一判斷）：
        1. os.path.isdir(path) 不通過 → stale
        2. git -C <path> rev-parse --show-toplevel，returncode != 0 → stale
        3. rev-parse 成功但輸出路徑與登記路徑不同（登記路徑是 repo 內子目錄，
           非 repo 根）→ stale——與既有 scan-*.sh 腳本的根目錄檢查一致，避免
           health-check 判定為健康、但腳本仍拒絕執行的落差。
        4. subprocess timeout，或 git 執行檔本身找不到 → stale（不拋例外）
    """
    registry_path = str(registry_path)

    # ── 情境一：檔案不存在 ─────────────────────────────────────────────────────
    if not os.path.exists(registry_path):
        return RegistryResult(
            registry_error=f"Registry file not found: {registry_path}"
        )

    # ── 情境二：JSON 讀取（處理格式損壞／無法讀取） ────────────────────────────
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        data = json.loads(content) if content else {}
        if not isinstance(data, dict):
            raise ValueError(
                f"Top-level structure must be a JSON object, "
                f"got: {type(data).__name__}"
            )
    except json.JSONDecodeError as e:
        return RegistryResult(
            registry_error=f"Registry JSON is malformed ({registry_path}): {e}"
        )
    except ValueError as e:
        return RegistryResult(
            registry_error=f"Registry JSON is invalid ({registry_path}): {e}"
        )
    except OSError as e:
        # open() 本身失敗（權限不足、或檔案在 os.path.exists 通過後被刪除的
        # TOCTOU 競態）——docstring 承諾的「不拋例外」涵蓋這個情境，不只是
        # JSON 解析錯誤。
        return RegistryResult(
            registry_error=f"Registry file is unreadable ({registry_path}): {e}"
        )

    # ── 情境三：合法空物件 ─────────────────────────────────────────────────────
    if not data:
        return RegistryResult()

    # ── 收集所有唯一路徑（子專案路徑鍵 ∪ 各條目的軍師路徑） ──────────────────
    # Registry schema:
    #   { "<sub_repo_abs_path>": [{"kunsu": "<kunsu_abs_path>", "roles": [...]}] }
    all_paths: set[str] = set()
    for sub_repo, entries in data.items():
        if not isinstance(entries, list):
            continue
        all_paths.add(sub_repo)
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            kunsu = entry.get("kunsu", "")
            if kunsu:
                all_paths.add(kunsu)

    # ── 對每個唯一路徑做健康檢查 ───────────────────────────────────────────────
    healthy: list[str] = []
    stale: list[str] = []

    for path in sorted(all_paths):
        if not os.path.isdir(path):
            stale.append(path)
            continue

        try:
            result = subprocess.run(
                ["git", "-C", path, "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # returncode == 0 僅代表「path 位於某個 git repo 內」，不代表
            # path 本身就是 repo 根——比照 scan-*.sh 對 $KUNSU_ROOT 的根目錄
            # 檢查（直接比對原始路徑字串，不做 realpath 正規化），兩者須相等
            # 才算 healthy，否則後續呼叫 scan-*.sh 會被腳本自身拒絕。
            if result.returncode == 0 and result.stdout.strip() == path:
                healthy.append(path)
            else:
                stale.append(path)
        except (subprocess.TimeoutExpired, OSError):
            # OSError 涵蓋 git 執行檔本身不存在（FileNotFoundError）等情況；
            # 兩者皆不拋例外，比照其餘路徑一律標記 stale。
            stale.append(path)

    return RegistryResult(healthy=healthy, stale=stale, raw=data)
