---
title: handoff 暫離回報與攔截點選擇——切任務無回報導致交接狀態失真
date: "2026-07-26"
last_updated: "2026-09-03"
category: workflow-issues
module: kunsu-handoff-skill
problem_type: workflow_issue
component: tooling
severity: high
root_cause: missing_workflow_step
resolution_type: workflow_improvement
applies_when:
  - "接手方切換至其他任務，離開前的自然語言不含任何交接領域語彙"
  - "skill 觸發詞已多輪補充但同型失效反覆重現"
  - "session 必然讀取某份產出物（如交接檔本體）且可在其中植入指引"
  - "工作流程狀態以協議產出物為唯一真實來源，狀態更新需有補報慣例"
  - "多步驟工作流程中途可能中斷，需定義最小中途回報步驟"
symptoms:
  - "接手方已完成工作並 commit 至 branch，交接仍被標記為「未接手」"
  - "使用者表達切換任務意圖時不使用交接語彙，觸發詞完全攔不住"
  - "沙盤與 /kunsu-inbox 因缺回覆檔而誤報交接狀態"
  - "同型觸發詞失效反覆重現（reply 路由 → done 收尾 → 暫離回報）"
related_components:
  - documentation
tags: [handoff, intercept-point-pattern, skill-triggers, partial-reply, boilerplate-injection, workflow-gap, kunsu-inbox, recurring-failure]
---

# handoff 暫離回報與攔截點選擇——切任務無回報導致交接狀態失真

## Context

kunsu 協議的狀態機以回覆檔（`docs/handoffs/replies/*.md`）為唯一訊號源：零回覆＝未接手。這在正常路徑下是設計優點（發起方不必猜測對方意圖），但在一個場景下形成盲點——接手方已把工作 commit 至 git branch，因臨時插入其他需求而切走，當下沒有投遞任何回覆。軍師端 `/kunsu-inbox` 與軍師沙盤把該交接持續列為「未接手」，與實際狀況（已有階段性成果、只是暫時離開）不符。

根因是行為層斷點：切換任務當下沒有任何東西提醒接手方先投遞回覆。更深一層：事發原話「把做好的部份先移到新的 branch，現在要先做新的需求，之後再回來整合」**不含任何交接語彙**（交接／軍師／回覆皆未出現），因此不論怎麼堆 description 觸發詞都存在根本覆蓋上限。這是同型失效的第三次出現：

- v0.3.0 reply 路由補洞：「回覆軍師」等口語未命中 description 觸發詞
- v0.6.0 done 收尾口語：「收尾」「歸檔」等零覆蓋
- 本次：切走口語完全不在交接語義域內

## Guidance

解法由三個互補層構成（handoff v0.9.0）。

### 第一層：暫離回報慣例（核心）

接手方切走前先投遞最小回覆，操作與一般 `/handoff reply` 完全相同，僅固定以下限制：

**`status` 固定用 `partial`，不用 `submitted`。** 判準是「剩餘步驟在誰手上」：

| 情況 | 正確 status |
|------|-------------|
| 合併、上線等剩餘步驟仍在接手方手上 | `partial` |
| 接手方工作完畢，純等發起方驗收 | `submitted` |

暫離時整合尚未完成，用 `submitted` 會讓發起方以為只差驗收而誤啟 done 收尾。

**內文至少三要素**：branch 名、一句現況、之後回來繼續的意向。例：「已在 branch `feature/xxx` 實作完成，尚未合併，插單處理完回來整合。」

**`verify` 照常選填**；branch 資訊寫內文、不放進 `verify`（維持其純驗收語意，不新增建議代碼）。回來完成後照常投遞 `submitted` 完成回覆，`verify` 不跨回覆繼承、需顯式複寫。

### 第二層：description 觸發詞補充

比照既有「補詞三步驟」教訓（真實口語、帶語境拒裸詞、負向場景驗證）補四個帶交接語境的口語：「交接工作先暫停」「暫停這份交接」「交接先放著，先做別的需求」「交接工作先放到 branch，之後再回來」。裸詞（「暫離」「先放著」）會在無關情境誤觸，一律夾帶「交接」語彙。

### 第三層：攔截點遷移（可遷移的一般化模式）

**問題模式**：使用者說的是工程語言（branch、需求），不是協議語言（交接、回覆）。當自然語言不含領域語彙時，堆觸發詞的覆蓋率有根本上限——攔截依賴「使用者說出正確的話」。

**通用解法**：把指引種進**接手方 session 必讀路徑上的產出物**，而非繼續堆觸發詞。此處的必讀產出物是每份交接檔自動附上的「回覆方式」定型文字（`skills/handoff/scripts/new-handoff.sh` 的 printf 產生器），末尾加一行：

```
中途需切換任務時，請先投遞暫離回報——`status: partial`、內文附 branch 名與現況，之後回來再照常回覆。
```

接手方 session 接到交接時必讀此段，指引進入其 context；之後使用者說出無交接語彙的話時，session 自己就有規則可以主動建議。

**條件式可靠，不是無條件可靠**：前提是接手方 session 本輪已讀過交接檔。若使用者口語轉述任務（session 從未 Read 交接檔）、或長 session context 稀釋，此路徑同樣攔不住。文件與規劃陳述此機制時應誠實寫出前提，不要宣稱「可靠攔截」（本輪 doc review 曾把初稿的過度承諾降級為條件式陳述）。

### 防錯：兩副本同步紀律

「回覆方式」定型文字有兩份逐字副本：`new-handoff.sh` 的 printf（產生器，接手方真正讀到的字）與 `skills/handoff/SKILL.md`「檔案格式範例」段（人讀的靜態展示）。修訂任一處必須連動；最高風險錯誤是只改範例、漏改產生器。驗證方式：暫存目錄實跑產檔＋grep 字面比對兩副本。本輪實作時發現既有斷行差異比研究預告的多一處（研究一處、實際兩處）——同步核查要對整段做，不能只看被點名的行。

（2026-09-03 補記）此核查已由 `scripts/consistency-check.sh` C 項機械化（實跑產檔＋錨句逐字比對）；`new-handoff.sh` 輸出結構其後多輪演進（stderr 指路行、產檔查重、修改檔案清單條款行），副本盤點以 C 項錨句清單為權威、勿沿用本文「兩份」時點快照。另一個已實證邊界：經 shell 產生的文字，比對必須走執行期實跑——雙引號內反引號是指令替換，靜態字面比對會假 PASS，見 [assertion-level-discipline-coverage-gap.md](assertion-level-discipline-coverage-gap.md)。

## Why This Matters

不遵循的影響：

1. **狀態失真、積壓掃描**：零回覆使軍師誤判「未接手」，該交接持續佔用 `/kunsu-inbox` 與沙盤掃描，多 repo 場景下積壓放大。
2. **收尾誤判**：發起方在「未接手」誤報下可能誤啟 done 收尾或重派工作，與接手方已在 branch 的成果撞車。
3. **協作透明度喪失**：發起方不知道接手方有無動工、進展到哪。

遵循的效果：暫離回報一投遞（即使只有三行），沙盤立即把該交接從「未接手」移至「部分完成」，發起方不必等接手方回來就知道工作已開始、在哪個 branch。

## When to Apply

暫離回報適用於以下條件同時成立：

- 使用者是接手方，工作已有階段性成果（如已 commit 至 branch）
- 需暫時切換到其他任務，不確定何時回來
- 尚未投遞任何回覆，或需在切走前更新現況

不適用：工作完畢純等驗收 → `submitted`；被外部依賴卡住 → `blocked`。

攔截點遷移模式適用於：觸發詞同型失效重現、使用者自然語言不含領域語彙、且存在 session 必讀的產出物可植入指引時。

## Examples

**Before（未投遞暫離回報）**——事發原話：「把做好的部份先移到新的 branch，現在要先做新的需求，之後再回來整合。」語彙分析：含「branch」（工程詞）、「新的需求」（任務切換詞），零協議詞彙。結果：`replies/` 零新檔案，沙盤列「⚠ 未接手」，發起方無從判斷是否已動工。

**After（投遞暫離回報）**：

```bash
echo "已在 branch feature/bulk-sync 實作完成，尚未合併，插單處理完回來整合。" \
  | bash ~/.claude/skills/handoff/scripts/new-handoff-reply.sh "<原交接檔 slug>" "" ""
```

回覆檔 frontmatter `status: partial`。結果：沙盤自「未接手」移至「部分完成」，發起方清楚知道已有進展、只是暫時插單；接手方回來後照常投 `submitted` 完成回覆並顯式複寫 `verify`。

## Related

- [handoff-done-closure-gap.md](handoff-done-closure-gap.md) — 同 module 的上游教訓：補詞三步驟（本文第二層直接援引）與多副本定型文字同步紀律（本文防錯段的方法論出處）。差異：該文修理「動作在對的時機被觸發」（trigger repair），本文把攔截點前移到產出物（intercept-point shift），是設計哲學層的補充。
- 需求文件：`docs/brainstorms/2026-07-25-handoff-pause-report-requirements.md`；實作計畫：`docs/plans/2026-07-25-001-feat-handoff-pause-report-plan.md`。
- [assertion-level-discipline-coverage-gap.md](assertion-level-discipline-coverage-gap.md) — 攔截點模式的第四次同型應用與一般化（掛載點覆蓋、雙態措辭）；本文防錯段靜態比對法的修正性補充。
