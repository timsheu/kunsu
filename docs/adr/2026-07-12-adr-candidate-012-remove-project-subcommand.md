---
title: ADR Candidate 012 — 軍師端 remove-project 子指令：整筆移除子專案登記
date: 2026-07-12
type: adr
status: accepted
---

# ADR 012：軍師端 remove-project 子指令：整筆移除子專案登記

> 狀態：**Accepted**（2026-07-12 起草）。源自使用者發現「子專案可能因檔案結構
> 合併或拆分而需要刪除，但目前只有 add-project 沒有對應的移除路徑」；經
> `/ce-brainstorm` → `/ce-plan` 完整流程定案，決策內容已由實作計畫的
> 4-persona `/ce-doc-review`（coherence／feasibility／scope-guardian／
> adversarial，8 項發現、6 項直接修正）逐一壓力測試，不另立獨立的 ADR 審查
> 回合。需求文件見
> [2026-07-12-remove-project-requirements.md](../brainstorms/2026-07-12-remove-project-requirements.md)，
> 實作計畫見
> [2026-07-12-002-feat-remove-project-subcommand-plan.md](../plans/2026-07-12-002-feat-remove-project-subcommand-plan.md)。

## Context

### Observations（現況盤點）

- `kunsu-init` 的 `add-project` 子指令支援新增子專案登記與角色代碼異動，但沒有
  對應的移除路徑；目前唯一手段是手動編輯 `~/.claude/kunsu-registry.json` 與
  軍師 CLAUDE.md，前者是全域 JSON 檔，手改容易破壞格式且無版控保護。
- `kunsu-list` 已具備 stale 偵測能力（路徑不存在的登記標 ⚠）但只報不修，缺一個
  對應的「修」動作收尾。
- 全域反向註冊表 `~/.claude/kunsu-registry.json` 是機器路徑常設登記的兩處之一
  （另一處是軍師 CLAUDE.md 關聯專案表），且**不受任何 repo 版控**——這與軍師
  CLAUDE.md 的可復原性（git checkout）不對稱，移除操作若不謹慎設計順序與確認
  機制，容易在中斷時留下無法回頭的殘留狀態。

### Hypothesis（推斷，非事實）

- 推斷：子專案檔案結構合併或拆分並非高頻事件，但一旦發生，使用者若被迫手動
  編輯 registry JSON，出錯機率（格式損壞、誤刪其他軍師的登記）高於透過工具
  操作；工具化的邊際價值主要在「防呆」而非「省時」。

## Decision（proposed）

1. **只做軍師端發起，整筆移除**：新增 `remove-project` 子指令，對稱
   `add-project`，僅能在軍師根目錄的 session 執行；一次移除該子專案在本軍師的
   **所有**角色代碼登記，不支援保留部分角色代碼。不做子專案端「退出申請」投遞
   （對稱 `kunsu-apply` 的反向流程）——移除通常是軍師先發現舊登記失效，子專案
   端此時未必還能正常執行任何 skill。

2. **清單呈現採失效感知輔助選取，且兩來源聯集而非只認 registry**：比照
   `kunsu-list` 既有的 stale 偵測邏輯（路徑存在性查核），路徑已不存在的登記
   標記並排在前；候選清單合併 registry 與軍師 CLAUDE.md 關聯專案表兩個來源
   （兩側路徑正規化後聯集去重）——若清單只認 registry，僅存在於 CLAUDE.md 的
   殘留列將永遠無法被本子指令選中清除，形同留下沒有出口的孤兒資料。

3. **兩階段確認語意分離，不可合併**：移除前先掃描軍師自身 `docs/handoffs/`
   頂層的未完成交接文件（`to:` 屬於待移除角色代碼集合、且無回覆或最新回覆
   `status` 非 `done`），列清單警告但不阻擋（比照 `add-project` 步驟⑨角色改名
   警告）；再呈現一次獨立的**不可逆確認**（摘要＋「registry 不受版控、無法
   git 復原」的明確聲明）。前者是「你知道會有孤兒交接嗎」，後者是「你確定要做
   這個不可逆動作嗎」，目的不同、不可壓成一次確認。

4. **雙側寫入順序固定為先 CLAUDE.md、後 registry**：CLAUDE.md 受 git 版控、
   未 commit 前可用 `git checkout` 復原；registry 不受版控、寫入即不可逆。
   把可復原的操作放前面、不可逆操作放最後，並在 CLAUDE.md 編輯後加一道 Grep
   核查關卡（核查失敗即停止、不呼叫 registry 移除）——任何中斷後的殘留狀態都
   停在「CLAUDE.md 已編輯未 commit（可復原）＋registry 未動」，而非相反。

5. **`registry-remove.sh` 以獨立 exit code 區分「冪等略過」與「成功移除」**：
   新增對稱 `registry-merge.sh` 的獨立腳本；找不到對應登記時仍視為已達成移除
   目的（不阻斷「僅 CLAUDE.md 有登記」的情境），但用 exit 3（而非與「成功移除」
   共用的 exit 0）回報——這是不可逆操作，若呼叫端把「路徑打錯、registry 其實
   沒動」與「已成功移除」混為一談，使用者會誤以為完成了實際上沒發生的移除。

6. **未完成交接掃描的角色代碼集合取聯集，不是擇一 fallback**：待掃描的角色
   代碼集合是 registry `roles` 陣列與 CLAUDE.md 代碼欄的聯集，而非「registry
   有就只看 registry」——兩者可能因手動編輯而漂移，擇一 fallback 會讓另一側
   才有的角色代碼被漏掃，使該代碼底下的未完成交接在警告清單中悄悄消失，使用者
   不會被告知就完成了移除。

7. **Invariant 2 邊界聲明**：`remove-project` 的全部寫入僅發生在軍師自己的
   CLAUDE.md（軍師 repo 內）與軍師 repo 外的全域 registry；未完成交接掃描只讀
   軍師自身 `docs/handoffs/`，不讀取任何子專案目錄——不構成「軍師對子專案
   唯讀」的例外，本條明文聲明供未來讀者溯源，不需重新推導。

## Alternatives（否決方案）

- **支援選擇性移除單一角色代碼**（保留其他角色）：子專案在同一軍師底下多半
  只掛單一角色代碼，為少見的多角色部分退場場景增加選取介面複雜度不划算。有
  此需求時，使用者可先整筆移除、再以 `add-project` 重新登記其餘角色。否決。
- **子專案端主動投遞「退出申請」**：對稱 `kunsu-apply`，但移除觸發時子專案
  端狀態通常已不可靠（路徑已合併/拆分/消失），投遞流程無實益。否決，本次只做
  軍師端手動移除。
- **registry 移除操作走與 `registry-merge.sh` 相同的 exit code（0/1/2）**：
  不區分「冪等略過」與「成功移除」，實作簡單，但無法讓呼叫端分辨「路徑打錯
  導致靜默無操作」與「確實移除了東西」——在不可逆操作上這個模糊地帶風險過高。
  經 `/ce-doc-review` adversarial persona 指出後否決，改用獨立 exit code 3。
- **雙側寫入順序改為先 registry、後 CLAUDE.md**：規劃初期曾考慮「先做不可逆
  的、再做可復原的」，理由是「若可復原的一側失敗，好歹不可逆的一側已經正確
  完成」。但推演後發現：CLAUDE.md 是三種失敗情境中較脆弱的一環（手動編輯過的
  軍師可能使 Edit／Grep 定位失敗機率更高），若把它排在 registry 之後，一旦
  CLAUDE.md 編輯失敗，殘留狀態會是「registry 已不可逆移除＋CLAUDE.md 卡在
  半刪除」——對人類讀者而言，這比「CLAUDE.md 已改未 commit＋registry 未動」
  更難排解。否決，改採 Decision 4 的順序。
- **registry 移除前建立稽核快照或版本歷史**：維持現行「registry 無版控、無
  稽核歷史」慣例（與 `registry-merge.sh` 一致），不在本次新增額外的復原機制。
  否決，複雜度與目前用量不成比例。

## Consequences

- `kunsu-init` 新增 `skills/kunsu-init/scripts/registry-remove.sh`（新腳本，
  沿用 `registry-merge.sh` 的 python3 行內執行、`realpath` 正規化、
  `tempfile` + `os.replace` 原子寫入慣例，但 exit code 語意不同：0＝成功
  移除、3＝冪等略過、1＝JSON 損壞、2＝參數錯誤）。
- `skills/kunsu-init/SKILL.md` 新增 `remove-project` 子指令段落（版本
  0.2.0 → 0.3.0），frontmatter description 補觸發語。
- 移除操作不刪除任何既存的 `docs/handoffs` 或 `docs/handoffs/replies`
  檔案；移除後這些角色代碼底下的孤兒交接會在軍師沙盤被歸類為「to: 不符
  清單」，需使用者自行判斷是否手動歸檔——本 ADR 不引入自動歸檔或清理機制。
- registry 與 CLAUDE.md 長期漂移的主動偵測／修復工具不在本次範圍；
  `remove-project` 只在執行當下優雅處理「registry 有、CLAUDE.md 無」與
  「CLAUDE.md 有、registry 無」兩種不同步情境，不建立獨立的漂移掃描機制。
- 合併/拆分情境的自動偵測或新舊登記自動合併（例如自動判斷兩個路徑其實是
  同一專案）不在本次範圍；`remove-project` 只負責移除舊登記，新增登記仍走
  既有 `add-project`。

## Open Questions

- registry 與 CLAUDE.md 長期漂移的主動偵測／修復工具是否值得獨立建置（現為
  `remove-project` 執行當下優雅處理，非系統性偵測）——待漂移案例累積後評估。
- 「to: 不符清單」孤兒交接的批次歸檔輔助（如 `/kunsu-inbox` 提示「以下孤兒
  交接可批次歸檔」）是否有必要——待使用量觀察。
- `registry-remove.sh` 與 `registry-merge.sh` 是否應進一步抽出共用的
  read-JSON／原子寫入輔助函式庫，減少兩支腳本的重複——現階段兩支腳本均短小
  獨立維護成本低，暫不處理。
