#!/usr/bin/env bash
# start.sh — 一鍵啟動 kunsu dashboard
#
# 仍是手動觸發（使用者自己執行這支腳本），不涉及 launchd／cron／開機自動啟動，
# 符合 docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md
# Decision 第 1 項第 3 條（啟動停止須使用者手動掌握）。
#
# 用法：
#   ./start.sh              # 預設 port 8000
#   ./start.sh 8001         # 指定 port

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-8000}"

cd "$SCRIPT_DIR"

if ! python3 -c "import fastapi, uvicorn, yaml" >/dev/null 2>&1; then
  echo "錯誤：缺少必要 pip 依賴（fastapi／uvicorn／PyYAML）。" >&2
  echo "請先執行：pip install -r requirements.txt" >&2
  exit 1
fi

exec python3 app/main.py --port "$PORT"
