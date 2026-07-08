---
title: "refactor: 角色識別正規化——角色代碼與角色說明分離"
type: refactor
status: completed
date: 2026-07-08
origin: docs/adr/2026-07-08-adr-candidate-007-role-code-description-separation.md
---

# refactor: 角色識別正規化——角色代碼與角色說明分離

## Summary

將 kunsu 體系的「角色」單一概念拆為兩個獨立欄位：**角色代碼**（短、kebab-case、穩定，作為 registry `roles`、handoff `to:`／`in_reply_to` 對應角色、CLAUDE.md 關聯專案表代碼欄的唯一比對鍵）與**角色說明**（整句職責，display-only，只落 CLAUDE.md 說明欄，不進 registry、不比對）。改動範圍：CONCEPTS.md 詞彙、範本、四支 SKILL、兩支腳本，並一次性遷移現存 ivm／ebook 兩軍師的 live 資料。實作依 [ADR 007](../adr/2026-07-08-adr-candidate-007-role-code-description-separation.md)（經兩輪 `/ce-doc-review` 審定）。

---

## Problem Frame

現行「角色字串」單一欄位同時擔任「人看的職責描述」與「handoff `to:` 的機器比對鍵」兩個相互衝突的職責。工具在 add-project／kunsu-apply 問「角色描述」誘導使用者填整句，但 `/handoff` 的 `to:` 慣例是短碼，導致 `/kunsu-inbox` 的 `to ∈ roles` 精確比對對整句登記的軍師 false-negative（ivm 實例）。ebook 側因當初剛好填短碼而運作正常，屬巧合非工具保證——同一套工具產出兩種不相容資料。修法是把身分（代碼）與描述（說明）正規化為兩欄，並遷移已污染的 live 資料（see origin ADR 007）。

---

## Requirements

**概念與詞彙**

- R1. CONCEPTS.md 將「角色字串」詞條拆為「角色代碼」與「角色說明」兩詞；「角色代碼」詞條註明「角色識別」為回覆信箱 frontmatter 佔位符（`from`／`to`）的別稱，收束 Observations 指出的第三段命名。

**範本（`kunsu-claude.md`）**

- R2. 關聯專案表由單欄「角色」改雙欄「角色代碼｜角色說明」；`{{PROJECT_ROWS}}` 產列格式改為 `| 顯示名稱 | 絕對路徑 | 角色代碼 | 角色說明 |`，`PLACEHOLDERS.md` 同步更新。
- R3. 申請信箱協議 frontmatter 範例：`proposed_role` 語意改為「提議角色代碼」，新增 `role_desc`（角色說明，選填）。
- R4. 回覆信箱協議 frontmatter 佔位符「角色識別」文字**不變**（語意由 CONCEPTS.md 釐清）。

**`kunsu-init` SKILL**

- R5. 步驟 ①-B 子專案清單訪談改收「角色代碼（kebab-case，即 handoff `to:`）」與「角色說明（選填）」（一行式欄位由 5 欄改 6 欄：`顯示名稱 | 絕對路徑 | 角色代碼 | 角色說明 | 環境限制 | 自我驗證`）。
- R6. 步驟 ④-1 產 `{{PROJECT_ROWS}}` 雙欄；步驟 ⑦ registry-merge 傳入 `roles` 為代碼；步驟 ⑧ 驗收與完成提示的「三處一致」改指角色代碼。
- R7. 多子專案登記時代碼唯一性：以 session 累積集逐筆比對，撞名阻擋並要求改碼（Decision 7）。

**`kunsu-apply` SKILL ＋ `new-application.sh`**

- R8. 步驟 5 訪談改收「提議角色代碼」與「角色說明（選填）」，取代單一「角色描述」。
- R9. `new-application.sh` 新增 `role_desc` 參數；frontmatter 寫 `proposed_role`（代碼）＋`role_desc`（說明）；申請本文表格對應新增列。
- R10. kunsu-apply 代碼唯一性為**早期最佳努力訊號**：讀 registry 已核准代碼比對，撞名提示列既有代碼；明示其看不到在途待審申請、非權威（Decision 7）。

**`add-project` 子指令**

- R11. 審核（④-3）呈現與追問改為「角色代碼」＋「角色說明」；定案代碼、寫 CLAUDE.md 雙欄（⑥），`role_desc` 寫說明欄。
- R12. 步驟 ⑦ registry-merge 傳角色代碼；訪談 fallback（⑤）與完成提示（⑩）的「三處一致」改指代碼。
- R13. **唯一性權威強制點**：④-3 核准後、⑦ registry-merge 前，取本軍師 registry 已登記代碼聯集（排除當前子 repo）＋**本批次已核准代碼的 session 級暫存集**，同批每筆重新比對（不用 ④-1 批次快照），撞名阻擋、訊息列既有代碼。
- R14. 角色改名警告（⑨）掃 `to:` == 舊角色代碼（語意不變，比對對象為代碼）。

**`kunsu-inbox` SKILL**

- R15. 步驟 4a-4「to: 不符清單」文案改為「不在此軍師已登記的任何角色代碼集合」；比對邏輯（4a-3 精確比對）與 `scan-*.sh` 不變。

**`handoff` SKILL**

- R16. 指令格式或注意節補一句：kunsu 情境下 `to:` = 軍師登記的角色代碼；`/handoff` 作為通用原語不強制此約定。

**`registry-merge.sh`**

- R17. 軟警告：`roles` 條目含空白字元或超過長度閾值（30 字元）時向 stderr 輸出 WARN（不阻斷寫入、exit 0）；提示訊息補「代碼宜為 kebab-case」。作用域限格式層，不與 add-project 唯一性硬擋衝突。

**live 資料遷移**

- R18. registry 遷移以 **python3 原子寫入**（`json.load` → 替換 `roles` → `tempfile` ＋ `os.replace`）＋先 `cp` 備份，將 ivm 三筆（`backend`／`shun-tien`／`ivm-website`）與 `ebook-store-nginx`（`store-nginx`）的 `roles` 整組替換為代碼；**不呼叫 `registry-merge.sh`**（union-merge 會留舊整句）。
- R19. ivm 與 ebook **兩軍師** CLAUDE.md 關聯專案表改雙欄：ivm 四筆整句降說明欄、補代碼欄；ebook 四筆代碼欄取 registry 現值、現有「角色」欄描述降說明欄。
- R20. 遷移後核查雙軌：(a) ivm／ebook 子專案 session 各跑 `/kunsu-inbox` 子 repo 模式確認 false-negative 消除、無「to: 不符」孤兒；(b) 因無 handoff 的 `ivm-website`／`ebook-store-nginx` 掃不到 `to:`，另以 python3 印兩軍師所有 `roles` 逐條確認皆短碼（無空白、< 30 字）。

**部署與文件同步**

- R21. 重跑 `install.sh` 部署至 `~/.claude/skills/`（無新增檔案，SKILLS 陣列不變）。
- R22. 同步 kunsu repo：CLAUDE.md「開發狀態」與 ADR 清單納入 007、`docs/README.md` 索引補計畫與 ADR。

---

## Key Technical Decisions

- **不引入 `aliases` 欄，registry schema 不變**：`roles` 仍為 `string[]`，語意收斂為代碼。否決「整句 canonical＋代碼別名」（需維護對照表與模糊比對、未真正 unify，ADR Alternatives）。
- **三處核對強度不對等**：add-project 為唯一性的權威最終強制點（含同批 session 暫存集）；kunsu-apply 只讀 registry 已核准代碼、為早期訊號；kunsu-init 首建以累積集逐筆比對。ADR 不誇大 kunsu-apply 的保證強度。
- **遷移用 python3 原子寫入、禁編輯器直存**：與 `registry-merge.sh` 同一 `tempfile`＋`os.replace` 模式，避免中斷截斷 JSON 觸發全套工具「格式損壞」硬停；操作前 `cp` 備份。
- **兩軍師 CLAUDE.md 皆須雙欄遷移**：ebook registry 雖已是代碼，其 CLAUDE.md 仍停舊單欄，不遷則 Decision 1「CLAUDE.md 代碼欄」在 ebook 側不存在、三處一致破功（doc-review R2 finding，信心 100）。
- **`ivm-website` 為一次性代碼例外**：無既有 handoff 依據、以 repo 全名即席定案（使用者確認），不代表 `{軍師名}-{子專案名}` 複合碼為範式；Decision 2 給「短」軟性錨點（≤ 20 字、不含軍師名前綴）。
- **軟警告 vs 硬擋分層**：registry-merge.sh 軟警告作用於格式層（是否像代碼）、add-project 唯一性硬擋作用於語意層（是否撞名），兩者分屬不同層次不衝突。

---

## Implementation Units

### U1 — CONCEPTS.md 詞彙拆分

- **Goal**：R1。
- **Files**：`CONCEPTS.md`。
- **Approach**：將「角色字串」詞條改寫為「角色代碼」（比對鍵，三處字面一致的對象）與「角色說明」（display-only）兩條；「角色代碼」條註明「角色識別」為回覆 frontmatter 佔位符別稱。全域反向註冊表詞條的「角色字串」指稱改為「角色代碼」。
- **Verification**：`grep -n '角色字串' CONCEPTS.md` 應為 0（除歷史引用）；「角色代碼」「角色說明」「角色識別」三詞可查。

### U2 — 範本 `kunsu-claude.md` 雙欄與 frontmatter

- **Goal**：R2, R3, R4。
- **Files**：`skills/kunsu-init/assets/templates/kunsu-claude.md`、`skills/kunsu-init/assets/templates/PLACEHOLDERS.md`。
- **Approach**：關聯專案表表頭改 `| 專案 | 路徑 | 角色代碼 | 角色說明 |`；申請信箱協議 frontmatter 範例補 `role_desc`、`proposed_role` 註為代碼；回覆信箱協議「角色識別」佔位符不動。PLACEHOLDERS.md 更新 `{{PROJECT_ROWS}}` 格式說明。
- **Verification**：範本渲染後 `grep '角色代碼｜\|角色代碼 | 角色說明'` 命中；`{{` 佔位符數不變。

### U3 — `kunsu-init` SKILL 訪談、產列、唯一性

- **Goal**：R5, R6, R7。
- **Files**：`skills/kunsu-init/SKILL.md`。
- **Approach**：①-B 一行式欄位改 6 欄（代碼＋說明）；④-1 `{{PROJECT_ROWS}}` 產雙欄；⑦ 傳代碼；⑧ 完成提示改指代碼；新增多子專案登記時的 session 累積集代碼唯一性比對與撞名阻擋。
- **Verification**：SKILL 內「角色描述」單問改「角色代碼＋角色說明」；步驟 ⑧ 三處一致提示指代碼。

### U4 — `kunsu-apply` SKILL ＋ `new-application.sh`

- **Goal**：R8, R9, R10。
- **Files**：`skills/kunsu-apply/SKILL.md`、`skills/kunsu-apply/scripts/new-application.sh`。
- **Approach**：步驟 5 訪談收提議代碼＋說明；步驟 6 呼叫新增 `role_desc` 參數。腳本新增第 8 位置參數 `role_desc`，frontmatter 寫 `proposed_role`（代碼）＋`role_desc`，本文表格補列。步驟 4／新增早期唯一性訊號（讀 registry 已核准代碼、撞名提示列既有代碼、明示非權威）。
- **Verification**：`bash new-application.sh` 產出 frontmatter 含 `proposed_role` 與 `role_desc` 兩欄。

### U5 — `add-project` 子指令 審核收代碼、雙欄、唯一性強制點

- **Goal**：R11, R12, R13, R14。
- **Files**：`skills/kunsu-init/SKILL.md`（add-project 章節）。
- **Approach**：④-3 追問改代碼＋說明；⑥ 寫 CLAUDE.md 雙欄、`role_desc` 入說明欄；⑦ 傳代碼；在 ④-3 核准後、⑦ 前插入唯一性權威強制步驟（registry 聯集＋批次 session 暫存集逐筆重比、撞名阻擋列既有代碼）；⑨ 改名警告掃 `to:` == 舊代碼；⑩ 完成提示改指代碼。
- **Verification**：add-project 章節含「session 暫存集」唯一性步驟；三處一致提示指代碼。

### U6 — `kunsu-inbox` ＋ `handoff` 文案

- **Goal**：R15, R16。
- **Files**：`skills/kunsu-inbox/SKILL.md`、`skills/handoff/SKILL.md`。
- **Approach**：kunsu-inbox 4a-4「to: 不符清單」文案改「角色代碼集合」；比對邏輯與腳本不動。handoff 指令格式／注意節補「kunsu 情境 `to:` = 軍師登記的角色代碼」一句。
- **Verification**：kunsu-inbox 文案更新；handoff 補句可查；`scan-*.sh` 無 diff。

### U7 — `registry-merge.sh` 軟警告

- **Goal**：R17。
- **Files**：`skills/kunsu-init/scripts/registry-merge.sh`。
- **Approach**：python3 段於寫回前檢查每個 role 是否含空白或長度 > 30，命中則 stderr 印 WARN（不 exit 非零）；CLI 提示補「代碼宜 kebab-case」。
- **Verification**：以整句 role 呼叫 → stderr 有 WARN、exit 0、仍寫入；以短碼 role → 無 WARN。

### U8 — live 資料遷移與核查

- **Goal**：R18, R19, R20。
- **Files**：`~/.claude/kunsu-registry.json`、ivm 軍師 CLAUDE.md、ebook 軍師 CLAUDE.md（本機 live 路徑）。
- **Approach**：先 `cp` 備份 registry；python3 原子寫入替換 ivm 三筆＋ebook-store-nginx 的 `roles`；讀兩軍師 CLAUDE.md 關聯專案表、改雙欄（ivm 整句降說明、ebook 描述降說明、代碼欄填 registry 值）；核查雙軌（/kunsu-inbox＋python3 印 roles）。
- **Verification**：python3 印兩軍師 roles 皆短碼；ivm 子專案跑 /kunsu-inbox 無 false-negative、無 to: 不符孤兒。

### U9 — 部署與文件同步

- **Goal**：R21, R22。
- **Files**：`install.sh`（重跑，無檔案增減）、kunsu `CLAUDE.md`、`docs/README.md`。
- **Approach**：`bash install.sh`（或 `--link` 開發模式）重部署；kunsu CLAUDE.md「開發狀態」與 ADR 清單納入 007、docs/README 索引補本計畫與 ADR 007。
- **Verification**：`~/.claude/skills/` 內容與 repo 一致；kunsu 文件無殘留舊「角色描述」單欄描述。

---

## Risks & Dependencies

- **遷移動到 kunsu 工具外的 live 軍師 repo**：ivm／ebook 兩規劃中心是本機私有 repo，遷移是使用者授權的一次性資料修正，非 kunsu 工具注入；先 cp 備份、python3 原子寫入降低損壞風險。
- **順序相依**：U8（遷移）依賴 U7（軟警告，可先驗證整句會 WARN）與 U1–U6（工具側語意）落地後較安全，但遷移本身只改資料、可獨立執行；建議工具側（U1–U7, U9 部署）先行，最後跑 U8 並以更新後的 `/kunsu-inbox` 核查。
- **既有 handoff `to:` 對齊**：ivm 既有兩份交接 `to:` 為 `backend`／`shun-tien`，與定案代碼一致，遷移後不產生孤兒；`ivm-website`／`ebook-store-nginx` 無既有 handoff，代碼為即席定案、無對齊風險。
- **後續延後項（ADR 007 Open questions）**：add-project 內建「整句→代碼」自動遷移偵測、角色改名追溯修復工具化、說明欄留空呈現規格——均不在本計畫範圍。
