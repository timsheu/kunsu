#!/usr/bin/env python3
"""
handoff-graph.py — 交接依賴圖 CLI：印固定前綴文字行供 kunsu-inbox skill 步驟 4a／4b 讀取

用法：
    python3 handoff-graph.py <軍師 repo 路徑> [--role <角色代碼>]

輸出（stdout，一行一筆；供模型閱讀，非機器 API——沙盤例外的 text/html 精神）：
    DEP:<檔名>\t<ready|waiting>\t<waiting_on 逗號分隔，ready 為空>
    DEP_CYCLE:<檔名,…>
    DEP_UNRESOLVED:<檔名>\t<目標>\t<原因>
    DEP_ANOMALY:<檔名>\t<種類>
    DEP_ERROR:<訊息>            （建圖或匯入失敗，advisory）
    DEP_NONE                    （無任何 DEP／DEP_CYCLE／DEP_UNRESOLVED／DEP_ANOMALY 行時）

`--role` 給定時 DEP: 行只列 to: 為該角色代碼的交接（子 repo 模式 4a）；
異常類行不受角色過濾（軍師模式 4b 亦需）。

推導邏輯單一來源：kunsu-dashboard app/handoff_graph.py（比照 session_hook.py
推算沙盤路徑並延遲匯入）；本腳本零圖邏輯，模型不得手算依賴。
一律 exit 0（advisory，不阻斷 inbox 彙整）。
"""

from __future__ import annotations

import sys
from pathlib import Path

_DASHBOARD_ROOT = Path(__file__).resolve().parents[2] / "kunsu-dashboard"


def _parse_args(argv: list[str]) -> tuple[str | None, str | None]:
    kunsu: str | None = None
    role: str | None = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--role":
            role = argv[i + 1] if i + 1 < len(argv) else None
            i += 2
            continue
        if arg.startswith("--role="):
            role = arg[len("--role="):]
        elif kunsu is None:
            kunsu = arg
        i += 1
    return kunsu, role


def main(argv: list[str]) -> int:
    kunsu, role = _parse_args(argv)
    if not kunsu:
        print("DEP_ERROR:缺少軍師 repo 路徑（用法：handoff-graph.py <路徑> [--role <角色代碼>]）")
        return 0
    try:
        sys.path.insert(0, str(_DASHBOARD_ROOT))
        from app.handoff_graph import DERIVED_WAITING, get_handoff_graph

        graph = get_handoff_graph(kunsu)
    except Exception as e:  # noqa: BLE001 — advisory：任何失敗只印一行
        print(f"DEP_ERROR:{type(e).__name__}: {e}")
        return 0

    lines: list[str] = []
    for filename in sorted(graph.derived):
        node = graph.nodes.get(filename)
        if role and (node is None or node.to_role != role):
            continue
        state = graph.derived[filename]
        waiting = ",".join(graph.waiting_on.get(filename, [])) if state == DERIVED_WAITING else ""
        lines.append(f"DEP:{filename}\t{state}\t{waiting}")
    for cyc in graph.cycles:
        lines.append("DEP_CYCLE:" + ",".join(cyc))
    for u in graph.unresolved:
        lines.append(f"DEP_UNRESOLVED:{u.source}\t{u.target}\t{u.reason}")
    for a in graph.anomalies:
        lines.append(f"DEP_ANOMALY:{a.filename}\t{a.kind}")
    for e in graph.errors:
        lines.append(f"DEP_ERROR:{e.filename}: {e.error}")

    if not lines:
        print("DEP_NONE")
    else:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
