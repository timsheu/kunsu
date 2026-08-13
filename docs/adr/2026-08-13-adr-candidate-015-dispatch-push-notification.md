---
title: ADR Candidate 015 — 派發即推播：對 ADR 002 推播否決的翻案
date: 2026-08-13
type: adr
status: proposed
---

# ADR 015：派發即推播（軍師 session 派發完成當下通知目標子專案長駐 session）

> 狀態：**Proposed**（依 [2026-08-12 知悉層自動化需求](../brainstorms/2026-08-12-awareness-automation-requirements.md) Phase B 動工，待使用者審定；全面啟用前須先完成單一子專案試點——R13）。

## Context

[ADR 002](2026-07-06-adr-candidate-002-relay-automation-registry-inbox.md) Alternatives 曾否決「fswatch／daemon 輪詢推播」，理由有二：違反「不主動輪詢」設計；「session 非常駐，推播無處落地」。

本翻案建立在兩層變更之上，不動搖被否決案的原始判斷：

1. **事實前提變更**：使用者實況（2026-08-12 確認）為各子專案 session 長駐數小時不關、以 `/clear` 清理 context；本機 session 網格實測確認互動 session 彼此可見、可定址傳訊（當日清單含 ivm、eBookApp、iOS 三個子專案長駐 session）。「推播無處落地」的前提已不成立——**長駐 session 本身就是落地點**。
2. **機制變更**：本案不是 daemon 輪詢。推播由軍師 session 在**派發完成的當下**主動送出一次性訊息——派發者最知道派發時刻，事件驅動、零輪詢、零常駐程序、零狀態檔。「不主動輪詢」原則零觸碰；Invariant 1 字面即合規，無需比照 [ADR 010](2026-07-11-adr-candidate-010-dashboard-service-exception.md) 開例外。

## Decision

1. **掛載點**：handoff skill add 流程新增收尾步驟（確認 commit 之後），僅 kunsu 語境（當前 repo 為註冊表任一條目的 `kunsu` 值）適用；一般 repo 的交接不受影響。
2. **目標定位**：以註冊表反查 `to:` 角色代碼對應的子專案路徑，再以 ListAgents 列出本機 session、以名稱啟發式匹配（正規化後 session 名稱與子專案目錄 basename 對應）。**唯一且明確才發送**；找不到、多重命中、或 ListAgents／SendMessage 工具不可用時一律降級跳過——不重試、不排隊，由 SessionStart hook（ADR 014）於該視窗下次 `/clear` 兜底。
3. **通知訊息自足（Invariant 2 零觸碰）**：定型文案含軍師名、角色代碼、份數、檔名清單（上限 5 筆），並**自帶收方指令**——請只向使用者回顯重點、勿開始任何工作、勿讀取交接檔內文、勿回覆本訊息或軍師。收方行為規則以訊息本身承載，不在任何子 repo 寫入設定或規則。
4. **只告知不開工**：本步驟只發送訊息，不等待、不確認收方回應；接手與否、何時開工，仍由使用者在目標 session 明確指示（ADR 002 Decision 5 人工閘門零改動）。
5. **試點閘門**：全面啟用前，先以單一子專案完成試點，驗證需求文件的三項推斷——收方 session 依訊息內指令僅回顯（推斷一）、busy session 收訊排隊時機（推斷二）、軍師 session 具備傳訊工具（推斷三）；試點結論補記於需求文件。
6. **回覆方向對稱納入**（2026-08-13 同日修訂：原訂「試點成功後另行補上」，試點當日即由使用者確認派發方向實測可用——軍師 session 實發至 ios-app session 觸發成功——遂依需求文件 Open Questions 3 定案納入同批）：子專案投遞回覆（含暫離回報）落入軍師信箱後，反向通知軍師 session（handoff reply 步驟 6）；目標匹配採同一套兩層規則，軍師 session 慣例名 `<軍師目錄名>-kunsu`，降級由軍師端 SessionStart hook 與 `scan-replies.sh` 兜底；「未 commit 即新回覆訊號」的掃描機制零改動。

## Consequences

- **正面**：使用者晃回子專案視窗時通知已在眼前，「逐視窗切換＋手動查信箱」的知悉成本歸零；與 hook 互為備援（推播管 session 開著的主場景、hook 管兜底），兩層皆為告知性質。
- **負面／限制**：收方 session 處理通知會消耗一輪少量 token；收方「僅回顯」是對模型遵循度的推斷，以試點驗證並以訊息內指令與 hook 兜底雙重防護；名稱啟發式在同前綴多 session 時保守降級，覆蓋率非 100%（設計取捨——寧漏發不誤發）；通知不持久，收方視窗被 `/clear` 後訊息消失，持久面由 hook 與軍師沙盤承擔。
- 本 ADR 使 ADR 002 Alternatives 的推播否決**限縮於 daemon 輪詢形態**；其對 MCP、注入子 repo CLAUDE.md 的否決維持不變。

## Alternatives considered

- **launchd 通知哨兵（macOS 系統通知）**：單人拓撲中所有信箱事件皆使用者自己觸發，推播只轉述已知之事，且通知發射時刻與遺忘時刻錯位。於需求審視階段廢棄（見需求文件改版註記）。
- **tmux send-keys 注入既有視窗**：要求使用者遷移至 tmux 工作流，成本不成比例。不採。
- **僅靠 SessionStart hook（不推播）**：hook 只在 `/clear`／啟動時發射，無法覆蓋「視窗開著沒動、使用者路過瞄一眼」的場景；兩者互補而非互代。
