# kunsu-dashboard — kunsu 訊息聚合本機 Dashboard

**這不是一個 Claude Code skill（不透過 `/kunsu-dashboard` 或任何觸發語啟動）。** 這是一個獨立的本機 FastAPI 服務，只是借用 `skills/` 目錄的部署慣例（隨 `install.sh` 一併複製或 symlink），執行時完全不經過 Claude Code session。設計理由與例外條件見 [ADR 010](../../docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md)。

彙整全域反向註冊表 `~/.claude/kunsu-registry.json` 裡所有軍師與子專案的 kunsu 訊息狀態（交接待接手／已回覆、新申請、新上報），取代逐一切換 CLI 視窗手動執行 `/kunsu-inbox` 的做法。刷新瀏覽器頁面即觸發全新掃描，不跑背景服務。

---

## 安裝

需要 **Python 3.10 以上**（`python3 --version` 確認；FastAPI 0.139.0／uvicorn 0.51.0 皆要求 `>=3.10`）。macOS 內建系統 Python 通常是 3.9，不足時以 Homebrew（`brew install python@3.12`）或 pyenv 安裝較新版本。

```bash
cd ~/.claude/skills/kunsu-dashboard   # 或本 repo 的 skills/kunsu-dashboard/（開發模式）
pip install -r requirements.txt
```

`install.sh` 本身只負責複製／symlink 這個目錄，不負責安裝上述 pip 依賴——依賴安裝是一次性的手動步驟。

## 啟動

```bash
python3 app/main.py --port 8000
```

伺服器綁定 `127.0.0.1:8000`（port 可自訂），只服務本機、單一使用者。開啟瀏覽器造訪 `http://127.0.0.1:8000/`。

**刷新瀏覽器頁面即重新掃描全部已登記的軍師與子專案**——不需要重啟伺服器。伺服器本身不會自動刷新、不跑背景排程；關閉終端機視窗即停止服務，下次要用再手動啟動一次。

## 停止

在啟動伺服器的終端機視窗按 `Ctrl+C`，或 `kill` 對應的 process。沒有背景常駐機制，不會自動重啟。

## 疑難排解

- **`pip install` 失敗**：多半是 Python 版本不足 3.10，先用 `python3 --version` 確認。
- **Port 已被佔用**：換一個 `--port`（如 `python3 app/main.py --port 8001`）。
- **頁面顯示「Registry 讀取錯誤」**：`~/.claude/kunsu-registry.json` 不存在或格式損壞，先用 `/kunsu-init` 或 `/kunsu-list` 確認註冊表狀態。
