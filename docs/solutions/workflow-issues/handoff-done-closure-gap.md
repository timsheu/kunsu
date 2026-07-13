---
title: handoff done 收尾閉環四斷點——觸發詞、流程步驟、輸出提示與憲章同步
date: "2026-07-13"
category: workflow-issues
module: kunsu-handoff-skill
problem_type: workflow_issue
component: tooling
severity: high
root_cause: missing_workflow_step
resolution_type: workflow_improvement
applies_when:
  - "新增或擴充 skill 動作時，description 觸發詞未覆蓋該動作的實際口語變體"
  - "設計多步驟工作流程，最後一步之後仍有必要的收尾動作但未明文列出"
  - "機制層（ADR、掃描豁免）已授權某例外行為，但憲章層（範本 Invariant）字面尚未同步"
  - "同一份語意定型文字在多處存有副本（SKILL.md 多段、shell printf、scaffold 範本、live 系統）"
  - "對既有 live 系統做範本對稱遷移（將舊版文件改至新版規格）"
symptoms:
  - "submitted 交接長期積壓頂層，每次掃描都列出但從未被推進至 done"
  - "軍師 session 查核完回覆後不出現 /handoff done 建議，使用者也想不起要要求"
  - "口語「這份交接可以收尾了」未命中任何 skill 觸發詞，skill 根本不被載入"
  - "範本 Invariant 字面禁令與機制層已授權的行為形成字面矛盾，守規 session 迴避該動作"
  - "只修改一份定型文字副本，腳本與範本副本持續輸出舊語意"
related_components: [documentation]
tags: [handoff, skill-triggers, workflow-closure, invariant-sync, multi-copy-sync, live-migration, kunsu-inbox]
---

# handoff done 收尾閉環四斷點——觸發詞、流程步驟、輸出提示與憲章同步

## Context

kunsu 多 repo 協作套件中，軍師 session 查核完接手方回覆後，應以 `/handoff done` 將交接收尾歸檔（改本體 `status` ＋ `git mv` 至 `archive/`），`/kunsu-inbox` 與軍師沙盤才不再重複掃描。實際使用中 done 幾乎從未發生——`status: submitted` 的交接長期積壓在 `docs/handoffs/` 頂層，持續消耗掃描與讀檔 token。歸檔機制本身完備，缺的是「動作在對的時機被想起」。調查發現不是使用者習慣問題，而是四個斷點同時存在，任何一個單獨修好都不足以閉環：

1. **觸發詞缺口**：SKILL.md description 完全沒有 done 口語（「收尾」「歸檔交接」都不命中）——skill 不被載入，功能等於不存在。這是第二次同型缺口（v0.3.0 時「回覆軍師」口語未命中 reply）。
2. **流程文件無收尾步**：軍師範本工作流程六步驟結束在「讀取新回覆、調整規劃」，session 的流程認知裡沒有下一個動作。
3. **輸出範本無下一步提示**：`/kunsu-inbox` 回報新回覆段沒有「→」後續提示行（同輸出裡的申請段與上報段都有）。
4. **憲章字面禁令**：範本 Invariant #5「本體任何人都不再編輯（含本 session）」無例外條款，但 done 流程正是編輯本體 `status`——機制層（done 七步驟、`scan-replies.sh` 授權歸檔豁免、ADR 009）早已授權，憲章層沒跟上；守規矩的 session 讀到字面禁令會迴避建議 done。

修補過程另暴露第五個學習：回覆檔 `status` 值域定型文字有**四份語意副本**，原計畫只改其中一份，另兩份分別由 doc review 與 code review 才抓出。

## Guidance

### (a) Skill 觸發詞補洞三步驟

1. **收集使用者實際口語**：從問題回報與實際 session 對話整理「使用者說過但未命中任何觸發詞」的真實語句（本案：「可以收尾了」「這份交接做完了」「歸檔這份交接」）。
2. **補詞一律帶語境、拒收裸詞**：skill 部署於所有 repo 時，裸詞（「收尾」「結案」）會在無關情境（「這個 bug 可以結案了」）誤觸發。每個新觸發詞都要夾帶領域語境（「**交接**收尾」「這份**交接**做完了」「**handoff** done」）。
3. **負向場景驗證防過泛**：對每個新詞構造一個「不應觸發」的相鄰句型（「幫這個功能收尾」「這個 PR 可以結案了」）確認不命中。注意 skill 觸發是語意匹配、機率性的——負向驗證是盡力設計，不是硬保證，觸發詞修訂後應以多個變體實測。

### (b) 「機制已授權、憲章未跟上」的字面禁令掃蕩法

為某動作新增例外授權（ADR、腳本豁免邏輯）後，散落全文的同型禁令句若有任何一句沒帶例外，守規矩的 session 讀到就會迴避該動作——只改一句的效果等於沒改。

1. **grep 全文所有同型禁令句**：

   ```bash
   grep -n "不再編輯\|不回頭修改" skills/kunsu-init/assets/templates/kunsu-claude.md
   ```

   本案命中三句：Invariant #5、工作流程第 6 步、回覆信箱協議段。另有一句「不要編輯交接文件本體」對象是接手方（非發起方），不需例外——**逐句判斷禁令對象**，不順手全加。
2. **例外主文單點、其餘交叉參照**：完整例外語（動作、範圍、為何不破壞原則）只寫在禁令源頭一處（Invariant #5），其餘同型句以短交叉參照指回（「唯一例外：第 7 步的 done 收尾，見 Invariant #5」），避免多處各自維護完整例外語再度漂移。

### (c) 多副本定型文字同步核查

frontmatter 值域說明、限制語這類定型文字常有多份副本，改一漏一不會報錯。本案的副本清單：

| 副本 | 位置 | 漏改後果 |
|------|------|---------|
| SKILL.md「檔案格式範例」段 | `skills/handoff/SKILL.md` | 人與 session 讀到舊值域 |
| SKILL.md「注意」段 | 同檔另一段 | 兩段自相矛盾 |
| `new-handoff.sh` printf | `skills/handoff/scripts/new-handoff.sh` | **實際產生交接文件的來源**——新建交接的「回覆方式」段落永遠沒有新限制語 |
| 軍師範本值域行 | `skills/kunsu-init/assets/templates/kunsu-claude.md` | scaffold 出的每個新軍師都缺 |
| 既有軍師 CLAUDE.md | 各軍師 repo | live 系統持續舊語意 |

做法：修訂任何一份時**全數連動**；在 SKILL.md 定型文字旁加副本清單說明（「修訂此文案時須連動修改」並列出路徑）；Verification 步驟加 grep 字面一致核查：

```bash
grep -n "勿自標" \
  skills/handoff/SKILL.md \
  skills/handoff/scripts/new-handoff.sh \
  skills/kunsu-init/assets/templates/kunsu-claude.md
# 三檔皆應命中且語意一致
```

尤其注意：**「範例」與「產生器」是不同副本**——文件裡的範例改了，腳本 printf 沒改，實際產出物就永遠是舊的。

### (d) Live 遷移的舊句 grep 核查紀律

對既有系統做範本對稱遷移時：

1. **以定稿範本為唯一基準**建對比清單（每個待改句 × 每個目標檔），不沿用規劃期查證的舊快照。
2. **逐筆以舊句原文 grep 核查**，恰中一次才整句替換：

   ```bash
   grep -cF '交接文件本體與回覆檔案皆不回頭修改。' /path/to/軍師/CLAUDE.md
   # 1 → 可整句替換；0 → 措辭已漂移，停下回報實際措辭再定位，不憑印象改；2+ → 逐筆確認
   ```

3. **遷移後反向核查**：新句 grep 應命中、舊句應歸零，且 `git diff --stat` 僅含預期檔案與行數。
4. 每個目標系統一筆確認 commit 收斂。

已驗證的規律：遷移遺漏一律是第三方 review 才發現，從不是遷移者自己——遷移者腦中已有「改過了」的錯覺。對策是把核查義務前移為 grep 字面確認，不依賴記憶。

## Why This Matters

- 觸發詞缺口讓功能形同不存在，且已是第二次同型失效——這是 skill 架構的系統性風險，不是偶發。
- 憲章字面禁令未掃蕩乾淨時，越守規矩的 session 越不敢建議該動作；三句只改一句的後果等於沒改。
- 腳本 printf 副本未同步時，「接手方勿自標 done」限制語永遠到不了新產生的交接文件——接手方自標 done 會使交接從所有掃描面靜默消失、本體卻未歸檔，形成看不見的積壓。
- 收尾閉環斷裂的總成本是持續性的：每個積壓交接在每次 `/kunsu-inbox`、每次沙盤掃描、每次 `/handoff list` 都重複付費。

## When to Apply

| 觸發條件 | 適用子模式 |
|----------|-----------|
| 新增 skill 子指令、或發現實際口語與 description 觸發詞有落差 | (a) 觸發詞補洞三步驟 |
| 在流程文件、ADR 或腳本豁免邏輯中新增例外授權後 | (b) 字面禁令掃蕩法 |
| 修改 frontmatter 值域、欄位說明、限制語等定型文字 | (c) 多副本同步核查 |
| 對既有 live 系統做範本對稱遷移 | (d) 舊句 grep 核查紀律 |

組合情況（同時新增例外又改值域）時各子模式獨立執行、互不替代。

## Examples

### (a) description 觸發詞 before/after（handoff v0.5.0 → v0.6.0）

```yaml
# Before：done 口語零覆蓋
  Use when asked to「寫一份交接文件」…「新增 handoff」「list handoffs」「/handoff」.

# After：補七個帶語境口語，拒收裸詞「收尾」「結案」
  Use when asked to「寫一份交接文件」…「新增 handoff」「list handoffs」
  「交接收尾」「這份交接可以收尾了」「這份交接做完了」「完成這份交接」
  「歸檔這份交接」「標記交接完成」「handoff done」「/handoff」.
```

### (b) 字面禁令三處差分（範本 kunsu-claude.md）

```markdown
# Invariant #5（例外主文，完整理由只寫這一處）
- Before：…不回頭改動原檔，以維持單一作者、避免版本漂移。
- After： …避免版本漂移。**唯一例外**：發起方（本 session）執行 `/handoff done`
  收尾時，將本體 frontmatter `status` 改為 `done`，並與其回覆成對 `git mv` 至
  `docs/handoffs/archive/`——這是作者自己對文件的生命週期標記，屬授權歸檔
  （掃描規則已豁免），不改內文，單一作者原則不變。

# 工作流程第 6 步（短交叉參照）
- Before：…交接文件本體與回覆檔案皆不回頭修改。
- After： …皆不回頭修改（唯一例外：第 7 步的 done 收尾，見 Invariant #5）。

# 回覆信箱協議段（短交叉參照）
- Before：…產出後即為定案快照，任何人（含本 session）不再編輯。
- After： …不再編輯（唯一例外：`/handoff done` 收尾時的 `status` 更新與歸檔搬移，
  見 Invariant #5 與工作流程第 7 步）。
```

### (c) 產生器副本同步（new-handoff.sh printf）

```bash
# Before：三值、無 done、無限制語
printf '\n回覆檔 `status` 值：`submitted`（預設，已完成待發起方確認）／`partial`（部分完成，後續會再回報）／`blocked`（卡關）。另可加選填欄位 `verify:` …\n'

# After：四值＋接手方勿自標限制語（與 SKILL.md 範例段逐字一致）
printf '\n回覆檔 `status` 值：`submitted`（預設，已完成待發起方確認）／`partial`（部分完成，後續會再回報）／`blocked`（卡關）／`done`（已結案——**由發起方經 `/handoff done` 對交接本體執行，接手方回覆請勿自標**；自標會使此交接從 `/kunsu-inbox` 與軍師沙盤消失，本體卻仍留在頂層未歸檔）。另可加選填欄位 `verify:` …\n'
```

### (d) live 遷移實際使用的核查指令

```bash
# 遷移前：四個施工點逐筆核查（每句恰中一次、例外句尚不存在）
for pat in '不回頭改動原檔，以維持單一作者、避免版本漂移。' \
           '交接文件本體與回覆檔案皆不回頭修改。' \
           '產出後即為定案快照，任何人（含本 session）不再編輯。'; do
  grep -cF "$pat" /path/to/軍師/CLAUDE.md   # 各應為 1
done
grep -cF '唯一例外' /path/to/軍師/CLAUDE.md  # 應為 0（尚未遷移）

# 遷移後：新句全數命中、diff 僅含預期改動
grep -cF '7. **確認回覆後以 done 收尾歸檔**' /path/to/軍師/CLAUDE.md  # 應為 1
git -C /path/to/軍師 diff --stat -- CLAUDE.md   # 1 file changed，行數符合預期
```

## Related

- [docs/plans/2026-07-13-001-feat-handoff-done-closure-plan.md](../../plans/2026-07-13-001-feat-handoff-done-closure-plan.md) — 本學習的直接來源計畫（KTD-1 憲章三處同步、U1 觸發詞、U5 live 遷移）
- [docs/brainstorms/2026-07-13-handoff-done-closure-requirements.md](../../brainstorms/2026-07-13-handoff-done-closure-requirements.md) — 四斷點問題陳述一手資料
- [docs/adr/2026-07-09-adr-candidate-009-protocol-commit-confirmation.md](../../adr/2026-07-09-adr-candidate-009-protocol-commit-confirmation.md) — 「全域規範 vs 協議動作」的前例，done 收尾的確認 commit 協議出自此 ADR
- [docs/solutions/best-practices/git-porcelain-scan-script-pitfalls.md](../best-practices/git-porcelain-scan-script-pitfalls.md) — 同一批掃描腳本的 git 實作層陷阱（本文覆蓋 skill 設計層，互補）
- 母體 CLAUDE.md 開發狀態 2026-07-08 條目 — v0.3.0「回覆軍師」觸發詞補洞（同型缺口第一次發生的記錄）
