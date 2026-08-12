---
title: ADR Candidate 014 — SessionStart hook 第二階段啟用
date: 2026-08-13
type: adr
status: proposed
---

# ADR 014：SessionStart hook 第二階段啟用

> 狀態：**Proposed**（依 [2026-08-12 知悉層自動化需求](../brainstorms/2026-08-12-awareness-automation-requirements.md) Phase A 動工，待使用者審定）。

## Context

[ADR 002](2026-07-06-adr-candidate-002-relay-automation-registry-inbox.md) Decision 3 已預留 SessionStart hook 為傳令自動化的「第二階段」——同一支檢查腳本改為 session 啟動時自動注入提示——並明訂決策時機為「`/inbox` 實際使用後再決定」。

啟用證據（2026-08-12 使用者回饋）：

- `/kunsu-inbox` 自 2026-07-06 上線實際使用逾一個月。
- 實際工作型態為一次派發同時涵蓋 3～4 個子專案，各子專案 session 長駐不關、以 `/clear` 清理 context；逐一切換視窗、手動輸入 `/kunsu-inbox`、等待掃描的輪詢成本全落在使用者身上。
- 官方文件查證（2026-08-12）：SessionStart hook 的 matcher source 值域為 `startup`／`resume`／`clear`／`compact`／`fork`，**`/clear` 確定觸發**，且 SessionStart 的 stdout 屬「注入 context」的例外清單——hook 與「長駐＋`/clear`」的使用習慣直接咬合，按 `/clear` 即攤開信箱。

## Decision

1. **啟用 SessionStart hook**：新增 `skills/kunsu-inbox/scripts/session_hook.py`，於 session 啟動事件（startup／resume／clear／compact／fork，不設 matcher 過濾）依當前 repo 在 `~/.claude/kunsu-registry.json` 的身分（ADR 002 Decision 2 的獨立雙判斷）輸出信箱摘要至開場 context；未登記 repo 靜默零輸出。
2. **分類邏輯零重寫**：子專案模式匯入軍師沙盤 `app/subrepo_status.py`（= kunsu-inbox SKILL.md 步驟 4a 的既有 Python 實作，ADR 011 三分類與 verify 標籤照用）；軍師模式匯入 `app/kunsu_scan.py`（= 三支 `scan-*.sh` 的既有包裝）。判斷規則維持單一來源，協議演進時 hook 自然跟隨。
3. **只告知不開工**：輸出僅含分類摘要（每分類上限 5 筆＋「另有 N 筆」）與 `/kunsu-inbox` 提示，不開啟交接檔內文、不起草回覆、不執行任何 git 寫入。ADR 002 Decision 5 人工閘門零改動。
4. **「不主動輪詢」界定**：hook 為使用者自行於 `~/.claude/settings.json` 掛載的**事件驅動**通道——session 啟動是使用者的動作，hook 隨之執行一次，無定時器、無背景監聽。與 kunsu-inbox 授權邊界第 2 條「不主動輪詢」不牴觸，該條同步補註明文化。
5. **fail-open**：任何錯誤（含 PyYAML 缺失、註冊表毀損）一律 exit 0；已確認身分後的錯誤輸出單行降級提示，身分確認前的錯誤靜默。hook 絕不阻斷 session 啟動。
6. **開發部署分離（Invariant 3）**：腳本於本 repo 開發，經 `install.sh` 隨 kunsu-inbox skill 部署；settings.json 的 hook 設定屬機器層級（與註冊表同類），指向部署路徑，不進任何 git repo。

## Consequences

- **正面**：傳令成本自「每視窗手動一輪指令」降為「`/clear` 順手觸發」；確定性腳本掃描較 LLM 執行 SKILL.md 步驟快且零 token；與軍師沙盤共用分類模組，維護面不擴大。
- **負面／限制**：已登記 repo 的 session 啟動增加一次掃描延遲（目標 2 秒內）；hook 依賴沙盤模組與 PyYAML（沙盤既有依賴，缺失時降級提示）；`compact` 事件也會注入摘要，任務中壓縮後多出數行信箱資訊屬已接受的輕微噪音。
- 本 ADR 不涉及 Phase B（派發即推播）——該案須另以 ADR Candidate 015 對 ADR 002 的推播否決翻案後才動工。

## Alternatives considered

- **維持純手動 `/kunsu-inbox`**：即現況，輪詢成本已被實際使用證實為主要痛點。不採。
- **hook 內重寫輕量分類邏輯（避開 PyYAML 依賴）**：產生第三份 4a 語意副本，違反本 repo 多副本漂移的既有教訓。否決。
- **launchd 通知哨兵（macOS 推播）**：單人拓撲中所有信箱事件皆使用者自己觸發，推播只會轉述已知之事，且通知時刻與遺忘時刻錯位。於需求文件審視階段廢棄。
