# Codex 雙端試點：`scripts/codex-pilot.sh` 用法與手動核對清單

kunsu 同一份原始碼雙部署至 Claude Code 與 Codex（[ADR 019](../adr/2026-09-06-adr-candidate-019-agent-neutral-deployment.md)）後，以本試點證明 Codex 在軍師端與子專案端都能經 handoff 文件與對方雙向溝通、兩支 hook 在 Codex 側生效、確認 commit 的兩態（同意／取消）成立。試點是 repo 內首支持久化的 shell 測試腳本，每次 handoff skill 版號變動後重跑一次（計畫 R19）。

## 前置條件

- Codex CLI 已安裝（試點於 0.142.5 撰寫；官方文件內容領先此版，升版後重跑本腳本並重驗掛載說明）。
- 已執行 `./install.sh`（偵測到 `~/.codex/` 即一併部署至 `~/.agents/skills/`）。
- `python3` 可用；試點目錄固定為 `${TMPDIR:-/tmp}/kunsu-codex-pilot/`，每輪先刪再建。
- 不需先掛載 hook：試點以 `-c hooks.*` 注入兩支 hook（與使用者 `~/.codex/hooks.json` 為合併而非取代）並帶 `--dangerously-bypass-hook-trust`；正式使用時的掛載與信任步驟見 `skills/kunsu-inbox/SKILL.md`。

## 執行

一輪約 15 次 `codex exec`（含 `resume`）。ChatGPT 免費方案的 Codex 用量額度有限（2026-09-07 五輪即用盡、次月重置）；任一呼叫 `turn.failed`（額度、模型不支援）腳本即早停 exit 2，不會把環境錯誤誤報為 kunsu 缺陷。

```bash
bash scripts/codex-pilot.sh                     # 預設模型 gpt-5.5
KUNSU_PILOT_MODEL=gpt-5.5 KUNSU_PILOT_KEEP=1 bash scripts/codex-pilot.sh   # 保留試點目錄與日誌
```

腳本會：

1. **第 0 步四探針**（任一失敗即中止，不進入斷言）：`.git/` 在 workspace-write 下可寫（試點路徑在 `$TMPDIR` 屬例外，真實路徑見手動核對）；`KUNSU_SCAN_STATS_FILE` 隔離路徑傳入模型 shell；`-c features.hooks=false` 能關閉 hook（對照組）；SessionStart 注入落 rollout。
2. **接手方鏈**：腳本先以 `new-handoff.sh` 派發一份交接，Codex 在已登記子專案以 `$handoff reply` 回覆（斷言回覆檔落軍師信箱、`scan-replies.sh` 偵測、回報推播跳過）；`$kunsu-report` 上報與 `$kunsu-apply` 申請各一（斷言檔案落地與兩支掃描腳本偵測）。
3. **軍師端鏈**：`$handoff add` 派發（斷言本體與 `to:`、回報未推播、確認 commit 印指令後零新 commit）；`$handoff done` 同意分支以 `codex exec resume <thread_id>` 第二回合送同意（斷言 commit 存在、本體在 `archive/`、commit 含 rename）；否定分支另建交接、不 resume（斷言零新 commit、歸檔停在 index 中間態）；canary（斷言 rollout 內專案指引注入含末節 sentinel，證明 `AGENTS.md → CLAUDE.md` symlink 完整讀入、未被截尾）；`$kunsu-inbox` 於關 hook 對照下使隔離統計檔 `total_runs` 遞增；最後 `git add -A` 被 PreToolUse 守門 deny（斷言隔離統計檔 `GUARD_DENY` 遞增、`--json` 內該呼叫零痕跡、porcelain 與快照一致）。
4. 印出 pass／fail 與手動核對清單；trap 以 `registry-remove.sh` 移除試點子專案的暫登（不整檔還原，避免覆蓋他 session 的寫入）。

日誌落在試點目錄 `logs/`：每步一份 `*.jsonl`（`codex exec --json` 事件）與 `*.err`。

## 可觀測面（依 0.142.5 原始碼查證）

- `--json` 只含 `thread.started`／`turn.*`／`item.*`（`command_execution`、`agent_message`、`error`）；hook 執行紀錄與 SessionStart 注入都不進 `--json` 也不進 `-o`，被 PreToolUse 擋下的呼叫連 `command_execution` 都不產生。
- 因此 AE3 以隔離統計檔的 `GUARD_DENY` 計數為主斷言，AE4 與 canary 以 rollout 檔（`~/.codex/sessions/…/rollout-*-<thread_id>.jsonl`）為斷言。
- `codex exec resume` 沒有 `-C`／`--sandbox` 旗標：第二回合以 shell `cd` 進軍師目錄、以 `-c sandbox_mode` 重帶 sandbox、以 thread id（非 `--last`）定位。
- `codex exec` 會把 cwd 寫成 `~/.codex/config.toml` 的 `[projects.*] trust_level`；固定試點路徑使寫入收斂為一次，腳本不代為清理。

## 手動核對清單（無法非互動承載）

| 項目 | 核對方式 | 預期 |
|------|----------|------|
| TUI `/clear` 觸發 SessionStart | 在已登記子專案開 Codex TUI、執行 `/clear`（或 Codex 對應的新對話指令） | 摘要「📬 kunsu 信箱」再次出現 |
| hook 信任流程 | 依 `skills/kunsu-inbox/SKILL.md` 三步驟掛載 `~/.codex/hooks.json` 後啟動 TUI | 「Hooks need review」→ 信任；`/hooks` 顯示 Trusted；`bash scripts/consistency-check.sh` N 項 PASS |
| 真實路徑 `.git/` 唯讀核准 | 在真實軍師 repo（非 `$TMPDIR`）以 Codex TUI 執行 `$handoff done` 並同意 | git 寫入觸發 sandbox 核准提示；拒絕後零新 commit；接受後完成 |
| 真實路徑統計檔 | 真實軍師 repo 執行 `$kunsu-inbox` 後查 `~/.claude/kunsu-scan-stats.json` | 未列 `~/.claude` 於 `writable_roots` 時 `total_runs` 不遞增（靜默缺漏，ADR 019 Decision 5 已接受） |
| 隱式選用 | 不加 `$handoff`，以口語「回覆軍師的交接」 | 是否命中 handoff skill（不作斷言，僅觀察） |
| `default_mode_request_user_input` | config 開啟旗標後在 TUI 執行 `$handoff add` | 確認 commit 改走原生阻塞式提問 |

## 已知邊界

- 試點只證明「軍師與子專案雙向能經 handoff 文件溝通」與 hook 生效；done 六道查核、斷言層級紀律等多步驟流程在 Codex 上的保真度未被量測（ADR 019 residual）。
- Codex 軍師 add-project 審核不入試點（核准寫 registry 走模型 shell 受 sandbox，待 Decision 5 處置定案）。
- 本機 `~/.codex/plugins/.../hooks.json` 若因頂層多鍵解析失敗，每次 `codex exec --json` 會先吐幾筆 `item.type == "error"`，屬環境噪訊，腳本不對 error item 斷言。
