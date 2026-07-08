---
title: ADR Candidate 006 — 申請信箱：例外授權自單一信箱擴為雙信箱
date: 2026-07-07
type: adr
status: proposed
---

# ADR 006：申請信箱——例外授權自單一信箱擴為雙信箱

> 狀態：**Proposed**（2026-07-07 隨申請信箱功能實作提出，待審定；上游決策脈絡見
> [brainstorm](../brainstorms/2026-07-07-application-inbox-requirements.md) 與
> [實作計畫](../plans/2026-07-07-001-feat-application-inbox-plan.md)，兩者均經使用者逐項確認）。

## Context

### Observations（現況盤點）

- ADR 002 Decision 2 定義「信箱範圍是**唯一的**例外授權」：子專案 session 對軍師 repo 的寫入僅限在 `docs/handoffs/replies/` 新增回覆檔案，tripwire 以此為核對邊界。
- `add-project` 原以一行式五欄輸入收集子專案資訊，長字串在終端機輸入框的體驗差（VSCode 終端顯示錯亂、白色佈景下提示字不可辨），且路徑與技術棧等欄位實可自動偵測。
- 子專案端沒有任何「請求加入軍師」的入口：登記動作只能由使用者切到軍師目錄的 session 發起。

### Hypothesis（推斷，非事實）

- 子專案 session 是資訊最齊的位置（路徑、目錄名、技術棧都在腳下），在此投遞申請可將人工輸入降到只剩角色描述與環境限制。

## Decision（proposed）

1. **例外授權自單一信箱擴為雙信箱**：在回覆信箱之外，新增申請信箱 `docs/applications/`（scaffold 內建，含 `archive/` 與兩層 `.gitkeep`）。授權形式不變——對方 session 僅能在信箱內**新增新檔案**（申請限頂層），不得編輯任何既有檔案。ADR 002 的「唯一」語義由本 ADR 修訂為「僅有的兩個」；ADR 002 主文維持原貌（循 ADR 005 歷史快照前例）。
2. **投遞與審核分離（單點登記）**：子專案以 `/kunsu-apply` 投遞申請（自動偵測路徑／名稱／技術棧，手填僅角色描述與環境限制）；軍師端 `add-project` 掃描待審申請逐筆審核，**核准當下**才寫入軍師 CLAUDE.md 關聯專案表與全域註冊表。待審申請不進任何正式登記，避免半登記狀態。角色字串定案權在軍師。
3. **tripwire 分類規則**：申請信箱頂層 `*.md` 的新增＝新申請；「頂層→`archive/`」的搬移（可攜帶 frontmatter 更新）＝授權歸檔；`archive/` 內新增＝合法；反向搬移、頂層修改與刪除、外部搬入＝異常硬停。rename 豁免採雙側核驗（src 頂層＋dst archive/，缺一即異常）。掃描實作為 `scan-applications.sh`，置於 kunsu-inbox（信箱掃描域），`add-project` 跨 skill 呼叫部署路徑，不複製副本。
4. **審核結果以 frontmatter 更新落檔**：歸檔當下由軍師更新申請檔 `status`（`approved`／`rejected`，退回附 `decision_note`）後 `git mv` 至 `archive/`。此處**刻意偏離** handoff 本體「絕不編輯」的嚴格慣例：該慣例防的是跨 repo 雙寫入方的版本漂移，而歸檔時點僅剩軍師單一寫入方、漂移條件不成立；換得單檔可查（Obsidian dataview 可依 `status` 檢視申請歷史）。申請檔於頂層待審期間仍為不可變快照，由 tripwire 守護。
5. **既有軍師遷移內建於 add-project**：偵測缺 `docs/applications/` 時提議補建目錄並比照範本補協議文字，Grep 完成核查、失敗明確回報不回滾；子專案端投遞前檢查目標軍師已有信箱，未遷移即導引不投遞。不做獨立遷移指令。

## Consequences

- 子專案端新增 `/kunsu-apply` skill（`kunsu-` 前綴循 ADR 004），`install.sh` SKILLS 陣列同步。
- 軍師 CLAUDE.md 範本新增「申請信箱協議」章節，「唯一例外授權」與 tripwire 兩條 bullet 改為雙信箱表述；`/kunsu-inbox` 授權邊界聲明同步、軍師模式一併回報新申請份數。
- scaffold 驗收清單自五項擴為八項（applications 結構三項），結構不變量延伸：`docs/applications/` 與 `archive/` 需含 `.gitkeep`（clone 後目錄需存在，否則掃描在首份申請前無從核對——與 ADR 001 對 `replies/` 的論證相同）。
- 重複投遞不覆寫：子端永遠只新增檔案（同日同名自動 `-2`、`-3`），由軍師端「同路徑取最新、舊份退回歸檔」收斂——覆寫語義與「不得編輯既有檔案」授權相衝，故不採。
- Invariant 2「機器路徑只存在於兩處」的語義釐清：該不變量指涉**常設登記處**。申請檔的 `path` 欄位是暫態投遞內容（審核用的分組與驗證鍵），核准即轉入正式登記、歸檔後僅為歷史紀錄，不構成第三個登記處；母體 repo CLAUDE.md 的 Invariant 2 文字已同步補註。

## Alternatives considered

- **子專案 session 直接寫軍師 CLAUDE.md 與註冊表**：輸入體驗最直接，但正面違反協議精神（軍師端 tripwire 應視其為異常），且登記寫入分散兩端、易半登記。否決。
- **申請檔放子專案自身 repo＋全域指標**：申請有版控，但軍師無權清理子 repo 殘檔（Invariant 2）、兩處落點易不同步。否決。
- **借用 `docs/handoffs/replies/` 偽裝回覆**：不新增授權範圍，但語意錯置且 `scan-replies.sh` 會誤計為新回覆，實質仍動協議。否決。
- **全域申請佇列（`~/.claude/kunsu-join-requests/`）**：兩個 repo 零寫入、既有軍師零遷移，但申請不進版控、Obsidian 不可見，且與回覆信箱不對稱。使用者裁定信箱應在軍師 repo 內。否決。

## Open questions

- 申請信箱是否需要類似 handoff `archive/` 的定期整理慣例（歸檔數量成長後）——待實際使用量出現再評估。
- `/handoff` 升版改查註冊表（ADR 002 Decision 6）仍為獨立延後決策；`kunsu-apply` 的 registry 查詢模式可作為升版參考實作。
