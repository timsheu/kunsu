---
title: kunsu 通用化——同一份原始碼雙部署至 Claude Code 與 Codex
date: 2026-09-06
topic: codex-agent-neutral-deployment
---

# kunsu 通用化——同一份原始碼雙部署至 Claude Code 與 Codex — 需求文件

## Summary

把 kunsu 工具組做成與 AI coding agent 無關的協作協議：同一份 skill 原始碼經 `install.sh` 同時部署至 Claude Code 與 Codex 的 skill 目錄，兩支 hook 同時掛進兩個 agent 的 hook 設定，SKILL.md 內的 Claude Code 專屬工具名改寫為「能力＋各 agent 對應」。以暫存目錄試點證明 Codex 在軍師端與子專案端都能經 handoff 文件與對方雙向溝通，且 Claude Code 側零行為改變。

---

## Problem Frame

kunsu 的資料層（交接、回覆、上報、申請、todo 皆為 YAML frontmatter＋markdown；註冊表為純 JSON；「未 commit 即未處理」訊號是 git）與腳本層（產檔、歸檔、掃描共十八支 shell／python 腳本）從一開始就沒有依賴任何特定 agent。但工具組的**部署與指引**只認 Claude Code：`install.sh` 唯一部署目標是 `~/.claude/skills/`，兩支 hook 的掛載說明只寫 `~/.claude/settings.json`，七份 SKILL.md 直接以 Claude Code 的工具名（AskUserQuestion、ListAgents、SendMessage、`$CLAUDE_SKILL_DIR`）描述流程步驟。

使用者曾以軍師早期版本試過讓 Codex 參與，但現行版本（handoff v0.21.0、含 hook、歸檔腳本與六道 done 查核）從未在 Codex 上跑過，也沒有一個可重複的方式確認它能跑。2026-08-31 的外部計畫《Kunsu 通用 Agent 架構重構》提出 Core／Adapter 程式化重構與 Agent Runtime interface，經 2026-09-01 評估屬過度設計：kunsu 本體是 markdown 協議＋檔案系統慣例＋膠水腳本（Invariant 1），落實 orchestrator 或 daemon 會推翻 ADR 002／010／015 的手動掌控設計。

本次需求以查證結果重新定錨。2026-09-06 查證 Codex CLI 0.142.5 得到四項事實：hooks 支援 `PreToolUse`（可以 JSON `permissionDecision: "deny"` 或 exit code 2 阻擋）與 `SessionStart`（stdout 注入 context），stdin 欄位（`tool_name: "Bash"`、`tool_input.command`、`source`、`cwd`）與 Claude Code 一致；skills 採同一套 `SKILL.md`（name／description frontmatter）格式，放 `~/.agents/skills/`（`~/.agents/skills` 於 0.142.5 原始碼標為 deprecated，規劃期查證後改正），可依 description 隱式選用或以 `$skill` 顯式呼叫；設定 `project_doc_fallback_filenames = ["CLAUDE.md"]` 後，AGENTS.md 缺席時 Codex 讀 CLAUDE.md；Codex 的阻塞式提問工具 `request_user_input` 存在但只在 plan mode 可用。副官盤點本 repo 十八支腳本，只有 `session_hook.py`、`pretooluse_git_guard.py`、`kc.fish` 三支是換 agent 就整支失效的硬耦合，其中兩支 hook 的契約 Codex 已相容；其餘十五支的 Claude 字面只剩 `~/.claude/*.json` 狀態檔路徑與 `CLAUDE.md || AGENTS.md` 專案根標記。

因此 idea 文件中「Codex 無 PreToolUse 等價攔截點、ADR 017／018 防線在 Codex 側退回提醒層」的前提不成立。真正沒有對應物的只剩跨 session 推播（ListAgents／SendMessage）與 `kc.fish` 的啟動命名，兩者本就有降級路徑或不在賭注內。

---

## Key Decisions

- **Adapter 是「部署目標＋字面對應」，不是程式層。** 原計畫的 Agent Runtime interface（start／attach／status／stop）與 registry live state store 需要常駐程式，違反 Invariant 1。本次以 `install.sh` 多一個部署目標與 SKILL.md 字面改寫達成同等效果：Claude Code 成為第一個 adapter，Codex 是第二個，第三個 agent 只需再加一個部署目標與一組對應字面。
- **單一副本，字面中性化，不另寫 Codex 薄殼。** 另寫一組 `~/.agents/skills/kunsu-*/SKILL.md` 薄殼會讓 done 六道查核、斷言層級紀律、矛盾回報指引出現第二副本，正是本 repo 已實證會漂移的形狀（v0.13.0 四份值域副本、v0.16.0 觸及率三件套皆為此教訓）。代價是七份 SKILL.md 各掃一輪字面。
- **Codex 第一階段同時扮演接手方與軍師。** 使用者定案兩端都要，因此兩支 hook（SessionStart 信箱摘要、PreToolUse git add 守門）都要在 Codex 側成立，Codex 軍師 session 也要能跑 add、done、inbox 與歸檔腳本。
- **確認 commit 在 Codex 側以對話文字確認作為 AskUserQuestion 的規範層替代。** ADR 009 的「使用者明確要求」精神不變：agent 印出定型指令與訊息並結束該回合，只在下一回合收到使用者明確同意的文字才執行。此形態屬規範層而非結構關卡（AskUserQuestion 的阻塞由工具層強制，文字同意由 agent 判讀），事後偵測（`scan-replies.sh` 歷史夾帶偵測與掃描統計檔）為其兜底。handoff SKILL 現行「非互動環境：AskUserQuestion 不可用一律視同取消」須改以 agent 身分而非「使用者是否在線」為判準（見 R6），否則 Codex 永遠不 commit。此為對 ADR 009 已接受條款的修訂，由 ADR candidate 019 承載（見 R11）。
- **最小成立版本＝軍師與子專案雙向都能經 handoff 文件溝通。** 協議規格文件、狀態檔搬離 `~/.claude/`、`kc.fish` 的 Codex 版都不在賭注內，一律不做。
- **Invariant 3 字面擴張以 ADR candidate 019 承載。** 「部署至 `~/.claude/skills/`」擴為「部署至各 agent 的 skill 目錄」屬憲章層改動，比照 ADR 010／017 慣例先出 candidate 再實作，不直接改 CLAUDE.md 了事。
- **派發即推播在 Codex 側整步跳過。** Codex 無 ListAgents／SendMessage 對應物，handoff add 步驟 6 與 reply 步驟 6 既有「工具不可用整步跳過」分支直接生效；Claude 軍師派發給 Codex 接手方時亦無推播目標，由 Codex 側 SessionStart hook 兜底。ADR 015 零改動。

---

## Actors

- A1. **使用者** — 同一台機器同時使用 Claude Code 與 Codex CLI，自行決定每個 session 用哪個 agent；負責機器層級設定（hook 掛載、`project_doc_fallback_filenames`）與確認 commit。
- A2. **Claude Code session** — 現行唯一支援的 agent，軍師端或子專案端皆可；本次改動後行為不變。
- A3. **Codex session** — 新加入的對等 agent，軍師端或子專案端皆可；經 `~/.agents/skills/` 與 `~/.codex/hooks.json` 取得與 Claude Code 相同的 skill 與 hook。
- A4. **kunsu 腳本層** — 十八支產檔、歸檔、掃描腳本與兩支 hook，被 A2 與 A3 以相同方式呼叫。

---

## Requirements

**部署**

- R1. `install.sh` 同時部署至 Claude Code 與 Codex 的 skill 目錄，兩處指向同一份原始碼；Codex 目錄不存在時略過並提示，不視為錯誤。
- R2. 兩支 hook（`session_hook.py`、`pretooluse_git_guard.py`）的掛載說明同時涵蓋 Claude Code 與 Codex 的 hook 設定檔，兩者皆為機器層級設定、不進任何 git repo。Codex 側說明含信任審查步驟：編輯 `~/.codex/hooks.json` 後首次啟動 TUI 於「Hooks need review」提示選擇信任，信任狀態記於 config.toml 的 `hooks.state`；hooks.json 任何改動（含腳本路徑）須重新信任；非互動 `codex exec` 無審查介面，須先於 TUI 信任或加 `--dangerously-bypass-hook-trust`。
- R3. kunsu-inbox SKILL 的掛載說明新增 Codex 讀取軍師 CLAUDE.md 所需的兩項設定：`project_doc_fallback_filenames = ["CLAUDE.md"]`，以及 `project_doc_max_bytes`（預設 32 KiB，須上調至高於現存最大軍師 CLAUDE.md 並留成長餘裕，ebook 軍師現為 34,581 bytes）；位置與 hook 掛載說明並列。

**指引字面中性化**

- R4. 七份 SKILL.md 中每一處 Claude Code 專屬工具名，改寫為「能力描述＋各 agent 對應」的形式；能力描述為主詞，agent 工具名為附註。
- R5. 阻塞式確認（現為 AskUserQuestion）的對應規則：Claude Code 用 AskUserQuestion；無阻塞式提問工具的 agent 以對話文字確認，agent 印出定型指令與訊息並結束該回合，下一回合收到使用者同意文字才執行。
- R6. handoff SKILL「非互動環境」條款改依可觀察條件拆分：Claude Code 下 AskUserQuestion 不可用即為 headless／pipeline，一律視同取消；Codex 下阻塞式工具恆不可用，一律印出定型指令與訊息後以文字詢問並結束該回合，僅在下一回合收到使用者明確同意文字才執行，未獲回覆即不執行（`codex exec` 下自然等價取消）。條款不以「使用者是否在線」為判準。
- R7. 跨 session 推播（ListAgents／SendMessage）保留既有「工具不可用整步跳過」分支，字面補明 Codex 屬此情況。
- R8. `$CLAUDE_SKILL_DIR` 的引用改為「skill 目錄」能力描述，沿用既有「未注入時以 SKILL.md 所在路徑推算」fallback。
- R9. 腳本 stderr 文案與 `session_hook.py` 注入文案中的 Claude Code 工具名與斜線呼叫形（現查得 `archive-report.sh` 一處、`session_hook.py` 六處）一併中性化；stdout 契約零改動。
- R10. kunsu-init 產出的軍師範本中，副官慣例、確認 commit 與斜線呼叫形的字面同樣中性化；三個 live 軍師的同步時機依 Outstanding Questions 該題於規劃期定案。
- R17. skill 呼叫形 `/handoff`、`/kunsu-inbox`、`/todo` 等斜線形式視為 Claude Code 專屬字面，改寫為「執行 <skill 名> skill（Claude Code：`/<name>`；Codex：`$<name>`）」，範圍涵蓋 SKILL.md 交叉引用、kunsu-init 範本、CONCEPTS 與 `session_hook.py` 注入文案；kunsu-inbox 掛載說明一次列出兩 agent 的呼叫形對應。

**憲章與文件**

- R11. 新增 ADR candidate 019，內容涵蓋四項：（一）將 Invariant 3「部署至 `~/.claude/skills/`」擴為「部署至各 agent 的 skill 目錄」；（二）「adapter 是部署目標＋字面對應而非程式層」的決策與原計畫程式化重構被否決的理由；（三）對 ADR 009 的修訂——阻塞式提問工具不可用的 agent 以對話文字同意作為「使用者明確要求」的第二種實現形態，明文此形態屬規範層而非結構關卡、事後偵測為兜底；（四）對 ADR 001 Consequences「無法服務不跑 Claude Code 的使用情境（接受）」一句的翻案，翻案基礎為使用者工作流已同時含 Codex，ADR 001 Decision 1（純 skill＋範本＋膠水腳本）零改動。
- R12. CLAUDE.md、CONCEPTS.md 與 kunsu-init 範本中提到「Claude Code session」處，凡語意為「任一 agent session」者改為中性用語；語意確為 Claude Code 專屬者保留。

**驗證**

- R13. 一組可重複執行的暫存目錄試點，證明 Codex 在子專案端能讀交接、以 reply 腳本寫回覆、投遞申請與上報，且軍師端的 `scan-replies.sh` 偵測到新回覆。
- R14. 同一組試點證明 Codex 在軍師端能執行 inbox 掃描、add 派發、done 收尾與歸檔腳本，並經對話文字確認後 commit；另含兩項斷言——軍師 session 啟動後能引述 CLAUDE.md 最末節內容（證明未被預算裁切），inbox 掃描後統計檔該軍師 `total_runs` 遞增（證明狀態檔寫入未被 sandbox 靜默擋下）。
- R15. 試點證明兩支 hook 在 Codex 側生效：SessionStart 注入信箱摘要（含 `/clear` 觸發）、PreToolUse 對軍師 repo 的 `git add -A` 回傳 deny。
- R16. Claude Code 側零行為改變：`scripts/consistency-check.sh` 全項通過、既有 pytest 全數通過、既有 dogfooding 斷言不回歸，並含一次互動實跑的工具呼叫證據（見 AE5）。
- R18. `scripts/consistency-check.sh` 新增檢查項：七份 SKILL.md、kunsu-init 範本與 `session_hook.py` 導引文案中，Claude Code 專屬工具名與斜線呼叫形只允許出現在 R4／R17 定義的對應格式內，裸出現即 FAIL。
- R19. R13–R15 的試點定義為可重跑腳本，每次 handoff 版號變動後重跑；AE2 的同意分支若無法以非互動方式承載，明列為版號變動時的手動核對項。

---

## Key Flows

- F1. 首次部署至 Codex
  - **Trigger:** 使用者執行 `install.sh`。
  - **Actors:** A1、A4
  - **Steps:** 腳本部署至 Claude Code skill 目錄；偵測 Codex skill 目錄存在則一併部署，否則提示略過；印出兩個 agent 各自的 hook 掛載與設定步驟供使用者手動完成。
  - **Outcome:** 同一份原始碼在兩個 agent 皆可被選用；hook 與設定由使用者依提示掛載。
  - **Covered by:** R1、R2、R3

- F2. Codex 子專案 session 回覆交接
  - **Trigger:** 使用者在已登記子專案開 Codex session；SessionStart hook 注入待接手交接摘要。
  - **Actors:** A3、A4
  - **Steps:** Codex 依 description 選用 handoff skill 的 reply 段；讀交接本體；以 reply 產檔腳本在軍師 repo 的回覆信箱落檔；推播步驟因工具不存在整步跳過；不 commit（維持「未 commit 即新回覆」訊號）。
  - **Outcome:** 軍師端 `scan-replies.sh` 或沙盤偵測到新回覆。
  - **Covered by:** R4、R7、R8、R13

- F3. Codex 軍師 session 收尾交接
  - **Trigger:** 使用者在軍師目錄開 Codex session；Codex 經 `project_doc_fallback_filenames` 讀入軍師 CLAUDE.md。
  - **Actors:** A1、A3、A4
  - **Steps:** Codex 執行 handoff done 段：六道查核、`archive-handoff.sh` 歸檔、印出帶兩形 pathspec 的待確認 commit 指令；以對話文字向使用者確認；使用者文字同意後執行 commit。
  - **Outcome:** 交接歸檔並 commit，與 Claude Code 側產物形狀一致。
  - **Covered by:** R3、R5、R6、R14

- F4. Codex 軍師 session 誤用寬範圍 git add
  - **Trigger:** Codex 在軍師 repo 執行 `git add -A`。
  - **Actors:** A3、A4
  - **Steps:** PreToolUse hook 收到 `tool_name: "Bash"` 與 `tool_input.command`；判定為凍結三形狀之一；回傳 `permissionDecision: "deny"` 並內嵌正確做法；deny 事件記入掃描統計檔。
  - **Outcome:** 指令被擋，行為與 Claude Code 側一致。
  - **Covered by:** R2、R15

---

## Acceptance Examples

- AE1. Codex 接手方回覆
  - **Covers R13、R7.**
  - **Given** 暫存目錄已建軍師與一個已登記子專案，軍師派發一份 `to:` 為該角色代碼的交接。
  - **When** 在子專案目錄以 Codex 開 session，要求回覆該交接。
  - **Then** 回覆檔落在軍師 repo `docs/handoffs/replies/`、未 commit；Codex 回報推播步驟跳過；軍師端 `scan-replies.sh` 列出該筆新回覆。

- AE2. Codex 軍師收尾並確認 commit
  - **Covers R14、R5、R6.**
  - **Given** AE1 的回覆已存在，Codex 在軍師目錄開 session。
  - **When** 使用者要求收尾該交接。
  - **Then** session 啟動時 SessionStart 摘要列出該筆新回覆；Codex 執行歸檔腳本後印出定型 commit 指令並以文字詢問；使用者回覆同意後 commit 完成；使用者未回覆或回覆否定時不 commit。

- AE3. Codex 側 git add 守門
  - **Covers R15.**
  - **Given** Codex 軍師 session，`~/.codex/hooks.json` 已掛 PreToolUse。
  - **When** Codex 執行 `git add -A`。
  - **Then** 指令被 deny，deny 訊息含逐檔列名與歸檔腳本指引；掃描統計檔多一筆 `GUARD_DENY`。

- AE4. Codex 側 SessionStart 摘要
  - **Covers R15.**
  - **Given** 子專案有一筆待接手交接，`~/.codex/hooks.json` 已掛 SessionStart。
  - **When** 在子專案目錄開 Codex session，或於 session 內執行 `/clear`。
  - **Then** context 內出現與 Claude Code 側相同格式的信箱摘要。

- AE5. Claude Code 側零回歸
  - **Covers R16.**
  - **Given** 全部字面中性化改動完成並重新 `install.sh`。
  - **When** 執行 `scripts/consistency-check.sh`、pytest 與既有 dogfooding。
  - **Then** 全數通過；Claude Code session 的 add、reply、done 產物形狀與改動前逐字一致；另以一次互動 Claude Code session 實跑 add（kunsu 語境）與 done，session 紀錄顯示確認 commit 步驟實際呼叫 AskUserQuestion、推播步驟實際呼叫 ListAgents，而非以訊息文字替代。

- AE6. Codex 目錄不存在
  - **Covers R1.**
  - **Given** 機器未安裝 Codex。
  - **When** 執行 `install.sh`。
  - **Then** Claude Code 部署照常完成，Codex 目標印一行略過提示，exit code 為 0。

- AE7. Codex 接手方投遞申請與上報
  - **Covers R13.**
  - **Given** AE1 的暫存目錄；子專案已登記，另備一個未登記的暫存子專案。
  - **When** 在已登記子專案目錄以 Codex 開 session 要求向軍師上報一則情報；在未登記子專案目錄以 Codex 開 session 要求投遞加入申請。
  - **Then** 上報檔落在軍師 `docs/reports/`、申請檔落在軍師 `docs/applications/`，皆未 commit；軍師端 `scan-reports.sh` 與 `scan-applications.sh` 各列出一筆新件。

- AE8. Codex 軍師派發交接
  - **Covers R14、R7.**
  - **Given** 暫存目錄軍師，Codex 在軍師目錄開 session。
  - **When** 使用者要求向某角色代碼派發一份交接。
  - **Then** 交接本體落在軍師 `docs/handoffs/` 頂層、frontmatter `to:` 為該角色代碼；推播步驟因工具不存在整步跳過並回報；經文字確認後 commit。

---

## Scope Boundaries

- **不做協議規格抽取。** 原計畫縮減版第 1 項（agent-neutral spec 文件）不在賭注內；SKILL.md 中性化後本身即為 agent 無關的權威副本。等第三個 agent 真的出現再評估。
- **不搬狀態檔。** `~/.claude/kunsu-registry.json`、`~/.claude/kunsu-scan-stats.json`、`~/.claude/kunsu-hook-state.json` 留在原處；任何 agent 用 bash 都讀得到，搬動要付六個消費端同步成本。
- **不做 `kc.fish` 的 Codex 版。** Codex 啟動時無 session 命名旗標，慣例名對 Codex 無用；推播本就在 Codex 側跳過。
- **不建 Codex 側推播。** 派發即推播與回覆即推播在 Codex 側整步跳過，由 SessionStart hook 與 `scan-replies.sh` 兜底；ADR 015 零改動。
- **不改資料層與腳本行為。** 交接、回覆、上報、申請、todo 的檔案格式、註冊表 schema、歸檔形狀、掃描豁免、stdout 契約一律零改動。
- **沙盤零改動。** `kunsu-dashboard` 已完全脫鉤。
- **不做 Codex 專屬薄殼。** 見 Key Decisions。

---

## Dependencies / Assumptions

- **Codex sandbox 的三類寫入與存取（試點第一道牆）。** （一）信箱檔寫入軍師 repo：Codex 子專案 session 的回覆、申請、上報都寫進軍師 repo 路徑，在 cwd 之外，預設 workspace-write 會擋下或要求逐次核准，失敗顯式。（二）腳本層對 `~/.claude/kunsu-scan-stats.json`（`scan-replies.sh` 統計與基線、守門 deny 事件）與 `~/.claude/kunsu-registry.json`（add-project）的寫入：腳本設計為 fail-open，被擋時靜默不記、基線不前進使同一警示每次重報；hook 程序**不受 sandbox**（2026-09-06 `codex exec` 實測：read-only 下 hook 仍可寫入家目錄；原始碼 hook runner 無 sandbox 包裝），因此兩支 hook 對狀態檔的寫入不在此牆內，此類只影響模型經 shell 工具執行的腳本。（三）`new-handoff.sh` 查重的 zoekt 網路存取，sandbox 預設無網路時永遠降級。本需求不預先設計繞法，由試點實測後決定機器層級設定（如 `[sandbox_workspace_write] writable_roots`／`network_access`）或顯式接受缺口，結果回填至 R2／R3 的掛載說明。
- **Codex 對 SKILL.md 陌生 frontmatter 的容忍度。** 七份 SKILL.md 帶 `allowed-tools` 等 Claude Code 欄位；Codex 依 Agent Skills 開放規格只要求 name／description，推定忽略其餘欄位，試點驗證。
- **Codex hooks 的 deny 語意與 fail-open 行為。** 文件記載 PreToolUse 可 deny；hook 自身錯誤時 Codex 是 fail-open 或 fail-closed 未查證（Claude Code 為 fail-closed，2026-08-29 實測）。試點驗證，結果寫入掛載說明的掛載順序警語。
- **`project_doc_fallback_filenames` 只在 AGENTS.md 缺席時生效。** 軍師 repo 現無 AGENTS.md，條件成立；若日後軍師 repo 加入 AGENTS.md，此 fallback 失效，需另行處理。
- **Codex project doc 有位元組預算。** `project_doc_max_bytes` 預設 32 KiB，超限只在 log 留 warn、靜默裁切尾段；ebook 軍師 CLAUDE.md 已達 34,581 bytes（ivm 23,212、px 24,900 在預算內），不上調則 F3 依賴的「版本控制」節在 Codex 側消失。預算是否與 `~/.codex/AGENTS.md` 共用未查證，若共用則裁切點更早。
- **hook 狀態檔跨 agent 共用。** `~/.claude/kunsu-hook-state.json` 的版號變動提示會被先啟動的 agent 消耗一次，另一個 agent 不再提示；屬已知可接受的小損失。
- **Codex 的 subagent 對應副官慣例。** 軍師範本副官慣例以 subagent 為載體；Codex 有自訂 agents（`~/.codex/agents/*.toml`），推定可承接查證副官與提取副官的契約，試點不涵蓋、留待實際使用觀察。

---

## Outstanding Questions

**Resolve Before Planning**

- 無。

**Deferred to Planning**

- 七份 SKILL.md 字面對應的具體措辭形狀：逐處「能力描述＋括號內各 agent 工具名」，或內文一律用能力名、各 SKILL 頂部一張「能力→各 agent 工具」對應表；後者才使「第三個 agent 只改對應表」成立，R18 檢查項的錨句依定案形狀設計。
- 試點的載體：擴充既有 dogfooding 腳本加 Codex 分支，或獨立一支只跑 Codex 場景的腳本；Codex 非互動執行（`codex exec`）能否承載 AE2 的對話文字確認場景（exec 模式無核准介面，只能證明「未獲同意即不 commit」半邊，同意分支需 TUI 實跑；Codex 側須先信任 hook 或加 `--dangerously-bypass-hook-trust`，否則 hook 不觸發會被誤判為不相容）。
- 掃描統計檔的 `GUARD_DENY` 事件是否加 `agent` 欄位以區分來源 agent：Codex 上線後 ADR 017／018 觀察期數據會混流無法歸因，commit 衍生事件（MISDECLARED／SMUGGLED）天生無法歸因；此項觸及腳本行為與 Scope Boundaries「不改腳本行為」，規劃期裁決。
- Codex 側 `install.sh` 部署方式：symlink 或 copy 是否與 Claude Code 側的 `--link` 旗標共用同一開關。
- 三個 live 軍師的範本同步是否與本批合併執行，或延至試點通過後。

---

## Sources / Research

- `docs/ideas/2026-09-01-Codex參與kunsu協作的縮減版方案.md` — 本需求的上游 idea，其「防線真空」前提經本次查證推翻。
- 外部計畫《Kunsu 通用 Agent 架構重構》（`~/Downloads`，2026-08-31）— 原程式化重構方案；其「Claude 是第一個 adapter」目標與「不要過度設計、保持 local-first 與 filesystem-friendly」原則被本需求採納，Agent Runtime interface 與 registry live state store 被否決。
- Codex hooks 文件（learn.chatgpt.com/docs/hooks）— 事件清單、stdin 欄位、deny 語法、SessionStart stdout 注入、`~/.codex/hooks.json` 與 `<repo>/.codex/hooks.json` 位置。
- Codex config 文件（learn.chatgpt.com/docs/config-file/config-reference）— `project_doc_fallback_filenames`、`project_root_markers`；無啟動時命名 session 的旗標。
- Codex skills 文件（developers.openai.com/codex/skills）— SKILL.md 格式、`~/.agents/skills/` 與 `.agents/skills` 位置、`$skill` 顯式呼叫與 description 隱式選用。
- openai/codex issues #10384、#11536、#11892 — `request_user_input` 僅 plan mode 可用的現況與擴展請求。
- 本機 `codex exec` 實測（2026-09-06）：PreToolUse payload 實收 `tool_name: "Bash"`、`tool_input.command`，與文件一致；hook 程序不受 sandbox（read-only 下 hook 仍寫入家目錄成功；先前一次「Failed」為全域 hooks.json 內指向已刪除第三方腳本的既有壞條目）；exec 需 `--dangerously-bypass-hook-trust` 才跑未信任 hook；全域與 repo 層兩個 hook 來源各觸發一次。
- 本機查證（2026-09-06）：Codex CLI 0.142.5；`~/.codex/hooks.json` 已存在 PreToolUse／PostToolUse 條目（第三方 plugin 掛載，格式與 Claude Code 一致）；`~/.agents/skills/` 已有第三方 skill 採同格式 SKILL.md；`~/.codex/agents/` 有自訂 agents。
- 副官盤點（2026-09-06）：十八支腳本的 Claude 耦合分類——硬耦合三支（`skills/kunsu-inbox/scripts/session_hook.py`、`skills/kunsu-inbox/scripts/pretooluse_git_guard.py`、`scripts/kc.fish`），其餘為狀態檔路徑與專案根標記；指令載體層耦合五種機制（AskUserQuestion 八載體、ListAgents／SendMessage 僅 handoff 九處、hook 掛載說明僅 kunsu-inbox、`$CLAUDE_SKILL_DIR` 四份 SKILL、frontmatter `allowed-tools` 七份）；`skills/kunsu-inbox/scripts/archive-report.sh` stderr 文案含 AskUserQuestion 一處；斜線呼叫形（範本 kunsu-claude.md 28 處、`session_hook.py` 6 處）為盤點未列的第六類，經 doc review 補入。
- 相關 ADR：001（純 skill 不建編譯型工具）、002（推播否決與手動掌控）、003（開發與部署分離）、009（協議 commit 逐次確認）、010（沙盤例外的判準）、015（派發即推播與降級）、017（git add 守門）。
