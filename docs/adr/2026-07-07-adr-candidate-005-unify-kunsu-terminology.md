---
title: ADR Candidate 005 — 詞彙統一：scaffold 產物正式稱「軍師」，全面取代「規劃中心」
date: 2026-07-07
type: adr
status: accepted
---

# ADR 005：詞彙統一——「規劃中心」改稱「軍師」

> 狀態：**Accepted**（2026-07-07 由使用者發起並確認，理由：「名稱統一比較不會誤解」；同日實施）。

## Context

### Observations（現況盤點）

- ADR 004 rebrand 時，「軍師」指向工具組本體（kunsu），scaffold 產物仍沿稱「規劃中心」（命名故事：「`/kunsu-init` 建中心」）。
- 2026-07-07 使用者發現 README 存在品牌斷層——工具已叫軍師，對外門面仍滿版「規劃中心」——並指示改稱。README 全文與 `/kunsu-init` 觸發語（新增「建立軍師」「幫我建一個軍師」等，舊觸發語保留）已先行完成並重新部署。
- 「規劃中心／規劃協調中心」仍存在於五個層面：
  1. **skill 指令層**：`kunsu-init`／`kunsu-inbox` 的 SKILL.md 本文與輸出範本文案（如「## 規劃中心：{path}」）。
  2. **腳本訊息層**：`registry-merge.sh`（「→ 規劃中心：」等）與 `scan-replies.sh` 的輸出與錯誤訊息。
  3. **範本與種子層**：`assets/templates/` 五份範本（scaffold 產物的 CLAUDE.md／CONCEPTS.md 等自稱「規劃中心」）與 `assets/solutions/` 兩篇種子文件。
  4. **本 repo 內部文件**：CLAUDE.md、docs/README.md、docs/HOME.md。
  5. **歷史快照**：ADR 001–003 本文、docs/plans、docs/brainstorms。
- 機器識別字現況：註冊表 JSON 欄位 `planner`（`registry-merge.sh` 寫入、`kunsu-inbox` SKILL.md 讀取）、腳本參數 `<planner-abs-path>` 與內部變數、範本檔名 `planner-claude.md` 等。
- 截至本文撰寫，`~/.claude/kunsu-registry.json` **尚不存在**（dogfooding 後已清理、無真實部署）——與 ADR 004 Decision 4（趁檔案尚不存在零成本改名）相同的窗口仍開著。

### Hypothesis（推斷，非事實）

「軍師」一詞將同時關聯工具組（kunsu）與 scaffold 產物，理論上有語意重疊；推斷實際對話中以「kunsu／工具組」稱工具、以「軍師」稱產物即可自然消歧，成本可忽略——此推斷待實際使用手感驗證。

## Decision（proposed）

1. **詞彙定案**：「軍師」為 scaffold 產物（原「規劃協調中心」）的正式稱呼；工具組稱「kunsu」或「kunsu 工具組」。命名故事更新為：**kunsu 為專案群立軍師；軍師運籌帷幄、各營（子專案）上陣實作；`/kunsu-init` 立軍師、`/kunsu-inbox` 傳令；`/handoff` 是軍師與各營共用的公文格式。**「規劃協調中心」降為概念註解，僅於各文件首次出現處以「軍師（規劃協調中心）」形式保留一次。
2. **人讀文案層全面改稱**：SKILL.md 本文與輸出範本文案、兩支腳本的輸出與錯誤訊息、`assets/templates/` 範本內容（scaffold 產物自稱軍師，建議句式「本 repo 是 X 專案群的軍師（規劃協調中心）」）、`assets/solutions/` 種子文件、本 repo CLAUDE.md／docs/README.md／docs/HOME.md。
3. **機器識別字趁零部署窗口一併改**：註冊表 JSON 欄位 `planner` → `kunsu`（`registry-merge.sh` 寫入端與 `kunsu-inbox` SKILL.md 讀取端同步）、腳本參數與內部變數名同步、範本檔名 `planner-*.md` → `kunsu-*.md`（`kunsu-init` SKILL.md 引用同步）。
4. **歷史快照不改**：ADR 001–003 本文、docs/plans、docs/brainstorms 維持原貌（沿 ADR 004 Decision 5）；ADR 004 已加補充註記指向本文。
5. **母本不回改**：ebook 中心為範本母本，依 CLAUDE.md Invariant 4 唯讀；其自身是否改稱屬該中心 session 的決定，不在本 repo 範圍。
6. **驗證要求**：實施後重跑 dogfooding 重點場景（scaffold 全流程、`add-project`、`/kunsu-inbox` 雙模式、registry 欄位讀寫一致性），並以 `install.sh` 重新部署。

## Consequences

- **正面**：對外（README）、對內（skill 輸出與腳本訊息）、產物（scaffold 出的中心文件）三層詞彙一致，消除「工具叫軍師、產物叫規劃中心」的斷層；機器識別字在零部署窗口改名，未來不需任何遷移邏輯。
- **負面／限制**：範本與 SKILL.md 是 scaffold 行為的一部分，改動需重跑 dogfooding 驗證（重點場景即可，非全部 19 場景）；「軍師」不再唯一指工具組，消歧依賴 Decision 1 的稱呼慣例（推斷成本可忽略，待驗證）；若在審定前註冊表已產生真實資料，Decision 3 的欄位改名須降級為「保留 `planner` 不改」（見替代方案一）。

## Alternatives considered

- **只改人讀文案，機器識別字保留 `planner`**：零風險且對使用者不可見，但錯過零部署窗口——註冊表一旦有真實資料，欄位改名需遷移邏輯，屆時理性選擇將是永遠不改，形成永久的內外名稱斷層。窗口論證與 ADR 004 Decision 4 相同。否決（但作為窗口關閉後的降級方案保留）。
- **產物改稱「軍師中心」**：消歧更明確，但詞彙冗長、弱化擬人隱喻，且與 README 已上線的用法（「軍師是一個獨立的第三方 repo」）不一致。否決。
- **維持 ADR 004 原命名故事（軍師僅指工具組）**：使用者已於 2026-07-07 明示走向統一，且 README 已先行。否決。

## Open questions

- 既有 ebook 中心是否在其自身 repo 補一段詞彙對照（「本 repo 即 kunsu 所稱之軍師」）——非本 repo 範圍，留待該中心 session 決定。
- Hypothesis 所述「軍師雙關聯的消歧成本可忽略」需在遷移後的實際使用中回頭驗證；若造成混淆，補救方向是在 CONCEPTS.md 範本強化詞彙定義，而非回退改名。
