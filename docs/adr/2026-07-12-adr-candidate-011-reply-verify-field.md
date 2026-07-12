---
title: ADR Candidate 011 — 回覆驗收方式欄位（verify）與未接手／部分完成分類拆分
date: 2026-07-12
type: adr
status: accepted
---

# ADR 011：回覆驗收方式欄位（verify）與未接手／部分完成分類拆分

> 狀態：**Accepted**（2026-07-12 起草，同日經 5-persona `/ce-doc-review`（9 項
> 修正）審定。源自軍師沙盤試用回饋「看不出 partial 的原因是哪一種測試需求」；
> 與實作同日並行起草、實作先行落地——三項核心決策為使用者當日互動拍板，
> 程式碼與文件在審定前已完成。實作計畫見
> [2026-07-12-001-feat-reply-verify-field-plan.md](../plans/2026-07-12-001-feat-reply-verify-field-plan.md)。）

## Context

### Observations（現況盤點）

- 回覆檔 frontmatter 的 `status` 值域為 `submitted`／`partial`／`blocked`／`done`
  四值（定義於 `skills/kunsu-inbox/SKILL.md` 依賴聲明）。`/kunsu-inbox` 步驟 4a-3
  與其 Python 鏡像 `skills/kunsu-dashboard/app/subrepo_status.py` 據此把交接文件
  分成兩類：無回覆或最新回覆 `partial`／`blocked` → 「待接手」；最新回覆
  `submitted` → 「已回覆待確認」。
- 協議中沒有任何欄位承載「還缺哪種驗證」：實務上「做完但還不能結案」的原因各不
  相同——有的需上線部署後才能測試、有的馬上可測、有的得實機測試——沙盤上一律
  糊成「待接手」或「已回覆待確認」，需點開全文才能得知（且全文未必有寫明）。
- 「待接手」一詞對 `partial`／`blocked` 的回覆語意失準：這些交接其實已有人接手
  並回報過進度，與「完全無回覆」混在同一分類，反而掩蓋了「等的是驗證，不是等人
  接手」的實情。
- 沙盤每筆項目的摘要列目前僅顯示標題、檔名與最後修改時間
  （`main.py` `_html_handoff_detail`），連既有的 `partial`／`blocked` 區分都
  未呈現。

### Hypothesis（推斷，非事實）

- 推斷：隨交接數量增加，「知道每筆卡在哪種驗證」會直接影響使用者安排工作順序
  （例如集中一次部署後批次驗證所有 needs-deploy 項目、出門時帶上實機處理
  needs-device 項目）；缺這個維度時沙盤的聚合價值打折。

## Decision（proposed）

1. **回覆檔 frontmatter 新增選填欄位 `verify:`**（驗收方式），由接手方回覆時
   宣告「此回覆對應的工作還缺哪種驗證／目前可怎麼驗證」。只掛回覆檔、不掛交接
   文件本體——受影響的兩類顯示（partial／blocked→部分完成、submitted→
   已回覆待確認）必有回覆檔可承載，改動面最小；單一作者原則不變（回覆檔仍只有
   接手方寫）。

2. **值域採「建議代碼＋開放值域」**：定義三個建議代碼——
   `needs-deploy`（需上線測試 🚀）／`testable-now`（馬上可測 ⚡）／
   `needs-device`（需實機測試 📱）——顯示端以對應中文彩色標籤呈現；填其他自由
   字串則原樣顯示為一般標籤；欄位缺省不顯示標籤。未來擴充新建議代碼只改顯示端
   對照，不改協議。

   建議代碼一律**全小寫 kebab-case**；顯示端於查找對照表前將 verify 值正規化為
   小寫（`Needs-Deploy` 等大小寫變體仍命中彩色標籤），未命中的自由字串一律原樣
   顯示原始值，拼寫變體不靜默降格。

   verify 與 status 相關標籤（⛔ 卡關等）一律置於每筆交接文件的**摘要列**
   （`<summary>` 節點），不展開即可掃描——支撐 Hypothesis 所述的批次排程情境。
   同一分類內的項目依 verify **聚合排序**：已知建議代碼在前、自由字串次之、
   缺省最後（同 verify 值相鄰，組內依檔案修改時間降序），相同驗收方式的項目
   相鄰呈現。

3. **「待接手」拆分為「未接手」與「部分完成」**：判準是「有無回覆」——
   無回覆（零筆）→ **未接手**；最新回覆 `partial`／`blocked` → **部分完成**
   （blocked 另標 ⛔ 卡關）；最新回覆為未知 status 值 → **部分完成**（原樣顯示
   該 status，保守不略過；原「未知值視同待接手」規則隨拆分改歸此類，因為有回覆
   就不是未接手）；`submitted` → 已回覆待確認；`done` → 略過。

   `status: blocked` 與 `verify` 同時存在時，兩標籤**並列顯示**（⛔ 卡關置前、
   verify 標籤置後），不互相抑制——接手方填入的驗收方式在卡關期間仍有參考價值。

4. **`verify` 為 display-only 欄位**：不進全域註冊表、不參與任何精確比對邏輯、
   不影響 tripwire——`scan-replies.sh` 只看 git 狀態與路徑形狀、不解析
   frontmatter，零改動。Invariant 2（機器路徑常設登記僅存兩處）不受影響。

## Alternatives（否決方案）

- **擴充 `status` 值域**（如 `partial-needs-deploy`）：`status` 是協議狀態機的
  精確比對鍵（4a-3 分類、done 歸檔豁免、`/kunsu-report` 反向重導的
  「`status` 非 `done`」判斷都依賴既有值域），把「狀態」與「原因」壓進同一欄位
  會迫使所有比對端改寫，且值域組合爆炸。否決。
- **掛交接文件本體**（發起方預告驗收方式，回覆時覆蓋）：能讓「未接手」項目也
  顯示測試需求，但需改動 `/handoff add` 流程與 `new-handoff.sh`，且發起方預告
  的準確度存疑（實際驗收型態常在實作後才明朗）。使用者拍板不採，維持最小改動。
- **登記在專案層級**（註冊表或軍師 CLAUDE.md 關聯專案表標注「此 repo 天生要
  實機測試」）：無法表達同一專案不同交接的差異；且註冊表定位是機器路徑的常設
  登記，不宜混入工作狀態維度。否決。

## Consequences

- 完全向後相容：既有回覆檔無 `verify` 欄位，顯示行為除分類名稱拆分外不變，
  零遷移需求。
- **verify 不跨回覆繼承**：顯示端只讀最新回覆的 verify 值，最新回覆未填即顯示
  缺省（—），不沿用前輪值。驗收需求未改變時，接手方在每次補充進度的回覆中應
  **顯式複寫**相同的 verify 值，否則標籤靜默消失；此設計可表達「刻意清除」，
  代價是複寫義務（handoff SKILL.md reply 流程內建提示）。
- **verify 不設自動過期**：驗收環境改變（如部署已完成）時，接手方應以新回覆
  更新 verify 值，否則沙盤持續顯示舊標籤——過期的 verify 是錯誤資訊而非無資訊，
  更新義務同樣落在 reply 流程提示。
- **未接手（零回覆）項目不顯示 verify**：reply-only 落點的結構性限制——
  Hypothesis 所述的排班收益僅在已有至少一筆回覆後實現，此為拍板時已權衡的
  取捨；若未來評估此限制對排班目標影響重大，可重審「掛交接文件本體」替代案
  （已否決但可重審）。
- `/handoff` skill 升版 v0.4.0 → v0.5.0（回覆 frontmatter 規格新增選填欄位、
  `new-handoff-reply.sh` 新增選填參數）；`/kunsu-inbox` 依賴聲明同步。
- `skills/kunsu-inbox/SKILL.md` 步驟 4a 與 `subrepo_status.py` 為鏡像關係，
  兩者必須同步修改（模組頂端維護提示既有約定）。
- 軍師 scaffold 範本（`kunsu-claude.md`）的回覆信箱協議同步補述；既有軍師
  （ivm／ebook）CLAUDE.md 協議段落建議 live 遷移補述——僅文件說明性質，
  不影響任何機器比對，未遷移不造成故障。

## Open Questions

- Obsidian HOME dataview 是否加 `verify` 欄呈現（本次不做，待用量評估）。
- 建議代碼值域是否隨用量擴充（如 `needs-data-migration`）；擴充時只改顯示端
  對照表，協議不動。
- 「部分完成」與「卡關」（blocked）是否值得再拆為獨立分類（現為同分類加標籤，
  待實際卡關數量成長後評估）。
