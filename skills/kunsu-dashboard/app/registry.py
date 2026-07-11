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


@dataclass
class RegistryResult:
    """Registry 讀取與路徑健康檢查的結構化結果。

    Attributes:
        healthy:        路徑存在且為有效 git repo 的絕對路徑清單。
        stale:          路徑不存在，或存在但不是有效 git repo 的絕對路徑清單。
        registry_error: 檔案不存在或 JSON 格式損壞時的錯誤描述；
                        None 表示 registry 本身無讀取錯誤。
    """

    healthy: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    registry_error: Optional[str] = None


def load_registry(registry_path: str | Path) -> RegistryResult:
    """讀取全域反向註冊表，對每個登記路徑做存在性與 git repo 有效性檢查。

    Args:
        registry_path: 全域反向註冊表檔案路徑
                       （通常為 ~/.claude/kunsu-registry.json）。

    Returns:
        RegistryResult，含 healthy 清單、stale 清單、registry_error。
        三種 registry 本身的錯誤情境均以 registry_error 字串回傳，不拋例外：

        - 檔案不存在    → registry_error 說明「not found」
        - JSON 格式損壞  → registry_error 說明「malformed」（訊息與前者不同）
        - 合法空物件 {} → registry_error 為 None，healthy 與 stale 皆空

    Health-check 規則（對聯集路徑逐一判斷）：
        1. os.path.isdir(path) 不通過 → stale
        2. git -C <path> rev-parse --show-toplevel，returncode != 0 → stale
        3. subprocess timeout → stale（避免卡住整頁刷新）
    """
    registry_path = str(registry_path)

    # ── 情境一：檔案不存在 ─────────────────────────────────────────────────────
    if not os.path.exists(registry_path):
        return RegistryResult(
            registry_error=f"Registry file not found: {registry_path}"
        )

    # ── 情境二：JSON 讀取（處理格式損壞） ──────────────────────────────────────
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
            if result.returncode == 0:
                healthy.append(path)
            else:
                stale.append(path)
        except subprocess.TimeoutExpired:
            stale.append(path)

    return RegistryResult(healthy=healthy, stale=stale)
