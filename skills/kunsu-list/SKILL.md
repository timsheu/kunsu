---
name: kunsu-list
version: 0.2.0
description: |
  列出全域反向註冊表 ~/.claude/kunsu-registry.json 的全部登記：按軍師（規劃協調中心）
  分組呈現角色代碼與子專案路徑，含 stale entry 偵測（登記路徑已不存在標 ⚠）與
  當前 repo 位置標記。純唯讀查詢、不需 git 身分，任何目錄（含多 repo 的父層
  workspace 資料夾）皆可執行。
  Use when asked to「/kunsu-list」「kunsu list」「kunsu-list」「列出子專案」
  「列出已登記的子專案」「列出軍師清單」「查看軍師登記」「有哪些子專案」
  「哪些專案加入了軍師」「加入了哪些軍師」「list 子專案」「kunsu 登記清單」
  「軍師管了哪些專案」「list kunsu projects」.
allowed-tools:
  - Bash
---

# kunsu-list — 列出軍師登記清單

列出全域反向註冊表（`~/.claude/kunsu-registry.json`）的全部登記，按軍師分組呈現，
供快速回顧「哪些子專案已加入哪個軍師、各用什麼角色代碼」。

**全域唯讀查詢，不需 git 身分**——在任何目錄（含非 git repo，例如多 repo 的父層
workspace 資料夾）皆可執行；不寫入註冊表、不寫入任何 repo。

## Agent 對應表

本 skill 以能力名描述步驟；各 agent 的實際工具與慣例對應如下（七份 SKILL.md 共用同一張表，由 `scripts/consistency-check.sh` 比對逐字一致；新增 agent 只改此表，不改內文）。

| 能力 | Claude Code | Codex |
|------|-------------|-------|
| 阻塞式確認（流程中需使用者當下裁決的提問） | AskUserQuestion 工具 | 預設無阻塞式工具（`request_user_input` 僅 plan mode；開啟 `[features] default_mode_request_user_input` 後可用即用）：印出定型指令與訊息並結束回合，下一回合收到使用者明確同意文字才執行 |
| 跨 session 推播（向另一個長駐 session 發一次性通知） | ListAgents＋SendMessage 工具 | 無對應物：整步跳過，由 SessionStart hook 兜底 |
| skill 目錄（本 skill 部署後所在目錄，用於定位 scripts/ 與 assets/） | `$CLAUDE_SKILL_DIR`（harness 注入；未定義時以本 SKILL.md 所在目錄推算），部署於 `~/.claude/skills/<name>/` | 無注入變數：以本 SKILL.md 所在目錄推算，部署於 `~/.agents/skills/<name>/` |
| skill 呼叫形（使用者或指引點名某個 skill） | `/<name>` 斜線指令 | `$<name>` 顯式呼叫，或依 description 自動選用（斜線只保留給內建指令） |
| hook 設定檔（機器層級，不進 repo） | `~/.claude/settings.json` 的 `hooks` | `~/.codex/hooks.json`（或 config.toml `[hooks]`）；改動後須於 TUI 重新信任 |
| 子 agent（副官：派出新鮮 context 分擔查證與提取） | Agent 工具（subagent） | `spawn_agent`（custom agents 於 `~/.codex/agents/*.toml`） |

未列於本表的 agent 一律採 Codex 欄行為：文字回合確認、不逕行執行；跨 session 推播整步跳過。

## 執行步驟

一次 `Bash` 呼叫完成（skill 目錄的定位見 Agent 對應表：以本 SKILL.md 所在目錄推算；
`git rev-parse` 失敗時傳入空字串，腳本視為「不標記當前位置」，照樣列出全表）：

```bash
bash "<skill 目錄>/scripts/registry-list.sh" \
  "$(git rev-parse --show-toplevel 2>/dev/null || true)"
```

依退出碼處理：

- **exit 0** → 以正體中文、等寬代碼區塊**原樣呈現**腳本輸出（勿改排版），輸出含：
  - 按軍師分組的登記清單（角色代碼＋子專案路徑，HOME 前綴以 `~` 縮寫）
  - 當前 repo 命中登記時的「← 你在這」標記
  - 登記路徑已不存在時的 ⚠ stale entry 清單（子專案與軍師路徑皆檢查）
  - 末尾統計（N 個軍師、M 筆登記）

  呈現後可視情境以一句話補充（如有 ⚠ 時提醒可能是專案搬家，可於軍師端以
  `add-project` 更新登記；註冊表不存在或為空時導引執行 kunsu-init skill 或 kunsu-apply skill）。
- **exit 1**（JSON 損壞或 python3 缺失）→ 原樣回報 stderr 內容，提示手動修復
  `~/.claude/kunsu-registry.json` 後重試，終止。
- **腳本不存在** → 報錯「找不到 `registry-list.sh`，請重跑 kunsu toolkit 的
  `install.sh` 更新部署後再執行。」終止。

---

## 設計備註

- **為何獨立成 skill 而非 kunsu-init 子指令**：查詢頻率高，獨立 skill 才有
  skill 顯式呼叫入口（Claude Code `/kunsu-list`、Codex `$kunsu-list`；子指令只能口語觸發）；且 `kunsu-init` 的兩個入口
  都有身分或路徑前提，`list` 刻意無任何前提，是給「忘記登記過哪些」的使用者的
  全域回顧視角。
- **stale entry 偵測只報不修**：⚠ 僅提示，不自動清理註冊表——路徑消失可能是
  暫時卸載或搬家，清理決策留給使用者（於軍師端以 `add-project` 或手動修復）。
- **腳本自持於本 skill**：`scripts/registry-list.sh` 隨本 skill 部署，
  與 `kunsu-init` 的 `registry-merge.sh`（寫入）分工——一讀一寫，互不依賴。
