---
title: solutions 失效與衝突語意欄位
type: idea
status: closed
created: 2026-08-11
tags: [idea, memory, solutions]
---

# solutions 失效與衝突語意欄位

solutions 與 handoff archive 目前只進不出，沒有「這條教訓已被推翻／被取代」的表達方式。輕量做法：solutions frontmatter 加選填 superseded_by:／verified: 欄位（比照 ADR 011 verify 欄位的 display-only 開放值域模式，零遷移），規劃前既有盤點命中時可一眼判斷冷熱；經驗衝突時保留兩條並標注 disagreement，不覆寫。

## 背景 / 動機

Agent Memory 文章指出記憶是會變的——修改、衝突合併、失效都是機制的一部分；kunsu 現行盤點靠「以 handoff 回覆核對有效性」逐次人工判斷，缺失效語意。

## 查證結論（2026-08-12，判定不適用）

經 /ce-brainstorm 查證，CE plugin 已原生覆蓋本 idea 的目標，且設計哲學與新增標記欄位相反，判定不適用、不推進：

- `/ce-compound` 寫新教訓時，Related Docs Finder 對既有 solutions 做五維度重疊評估（問題、根因、解法、檔案、預防規則），新解法推翻舊文件時選擇性轉派 `/ce-compound-refresh`。
- `/ce-compound-refresh` 具備完整失效生命週期：Keep／Update／Consolidate／Replace／Delete 五種處置；模糊案例標 `status: stale`＋`stale_reason`＋`stale_date`（即本 idea 想要的失效標記，已存在）；更新過的文件加 `last_updated:`。
- 設計哲學相反：plugin 明訂「Delete, don't archive」——取代關係以合併後刪除處理，git history 即封存；衝突視為強烈 Replace 訊號、解決而非保留。`superseded_by:` 掛牌與「保留兩條標 disagreement」正是其刻意拒絕的模式，自創欄位需自行承擔慢性漂移。
- 殘餘缺口僅操作面（軍師 repo 從未跑過 refresh）；handoff done 沉澱提示（見 [2026-08-11-handoffdone收尾加教訓沉澱提示.md](2026-08-11-handoffdone收尾加教訓沉澱提示.md)）落地後 compound 頻率上升，`/ce-compound` 原生轉派會把 refresh 帶出來，不需另建機制。
