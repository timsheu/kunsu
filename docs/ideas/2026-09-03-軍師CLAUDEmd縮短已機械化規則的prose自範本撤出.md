---
title: 軍師 CLAUDE.md 縮短：已機械化規則的 prose 自範本撤出
type: idea
status: inbox
created: 2026-09-03
tags: [idea, kunsu-init, template, claude-md]
---

# 軍師 CLAUDE.md 縮短：已機械化規則的 prose 自範本撤出

來源：Uncle Bob 2026-08-19 專訪的 Lost in the Middle 論點（開場提示詞砍到最短留在優先區，不能違反的規矩改用後期檢核工具把關），加上本 session 對文獻數字的查證。

## 背景 / 動機

**現況量測（2026-09-02）**

- ebook 軍師 CLAUDE.md：244 行、34 KB（18,201 字元、6,628 中文字），含義務詞的句子 68 句。
- kunsu-init 範本：153 行、20 KB。ebook 多出的 14 KB 是 Lumen 環境約束、ADR 2026-08-24、免確認白名單等本地附加。
- 每個 session 排在它前面的全域規範（`~/.claude/CLAUDE.md` 與 rules）約 14 KB、約 120 條列項。
- 中段三信箱協議合計 11 KB，占全檔三分之一。五條 Invariants 在頭部、白名單在尾部，位置正確；關聯專案表、環境約束、工作流程七步、三信箱協議夾在中間。

**文獻數字**

- Liu et al. 2023《Lost in the Middle》：檢索型任務，10／20／30 篇文件約 1.5K／2.9K／4.4K token。20 篇設定 GPT-3.5-Turbo 答案在第 1 篇 75.8%、第 10 篇 53.8%、第 20 篇 63.2%，完全不給文件 56.1%。中段低於不給資料；長上下文版模型與短版曲線幾乎重合。
- Jaroslawicz et al. 2025《How Many Instructions Can LLMs Follow at Once?》（IFScale）：指令遵循型，頂級模型 100 條仍 95–98%、250 條掉到 73–85%、500 條 49–69%。首因效應（早段指令較被守）在 150–200 條達峰，300 條以上位置差異消失、全體一起崩。
- Levy et al. 2024《Same Task, More Tokens》：推理任務 250 至 3,000 token 平均準確率 0.92 降至 0.68，約 1,000 token 起明顯下滑。
- Anthropic 官方 Claude Code 文件：無數字上限；「CLAUDE.md 太長 Claude 會忽略一半」；context 模擬把典型專案 CLAUDE.md 算 1,800 token；建議「若 Claude 不加指令也做對，就刪掉或改成 hook」。

**「前段」的定義**

文獻裡一律是相對序位（Liu 以文件序位、IFScale 把指令清單三等分），且相對於整個 context、不是相對於檔案自身。Claude Code 啟動載入順序為 system prompt、自動記憶、環境、MCP、skill 描述、全域 CLAUDE.md、專案 CLAUDE.md、使用者第一句；專案 CLAUDE.md 在啟動區塊尾端，對話長了整塊往頭漂。因此檔案內部的頭尾差異是二階效應，一階是「可違反的指令總數」與「整個 context 長度」。衡量尺度建議改用指令條數：總數（含全域規範與 harness 自身）以 100 條以下為目標。

**可撤出的具體項目**

- 已被腳本計算的程序敘述：上報歸檔四步驟含 pathspec 細節（archive-report.sh 已計算）、申請歸檔步驟、三份 frontmatter 範本（new-handoff.sh、new-application.sh、new-report.sh 產生）、命名規則。prose 版是「靠記憶執行」的 fallback，正是 8/29 與 8/31 兩起事故的通道；依 v0.16.0 指路牌原則只留名字與權威位置。
- 已失效的規則：範本第 83 行「`/handoff reply` 以工作目錄找 CLAUDE.md，必須先 cd」。new-handoff-reply.sh 自 v0.3.0 起從原交接檔位置推算落點、與工作目錄無關，三軍師都帶著一條過期陷阱占優先區。
- 位置錯的核心輸入：ebook 的 Lumen 環境約束（PHP 7.2 語法上限、正式 MySQL 5.6 無 JSON、Redis 3.2、schema drift）是軍師規劃唯一不可從別處取得的事實，卻沉在中段。一旦被淡化，plan 帶著不相容語法進交接，接手方在 staging 才發現，走一輪矛盾回報再翻案。該上提到 Invariants 之後，或獨立成檔並於頭部一行指路。
- 專案結構樹與文件導航表內容重疊，可合併。

**限制與依賴**

- consistency-check H 依六個比對字串（規劃前既有盤點、勿自標、corrected_by、副官、不豁免、宣告範圍）判斷 live 軍師遷移狀態，撤出段落時須保留錨句或同步修改檢查項。
- 全域規範「文件潤飾採非破壞性流程」：先出範本的 refactor proposal，ebook 本地附加另列差異清單，再以第八波遷移同步三軍師。
- Lost in the Middle 對這份檔案沒有實測；引用的是 kunsu 自身事故證據（文件層機制全失效過、腳本 14/14 從未失效），屬間接推論。

## 下一步

- [ ] 成形後以 `/ce-brainstorm` 推進至 docs/brainstorms/
- [ ] brainstorm 時先數範本與 ebook 的原子指令條數，作為縮減目標的基準線
