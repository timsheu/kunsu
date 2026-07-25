---
date: 2026-07-24
topic: kunsu-pre-planning-inventory
---

# 軍師規劃前既有盤點與 kb 檢索接線——需求文件

## Summary

軍師工作流程新增「規劃前既有盤點」步驟：產出方案前先以 kb（zoekt）檢索自家 `docs/handoffs/`（含 archive）與 `docs/plans/`，再及子專案文件，確認「既有能力、做過沒、結果如何」後才開始規劃。kb skill 補上對應查詢 playbook 作為共用基礎；跨 repo solutions 檢索為可裁外環，以全域慣例薄段落地。

---

## Problem Frame

實證案例：ebook 軍師處理「已購書籍加入排序功能」時，未發現既有的已購書籍快取列表（從快取列表即可做離線排序），反而過度規劃、把方案複雜度過度提升，使用者人工提示後才收斂。該知識存在於過往 plan（或 handoff）中，不在任何 `docs/solutions/`。

這揭示的失敗模式不是「跨 repo 教訓查不到」，而是「軍師規劃期漏查自家歷史」——其代價是方案複雜度膨脹與使用者介入成本，比重複踩坑更貴，因為污染的是方案本身。本需求源自三個 2026-07-24 idea（跨 repo solutions 檢索慣例、軍師派發前 kb 掃描、kb playbook），依此實證重新定位主從後合併為一份。

---

## Key Decisions

- **主從反轉：軍師自家歷史盤點為核心，跨 repo solutions 為外環**——證據指向軍師漏查自家 plans／handoffs；跨 repo solutions 檢索至今是理論性痛點，保留為可裁外環，等實際痛過再擴。
- **檢索優先序：handoffs（含回覆與 archive）→ plans → 子專案 docs → 跨 repo solutions**——handoff 回覆是第一線紀錄，frontmatter `status` 與內文直接記錄「做了沒＋結果如何」；plans 是歷史意圖快照，命中後需判斷是否已被推翻。
- **kb 為軟依賴**——zoekt 服務未執行或 kb 未安裝時，盤點步驟降級為手動查閱自家 docs 與子專案文件，不阻斷派發流程（比照 `init-obsidian-vault` 軟依賴先例）。
- **虛擬 hub：solutions 留在原 repo，不搬運**——zoekt 已索引全機 git repo 的已 commit 內容，跨 repo 檢索原地可達；不建立集中式知識庫，消除搬運造成的重複與漂移。
- **慣例層落地，零新機制**——全部改動為 SKILL.md／範本／全域指引的文字慣例；不 fork CE plugin（版本化快取，升級即覆蓋），改以全域指引觸及 subagent context。

---

## Requirements

**軍師工作流程（核心）**

- R1. 軍師範本工作流程於「評估技術可行性」階段新增規劃前既有盤點：產出方案前，以 kb 檢索自家 `docs/handoffs/`（含 `replies/` 與 `archive/`）與 `docs/plans/`，再及子專案文件，依上述優先序確認既有能力與既有結論。
- R2. 盤點命中既有能力或既有結論時，方案須以其為基礎，或明確說明不採用的理由——防止與既有資產平行的過度規劃。
- R3. 拆解交接文件時，將盤點所得的相關既有結論（含他 repo solution）以「repo 名＋路徑」列入交接本體參考段，供接手方直接取用。
- R4. kb 不可用時（未安裝或服務未回應），盤點步驟降級為手動查閱，流程不中斷、不報錯中止。

**查詢基礎（kb playbook）**

- R5. kb skill 查詢 playbook 新增「搜歷史／搜教訓」段：`docs/handoffs/`、`docs/plans/`、`docs/solutions/` 的 query 模板、frontmatter 欄位過濾技巧，以及「先查頂層熱區、需要時翻 archive 冷區」的兩層檢索慣例。
- R6. 搜歷史／搜教訓的回報沿用 kb 既有慣例：附索引新鮮度與「已索引範圍內」的邊界說明。

**外環（可裁，最小版本由規劃階段裁定）**

- R7. 全域指引新增薄段跨 repo 檢索慣例：本 repo `docs/solutions/` 查無或命中不足時，以 kb 跨 repo 再查一次；含健康檢查（失敗靜默略過）與引用格式（標明他 repo 情境、自行判斷適用性）。
- R8. ce-learnings-researcher 經 R7 全域指引間接觸及（subagent context 載入全域指引），不修改 plugin 檔案。

**落地與遷移**

- R9. 軍師範本更新後，ebook／ivm 兩個 live 軍師 CLAUDE.md 同步遷移，比照歷次 live 遷移慣例。

---

## Acceptance Examples

- AE1. 既有能力命中回饋規劃。**Covers R1, R2.**
  - **Given** 軍師接到與過往功能相鄰的需求（如「已購書籍排序」型案例），相關既有能力記錄於自家 plan 或 handoff 回覆
  - **When** 軍師執行規劃前既有盤點
  - **Then** 檢索命中該紀錄，方案以既有能力為基礎（或述明不用的理由），不產生平行的過度規劃
- AE2. kb 不可用降級。**Covers R4.**
  - **Given** zoekt 服務未執行
  - **When** 軍師進行盤點步驟
  - **Then** 提示降級為手動查閱自家 docs 與子專案文件，派發流程繼續，不中斷不報錯
- AE3. 跨 repo 外環命中。**Covers R7.**
  - **Given** 某子專案 session 於本 repo `docs/solutions/` 查無相關教訓，而另一 repo 已有對應 solution
  - **When** 依全域慣例以 kb 跨 repo 再查
  - **Then** 命中他 repo solution，引用時標明來源 repo 與路徑

---

## Scope Boundaries

- 通用 `/handoff` skill 不改動（服務非 kunsu 場景，不綁 kb 依賴）。
- 不 fork、不修改 CE plugin 任何檔案。
- 不引入 mem0／向量 RAG／embedding 等新檢索基礎設施。
- 軍師沙盤（kunsu-dashboard）零改動。
- tshehtu 兩個既有缺陷（`~/.tshehtu/project-dir` 缺失、discovery 疑未入排程）不在本需求內修復，於該 repo 另記 todo。
- solutions 治理機制（升格／合併／歸檔三排水口）另案處理，不在本需求。

---

## Dependencies / Assumptions

- 依賴 tshehtu 的 zoekt 常駐服務與排程索引。前提風險：`inventory.json`／`repos.txt` 停留於 2026-07-07 而索引持續重建，推測 discovery（新 repo 發現）未入排程——7/7 後新建 repo 可能不在索引；`~/.tshehtu/project-dir` 缺失使 kb skill 的手動重建指引失效。兩者需先於 tshehtu 修復或確認，否則盤點涵蓋範圍有靜默缺口。
- 假設軍師 docs 皆已 commit（zoekt 僅索引已 commit 內容；kunsu 協議本以 commit 為收斂點，成立）。
- 已驗證（2026-07-24）：zoekt 索引涵蓋全機 152 repo，`f:docs/solutions/` 查詢命中 42 篇跨 repo solutions，含軍師 repo。

---

## Outstanding Questions

**Deferred to Planning**

- 最小首發版本：核心（R1–R4）之外，R5–R9 各項納入或延後，由規劃階段裁定（使用者明示尚未確定最小範圍）。
- plans 命中結果的有效性標註：檢索到的 plan 可能已被推翻，引用時是否附「以最新 handoff 回覆為準」之類的判別慣例，規劃時定。
- R7 全域慣例落點：全域 CLAUDE.md 直加一段，或 rules 來源 repo 新增規則檔後 install，規劃時定。

---

## Sources

- `docs/ideas/2026-07-24-跨reposolutions檢索慣例本地查無時改查kb.md`、`docs/ideas/2026-07-24-軍師派發交接前以kb掃相關solutions附進交接本體.md`、`docs/ideas/2026-07-24-kbskill補solutions教訓查詢playbook.md`——本需求的三個上游 idea，各含落地研究（CE plugin 快取位置與覆蓋風險、範本插入點、kb symlink 部署方式）。
- `skills/kunsu-init/assets/templates/kunsu-claude.md` 工作流程段——R1 插入點（第 2 步評估技術可行性、第 5 步拆解交接文件）。
- kb skill 原始碼位於 tshehtu repo（`~/.claude/skills/kb` 為 symlink，開發模式改 repo 即生效）。
- ce-learnings-researcher 定義於 CE plugin 版本化快取（`~/.claude/plugins/cache/compound-engineering-plugin/`），tools 含 Bash、可執行 zoekt 查詢，subagent context 載入全域指引——R8 的機制依據。
