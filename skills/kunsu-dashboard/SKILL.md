---
name: kunsu-dashboard
description: 軍師沙盤（kunsu dashboard）的安裝與啟動說明。不是可觸發的 skill——不要選用、不要依此執行任何流程；只在使用者要安裝或啟動沙盤時作為閱讀文件。
disable-model-invocation: true
user-invocable: false
---

# kunsu-dashboard — 軍師沙盤（kunsu dashboard）

**這不是一個可觸發的 skill（frontmatter 已以 Claude Code 與 Codex 的原生旗標停用選用，不透過任何觸發語啟動）。** 這是一個獨立的本機 FastAPI 服務，只是借用 `skills/` 目錄的部署慣例（隨 `install.sh` 一併複製或 symlink），執行時完全不經過任何 agent session。設計理由與例外條件見 [ADR 010](../../docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md)。

**軍師沙盤（kunsu dashboard）**——如統帥推演戰局的沙盤，一頁彙整全域反向註冊表 `~/.claude/kunsu-registry.json` 裡所有軍師與子專案的 kunsu 訊息狀態（未接手／部分完成／已回覆待確認交接、新回覆、新申請、新上報，含回覆 `verify` 驗收標籤，見 ADR 011），取代逐一切換 CLI 視窗手動執行 kunsu-inbox skill 的做法。重新整理瀏覽器頁面即觸發全新掃描，不跑背景服務。

---

## 安裝

需要 **Python 3.10 以上**（`python3 --version` 確認；FastAPI 0.139.0／uvicorn 0.51.0 皆要求 `>=3.10`）。macOS 內建系統 Python 通常是 3.9，不足時以 Homebrew（`brew install python@3.12`）或 pyenv 安裝較新版本。

```bash
cd ~/.claude/skills/kunsu-dashboard   # Codex 部署目錄為 ~/.agents/skills/kunsu-dashboard；或本 repo 的 skills/kunsu-dashboard/（開發模式）
pip install -r requirements.txt
```

`install.sh` 本身只負責複製／symlink 這個目錄，不負責安裝上述 pip 依賴——依賴安裝是一次性的手動步驟。依賴共四筆：fastapi、uvicorn、PyYAML、markdown-it-py（全文頁 `/handoff` 的 Markdown 伺服器端渲染；缺席時全文頁降級為純文字，其他頁面不受影響）。

## 啟動

一鍵啟動（推薦，會先檢查依賴是否已安裝）：

```bash
./start.sh          # 預設 port 8000
./start.sh 8001      # 指定 port
```

或手動呼叫：

```bash
python3 app/main.py --port 8000
```

兩種方式都是使用者自己觸發的前景啟動。要讓沙盤在登入後自動可用，見下方「登入自動啟動（選用）」；安裝 LaunchAgent 後不再以 `start.sh` 啟動同一個 port，開發時改以 `./start.sh <其他 port>` 跑工作樹版本（啟停規則見 [ADR 010](../../docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md) Decision 第 1 項第 3 條與 [ADR 020](../../docs/adr/2026-10-01-adr-candidate-020-dashboard-login-autostart.md) 的修訂）。伺服器綁定 `127.0.0.1:8000`（port 可自訂），只服務本機、單一使用者。開啟瀏覽器造訪 `http://127.0.0.1:8000/`：首頁是看板（每軍師一張，持球者泳道 × 狀態欄），`/overview` 是完整彙整頁，`/archive` 列出已歸檔交接；頁面說明見 `docs/playbooks/dashboard.md`。

**重新整理瀏覽器頁面即重新掃描全部已登記的軍師與子專案**——不需要重啟伺服器。伺服器本身不會自動重新掃描、不跑背景排程；前景啟動時關閉終端機視窗即停止服務，下次要用再手動啟動一次。

## 停止

前景啟動：在啟動伺服器的終端機視窗按 `Ctrl+C`，或 `kill` 對應的 process。伺服器不會自動重啟。LaunchAgent 啟動的停止與解除見下一節。

## 登入自動啟動（選用）

由使用者親手安裝一個只含 `RunAtLoad` 的 macOS LaunchAgent，登入後沙盤即可用（[ADR 020](../../docs/adr/2026-10-01-adr-candidate-020-dashboard-login-autostart.md)）。repo 只提供範本與指令，`install.sh` 與任何 skill 都不會代為寫入 `~/Library/LaunchAgents/`。下列指令供你在終端機執行；`<label>` 建議 `com.kunsu.dashboard`，`<port>` 不要用 `start.sh` 預設的 8000。

**安裝**

1. 停止任何手動執行中的 `start.sh`（否則它佔住 port，LaunchAgent 啟動失敗，而 curl 仍由 `start.sh` 回應造成假綠燈）。
2. 複製範本 `launchd/kunsu-dashboard.plist.template` 到 `~/Library/LaunchAgents/<label>.plist`，填入四個佔位值：`__LABEL__`、`__PYTHON__`（`python3 -c 'import sys; print(sys.executable)'` 取得的絕對路徑——launchd 不載入 shell 設定，pyenv／conda shims 不可用）、`__MAIN_PY__`（部署副本 `~/.claude/skills/kunsu-dashboard/app/main.py` 的絕對路徑，不指向 repo 工作樹）、`__PORT__`。
3. 載入：

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/<label>.plist
```

**驗收**（四步，任一失敗即先解除、查 `/tmp/kunsu-dashboard.log` 修正後再重裝，避免失敗的 LaunchAgent 於每次登入重複嘗試）

```bash
plutil -p ~/Library/LaunchAgents/<label>.plist          # 只含 Label／ProgramArguments／RunAtLoad／StandardOutPath／StandardErrorPath，RunAtLoad 為 true
launchctl print gui/$(id -u)/<label>                      # job 已載入且執行中
curl --retry 5 --retry-connrefused --retry-delay 1 -s http://127.0.0.1:<port>/ | grep -q '軍師沙盤（kunsu dashboard）' && echo OK
```

第四步：登出再登入一次，重複上面後兩行，確認下次登入確實自動啟動。

**程式碼更新後重啟**（每次重跑 `install.sh` 後都要；以 `install.sh --link` 部署時，repo 任何內容變動——含切換分支、`git pull`——後都要）

```bash
launchctl kickstart -k gui/$(id -u)/<label>
```

**解除**（只做 bootout 而未刪 plist，下次登入仍會再啟動）

```bash
launchctl bootout gui/$(id -u)/<label>
rm ~/Library/LaunchAgents/<label>.plist
```

解除後行為完全回到前景手動啟停。限制：launchd 啟動失敗（Python 路徑錯、依賴缺失、port 被佔）沒有主動通知，只表現為瀏覽器連不上，須查 `/tmp/kunsu-dashboard.log`（重開機清除）；日後切換 Python 環境時 plist 會靜默失效，同樣只表現為連線失敗。

## 疑難排解

- **`pip install` 失敗**：多半是 Python 版本不足 3.10，先用 `python3 --version` 確認。
- **Port 已被佔用**：換一個 `--port`（如 `python3 app/main.py --port 8001`）。若已安裝 LaunchAgent，先確認不是它正佔著同一個 port。
- **LaunchAgent 載入後連不上**：查 `/tmp/kunsu-dashboard.log`；常見原因是 `__PYTHON__` 指到沒裝依賴的 python、`__MAIN_PY__` 路徑錯、或 port 與其他服務（含綁 `0.0.0.0` 的 Docker 映射）衝突。
- **頁面顯示「Registry 讀取錯誤」**：`~/.claude/kunsu-registry.json` 不存在或格式損壞，先用 kunsu-init 或 kunsu-list skill 確認註冊表狀態。
