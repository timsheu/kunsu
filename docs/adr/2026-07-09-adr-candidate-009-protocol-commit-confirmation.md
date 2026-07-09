---
title: ADR Candidate 009 — 協議 commit 逐次確認制與 handoffs 授權歸檔豁免
date: 2026-07-09
type: adr
status: accepted
---

# ADR 009：協議 commit 逐次確認制與 handoffs 授權歸檔豁免

> 狀態：**Accepted**（2026-07-10 審定。2026-07-09 起草，源自「全域『不主動 commit』
> 規範與信箱協議『未 commit 即未處理』互相卡死」的流程問題討論；實作計畫見
> [2026-07-09-001-feat-protocol-commit-confirmation-plan.md](../plans/2026-07-09-001-feat-protocol-commit-confirmation-plan.md)，
> 經 4-persona `/ce-doc-review` headless 審查與 4 處修正。）

## Context

### Observations（現況盤點）

- 全域規範明訂「不主動 commit——只有在使用者明確要求時才執行」；kunsu 協議卻以
  commit 作為信箱狀態機的**轉移標記**：「未 commit 即未處理」是三信箱的狀態慣例，
  tripwire 以「授權範圍外的未 commit 變更」為異常判準。commit 在協議中不是版控
  便利，而是狀態轉移；兩者疊加使流程尾端的產出長期懸置。
- `/handoff done` 的 `git mv` 歸檔在 `scan-replies.sh` 現行規則（任何涉及
  `docs/handoffs/` 的 rename 一律 tripwire）下**必然誤觸**，`/kunsu-inbox` 軍師
  模式隨之硬停。`scan-applications.sh` 與 `scan-reports.sh` 均已內建「授權歸檔
  搬移豁免」（雙側核驗），`scan-replies.sh` 的全攔寫法是 replies 單層結構時代的
  保守設計，本 ADR 引入 handoffs 歸檔語境後該前提不再成立。
- 軍師自建交接檔未 commit 時，下次 `/kunsu-inbox` 觸發頂層 tripwire；訊息指引
  「確認並 commit 後再執行」，形成每輪一次的人工卡點。
- skill 套件內對 commit 已有三種並存的姿態：`kunsu-init` 步驟 ⑥ 的
  「AskUserQuestion 確認後執行」（唯一先例，FAQ 明載允許理由）；`add-project`
  步驟 ⑩ 的「提醒但不執行」；`/handoff` 三子指令的「不要主動 commit」硬性禁止。
  姿態不一致本身即是協議摩擦來源。
- 實測（暫存目錄 fixture）：`git mv` 對含未暫存修改的 tracked 檔案，porcelain
  呈現 `RM`（rename 已 stage、修改未 stage），**staged 內容仍是舊版**——任何在
  Edit 之後 `git mv` 的歸檔流程，commit 前必須 `git add` 歸檔目的地路徑，否則
  `status: done` 等修改不會進入 commit。

### Hypothesis（推斷，非事實）

- 推斷：隨三信箱用量增加，流程尾端 commit 懸置引發的 tripwire 誤報與人工卡點
  會更頻繁出現；及早把 commit 收斂為協議步驟可避免慣例各自漂移。

## Decision（proposed）

1. **確認 commit 升格為協議步驟**：kunsu 軍師側／發起側流程尾端的 commit 改為
   「AskUserQuestion 確認一次 → 執行」。逐次確認即構成「使用者明確要求」，與
   全域「不主動 commit」規則**相容而非牴觸**，全域規則零改動。此為 ADR 002
   Decision 5「人工閘門不動」的強化落地，不是新原則；先例為 `kunsu-init`
   步驟 ⑥，本 ADR 把允許理由自「新建 repo 初始 commit」擴為「協議流程尾端對
   自身產出的收斂 commit」。通用防護：執行前以 `git status --porcelain` 核對
   指定路徑確有待提交變更（無變更則回報、不產生空 commit）；只 `git add` 本
   流程產出的具體路徑（不用 `-A`、不整目錄打包）；**絕不 push**；使用者取消則
   保留全部產出、附可手動執行的 commit 指令提示。

2. **覆蓋矩陣與投遞端不對稱**：確認 commit 涵蓋——`/handoff add`、
   `/handoff done`、`/handoff reply`（本地語境）、`add-project` 審核歸檔、
   上報歸檔（依協議執行時）。**不涵蓋**——`/kunsu-apply` 與 `/kunsu-report`
   投遞、`/handoff reply`（kunsu 語境，跨 repo 寫入軍師 `replies/`）、
   `/kunsu-inbox`（唯讀）。理由：未 commit 是信箱的「新件」訊號，投遞方 commit
   會摧毀訊號、令軍師信箱漏報；此不對稱與例外授權信箱的不對稱（ADR 006／008）
   同構，是刻意設計。reply 的語境判定**以回覆檔實際落點是否位於當前 repo 根之下
   為準**，不以觸發語推斷。

3. **commit 訊息固定格式**：統一 `docs:` 類型、「動詞＋對象檔名」結構——
   add：`docs: 建立交接 <檔名>`；done：`docs: 歸檔交接 <檔名>`；reply（本地）：
   `docs: 回覆交接 <檔名>`；add-project：`docs: 審核申請 <子專案顯示名>（核准）`；
   上報歸檔：`docs: 歸檔上報 <檔名>`。用語可微調，結構固定。

4. **scan-replies.sh 授權歸檔豁免**：比照 `scan-applications.sh` 的雙側核驗模式
   重構（`strip_quotes`、src／dst 拆分），豁免三形狀——(a) 頂層交接檔 →
   `archive/` 的 rename；(b) `replies/` → `archive/replies/` 的 rename；
   (c) `archive/` 下所有路徑變更靜默略過（不做狀態欄篩選，與既有兩支腳本對
   archive/ 的取捨一致）。tripwire 保留項全數不變：反向搬移、其他 rename、頂層
   既有檔修改刪除、頂層 untracked 新交接檔。不驗 src／dst basename 同名（與
   既有兩支一致，`/handoff done` 的 `git mv` 天然同名）。archive 豁免分支必須
   置於 `docs/handoffs/*` catch-all 之前（bash glob `*` 跨 `/` 陷阱）。

5. **done 流程強化**：`git mv` 前對 untracked 的本體與回覆檔一律先 `git add`
   （untracked 檔直接 `git mv` 會 fatal）；步驟 3（Edit status）至步驟 5
   （git mv）連續執行、中間不執行 `/kunsu-inbox`（中間態 ` M` 無豁免，靠流程
   原子性）；確認 commit 置於步驟 6（跨文件連結修正）之後，`git add` 必含
   **歸檔目的地路徑**（`RM` 行為——`git mv` 不暫存 working tree 修改）與步驟 6
   修改的所有檔案。

6. **上報歸檔確認點掛範本協議文字**：上報歸檔無專屬 skill 子指令，軍師 session
   依 CLAUDE.md 協議執行歸檔（三步擴為四步：Edit `status` → `git add` →
   `git mv` → 確認 commit）時依協議文字觸發確認。純手動歸檔（不經 AI）無確認
   點——此落差明示接受，見 Open Questions。

## Consequences

- **正面**：`/handoff done` 歸檔不再誤觸 tripwire；流程尾端狀態即時收斂，
  「未 commit 即未處理」的訊號面更乾淨；全域規範零改動；三種並存的 commit
  姿態統一為一套協議語言。
- **取捨（明示接受）**：`docs/handoffs/archive/` 的直接寫入不再被攔——威脅模型
  與 `scan-applications.sh` 已接受的取捨等價（會寫 archive/ 的只有 done 流程，
  投遞腳本只往 `replies/` 寫），於腳本註解記錄。headless／pipeline 情境
  AskUserQuestion 不可用時退化為「不 commit＋提示」，與現狀相同、不劣化。
- **連動成本**：三 skill 升版（handoff `0.4.0`、kunsu-init `0.2.0`、kunsu-inbox
  `0.3.0`）、範本三處協議文字、母體文件與 CONCEPTS 詞條、ivm／ebook 兩 live
  軍師 CLAUDE.md 遷移；部署須單次 `install.sh` 原子上線（腳本豁免與 SKILL 確認
  commit 互為前提）。

## Open Questions

- 純手動上報歸檔（不經 AI session）無確認 commit 觸發點；待 ADR 008 open
  question「歸檔子指令化」評估時一併考慮，屆時可升級為 skill 內建確認。
- 「`git mv` 對已修改追蹤檔呈現 `RM`、staged 內容為舊版」擬補入
  `docs/solutions/best-practices/git-porcelain-scan-script-pitfalls.md` 作第四
  陷阱（傾向於實作收尾時落地）。
- basename 同名驗證強化：若未來出現「改名歸檔」誤用再議，現階段與既有兩支腳本
  保持一致。
