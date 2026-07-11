"""
conftest.py — 讓 pytest 能從 skills/kunsu-dashboard/ 找到 app 套件。

此檔案位於 skills/kunsu-dashboard/，pytest 執行任何子目錄下的測試前
都會先載入此 conftest，將 skills/kunsu-dashboard/ 加入 sys.path，
使 `from app.registry import ...` 等套件匯入能正確解析。
"""

import sys
from pathlib import Path

# 確保 skills/kunsu-dashboard/ 在 sys.path 最前端
_dashboard_root = str(Path(__file__).parent)
if _dashboard_root not in sys.path:
    sys.path.insert(0, _dashboard_root)
