---
title: ADR Candidate 017 — 軍師 repo 的 PreToolUse git add 守門（首個行為強制機制）
date: 2026-08-29
type: adr
status: accepted
---

# ADR 017：軍師 repo 內以 PreToolUse hook 攔截 `git add -A`／`.`／整目錄 add

> 狀態：**Accepted**（2026-08-29 使用者審定，三項開放問題同日裁決——逃生門採
> 環境變數豁免、黑名單凍結三形狀（增列須 ADR 修訂）、deny 事件記入掃描統計檔；
> 同日以 `skills/kunsu-inbox/scripts/pretooluse_git_guard.py` 實作並掛載。
> 本 ADR 是 kunsu 首次跨過「提醒→阻止」線的裁決記錄。源自 ebook 軍師分析文件
> `2026-08-29-軍師機制失效分析-手動執行等效步驟使skill指引靜默失效.md`）。

## Context

2026-08-29 事故：ebook 軍師 session 手動歸檔時以 `git add -A docs/handoffs/` 夾帶
16 份未讀回覆進「歸檔交接」commit，「未 commit 即未處理」狀態訊號被靜默清除，
雙方（子專案端顯示已回覆、軍師端顯示無待處理）皆無錯誤訊號。被違反的規則
（`git add` 僅限具體路徑，SKILL.md 與軍師 CLAUDE.md 皆明文）早已存在。

該分析文件的核心觀察：現有三道防護（文件規則、腳本 stderr 指路行、hook 版號變動
提示）全屬**提醒**，兌現條件是執行者當下選擇配合——本 session 期間 stderr 指路行
至少出現 14 次、回讀 0 次，實測兌現率 0%。同批落地的兩道機制（歸檔腳本
`archive-handoff.sh`、`scan-replies.sh` 歷史夾帶偵測）分別處理「讓正確路徑比手動
划算」與「失效後可偵測」，但都不在違規當下**阻止**。

kunsu 既有設計前提「harness 不做高能力模型的枷鎖——信息補全優先於行為強制」
（2026-08-14 立約）。本 ADR 的問題：這條前提是否容許一個**窄範圍、機械可判、
規則早已字面明文**的執行層強制點。

## Decision（提案）

1. **掛載 PreToolUse hook**（機器層級 `~/.claude/settings.json`，比照 SessionStart
   hook 先例不進任何 repo）：攔截 Bash 工具的指令，當**同時滿足**——
   - 當前 repo 為 `~/.claude/kunsu-registry.json` 任一條目的 `kunsu` 值（軍師
     repo；raw registry＋git root 快速比對，比照 session_hook.py 身分判斷）；
   - 指令含 `git add -A`、`git add .`、或 `git add <目錄>`（目錄參數涵蓋
     `docs/handoffs`、`docs/applications`、`docs/reports` 任一信箱路徑）——
   則**拒絕執行**（deny），拒絕訊息內嵌正確做法（方向 F 的 context-bearing
   提示搭在 deny 上兌現）：

   > ✋ 軍師 repo 內 `git add` 僅限具體檔案路徑（不用 `-A`、不整目錄打包）——
   > 整目錄 add 會夾帶未讀信箱檔案、靜默清除「未 commit 即未處理」訊號。
   > 歸檔請改用 `archive-handoff.sh`（自動處理 rename 兩側與暫存範圍）；
   > 逐檔列名後重新執行即可。

2. **判準（為何此強制點不違反「不做枷鎖」前提）**：被攔的是**機械性 git 誤用**，
   規則本身早已字面明文、無模型判斷空間——攔截不限縮任何分析、規劃、內容決策
   能力，只把「已禁止的操作形狀」從提醒升為報錯。deny 可立即以合規形式重做，
   完全可逆、無資訊損失。
3. **fail-open**：hook 腳本任何失敗（registry 損毀、python3 缺失）一律放行，
   不阻斷正常工作。
4. **範圍刻意最小**：僅軍師 repo、僅 `git add` 的三種寬範圍形狀。不攔
   `git commit`、不攔子專案 repo、不試圖窮舉「下一個沒想到的變體」——變體的
   後果面由 `scan-replies.sh` 歷史夾帶偵測（advisory）兜底，兩層分工：本 hook
   擋已知手段，偵測層接所有手段的後果。

## 開放問題（2026-08-29 審定時裁決）

1. **黑名單增長治理**：✅ **凍結三形狀**——hook 規則不隨事故增長，變體後果面
   由 `scan-replies.sh` 歷史夾帶偵測兜底；日後要增列規則須經 ADR 修訂。
2. **逃生門形式**：✅ **環境變數豁免**——指令前綴 `KUNSU_ADD_GUARD_OFF=1`
   （或程序環境同名變數）單次放行；打字成本即摩擦，且指令史留痕可稽。
3. **誤擋成本實測**：✅ **deny 事件記入掃描統計檔**（`kunsu-scan-stats.json`，
   type `GUARD_DENY`＋`guard_denies` 計數）——誤擋率與命中率有數據可查，作為
   日後定版或撤除 hook 的依據，與歷史夾帶偵測同一觀測體系。

## Consequences

- **正面**：違反從靜默變成當場報錯——事故形狀（`-A` 夾帶）在發生點被擋下，
  且 deny 訊息在「正要犯錯的時刻」送達正確做法，是提醒類防護中唯一有結構性
  兌現保證的位置。
- **負面／限制**：kunsu 首個行為強制機制，「不做枷鎖」前提出現第一個例外，
  後續任何強制點都會引用本例——判準（機械可判、規則已明文、可逆、零能力
  限縮）必須嚴格把關防滑坡；黑名單擋不住未列舉的手段（設計上接受，偵測層
  兜底）；hook 多一處機器層級設定需隨 install 流程維護。

## Alternatives considered

- **僅警告不攔截**（PreToolUse 注入提示但放行）：與 stderr 指路行同構，本事故
  已實測該類提醒兌現率 0%。不採。
- **方向 B（skill 成為唯一路徑）**：異常情境失去退路、「是否在 skill 上下文」
  無可靠判定，且屬能力枷鎖。不採。
- **不做（依賴甲＋乙）**：歸檔腳本降低誘因、偵測層事後接住，但事故形狀本身
  仍可能重演一次才被偵測。是否值得為此開強制先例，正是本 candidate 交付
  使用者裁決的問題。
