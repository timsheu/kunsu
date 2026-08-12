"""
conftest.py — 讓 pytest 能找到 session_hook 模組與軍師沙盤 app 套件。

session_hook.py 位於 skills/kunsu-inbox/scripts/（非套件目錄），
測試前將 scripts/ 與 skills/kunsu-dashboard/ 加入 sys.path，
使 `import session_hook` 與其內部的 `from app.X import ...` 皆能解析。
"""

import sys
from pathlib import Path

_scripts_dir = str(Path(__file__).resolve().parents[1] / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

_dashboard_root = str(Path(__file__).resolve().parents[2] / "kunsu-dashboard")
if _dashboard_root not in sys.path:
    sys.path.insert(0, _dashboard_root)
