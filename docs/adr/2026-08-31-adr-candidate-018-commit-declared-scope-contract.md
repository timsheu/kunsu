---
title: ADR Candidate 018 — 確認 commit 收斂宣告範圍、不收斂 index（pathspec 契約）
date: 2026-08-31
type: adr
status: accepted
---

# ADR 018：協議「確認 commit」自「提交 index」改為「提交宣告範圍」

> 狀態：**Accepted**（2026-08-31 使用者審定，六條 Decision、威脅模型顯式接受
> 清單（含活習慣複合訊息約 9.6% 誤報）與守門擴張啟動條件（上線後經人工核對
> 排除誤報的再犯事件才啟動）一併定案；機制已於同日隨 handoff v0.19.0／
> kunsu-inbox v0.11.1／kunsu-init v0.7.0 落地部署）。源自 ebook 軍師調查報告
> `2026-08-31-commit邊界失誤調查報告.md`——同一 session 內兩次「commit 內容
> 超出訊息宣告範圍」，第一次修正後的記憶型對策未能防住隔日第二次。

## Context

2026-08-31 事故：ebook 軍師 session 兩次把上報歸檔的 index 殘留夾帶進「建立交接」
commit（`b198530`、`96ac928`，皆已本地改寫修正）。技術成因：`git commit -m` 不帶
pathspec 時提交整個 index，而歸檔流程的 `git mv` 已預先在 index 留下內容。

三個條件疊加才出事：

1. **commit 編排無定型**——pathspec 有無、多 commit 排序、`;` 或 `&&` 串接，各
   session 自由發揮；
2. **index 殘留是協議常態**——ADR 009「先暫存、隔著 AskUserQuestion 確認、後
   commit」使暫存內容跨 Bash 呼叫存在是設計而非異常；
3. **權威文本教的正是脆弱寫法**——handoff SKILL 確認 commit 協議、範本上報歸檔
   第（4）步、`archive-handoff.sh` 印出的待確認指令，三處全是不帶 pathspec 的
   `git commit -m`，隱含假設 index 是空的。

系統層級後果：若被夾帶的是未讀回覆而非已處理上報，「未 commit 即未處理」訊號被
靜默清除——與 2026-08-29 `git add -A` 事故（ADR 017 的動機）同一條後果路徑，
入口自 add 換成 commit。現有防護對此形狀全盲：git add 守門只攔 add 三形狀，
掃描統計檔 ebook 條目 7 次掃描 0 事件。

兩起事故都發生在上報歸檔——v0.18.0 歸檔腳本化（`archive-handoff.sh`）未覆蓋的
唯一歸檔流程；該流程因此沒有「把 git 編排從記憶變計算」的載體可用。

## Decision（提案）

1. **確認 commit 的契約改為「提交宣告範圍」**：協議定型指令一律
   `git add -- <具體路徑> && git commit -m "<訊息>" -- <同一組路徑>`——add 與
   commit 的路徑集合一致，commit 與 index 殘留徹底脫鉤；`-m` 必在 `--` 之前
   （`--` 之後的一切都被解析為 pathspec）。殘留自地雷降級為無害狀態，「暫存等
   確認」的 ADR 009 設計零改動。
2. **pathspec 兩形，依來源狀態分**：存在於 HEAD 的檔案，歸檔 rename 成對列出
   來源與目的地（只列單邊會把 rename 拆半）；不存在於 HEAD 的來源（上報／申請
   的常態——porcelain `??`，或已 add 未 commit 的 `A `）僅列目的地——該來源
   路徑不在 git 歷史，成對必以 pathspec 不匹配失敗。判準為 `git mv` 前的 HEAD
   存在性檢查（`git cat-file -e HEAD:<路徑>`），非 porcelain 字面。
3. **編排規範入協議**：index 已有前一流程暫存內容時，先收斂該 commit 再開始新
   流程的 add；多指令串接一律 `&&`（任一步失敗即中斷可見——事故中空 index
   commit 的 exit 1 與失效 add 的 exit 128 均被 `;`／換行串接吃掉）。
4. **上報歸檔腳本化**（`archive-report.sh`，對稱 `archive-handoff.sh`）：status
   Edit→untracked 前置 add→`git mv`→add 目的地，stdout 印依兩形分支的待確認
   commit 指令；不自動 commit，ADR 009 確認制零改動。
5. **夾帶形狀 advisory 偵測**：`scan-replies.sh` 逐 commit 檢視新增
   `HISTORY_WARN:MISDECLARED_ARCHIVE_ADD`——subject 不以白名單前綴開頭的 commit
   以 diff-filter A 新增任一信箱 `archive/` 檔案即警示並入統計檔。白名單前綴
   集合窮舉現行正當形狀：`docs: 歸檔`（done 歸檔／上報歸檔）、`docs: 審核申請`
   （申請審核歸檔）；採 startswith 比對，不採「任意位置含詞」（標題含「歸檔」的
   建立交接 commit——正是事故吞噬者形狀——會被含詞判準豁免）。**新增正當歸檔
   訊息形狀時須同步擴白名單，屬本 ADR 修訂事項**。另記 `TRUNCATED` 事件
   （rev-list 滿 200 筆時聲明該輪數據不完整）。
6. **語意句**：pathspec commit 提交**確認當下的工作樹內容**，非暫存快照——
   add 與確認之間若同路徑再被編輯，後續修改一併入 commit。與 ADR 009 暫存語意
   的偏移顯式接受（歸檔檔案於流程內不再編輯，實害趨零）。

## 威脅模型（顯式接受的邊界）

偵測層（Decision 5）的已知盲點與噪音，均不視為缺陷：

- **「docs: 歸檔」訊息直寫 archive**：未讀檔案被手動 `mv` 直入 `archive/` 再以
  歸檔訊息 commit——無頂層新增、訊息又豁免，新舊形狀皆盲；git 層面無從區分
  「讀過才歸檔」。訊息紀律與歸檔腳本化是唯一防線（與「豁免 archive/ 等於信任
  軍師自身合法寫入」的既有取捨一致）。
- **evil merge**：變更僅存在於 merge commit 本身時 diff-tree 不可見（既有兩
  形狀同病）；軍師 repo 單人線性、無 merge 流程。merge 進行中 partial commit
  被 git 禁止亦同屬此類邊界。
- **revert 誤報**：revert「刪除 archive 檔」的 commit 會以 `Revert "…"` 訊息
  新增 archive 檔而觸發警示——advisory 性質下屬可欲提示（非常規操作值得人工
  核對）。
- **手工訊息不合定型**（全形冒號、缺空格、英文訊息）：正當歸檔會誤觸警示；
  腳本印出定型指令後發生率低。
- **活習慣複合訊息誤報**：兩 live 軍師全歷史回放實測 17/177（約 9.6%）正當
  歸檔 commit 因複合訊息（「docs: 彙整…並歸檔…」「docs: 結案歸檔…」
  「feat: 審核核准…」）不合白名單前綴而誤報。白名單維持凍結兩前綴不隨活習慣
  擴列（擴列即重開偽裝豁免面）；誤報屬 advisory 可接受，事件 detail 帶完整
  訊息供人工辨識，且走歸檔腳本產生的定型訊息不誤報——機制本身在收斂此噪音源。
- **跨信箱前綴錯配**：白名單為全域集合，不逐信箱配對——「docs: 審核申請」訊息
  夾帶其他信箱 archive 新增不會被抓；換取判準簡單。
- **統計檔並發**：hook 與沙盤同時掃描時 read-modify-write last-writer-wins，
  事件可能遺失或下輪重報；advisory 性質無實害升級。
- **警示呈現面**：一次性 stdout 警示多半被 hook／沙盤消耗（`kunsu_scan.py` 對
  未知前綴靜默、基線照樣前進）——**警示以統計檔為準**，CLI 呈現不可靠；hook／
  沙盤顯示維持後續評估。
- **python3 長期缺失後首掃不回溯**、**BASELINE_RESET 僅物件被 prune 才觸發**
  （reflog 期內 rebase 重寫段可能重報）：既有基線行為，新形狀繼承。

## 開放問題

1. **ADR 017 擴 `git commit` 守門**（自「提醒」跨「阻止」的第二個強制點）：
   本 ADR 落地後以統計檔觀察——啟動條件為出現**上線後、經人工核對排除誤報**
   的 `MISDECLARED_ARCHIVE_ADD` 再犯事件（活習慣複合訊息實測約一成誤報且與
   真再犯型別相同，事件 detail 帶完整訊息供辨識，不得以未核對的原始計數觸發）；
   計數不含上線前事件（各軍師基線已在 HEAD，歷史不回溯入統計），已知一次再犯
   （2026-08-31）不計入。零再犯則不跨線。若啟動，須依 ADR 017 判準四要件（機械可判、規則已明文、可逆、零能力
   限縮）另出 ADR 修訂。

## Consequences

- **正面**：吞檔在機制上不可能發生（pathspec 與 index 脫鉤，已於暫存目錄實測
  ——index 有殘留時 pathspec commit 只提交指名檔案）；上報歸檔取得計算載體，
  git 編排自「被記憶」變「被計算」的覆蓋自此完整；夾帶形狀首次可觀測，守門
  裁決有數據基礎。
- **負面／限制**：定型指令副本橫跨 handoff SKILL、kunsu-init SKILL、範本兩檔、
  兩支腳本 stdout 與三 live 軍師，修訂成本高（consistency-check 機械比對收口）；
  兩形規則比單一寫法多一個判斷分支（由腳本計算、協議文字載明判準）；偵測白名單
  隨協議訊息演化需維護（列為本 ADR 修訂事項）。

## Alternatives considered

- **解析中文訊息比對宣告範圍**（調查報告方向 B 全版）：「訊息宣告範圍」無機械
  判準，不採；窄版即 Decision 5 的前綴白名單。
- **歸檔腳本不留 index**（方向 C）：牴觸 ADR 009 暫存等確認設計，並連動掃描
  豁免的 porcelain 形狀（`RM`／`A`）與既有腳本生態，回歸風險大於收益。不採。
- **僅補文件指引不改定型指令**（方向 D）：熟練 session 手動執行時 skill 指引
  靜默失效（v0.16.0 觸及率教訓、2026-08-29 分析實證 0/23），且事故 session
  已示範記憶型對策跨流程邊界即蒸發。不採為主體，僅作為定型文字的一部分。
