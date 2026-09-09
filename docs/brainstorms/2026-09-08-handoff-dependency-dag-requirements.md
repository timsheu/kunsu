---
title: 交接依賴圖——以 depends_on 邊推導 DAG 式依賴追蹤
date: 2026-09-08
topic: handoff-dependency-dag
---

# 交接依賴圖——以 depends_on 邊推導 DAG 式依賴追蹤 — 需求文件

## Summary

交接本體 frontmatter 新增選填欄位 `depends_on`（被依賴交接的檔名列表），由軍師派發時寫入。節點即交接、邊即 `depends_on`，狀態沿用既有回覆推導，不新增任何狀態載體。後端單一模組建圖並推導「可開工」「等依賴」兩個推導態，供軍師沙盤、kunsu-inbox skill 與 SessionStart hook 三個消費端共用；軍師沙盤新增依賴圖區塊，以伺服器端產生的 inline SVG 呈現。營端零改動。

---

## Problem Frame

kunsu 的協調載體是純文件式的交接與回覆：軍師派發交接、營以回覆檔回報，狀態由回覆推導。沙盤與 hook 已能逐份呈現每份交接的狀態與停留天數，但交接之間的關係不存在於任何結構化位置——「B 要等 A 的 API 上線才能動」只寫在交接內文，軍師要靠記憶或通讀才知道誰在等誰。

同時 2～3 個營運作時，實際發生的成本形狀：軍師無法一眼判斷此刻哪些交接可以派、哪些營正在空等；營因等待上游而停滯時，沙盤看起來與「已接手正常進行」無異；重工（兩份交接做同一件事）與卡關（上游 blocked 使下游連帶停擺）都要靠人工比對才能發現。

現有機制中缺的只有**邊**與由邊推導的兩個狀態。節點、節點狀態與呈現面都已存在。

---

## Key Decisions

- **邊寫在交接本體 frontmatter，寫入方只有軍師。** 派發時寫入 `depends_on`，屬定案快照的一部分，與 Invariant #5「內文不可變」及 ADR 016「任何檔案永遠只有一個作者」原則相容。營維持只產回覆檔，不寫任何共享狀態；一份由多個營 session 更新的 state 檔會把回覆信箱當初解決的雙寫入方版本漂移問題重新請回來。
- **拓撲純推導，不落地第二份真相。** 營層級關係由交接圖依 `to:` 角色投影得出；可開工、等依賴、循環一律於讀取時計算、不寫回任何檔案。不建靜態營拓撲檔——那是多一份要手工同步的載體，本 repo 副本漂移的教訓反覆出現。
- **依賴滿足以本體 `status: done` 為準。** 被依賴交接的本體標 done（即已歸檔）才算滿足；回覆 `submitted` 只代表待確認，尚未經發起方驗收。此定義只讀發起方權威的生命週期 metadata，不引入回覆狀態的解讀歧義。
- **推導態與營自報的 blocked 分開。** 回覆 `status: blocked` 是營自報卡關（沙盤 ⛔），「等依賴」是推導態；兩者標籤、值域與樣式皆不混用，既有四份 `status` 值域副本零改動。
- **依賴變更走更正交接慣例。** `depends_on` 在派發時定案；事後要改依賴，發更正交接並在原本體補 `corrected_by`，不把 `depends_on` 納入 ADR 016 可事後編輯的欄位白名單，避免修訂 ADR。
- **引用檔名權威。** `depends_on` 值為交接檔名不含路徑，被依賴交接歸檔後仍可解析，與 `corrected_by` 及引用慣例同型。
- **圖以伺服器端 inline SVG 呈現。** 沙盤至今零 JS、零外部程式，SVG 字串可被 pytest 完整斷言，離線可用，回應仍為 `text/html`（ADR 010 條件 5 內）。Mermaid 需引入 CDN JS 且渲染結果無法在測試中驗證；Graphviz 需機器層級安裝。兩者不採，後端圖結構保留日後加 Graphviz 輸出的餘地。
- **邏輯放在腳本與後端，不放在 SKILL 指引。** 產檔腳本收參數寫欄位、後端模組算圖；模型只負責傳參數。此為「會飄移的紀律改用計算載體」的既有結論，也是本地 Ollama 模型相容的前提。

---

## Requirements

**資料模型**

- R1. 交接本體 frontmatter 新增選填欄位 `depends_on`，值為 YAML 列表，每個元素為一份交接的完整檔名（不含路徑）。
- R2. 產檔腳本 `new-handoff.sh` 新增參數接收依賴檔名列表並寫入 frontmatter；未給參數時不產生此欄位，既有交接零遷移。
- R3. handoff skill 的 add 子指令於派發流程中提示軍師宣告依賴，並說明依賴變更走更正交接慣例。
- R4. `depends_on` 為定案快照的一部分，不列入 ADR 016 的事後可編輯欄位；更正交接慣例、`corrected_by` 語意零改動。

**推導與圖計算**

- R5. 後端單一模組（位於沙盤 app 內）讀取軍師 `docs/handoffs/` 頂層與 `archive/` 的全部交接本體，以檔名建節點、以 `depends_on` 建邊。
- R6. 節點狀態沿用既有推導（未接手／部分完成／已回覆待確認／done），不新增狀態載體。
- R7. 依賴滿足的判準為被依賴交接本體 `status: done`；一份交接的所有依賴皆滿足且自身未 done 時，推導態為「可開工」；任一依賴未滿足時，推導態為「等依賴」。
- R8. 模組執行循環偵測；出現循環時回報涉及的交接檔名，不使任何消費端崩潰。
- R9. `depends_on` 指向不存在的檔名時，建圖不中斷，該邊標記為「無法解析」並回報。
- R10. 三個消費端（軍師沙盤、kunsu-inbox skill、SessionStart hook）共用同一份推導，不各自重寫圖邏輯。

**呈現**

- R11. 軍師沙盤新增依賴圖區塊，以伺服器端產生的 inline SVG 呈現：節點依狀態上色，推導態「可開工」「等依賴」以獨立標記呈現，節點可連結至該交接既有的展開明細。
- R12. 沙盤依賴圖零 JS、零新依賴；回應維持 `text/html`，符合 ADR 010 例外條件。
- R13. 軍師沙盤既有的分類清單於每筆交接附「等依賴」或「可開工」標記，孤立節點（無入邊無出邊）不附；營自報的 ⛔ 卡關標記與推導態並列不互抑。
- R14. kunsu-inbox skill 與 SessionStart hook 於各自的摘要中呈現推導態；營端看到自己被派的交接處於「等依賴」時，能看到它在等哪一份。
- R15. 循環與無法解析的邊在三個消費端皆顯式呈現，不靜默略過。

**協議與不變量**

- R16. 營端零改動：不新增營需執行的步驟、不新增營需寫入的檔案；營端的回覆流程與「未 commit 即新回覆」訊號零改動。
- R17. 掃描腳本、tripwire、歸檔豁免形狀與 `status`／`verify` 值域零改動。
- R18. 範本與三 live 軍師的憲章文字只在需要指路句時同步；不新增觸發詞。

**Agent 相容**

- R19. 依賴宣告與圖推導的全部邏輯位於腳本與後端；skill 指引只說明何時傳參數。
- R20. handoff skill 的 Agent 對應表涵蓋本功能的呼叫形；未列 agent（含本地 Ollama session）採 Codex 欄保守行為。

---

## Scope Boundaries

- 不建靜態營拓撲檔；營層級關係只由交接圖投影。
- 不建模交接以下粒度（子任務、里程碑）。
- 不支援跨軍師依賴；一份圖只涵蓋單一軍師的交接。
- 不採 Mermaid 或 Graphviz；Graphviz 輸出列為日後可選升級。
- 不引入新狀態載體、不新增回覆 `status` 值、不修訂 ADR 016 欄位白名單。
- 不試圖以依賴圖偵測「營接了沒回」——那屬暫離回報與停留天數的範圍。

---

## Acceptance Examples

- AE1. 依賴滿足推導
  - **Covers R5, R7.**
  - **Given** 交接 B 的 `depends_on` 列出交接 A 的檔名，A 本體位於 `archive/` 且 `status: done`。
  - **Then** B 的推導態為「可開工」。

- AE2. 等依賴推導
  - **Covers R7, R13, R14.**
  - **Given** 交接 B 依賴 A，A 的最新回覆 `status: submitted`、本體仍在頂層。
  - **Then** B 的推導態為「等依賴」，沙盤與 hook 皆顯示 B 在等 A。

- AE3. 營自報 blocked 與等依賴並列
  - **Covers R13.**
  - **Given** 交接 B 依賴未完成的 A，且 B 的最新回覆 `status: blocked`。
  - **Then** B 同時顯示 ⛔ 卡關與「等依賴」，兩者互不覆蓋。

- AE4. 循環
  - **Covers R8, R15.**
  - **Given** A 依賴 B、B 依賴 A。
  - **Then** 三個消費端皆列出循環涉及的兩個檔名；沙盤頁面其餘區塊正常渲染。

- AE5. 無法解析的邊
  - **Covers R9, R15.**
  - **Given** 交接 B 的 `depends_on` 含一個不存在的檔名。
  - **Then** 建圖完成，B 的其餘依賴照常推導，該邊以「無法解析」呈現於三個消費端。

- AE6. 無依賴宣告的既有交接
  - **Covers R2, R6, R16.**
  - **Given** 軍師的全部交接皆無 `depends_on`。
  - **Then** 三個消費端的既有輸出零變化，依賴圖區塊提示「無依賴宣告」，孤立節點不畫。

- AE7. 依賴變更
  - **Covers R3, R4.**
  - **Given** 派發後發現 B 其實還要等 C。
  - **Then** 軍師發更正交接並於 B 本體補 `corrected_by`；B 的 `depends_on` 不被編輯。

---

## Outstanding Questions

**Deferred to Planning**

- 循環偵測到時，三消費端的呈現形式與是否影響「可開工」判定（涉及循環的節點一律視為等依賴，或另立狀態）。
- SVG 分層排版對超過 8 個活節點時的降級方式（縮小節點、改文字清單，或只畫未 done 子圖）。
- 依賴圖區塊在沙盤頁面的位置（全域總覽列之下，或每個軍師分組內）。
- `new-handoff.sh` 參數形式（第幾個位置參數或具名旗標）與既有查重關鍵詞參數的相容。
- kunsu-inbox 子 repo 模式與 SessionStart hook 摘要中推導態的具體文案與排序。
- 更正交接發出後，圖是否讀取更正交接的 `depends_on` 覆蓋原本體的邊（需與 ADR 016「更正交接為一般交接」的定性一致）。

---

## Dependencies / Assumptions

- 沙盤 `subrepo_status.py` 的分類邏輯與 kunsu-inbox skill 步驟 4a 為同一套判準的兩份副本，本功能沿用其推導結果，不改判準。
- SessionStart hook 已匯入沙盤模組，共用推導模組的接線方式沿此既有路徑。
- 三 live 軍師的交接檔名遵循 `YYYY-MM-DD-標題.md` 慣例且同一軍師內唯一，檔名可作節點鍵。
- 節點規模假設為同時 3～8 個活交接；超過此規模的排版品質不在本輪保證範圍。

---

## References

- `skills/handoff/scripts/new-handoff.sh` — 交接產檔腳本，`depends_on` 的寫入點。
- `skills/kunsu-dashboard/app/subrepo_status.py` — 既有節點狀態推導；`main.py` — 沙盤渲染與既有 `<details>` 錨點。
- `skills/kunsu-inbox/scripts/session_hook.py` — 已匯入沙盤模組的消費端先例。
- `docs/adr/2026-08-14-adr-candidate-016-lifecycle-metadata-boundary.md` — 內文不可變、欄位白名單、更正交接與引用檔名權威。
- `docs/adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md` — 沙盤例外的五項技術條件。
- `docs/adr/2026-08-13-adr-candidate-015-dispatch-push-notification.md` — 派發即推播，add 流程的既有步驟結構。
