---
title: 回覆驗收方式欄位（verify）與沙盤「部分完成」子分類
type: feat
status: completed
date: 2026-07-12
origin: docs/adr/2026-07-12-adr-candidate-011-reply-verify-field.md
---

# 回覆驗收方式欄位（verify）與沙盤「部分完成」子分類

## Summary

回覆檔 frontmatter 新增選填 display-only 欄位 `verify:`（驗收方式），承載「此
交接還缺哪種驗證」——建議代碼 `needs-deploy`（需上線測試 🚀）／`testable-now`
（馬上可測 ⚡）／`needs-device`（需實機測試 📱），開放值域。並把「待接手」拆分
為「未接手（無回覆）」與「部分完成（partial／blocked，帶原因標籤）」，
「已回覆待確認」項目同樣帶標籤。決策紀錄見 origin ADR Candidate 011。

## Problem Frame

軍師沙盤目前只依最新回覆的 `status` 四值把交接文件分成「待接手」與「已回覆待
確認」兩類（`subrepo_status.py`，鏡像自 `kunsu-inbox/SKILL.md` 步驟 4a-3）。
實務上「做完了但還不能結案」的原因各不相同——需上線部署後才能測試、馬上可測、
得實機測試——但協議沒有欄位承載這個資訊，沙盤看不出 partial 的原因。

## 設計決策（使用者已拍板）

1. **資訊落點**：只掛回覆檔（接手方宣告），不掛交接文件本體、不掛專案層級。
2. **值域**：建議代碼＋開放值域；缺省不顯示標籤（向後相容，既有回覆檔零遷移）。
3. **呈現**：「待接手」拆成「未接手」與「部分完成」；未知 status 且有回覆歸
   「部分完成」（原樣顯示該 status）。

## 分類規則（取代現行 4a-3 表格）

| 情況 | 分類 |
|------|------|
| 無符合的回覆（零筆） | **未接手** |
| 最新回覆 `status: partial` 或 `blocked` | **部分完成**（blocked 另標 ⛔ 卡關） |
| 最新回覆 status 為未知值 | **部分完成**（原樣顯示該 status，保守不略過） |
| 最新回覆 `status: submitted` | **已回覆待確認** |
| 最新回覆 `status: done` | 略過，不列出 |

## 實作單元

- **U0 落地文件**：ADR Candidate 011（origin）＋本計畫文件。
- **U1 協議定義**（handoff v0.4.0 → v0.5.0）：`skills/handoff/SKILL.md` 回覆
  frontmatter 補 `verify:` 選填欄位＋值域說明、順修回覆 `status` 值域文件落差
  （本體 `open`／`in-progress`／`done` 與回覆 `submitted`／`partial`／`blocked`
  ／`done` 並列不可混淆）、reply 流程加驗收狀態評估步驟；
  `scripts/new-handoff-reply.sh` 新增選填第三參數 `[verify]`。
- **U2 掃描端規格**：`skills/kunsu-inbox/SKILL.md` 4a-3 讀 `verify`＋新分類表、
  4a-5 輸出格式拆段加「驗收」欄、依賴聲明表補 `verify` 列與 handoff v0.5.0。
- **U3 沙盤 Python 鏡像**：`subrepo_status.py` replies_index 加 verify、
  `HandoffInfo.latest_reply_verify`、`SubrepoStatusResult.pending` 拆
  `not_picked_up`／`partial_done`。
- **U4 沙盤渲染**：`main.py` `_html_subrepo` 三分類、`_html_handoff_detail`
  加 verify／blocked 標籤、CSS 標籤樣式。
- **U5 測試**：`test_subrepo_status.py` 隨拆分更新＋verify 案例（含非字串型別
  防呆）；渲染測試三分類與標籤。
- **U6 範本與母體文件**：`kunsu-claude.md` 範本、`CONCEPTS.md` 詞條、母體
  `CLAUDE.md`、`README.md` 檢查。
- **U7 收尾**（需使用者逐項確認）：ivm／ebook 軍師 CLAUDE.md live 遷移、
  `install.sh` 重新部署、commit。

## Scope Boundaries（明確不做）

- 不動 `status` 既有值域與任何精確比對邏輯（`scan-replies.sh`、done 歸檔豁免、
  tripwire 全部零改動）。
- 交接文件本體不掛 verify。
- 註冊表與 `registry-merge.sh` 零改動。
- Obsidian HOME dataview 的 verify 欄呈現不在本次範圍（ADR 011 open question）。
- 沙盤軍師模式的「新回覆」清單不加 verify 標籤（該清單來自 git 掃描檔名，
  不解析 frontmatter）。

## 驗證方式

1. `pytest skills/kunsu-dashboard/tests/`（既有 66 項＋新增案例全過）。
2. `new-handoff-reply.sh` 實跑：不帶 verify／帶 `needs-deploy`／帶自由字串
   三種呼叫，檢查 frontmatter 輸出。
3. 端到端：暫存目錄組 fixture 軍師 repo，覆蓋五情境（無回覆／partial＋
   needs-deploy／blocked＋自由字串／submitted＋needs-device／未知 status），
   啟動沙盤後 `curl` 驗證三分類段落與標籤 HTML。
