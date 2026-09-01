---
date: 2026-08-31
topic: dedup-and-todo-archive-scripts
---

# 會飄移的紀律改用腳本：產檔查重與 todo 歸檔腳本化需求

## Summary

把三個實證會飄移的敘述性紀律改成腳本計算：`new-handoff.sh` 產檔時自動查重（同收件角色時間窗交接清單保底＋tshehtu 關鍵詞跨 repo 疊加，advisory 列候選不擋產檔）；新增 `archive-todo.sh` 收斂 todo 歸檔的 git 編排；`archive-handoff.sh` 附掛來源 todo 雙向比對與引用連結偵測兩支 grep，把 done 查核的機械部分從「模型記得 grep」變「腳本印出候選」。

---

## Problem Frame

ebook 軍師 2026-08-31 兩份調查報告記錄了同一種失效：規則已寫成文件，執行者沒有想起它。沉澱失效報告的時序最尖銳——「發問前先搜自己 repo」的教訓在 T4 沉澱入 `docs/solutions/`，T5、T6 隨即發出兩份重複交接（重複對象是四天前已回覆的交接），中間沒有 context 中斷；「規劃前既有盤點」規範同 session 被繞過四次，繞過時零訊號。重複交接的代價：接手方白做工（backend 已完成其中一份）、三份更正交接返工、信箱信噪比劣化。

同報告 1.3 記錄另一形狀：上午在交接中引用 ADR 018 的 pathspec 兩形規則，下午手動執行 todo 歸檔 commit（`fc143a8`）時把 tracked rename 拆半——todo 歸檔是 v0.18.0 歸檔腳本化後唯一還沒有計算載體的歸檔流程。

兩報告共同的對照證據劃出載體光譜：文件層機制（solutions、CONCEPTS、CLAUDE.md 規範、SKILL 指引）全部失效過；具體指令部分有效（done 流程的 grep 攔截一次成功）；腳本從未失效（skill 呼叫 0/23 的 session 裡產檔腳本被呼叫 14/14）。有效性與「是否依賴記得」呈反比。

---

## Key Decisions

- **查重採時間窗清單保底＋關鍵詞層疊加，不採純關鍵詞比對**。中文標題無斷詞，自動抽取品質不穩；沉澱報告 T7 顯示「讀到既有交接標題」本身就足以辨識重複，時間窗清單零智能零漏報（窗內）。關鍵詞層交給 tshehtu 承擔跨 repo 深度——本地清單構不到的「backend 那邊已查過」只有這層攔得住。
- **關鍵詞為選填參數＋標題自動抽取保底，不採必填**。必填會破壞既有呼叫相容並增加使用摩擦，摩擦誘發手動繞道，正好反噬「腳本是唯一從未失效載體」的地位。
- **查重 advisory 不擋產檔**。kunsu harness 不做枷鎖——信息補全優先於行為強制；腳本的職責是把候選推到決策時點眼前，撤回與否由 session 與使用者判斷。
- **降級顯式聲明，不靜默**。tshehtu 不可用時若靜默略過，會重演「防護在場但全盲且無訊號」（掃描統計檔 7 掃 0 事件的教訓）。
- **附掛查核走既有腳本輸出，不新增獨立腳本**。done 收尾的必經路徑是 `archive-handoff.sh`；新增獨立腳本又要靠「記得去跑」。
- **判斷型查核不入腳本**。殘項清點的三去向裁決、收尾與否、連結修不修，留在模型與使用者層——這條界線是沉澱報告第三節自己劃的能力邊界，腳本只交付候選清單。

---

## Requirements

**甲、產檔查重（`skills/handoff/scripts/new-handoff.sh`）**

- R1. 產檔時自動執行查重，結果印 stderr；stdout 維持單行檔案路徑的機器可讀契約零改動。查重為 advisory——照常產檔，不因查重結果中止或阻斷。
- R2. 保底層（時間窗清單）：列出本 repo `docs/handoffs/`（含 `archive/`、`replies/`、`archive/replies/`）中 `to:` 同收件角色、日期落在時間窗內的交接，逐筆一行含日期、標題、狀態（open／已回覆／已歸檔）；超過筆數上限時顯示「另有 N 筆」。
- R3. 關鍵詞層（tshehtu）：以關鍵詞查詢 zoekt JSON API（`127.0.0.1:6070`），查詢範圍為全庫（含各 repo 的 handoffs、plans、solutions），逐筆印出 repo 相對路徑。關鍵詞來源：選填參數優先，未提供時自標題自動抽取（去除通用詞後的片段）。
- R4. 降級顯式：zoekt 健康檢查（短 timeout）失敗時印一行降級聲明（查重僅含本地層），不靜默；查重內部任何錯誤 fail-open，不阻斷產檔。
- R5. 候選清單尾端附固定提示句：若上列已涵蓋本次主題，請考慮撤回本檔。
- R6. 通用場景相容：查重不依賴 kunsu registry，於未登記 repo（handoff 作為通用原語的場景）照常運作，僅本地層生效即可。

**乙、todo 歸檔腳本（`skills/todo/scripts/archive-todo.sh`）**

- R7. 新增 `archive-todo.sh` 收斂 todo 歸檔執行：status Edit（done 語境改「已解決」、rm 語境改「已封存」）→ 選填解決依據回填（handoff done 語境帶入交接預期歸檔路徑）→ untracked 前置 `git add` → `git mv` 至 `docs/todos/archive/` → `git add` 歸檔目的地。
- R8. stdout 印出依 ADR 018 兩形 pathspec 的待確認 commit 指令，不自動 commit（ADR 009 確認制零改動）；已解決／已封存孤兒僅補歸檔、不改終態。
- R9. 已在 `archive/` 的目標冪等略過，供失敗重跑（比照 `archive-handoff.sh`）；殘項清點與跨檔連結修正不入腳本。
- R10. handoff SKILL done 步驟 4 與 todo SKILL done／rm 的歸檔執行字面改為呼叫本腳本；腳本 stderr 印查核指路（殘項清點等留在模型層的步驟提醒）。

**丙、done 查核附掛（`skills/handoff/scripts/archive-handoff.sh`）**

- R11. 來源 todo 雙向比對：收尾時掃描 `docs/todos/` 頂層，todo 內文含交接檔名、或交接本體含 todo 檔名者列為候選印出；done 步驟 3 字面改以腳本輸出為候選來源，收尾裁決仍走既有 AskUserQuestion 流程。
- R12. 引用連結偵測：grep 被歸檔交接檔名於 repo 內的命中清單印出；修正判斷、白名單（todo／plan）與「交接本體含 archive 內不修正僅回報」規則零改動。

**丁、協議與版本連動**

- R13. handoff SKILL、todo SKILL 版號升版，kunsu-inbox 依賴聲明同步；範本與三 live 軍師零改動（查重與歸檔腳本部署即自動生效，免遷移波）。
- R14. 掃描慣例、`status`／`verify` 值域、tripwire 與歸檔豁免形狀零改動；`archive-todo.sh` 產生的 porcelain 形狀不得觸發 `scan-replies.sh` 誤報。

---

## Acceptance Examples

- AE1. **T5 重演隔離**。**Given** 軍師 repo 存在 8/27 發給 backend 的 deviceName 交接（已回覆、已歸檔），**When** session 再以 deviceName 相關標題執行 `new-handoff.sh` 發給 backend，**Then** stderr 時間窗清單列出該筆（含狀態標示），檔案照常建立，session 可據候選撤回。**Covers R1, R2, R5.**
- AE2. **tshehtu 停機降級**。**Given** zoekt 服務未回應，**When** 產檔查重執行，**Then** 本地時間窗清單照列、另印一行降級聲明，產檔與 stdout 路徑輸出不受影響。**Covers R4.**
- AE3. **fc143a8 重演隔離**。**Given** 一筆 tracked 的 todo 待歸檔，**When** 以 `archive-todo.sh` 執行收尾，**Then** rename 由腳本成對執行、印出的待確認 commit 指令帶成對 pathspec，index 無拆半殘留。**Covers R7, R8.**
- AE4. **通用 repo 相容**。**Given** 未登記於 kunsu registry 的一般專案，**When** 執行 `new-handoff.sh`，**Then** 查重以本地層執行不報錯，行為與現行版本相容。**Covers R6.**

---

## Scope Boundaries

- 上報查重（`new-report.sh`）——另批評估。
- 申請歸檔腳本化——維持既有界線（量成長或實證事故再做）。
- `git commit` 守門 hook——維持 ADR 018 觀察期，統計檔真再犯才啟動修訂討論。
- 教訓動作綁定（`triggers_on`）基礎設施——另行發想；tshehtu 關鍵詞層全庫查詢兼任輕量版。
- tshehtu discovery 排程化——本輪不處理，新 repo 入索引維持手動。
- 判斷型查核（要不要做送使用者、斷言層級、沉澱訊號、反向路由、矛盾回報）腳本化——能力邊界外，明確不做。

---

## Dependencies / Assumptions

- tshehtu zoekt-webserver 為 launchd 常駐服務、reindex 每小時排程（2026-08-31 實查：`StartInterval 3600`，最近成功同日）；索引僅含已 commit 內容，未 commit 回覆與一小時內新 commit 由本地層補盲。
- discovery 未入排程：新增 repo 需手動跑 discovery 才入索引——列為已知前提，不在本輪修。
- 兩份調查報告的事實敘述已於 kunsu session 獨立核對屬實（reflog、commit 統計、守門範圍）。

---

## Outstanding Questions

**Deferred to Planning**

- 時間窗天數與筆數上限的預設值（候選：14 天、8 筆＋「另有 N 筆」）。
- 通用詞表內容（查證／更正／裁示／盤點等）與存放位置、治理方式。
- 標題自動抽取的具體演算法（標點切分、片段長度下限）。
- `archive-todo.sh` 參數介面（slug 定位、done／rm 終態旗標、解決依據選填參數的形）。
- consistency-check 是否擴充對應檢查項（定型提示句、指路行比對）。

---

## Sources

- `../../../kunsu-project-root/ebook/docs/2026-08-31-沉澱機制失效調查報告-需要比沉澱更好的方式.md`（失效時序 T1–T8、載體光譜、給 fable 的六問）
- `../../../kunsu-project-root/ebook/docs/2026-08-31-commit邊界失誤調查報告.md`（fc143a8 形狀、5.3 附加事實綁動作觀察）
- docs/brainstorms/2026-07-24-kunsu-pre-planning-inventory-requirements.md（規劃前既有盤點——本案把同一目的自敘述紀律改為產檔時計算，盤點規範本身不動）
- docs/adr/2026-08-31-adr-candidate-018-commit-declared-scope-contract.md（pathspec 兩形、計算載體路線）
- `~/.claude/skills/kb/SKILL.md`（zoekt API 呼叫形、健康檢查與降級程序、搜教訓 playbook）
