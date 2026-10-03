---
title: mod：以 fswatch 子程序做回覆抵達即時 toast
type: idea
status: inbox
created: 2026-10-03
tags: [idea, kunsu, mod, claude-code]
---

# mod：以 fswatch 子程序做回覆抵達即時 toast

## 背景 / 動機

回覆即推播依賴回覆方走 handoff skill 才觸發；2026-09-23 回覆方以 Write 直接落檔，推播沒發生、關鍵回覆在信箱躺 77 分鐘。訊號應綁檔案系統而非對方守規。

## 做法

mod 無原生 fs watch，但 `$.process.spawn` 可於 `session.start` 起一個 session 生命週期內的 `fswatch docs/handoffs/replies docs/reports docs/applications`，有新檔即 `$.ui.toast` 並更新狀態列。fswatch 是 OS 事件、非輪詢，但屬常駐子程序——須比照 ADR 010 開有限例外（唯讀、session 結束即終止、使用者可停用）。

## 待決

是否與 band（提示列）合併為同一 mod；fswatch 未安裝時的降級（退回 prompt.submit 掃描）。

## 下一步

- [ ] 成形後以 `/ce-brainstorm` 推進至 docs/brainstorms/
