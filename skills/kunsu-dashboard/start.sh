#!/usr/bin/env bash
# start.sh — 一鍵啟動 kunsu dashboard
#
# 手動觸發（使用者自己執行這支腳本）的前景啟動；登入自動啟動是另一條由使用者親手
# 安裝的選用路徑，見 SKILL.md「登入自動啟動（選用）」一節（ADR 020 修訂 ADR 010
# Decision 第 1 項第 3 條）。兩者不要共用同一個 port。
#
# 用法：
#   ./start.sh              # 預設 port 8000
#   ./start.sh 8001         # 指定 port

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-8000}"

cd "$SCRIPT_DIR"

if ! python3 -c "import fastapi, uvicorn, yaml, markdown_it" >/dev/null 2>&1; then
  echo "錯誤：缺少必要 pip 依賴（fastapi／uvicorn／PyYAML／markdown-it-py）。" >&2
  echo "請先執行：pip install -r requirements.txt" >&2
  exit 1
fi

exec python3 app/main.py --port "$PORT"
