---
title: "feat: 機制觸及率三件套——指路牌、腳本指路行與 hook 版號提示"
type: feat
status: completed
date: 2026-08-15
origin: docs/brainstorms/2026-08-15-mechanism-reach-signpost-requirements.md
---

# feat: 機制觸及率三件套——指路牌、腳本指路行與 hook 版號提示

## Summary

修復「skill 內部指引在手動執行等效步驟時靜默失效」：範本層指路牌（kunsu-concepts「done 收尾」詞條＋工作流程兩句指路，第 7 步含不豁免）、兩支產檔腳本 stderr 指路行（handoff v0.16.0）、session_hook.py 版號變動提示（kunsu-inbox v0.8.0，機器層級狀態檔）；三 live 軍師第四波遷移（kunsu-init v0.6.0）。

## Problem Frame

見 origin：`docs/brainstorms/2026-08-15-mechanism-reach-signpost-requirements.md`。版號基線承 002／003 計畫完成後的 handoff 0.15.0／kunsu-inbox 0.7.0／kunsu-init 0.5.0。

---

## Requirements

承 origin R1–R9，計畫層面不增減。摘記：R1–R3 範本指路牌（詞條點名六查核＋第 5／7 步指路句，第 7 步含不豁免）；R4–R6 腳本指路行（add／reply 兩腳本、產物零改動、不含定型句首）；R7–R8 hook 版號提示（變動一行、狀態檔機器層級、fail-open、兩模式）；R9 三軍師遷移與版號同步。

---

## Key Technical Decisions

- **指路行走 stderr、stdout 維持僅檔案路徑**（使用者裁決，修訂 origin「stdout 指路」字面）：repo 現查無任何 `$()` 消費端（scope-guardian 實查零命中），本決策的理由是**前瞻契約保護**——stdout 維持單行檔案路徑的機器可讀契約（Unix 慣例：資料走 stdout、診斷走 stderr），未來自動化消費端不被指路行破壞；對現有消費端（session 工具結果、終端）兩路等效可見，觸及效果相同。產出檔內容零改動（R6 由結構保證：指路行在 `} > "$file"` 之後輸出）。
- **hook 版號比對僅在身分確認後執行**：保 ADR 002「未登記 repo 快退零輸出」不變；首次執行（無狀態檔）靜默記錄當前版號、不提示——避免每台機器首個 session 收到無意義提示；此後版號變動才輸出一行，提示行置於信箱摘要之前。
- **狀態檔 `~/.claude/kunsu-hook-state.json`**：JSON dict（`{"handoff_version": "..."}`），可擴充其他 skill；讀寫任何失敗 fail-open（不阻斷 hook 既有輸出，一律 exit 0 慣例不變）；並行 session 競寫無害（告知層，重複提示可接受）。首發僅追蹤 handoff（最高頻），其他 skill 留待評估（origin OQ 就地定案）。
- **版號動態讀取，不建副本**：hook 與指路行如需展示版號，執行時自部署樹相對定位讀 SKILL.md frontmatter（hook 位於 `~/.claude/skills/kunsu-inbox/scripts/`，相對路徑 `../../handoff/SKILL.md`）；指路行首發不附版號（價值低，origin OQ 就地定案為不附）。
- **H 檢查追加「不豁免」比對字串**：第四波遷移完整性入機械檢查，沿 corrected_by／副官先例。
- **版號序列**：handoff 0.15.0→0.16.0（腳本輸出行為面）、kunsu-inbox 0.7.0→0.8.0（hook 功能）、kunsu-init 0.5.0→0.6.0（範本內容）；kunsu-inbox 依賴聲明同步 0.16.0＋續列一句（指路行不涉掃描慣例與定型文字比對）。

---

## Implementation Units

### U1. 兩支產檔腳本 stderr 指路行（handoff v0.16.0）

- **Goal**：手動呼叫腳本的執行者在產檔當下收到指引位置提示。
- **Requirements**：R4–R6。
- **Files**：`skills/handoff/scripts/new-handoff.sh`、`skills/handoff/scripts/new-handoff-reply.sh`、`skills/handoff/SKILL.md`（version 0.15.0 → 0.16.0）。
- **Approach**：兩腳本於 `echo "$file"` 之後各加一行輸出至 stderr——new-handoff.sh 指向 SKILL.md add 段（「本腳本僅產檔；撰寫與查核指引（斷言層級紀律、引用檔名權威、更正交接）見 handoff SKILL.md add 段——未經 /handoff skill 執行時請回讀對應步驟」）、new-handoff-reply.sh 指向 reply 段（逐項回答附證據、矛盾回報、暫離回報）。措辭不含 consistency-check C 的兩句定型句首字串。
- **Patterns to follow**：腳本既有 printf 慣例；訊息措辭比照 SKILL.md 對應段的機制名。
- **Test scenarios**：
  - Covers AE1：mktemp 實跑 new-handoff.sh——stdout 恰一行且為檔案路徑（`$()` 捕獲驗證）、stderr 含指路行。
  - Covers AE4：實跑後產出檔與改動前逐字一致（diff 零差異）；`scripts/consistency-check.sh` C 檢查 PASS。
  - reply 腳本同型兩檢核。
- **Verification**：兩腳本 stdout 契約不變、stderr 指路行就位、version 0.16.0。

### U2. session_hook.py 版號變動提示（kunsu-inbox v0.8.0）

- **Goal**：toolkit 更新後，長駐 session 於下次啟動／`/clear` 得知指引有變。
- **Requirements**：R7–R8。
- **Dependencies**：U1（版號值 0.16.0 為首個可被偵測的變動）。
- **Files**：`skills/kunsu-inbox/scripts/session_hook.py`、`skills/kunsu-inbox/tests/test_session_hook.py`、`skills/kunsu-inbox/SKILL.md`（version 0.7.0 → 0.8.0；SessionStart hook 節補此行為說明）。
- **Approach**：身分確認後、輸出信箱摘要前，讀部署樹 `../../handoff/SKILL.md` frontmatter version 與狀態檔 `~/.claude/kunsu-hook-state.json` 比對——無狀態檔：寫入當前版號、零輸出；版號不同：輸出一行「📌 handoff skill 已更新至 vX（自 vY），流程指引有變——本輪 add／done 建議經 /handoff 執行或回讀 SKILL.md 對應段」並更新狀態檔；相同：零輸出。全程 try/except fail-open，任何失敗跳過比對、hook 既有輸出照常、exit 0。狀態檔路徑定為模組常數（比照 `REGISTRY_PATH`），測試以 autouse fixture monkeypatch 至 tmp_path——否則既有 12 項測試會直寫真實 `~/.claude` 狀態檔並吃掉使用者的一次性更新提示。
- **Patterns to follow**：session_hook.py 既有 fail-open 與身分判斷結構（ADR 014）；測試比照 tests/ 既有 12 項的 fixture 形狀。
- **Test scenarios**：
  - Covers AE2：狀態檔記 0.15.0、部署 SKILL 為 0.16.0 → 輸出含提示行且狀態檔更新；再跑一次 → 零提示。
  - 首次（無狀態檔）→ 零提示、狀態檔建立。
  - 邊界：SKILL.md 不存在／version 行缺失 → 零提示不拋錯；狀態檔為損壞 JSON → 視同首次重建；未登記 repo → 快退零輸出（版號比對不執行）。
  - 整合：軍師模式下提示行出現在「📬 kunsu 信箱」摘要之前，摘要內容不受影響（顯式斷言順序，勿僅子字串比對）。
  - 隔離：既有 12 項測試在 fixture 隔離後不讀寫真實 `~/.claude/kunsu-hook-state.json`。
- **Verification**：新增測試全過、既有 12 項零回歸（pytest 全套）。

### U3. 範本指路牌（kunsu-init v0.6.0）

- **Goal**：手動收尾／手動產檔的軍師 session 知道查核存在與權威位置。
- **Requirements**：R1–R3。
- **Files**：`skills/kunsu-init/assets/templates/kunsu-concepts.md`（新增「done 收尾」詞條）、`skills/kunsu-init/assets/templates/kunsu-claude.md`（工作流程第 5／7 步各補一句）、`skills/kunsu-init/SKILL.md`（version 0.5.0 → 0.6.0）。
- **Approach**：詞條比照母體 CONCEPTS「done 收尾」形狀改寫（點名逐項驗收、沉澱訊號、反向路由、來源 todo 查核、殘項清點、斷言自查六查核，「細節以 handoff SKILL.md done 段為準」＋「手動等效執行不豁免」）；第 5 步句「含手動呼叫產檔腳本時，撰寫指引以 SKILL.md add 段為準」；第 7 步句「收尾無論經 skill 或手動等效執行，查核清單以 SKILL.md done 段為準、不豁免」。
- **Test scenarios**：
  - Covers AE3：詞條文字點名全部六查核名（grep 逐名核對）。
  - 範本值域句與 dataview SORT 行零 diff（B／F 檢查前提）。
- **Verification**：consistency-check B／F／G PASS。

### U4. 三 live 軍師遷移（第四波）

- **Goal**：ebook／ivm／px 指路牌就位。
- **Requirements**：R9。
- **Dependencies**：U3。
- **Files**：`kunsu-project-root/{ebook,ivm,px}` 各 CLAUDE.md（第 5／7 步兩句）與 CONCEPTS.md（「done 收尾」詞條）。
- **Approach**：與 U3 同構、逐錨點斷言腳本執行（錨點未命中即停不寫入——ebook 客製段先例）；詞彙變體保留；各一筆確認 commit。
- **Test scenarios**：三軍師 CLAUDE.md 與 CONCEPTS.md **各自** `grep -c "不豁免"` ≥1（兩檔分別命中，防單側漏遷）；變體字串仍在。
- **Verification**：三筆確認 commit；H 檢查（含 U5 新字串）全 PASS。

### U5. 版號鏈、機械檢查與驗證

- **Goal**：全鏈收斂與部署。
- **Requirements**：R9。
- **Dependencies**：U1–U4。
- **Files**：`skills/kunsu-inbox/SKILL.md`（依賴聲明 0.16.0＋續列一句）、`CLAUDE.md`（版號行、開發狀態新條目）、`CONCEPTS.md`（「done 收尾」詞條補點名「斷言自查」——與範本六查核點名對齊，消除母體五／範本六的無註記分歧）、`scripts/consistency-check.sh`（H 追加兩處：CLAUDE.md「不豁免」＋ `${kroot}/CONCEPTS.md` 一條 grep——否則 CONCEPTS 詞條漏遷不可見）。
- **Test scenarios**：
  - consistency-check 全項 PASS（A1 handoff 0.16.0 三源；C 兩句定型比對；H 五字串對三軍師）。
  - pytest 全套過；`install.sh` 部署後三 skill 版號就位、手動實跑部署版 new-handoff.sh 驗證 stderr 指路行生效。
- **Verification**：檢查全 PASS、部署完成。

---

## Scope Boundaries

承 origin：不提高手動摩擦、查核細節不搬 CLAUDE.md、產物層強制查核記錄留待 R10 實績、審計自指另議、注意力衰減殘餘接受。計畫層追加：hook 首發僅追蹤 handoff 版號；指路行不附版號展示；未登記於 registry 的 repo 收不到版號提示（快退零輸出，ADR 002）——顯式接受的觸及缺口，非缺陷。

---

## Sources & Research

- origin 與起源 idea；ebook 審計第四、五份（觀察三量化、觀察四 reply 結構性差異、觀察五）。
- 本 session 實查：兩腳本 stdout 契約（`} > "$file"` 後單行 `echo "$file"`——stderr 決策的依據）、session_hook.py 結構（main() 輸出點、fail-open 慣例、tests 既有 12 項）、母體 CONCEPTS「done 收尾」詞條為指路牌正確形狀、範本 kunsu-concepts 現無該詞條。
- 教訓：攔截點必經路徑（一般化為動態必經）、單一副本同步、逐錨點斷言遷移（第三波 ebook 客製段攔截先例）。
