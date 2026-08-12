---
date: 2026-08-12
topic: awareness-automation
---

# 知悉層自動化：SessionStart hook 啟用＋派發即推播（分階段提案）

> 改版註記（2026-08-12 同日）：初版 Phase B 為 launchd 通知哨兵（輪詢＋macOS 通知）。經使用者實況修正（子專案 session 長駐不關、以 `/clear` 清 context）與兩項技術查證（`/clear` 會觸發 SessionStart hook；本機互動 session 之間存在可傳訊的網格），Phase B 整體改為「派發即推播」——事件驅動、零輪詢、零常駐服務。哨兵方案廢棄，不再列入。

## Summary

把 kunsu 協作中「發現有信」這件事從人肉輪詢改為自動送達，同時完全不觸碰「決定接不接、做不做」的人工閘門。分兩個互為備援的階段：

- **Phase A — SessionStart hook**：啟用 [ADR 002](../adr/2026-07-06-adr-candidate-002-relay-automation-registry-inbox.md) Decision 3 早已規劃、延後至實際使用後再決定的「第二階段」——同一套檢查邏輯改為 session 啟動時自動注入提示。經官方文件查證，hook 於 `/clear` 時同樣觸發且 stdout 注入清空後的新 context，與使用者「session 長駐、以 `/clear` 清理」的實際習慣完美咬合：按 `/clear` 即見信箱清單。
- **Phase B — 派發即推播**：軍師 session 完成派發的最後一步，向各目標子專案**已開啟的長駐 session** 發送純告知訊息（session 間訊息能力已於本機實測確認）。事件驅動——派發的當下就是推播的時機，無輪詢、無 launchd、無狀態檔、無任何新服務。使用者晃回子專案視窗時，通知已經顯示在那裡。

兩階段皆不經 LLM 判斷邏輯（Phase B 的收發是 session 既有能力，通知內容為定型文案）；人工閘門（ADR 002 Decision 5「只告知不開工」）在任何階段皆不變。

## Problem Frame

使用者的實際使用情境（2026-08-12 修正確認）：

- 一次派發通常同時涵蓋前後端＋客戶端等 **3～4 個子專案**。
- 各子專案的 Claude Code session **長駐不關**——視窗常開數小時以上，context 以 `/clear` 清理，甚至不清理直接下 `/kunsu-inbox`。
- 因此痛點不是「開新 session 的成本」，而是：**逐一主動切換到每個視窗、在每個視窗手動輸入 `/kunsu-inbox`、等它掃描**。記憶負擔（哪些視窗有信）與按鍵成本（每視窗一輪指令）全落在使用者身上。

既有資產對此縫隙的覆蓋狀況：軍師沙盤解決「一頁盤點全局」的 pull 式需求，但要使用者記得開瀏覽器；`/kunsu-inbox` 是手動觸發；「等軍師寫完派發」的等待通知屬 Claude Code 自身的 session 完成通知設定（`/config`），不在本案範圍。

本提案的立場維持初版不變：把「知悉」與「決策」拆開——自動化只做知悉層（發現與告知），決策層（接單、開工、回覆、收尾）維持現有人工閘門一寸不讓。

## 關聯資產盤點

| 資產 | 與本案的關係 |
|------|--------------|
| [ADR 002](../adr/2026-07-06-adr-candidate-002-relay-automation-registry-inbox.md)（accepted） | Decision 3 已預留 SessionStart hook 為第二階段，採用與否「待 `/inbox` 實際使用後再決定」——Phase A 即此決策點的正式啟用。Alternatives 否決「fswatch／daemon 輪詢推播」，否決理由之二「session 非常駐，推播無處落地」——Phase B 對此翻案（見 ADR Candidate 015）。Decision 5「只告知不開工」為兩階段共同底線。 |
| Claude Code hooks 官方文件（2026-08-12 查證） | SessionStart matcher source 值域：`startup`／`resume`／`clear`／`compact`／`fork`；**`/clear` 確定觸發**，且 SessionStart 的 stdout 屬「注入 context」的例外清單。Phase A 對長駐 session 習慣的有效性以此為據。 |
| 本機 session 網格（2026-08-12 實測） | 於使用者機器實測列出互動 session 清單，確認子專案長駐 session（ivm、eBookApp、iOS 各一）互相可見、可定址傳訊。Phase B 的「落地點存在」以此為據。 |
| [ADR 010](../adr/2026-07-11-adr-candidate-010-dashboard-service-exception.md)（accepted） | 軍師沙盤對 Invariant 1 的例外先例。註：Phase B 改版後**不再需要比照此例外**——派發即推播無服務、無輪詢，字面即合規。 |
| [ADR 011](../adr/2026-07-12-adr-candidate-011-reply-verify-field.md)（accepted） | 交接三分類（未接手／部分完成／已回覆待確認）與 verify 標籤的判斷規則來源，hook 輸出沿用此分類，不另創詞彙。 |
| `skills/kunsu-inbox/scripts/`（scan-replies.sh／scan-applications.sh／scan-reports.sh） | 軍師模式掃描的單一事實來源，輸出前綴（`NEW_REPLY:` 等）已是穩定介面。hook 軍師模式包裝呼叫，不重寫。 |
| `skills/kunsu-dashboard/app/`（registry.py／subrepo_status.py／kunsu_scan.py） | 皆為 stdlib-only、有 pytest 覆蓋（137 項）。`registry.py` 已處理註冊表解析與路徑健康判斷；`subrepo_status.py` 是 `/kunsu-inbox` 步驟 4a 分類邏輯的 Python 實作。hook 腳本直接 import 複用，判斷規則零重寫。 |
| `skills/handoff/`（派發流程） | Phase B 的掛載點：派發完成後新增「向已開啟目標 session 發送通知」子步驟，屬 skill 文件層改動，符合 Invariant 1「純 skill＋範本」。 |
| `~/.claude/kunsu-registry.json` | hook 判斷當前 repo 身分的唯一依據；Phase B 匹配目標 session 時的角色—路徑對照來源。 |
| `~/.claude/settings.json` | 現況 `hooks` 為空物件，SessionStart hook 設定將是首個進駐項；hook 設定屬機器層級，不進任何 git repo。 |
| Invariant 2（絕不注入子 repo） | Phase B 收方行為規則**不得**寫入子專案 CLAUDE.md。解法：通知訊息自帶收方指令（self-contained），見 Key Decisions。 |

## 分層陳述

**Observations（可查證的事實）**

- ADR 002 Decision 3 原文把 SessionStart hook 定為第二階段，決策時機「`/inbox` 實際使用後」；`/kunsu-inbox` 自 2026-07-06 上線至今實際使用逾一個月。
- 官方文件明載 `/clear` 觸發 SessionStart（`matcher: "clear"`），且其 stdout 注入清空後的 context（2026-08-12 查證，確定程度高）。
- 本機實測：互動 session 彼此可見、可傳訊；使用者的 3 個子專案長駐 session 出現在清單中（2026-08-12）。
- ADR 002 否決 daemon 推播的理由之二為「session 非常駐，推播無處落地」；使用者實況（session 長駐數小時不關）與上述實測共同構成此前提不再成立的證據。
- `claude` CLI 以引數帶 slash command 啟動（如 `claude "/kunsu-inbox"`）未見官方文件支載——初版曾構想的「launcher 直接帶指令開 session」缺乏文件依據，且與長駐 session 實況不符，不採。

**Hypotheses（推斷，標明為推斷）**

- 推斷一：收方 session 收到自帶「僅回顯、勿開工」指令的通知訊息時，會如指令僅向使用者回顯——此為對模型遵循度的推斷，需試點實測驗證，且為 Phase B 的成立前提。
- 推斷二：busy 狀態的 session 收訊後會排隊至當前輪次結束才處理——時機行為需實測。
- 推斷三：軍師 session 與本 session 同版本 CLI，具備相同的 session 列表與傳訊能力——需在軍師 session 實測一次。

**Recommendations（建議）**

- 兩階段互為備援：Phase B 推播覆蓋「session 已開啟」的主場景；目標 session 不在線或匹配失敗時，Phase A hook 於下次 `/clear` 或啟動時兜底。先上 Phase A（無前提依賴），Phase B 以單一子專案試點驗證推斷一至三後再全面啟用。
- hook 腳本以 `subrepo_status.py`／`kunsu_scan.py`／`registry.py` 為依賴直接複用，延續「分類規則只有一份」。
- 通知文案定型且極簡（軍師名／角色／份數／檔名清單），細節留給 hook 清單與 `/kunsu-inbox`。

**Questions（留給使用者的開放決策）**

見文末〈Open Questions〉。

## Key Decisions（proposed）

- **Phase A 定性為「啟用 ADR 002 既定第二階段」，不是新架構** — 決策依據、身分偵測規則、人工閘門原則全部沿用 ADR 002 原文；本提案僅補充實作形態（複用沙盤模組）與輸出格式。`/clear` 觸發是官方既定行為，非本案客製。
- **Phase B 定性為「派發流程的收尾子步驟」，不是基礎設施** — 推播由軍師 session 在派發完成當下執行（事件驅動，派發者最知道派發時刻），掛載於 handoff skill 派發流程文件；無輪詢、無常駐程序、無狀態檔，Invariant 1 字面即合規，無需比照 ADR 010 開例外。
- **收方規則以訊息自帶，不注入子 repo（Invariant 2 零觸碰）** — 通知訊息內文即含收方指令：「此為 kunsu 派發通知：請僅向使用者回顯本訊息重點，勿開始任何工作、勿讀取交接檔內文」。子專案 CLAUDE.md 與任何子 repo 檔案零改動。
- **hook 只告知、不開工、不代答** — 開場注入清單與提示，不自動開啟交接檔內文、不預先起草回覆。ADR 002 Decision 5 人工閘門零改動。
- **判斷邏輯單一來源** — 子專案模式 import `subrepo_status.py`，軍師模式經 `kunsu_scan.py` 呼叫既有三支 scan 腳本；hook 不新增任何分類規則。
- **開發部署分離（Invariant 3）** — hook 腳本源碼落於本 repo `skills/kunsu-inbox/scripts/`（新增 `session-hook.py`），由 `install.sh` 部署至 `~/.claude/skills/`；`~/.claude/settings.json` 的 hook 設定指向部署路徑。
- **未登記 repo 靜默快退、失敗不阻斷** — hook 第一步查註冊表，皆不符合即靜默退出（毫秒級）；任何錯誤 exit 0 並輸出單行降級提示，絕不擋 session（fail-open）。
- **推播失敗降級為兜底，不重試** — 目標 session 匹配不到、離線或發送失敗時，跳過並於派發收尾摘要註明「N 個目標未推播，待其 `/clear` 由 hook 補位」；不排隊、不重試、不留待送清單。

## Requirements

**Phase A — SessionStart hook**

- R1. 使用者於任何目錄開啟 session（startup／resume／clear／compact 皆含）時，hook 腳本以當前 repo 根路徑比對 `~/.claude/kunsu-registry.json`，依 ADR 002 Decision 2 規則獨立評估子專案／軍師雙重身分；皆不符合時靜默退出，不輸出任何內容。
- R2. 具子專案身分時，掃描所屬各軍師信箱中 `to:` 為本 repo 角色、狀態非 done 的交接文件，依 ADR 011 三分類輸出摘要清單：每筆含檔名、分類、（有則）verify 標籤。
- R3. 具軍師身分時，經既有三支 scan 腳本輸出新回覆／新申請／新上報計數與 tripwire 異常摘要。
- R4. 巢狀拓撲（雙重身分）合併輸出兩種模式結果，與 `/kunsu-inbox` 行為一致。
- R5. 輸出設上限（每分類最多 5 筆，超出以「另有 N 筆」收尾），防止大信箱稀釋開場 context。
- R6. hook 全程不修改任何檔案、不執行 git 寫入操作、不呼叫 LLM。
- R7. 腳本錯誤或依賴缺失時 exit 0 並輸出單行降級提示，session 照常啟動。
- R8. 效能目標:未登記 repo 快退路徑 100ms 內；已登記 repo 完整掃描 2 秒內（現況規模：3 軍師、9 子專案登記）。
- R9. 隨附解除方式：自 `~/.claude/settings.json` 移除該 hook 條目即完全停用，文件明載。

**Phase B — 派發即推播（試點驗證推斷一至三後全面啟用）**

- R10. handoff skill 派發流程新增收尾子步驟：軍師 session 列出本機互動 session，依註冊表的角色—路徑對照匹配各目標子專案的已開啟 session，逐一發送通知訊息。
- R11. 通知訊息定型文案：軍師名、目標角色、派發份數、檔名清單（上限 5 筆），並自帶收方指令（僅回顯、勿開工、勿讀交接檔內文）；訊息自足，不依賴子 repo 任何設定（Invariant 2）。
- R12. 匹配不到、離線或發送失敗一律降級不重試：派發收尾摘要註明未推播目標，由 Phase A hook 兜底。
- R13. 試點範圍：先以單一子專案（建議 ebook 網路中 session 最常開的一個）驗證收方回顯行為、busy 排隊時機與 token 成本，試點結論補記於本文件後再全面啟用。

## Key Flows（兩階段上線後）

- F1. 派發—接手（3～4 子專案同時收件的主場景）
  - 使用者於軍師 session 描述需求、分案、派發（不變）。
  - 派發完成當下，軍師 session 向各目標子專案的長駐 session 推送通知（**新增**）；派發收尾摘要列出已推播／未推播目標。
  - 使用者晃回任一子專案視窗——通知已顯示在該視窗（**新增**：不切換也能一眼看到有無新信）；使用者直接說「開第一份」，或照舊 `/clear`（hook 攤開完整分類清單）／`/kunsu-inbox`。
  - 決策點不變：開哪份、何時開工，仍由使用者開口。
- F2. 回覆—確認
  - 子專案回覆投遞後，使用者回軍師視窗 `/clear`——hook 開場即報「收到 N 份新回覆」，接續查核與 done 收尾（不變）。（回覆方向的反向推播見 Open Questions 3。）

## ADR Candidates（依 CE 規範先行提出，供審視後定稿）

- **ADR Candidate 014 — SessionStart hook 第二階段啟用**：記錄 ADR 002 Decision 3 預留決策點的正式啟用、觸發證據（逾月實際使用後的輪詢成本回饋）、`/clear` 觸發之官方行為依據、實作形態（複用沙盤模組、開發部署分離）、人工閘門不變之確認。
- **ADR Candidate 015 — 派發即推播對 ADR 002 推播否決的翻案**：翻案論證分兩層——（一）事實前提變更：否決理由「session 非常駐，推播無處落地」不再成立，證據為使用者長駐 session 實況與 2026-08-12 本機 session 網格實測；（二）機制變更：非 daemon 輪詢，而是派發事件當下由軍師 session 主動送出的一次性訊息，「不主動輪詢」原則零觸碰。附收方規則以訊息自帶之 Invariant 2 合規設計、降級不重試策略、與 ADR 010 例外之對照（本案無需例外）。

## Open Questions（2026-08-12 已全數定案）

1. **session 與子專案的匹配慣例** — 定案：**名稱啟發式自動匹配**。軍師以 session 名稱對應註冊表路徑，匹配不到即降級（不重試、派發摘要註明），由 Phase A hook 兜底；不採派發時逐次人工確認。
2. **Phase A 首版是否含軍師模式** — 定案：**含軍師模式**。子專案與軍師端一次到位，F2 回覆確認流程同步受惠；軍師端開場延遲以 R8 的 2 秒目標約束。
3. **回覆方向是否也推播** — 定案：**Phase B 試點成功後再延伸**。首版僅做派發方向；收方行為（推斷一至三）經 R13 試點驗證無虞後，回覆方向作為對稱延伸另行補上。

## 驗收構想

- 沿用沙盤既有 pytest 慣例為 `session-hook.py` 補單元測試（身分偵測分支、輸出上限、fail-open 路徑）。
- Phase A 以四種真實情境手動驗證：未登記 repo（無輸出、無感延遲）、子專案 startup、子專案 **`/clear`**（本案關鍵路徑）、軍師（若納入首版）。
- Phase B 依 R13 以單一子專案試點，逐項記錄推斷一至三的實測結果後再全面啟用。
- 兩階段皆不引入新服務、新依賴、新常駐程序，無需額外維運驗證。
