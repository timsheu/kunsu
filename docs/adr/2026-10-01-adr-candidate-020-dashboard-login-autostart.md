---
title: ADR Candidate 020 — 軍師沙盤（kunsu dashboard）登入自動啟動：修訂 ADR 010 Decision 第 1 項第 3 條
date: 2026-10-01
type: adr
status: accepted
---

# ADR 020：軍師沙盤（kunsu dashboard）登入自動啟動——修訂 ADR 010 Decision 第 1 項第 3 條

> 狀態：**accepted**（2026-10-02 使用者審定；同日落地第 5 項交付物）。依 [ADR 010](2026-07-11-adr-candidate-010-dashboard-service-exception.md) 可證偽段要求，本 ADR 先對登入自動啟動做完整的 Invariant 1 例外評估（Decision 第 0 項），評估結論再落為對 ADR 010 例外範圍界定的修訂；審定前不修改 repo 交付物（plist 範本、SKILL.md、CLAUDE.md）。repo 外 `nohup` 腳本與其狀態檔的清理不屬本 ADR 範圍，已於 2026-10-01 先行完成（見 Consequences）。

## Context

### 觀察（observation）

- ADR 010 Decision 第 1 項第 3 條規定「啟動與停止必須由使用者手動掌握——不得有 `launchd`、`cron`、或任何其他 skill／排程觸發的自主重啟路徑」，且其可證偽段明寫：「任何提案若需要背景排程／開機自動啟動（違反 3）……即不適用本例外，須回頭走完整的 Invariant 1 例外評估，不能直接援引本 ADR。」ADR 010 Alternatives considered 延後的「背景排程自動更新」指資料定期刷新，與本 ADR 的「登入時啟動伺服器 process」是不同事項，**不構成本 ADR 的授權依據**。本 ADR 的依據是上述可證偽段：登入自動啟動違反第 3 條，故依其要求先走完整的 Invariant 1 例外評估（Decision 第 0 項），通過後才修訂 ADR 010。
- 使用者實際使用回饋（2026-10-01）：**開機後會忘了啟動沙盤**。沙盤只在伺服器運作時才有價值，忘了啟動時，打開瀏覽器只會看到連線失敗，必須回到終端機手動執行 `start.sh`，抵銷了沙盤「隨時瞄一眼」的設計目的（ADR 010 Alternatives considered 第二項的取捨理由）。
- 2026-10-01 已在 repo 外（`~/scripts/kunsu-dashboard.sh`，機器層級個人腳本，不屬本 repo 交付物）以 `nohup` 實作「終端機關閉後持續運作」的背景啟動。此做法仍由使用者手動下指令啟停，不違反第 1 項第 3 條；但它把日誌與 PID 檔寫入 `~/.local/state/kunsu-dashboard/`，字面上違反第 1 項第 1 條「不在 `skills/kunsu-dashboard/` 以外產生持久性資料（含日誌）」。該腳本也無法解決「開機忘了開」——開機後仍須手動執行一次。
- 先例：[ADR 014](2026-08-13-adr-candidate-014-sessionstart-hook-activation.md) 與 [ADR 015](2026-08-13-adr-candidate-015-dispatch-push-notification.md) 廢棄的「launchd 通知哨兵」是**輪詢信箱並主動推播**的常駐服務，廢棄理由是「推播只轉述已知之事、通知時刻與遺忘時刻錯位」。本 ADR 提議的 launchd 用途僅是「登入時把伺服器拉起來」，不輪詢、不推播，與該廢棄方案的被否決理由不重疊。
- 先例：ADR 014 的 SessionStart hook 掛載屬「機器層級設定、不進 repo」，由使用者手動寫入 `~/.claude/settings.json`，repo 只提供範例與解除說明。

### 假設（hypothesis）

- 「開機忘了開」的痛點只需要「登入時啟動一次」即可消除；伺服器執行期間崩潰的頻率低（沙盤自 2026-07-11 上線至今未有崩潰回報——此為推斷，未查證日誌），因此不需要崩潰後自動重啟。
- 登入當下啟動失敗（port 被佔用、Python 路徑失效、依賴缺失）的頻率低。**未驗證**：沙盤至今一律以 `start.sh` 前景執行，未留任何日誌，此假設與上一條皆無法回溯查證，只能由試用期觀察。
- **試用期**：本 ADR 審定為 accepted 後兩週。期間每次登入後第一次開啟沙盤時，順手查看 `/tmp/kunsu-dashboard.log` 有無 `Traceback` 或啟動錯誤。兩週內零次登入啟動失敗、零次執行期崩潰即視為假設獲支持；結果由使用者於試用期滿時判定。
- **重評訊號**：試用期間只要出現一次「使用者須查 `/tmp/kunsu-dashboard.log` 才得知原因」的登入啟動失敗或執行期崩潰，即重新評估本方案（含 `KeepAlive` 與 launchd Sockets 隨連線啟動等替代方案），另立 ADR。

## Decision（proposed）

0. **Invariant 1 完整例外評估**（ADR 010 可證偽段要求）。先列判準與否決條件，再逐項判定；任一否決條件成立即不通過：
   - **否決條件 1**：存在零常駐、且同樣能消除「開機忘了開」的替代方案。→ 判定：launchd Sockets 隨連線啟動可零常駐，但 uvicorn 須以 ctypes 呼叫 `launch_activate_socket` 接手 launchd 交付的 socket，Python 標準函式庫不支援，實作與維護成本超出痛點規模；靜態 HTML 方案（ADR 010 Alternatives 第二項）須手動重產，不解決「忘了」。**不成立**（判定依據為實作成本，屬判斷而非不可能，見 Alternatives）。
   - **否決條件 2**：修訂使沙盤提供機器可解析介面，或使 AI session 能自主取得信箱狀態而無檢查攔截。→ 判定：見第 4 項兩支柱與其 consistency-check 檢查項。**不成立**。
   - **否決條件 3**：修訂需要 repo 交付物自動寫入使用者機器的啟動設定。→ 判定：安裝一律由使用者執行，repo 程式碼不碰 `launchctl`／`LaunchAgents`（第 1 項檢查）。**不成立**。
   - **ADR 010 第 1 項其餘四條**：第 1 條（唯讀、不在 skill 目錄外持久化）——伺服器行為不變，僅 launchd 日誌需補充定義（第 3 項）；第 2 條（刷新才掃描、無背景計時器）——不變，自動啟動不新增任何計時器或執行緒；第 4 條（綁 `127.0.0.1`、單一使用者）——不變；第 5 條（僅回傳 `text/html`）——不變。
   - **ADR 001 延後 MCP 的成本「常駐 process 與設定負擔」**：ADR 001 原文將此列為與「解決傳輸層而非觸發層」並列的獨立成本。本修訂**接受這項獨立成本**——伺服器於登入期間全程常駐，並帶來 plist 絕對路徑維護、重新部署後須 `kickstart` 等設定負擔（見 Consequences）。接受理由：使用者實際回報的痛點（開機忘了開）只能以常駐消除（否決條件 1 不成立），且常駐不新增機器可解析介面（否決條件 2 不成立）。此為本 ADR 的取捨判斷，不代表 ADR 001 當初認為常駐成本可附條件接受。
   - **ADR 002 的 MCP 重啟評估訊號**（跨機器協作；需讓無法執行 hooks／skills 的 agent 型別化存取信箱）：兩訊號皆未出現；本修訂亦不服務其中任何一個——仍綁本機、仍無結構化端點。
   - **結論**：三項否決條件皆不成立，通過。依評估結論修訂 ADR 010 第 1 項第 3 條（第 1 項）、補充第 1 條（第 3 項），並同步改寫 ADR 010 可證偽段（第 5 項交付物）。

1. **修訂 ADR 010 Decision 第 1 項第 3 條**，由「啟動與停止必須由使用者手動掌握」改為：

   > 啟動與停止由使用者掌握。唯一允許的自動化路徑是**使用者親手安裝**的 macOS LaunchAgent，且須同時滿足：
   > 1. 僅使用 `RunAtLoad`（登入時啟動一次），**不得**設定 `KeepAlive`、`StartInterval`、`StartCalendarInterval`、`WatchPaths` 等任何重啟或排程鍵；
   > 2. 安裝與解除皆由使用者手動執行（repo 只提供 plist 範本與指令說明），`install.sh` 與任何 skill **不得**自動寫入 `~/Library/LaunchAgents/` 或呼叫 `launchctl`；
   > 3. 使用者可隨時以 `launchctl bootout` 停止，並刪除 `~/Library/LaunchAgents/` 內的 plist 完成解除；解除後行為完全回到 ADR 010 原始的手動啟停模式（只做 `bootout` 而未刪 plist，下次登入仍會再度啟動）。
   >
   > 不得有 `cron`、其他 skill 或排程觸發的啟動或重啟路徑。
   >
   > 本放寬僅適用於 `skills/kunsu-dashboard/`；其他工具依 ADR 010 Decision 第 3 項比照時，第 1 項第 3 條以 ADR 010 原始文字為準。

   可證偽性以 `scripts/consistency-check.sh` 新增檢查項落地（第 5 項），下列任一成立即不適用本修訂：
   - `install.sh` 或 `skills/` 下任何可執行腳本（`*.sh`、`*.py`）出現 `launchctl` 或 `LaunchAgents` 字串；
   - plist 範本（以 `plutil` 或 python `plistlib` 解析）含白名單（`Label`、`ProgramArguments`、`RunAtLoad`、`StandardOutPath`、`StandardErrorPath`；不含 `WorkingDirectory`——`app/main.py` 自行以 `__file__` 設定匯入路徑、不依賴工作目錄，且 copy 模式重跑 `install.sh` 會刪除重建部署目錄，使常駐 process 的 cwd 指向已刪除目錄）以外的鍵，或 `RunAtLoad` 不為 true，或 `StandardOutPath`／`StandardErrorPath` 任一不等於 `/tmp/kunsu-dashboard.log`；
   - 頂層 `scripts/` 下的腳本（`*.sh`、`*.fish`、`*.py`，排除 `consistency-check.sh` 自身——其檢查樣式必然含該字串）出現 `launchctl` 或 `LaunchAgents` 字串。

   「使用者親手安裝」定義為：**repo 交付物不自動化安裝**——上列檢查保證 repo 內任何程式碼都不寫入 `~/Library/LaunchAgents/` 或呼叫 `launchctl`。使用者在 AI session 中請 agent 代為執行 SKILL.md 列出的指令，與使用者親自輸入在機器層無從區分；本 ADR 接受此情形且不嘗試偵測（沙盤 SKILL.md 以 frontmatter 停用自動載入，寫在其中的「agent 不得代為執行」規範在一般對話中不會被讀到，宣稱它有效即是不可檢查的意圖聲明）。**已安裝於使用者機器 `~/Library/LaunchAgents/` 的 plist 不在 consistency-check 可檢查範圍內**；以第 5 項驗收步驟中由使用者執行的 `plutil -p` 檢查補足，事後自行加入 `KeepAlive` 等鍵屬機器層級設定，責任在使用者。

2. **ADR 010 Decision 第 1 項第 2、4、5 條維持不變；第 1 條僅補充「持久性」的定義**（見第 3 項）。特別是第 2 條「資料新鮮度由使用者刷新瀏覽器頁面觸發，伺服器不跑背景計時器或背景執行緒」——自動啟動只改變伺服器 process 的生命週期，不改變掃描的觸發方式。

3. **launchd 的 stdout／stderr 導向 `/tmp/kunsu-dashboard.log`**，並補充 ADR 010 Decision 第 1 項第 1 條：

   > 寫入 `/tmp/` 的伺服器 stdout／stderr 日誌不屬「持久性資料」——macOS 於重開機時清除 `/tmp/`（`/tmp` 為 `/private/tmp` 的連結），日誌生命週期不跨越開機。此補充僅涵蓋伺服器自身的 stdout／stderr，不涵蓋快取、已讀標記或任何掃描結果；後者仍須另立 ADR。使用者親手放置於 `~/Library/LaunchAgents/` 的 plist 屬「使用者管理的機器層級設定」，比照 ADR 014 SessionStart hook 由使用者寫入 `~/.claude/settings.json` 的先例，不屬工具產生的持久性資料。本補充僅適用於 `skills/kunsu-dashboard/`；其他工具依 ADR 010 Decision 第 3 項比照時，第 1 項第 1 條以 ADR 010 原始文字為準。

   理由：日誌導向 `/dev/null` 時，launchd 啟動失敗（Python 路徑錯誤、依賴缺失、port 被佔用）完全不可見，使用者只會看到瀏覽器連線失敗而無從得知原因；`/tmp` 日誌保留診斷能力，且不留下跨開機的狀態。

4. **與 MCP 路線的機制層級區隔重新檢視**：ADR 010 Decision 第 2 項的區隔表有兩根支柱——(a) 只回傳 `text/html`、無 API contract；(b) 無自主觸發路徑，使用者須主動開瀏覽器並刷新。本修訂後：
   - (a) 完全不變；
   - (b) 的字面「沒有任何自主觸發路徑」**在 process 生命週期層面不再成立**——登入自動啟動正是一條無使用者動作的啟動路徑。

   因此區隔改由兩點支撐：
   - (a) 只回傳 `text/html`、無 API contract（不變，可由程式碼檢查）；
   - **登入自啟不使任何 AI session 自主取得信箱狀態**：ADR 002 所稱「觸發層」指 AI session 不會自主呼叫工具、通知問題依舊；伺服器常駐後，沒有任何 session 會因此得知新件，掃描仍只在使用者刷新瀏覽器時發生，伺服器不主動通知任何人。觸發層問題仍未被（也不打算被）本工具解決，與 ADR 010 原表一致。此支柱以 consistency-check 檢查項落地（第 5 項）：`skills/` 下除 `kunsu-dashboard/` 以外的任何腳本、hook 與 SKILL.md，不得出現指向本機的 HTTP URL 字串（`http://127.0.0.1`、`http://localhost`），白名單僅限既有的 tshehtu zoekt 查詢（`KUNSU_ZOEKT_URL`，port 6070）；新增白名單須修訂本 ADR。沙盤 port 由使用者自訂，故以「本機 URL 白名單制」而非比對沙盤 port 判定。repo 外使用者自寫的腳本不在可檢查範圍內。

   ADR 001 所列「常駐 process 與設定負擔」由第 0 項明載承擔。結論：在上述兩點下區隔仍成立，本修訂不使沙盤滑向 MCP 類的機器對機器介面。

5. **repo 內交付物**（2026-10-02 已實作）：
   - `skills/kunsu-dashboard/` 新增 LaunchAgent plist 範本（label、python 絕對路徑、`main.py` 絕對路徑、port 皆為使用者需替換的佔位值）；
   - `SKILL.md` 新增「登入自動啟動（選用）」一節：安裝（使用者先將填妥的 plist 放到 `~/Library/LaunchAgents/<label>.plist`，再對該檔執行 `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/<label>.plist`——plist 須位於該目錄，下次登入才會自動載入）、程式碼更新後重啟（`launchctl kickstart -k gui/$(id -u)/<label>`）、解除（以同一 label 執行 `launchctl bootout gui/$(id -u)/<label>` 後刪除 `~/Library/LaunchAgents/<label>.plist`）三段指令；
   - plist 範本的佔位值使用不含角括號的形式（如 `__LABEL__`、`__PORT__`），確保範本本身可被 `plutil`／`plistlib` 解析、白名單檢查可執行；
   - plist 範本的 `main.py` 路徑指向部署副本（`~/.claude/skills/kunsu-dashboard/app/main.py`），不指向 repo 工作樹——符合 Invariant 3 開發與部署分離，且以 copy 模式部署時，「何時需要 `kickstart`」單純對應「何時執行 `install.sh`」。以 `install.sh --link` 部署時，部署副本即指向 repo 工作樹的 symlink，任何 repo 內容變動（含切換分支、`git pull`）後都須 `kickstart -k`，不限於執行 `install.sh`；
   - `SKILL.md` 的「登入自動啟動（選用）」一節列出供使用者於終端機執行的指令（不宣稱 agent 不得代為執行，理由見第 1 項「使用者親手安裝」定義），安裝段最後為四步驟驗收：(1) bootstrap 前先停止任何手動執行中的 `start.sh`（否則它會佔住 port、使 LaunchAgent 啟動失敗，而 curl 仍由 `start.sh` 回應造成假綠燈）；(2) `launchctl print gui/$(id -u)/<label>` 確認 job 已載入且執行中；(3) `curl --retry 5 --retry-connrefused --retry-delay 1 -s http://127.0.0.1:<port>/ | grep -q '軍師沙盤（kunsu dashboard）'` 成功——比對 `app/main.py` 固定輸出的頁面標題，排除同 port 其他服務回 200 的假綠燈；(4) 登出再登入一次，重複 (2)(3) 確認下次登入確實自動啟動。另以 `plutil -p ~/Library/LaunchAgents/<label>.plist` 確認已安裝的 plist 只含白名單鍵、`RunAtLoad` 為 true。任一步失敗時：先 `launchctl bootout gui/$(id -u)/<label>` 並刪除 plist 回到手動模式，查 `/tmp/kunsu-dashboard.log` 修正原因後再重新安裝——避免失敗的 LaunchAgent 於後續每次登入重複嘗試；
   - `scripts/consistency-check.sh` 新增 LaunchAgent 約束檢查項（第 1 項可證偽性三條）與本機 URL 白名單檢查項（第 4 項第二支柱）；
   - `start.sh` 第 4 行「不涉及 launchd／cron／開機自動啟動」註解改寫為與本修訂一致，且只指向 SKILL.md「登入自動啟動（選用）」一節，不得出現 `launchctl` 或 `LaunchAgents` 字面（否則觸發第 1 項第一條檢查）；
   - `SKILL.md` 現行「沒有背景常駐或開機自動啟動機制」等敘述改寫為與本修訂一致；
   - `SKILL.md`「登入自動啟動（選用）」與「啟動」兩節互相加註：安裝 LaunchAgent 後不再以 `start.sh` 啟動；開發時以 `./start.sh <其他 port>` 執行。plist 範本的 port 佔位說明註明不要與 `start.sh` 預設的 8000 共用——否則兩者互搶同一 port，後啟動者以 `Errno 48` 結束；
   - ADR 010 可證偽段的「開機自動啟動（違反 3）」補修訂註記指向本 ADR，說明僅限 `RunAtLoad` 單一鍵且由使用者親手安裝者適用本修訂；
   - ADR 010 Decision 第 1 項第 1、3 條原文旁，以及第 2 項區隔表「觸發層」欄，各補修訂註記指向本 ADR，說明修訂後區隔改由「(a) 只回傳 `text/html`」與第 4 項第二支柱支撐，避免日後比照者讀到已被推翻的「沒有任何自主觸發路徑」論述；
   - `CLAUDE.md` 的 ADR 索引與 kunsu-dashboard 說明同步提及本修訂。

## Consequences

- **正面**：開機登入後沙盤即可用，消除「忘了開」的摩擦；不需要再為了讓伺服器在終端機關閉後存活而另外維護 `nohup` 腳本。
- **負面／限制**：
  - 伺服器在使用者登入期間全程佔用一個本機 port（預設 8000）與一個 Python process 的記憶體；若其他開發服務也使用同一 port，結果依對方綁定位址而異：對方綁 `127.0.0.1` 時，後啟動的一方啟動失敗（uvicorn 報 `Errno 48` 並結束，`RunAtLoad` 不重試）；對方綁 `0.0.0.0`（如 Docker port 映射）時，兩者同時啟動成功，瀏覽器打 `localhost:<port>` 由綁定較精確的沙盤接走，表面上像對方服務異常且無錯誤可查（2026-10-01 doc review 本機實測）。緩解：plist 範本的 port 佔位值說明須選一個任何介面上皆無其他服務使用的 port。
  - launchd 啟動失敗時（例如 Python 路徑錯誤、依賴缺失、port 被佔用）沒有主動通知，使用者只會看到瀏覽器連線失敗，須自行查看 `/tmp/kunsu-dashboard.log`。日誌以附加方式寫入，單次開機期間若伺服器頻繁輸出會持續增長，重開機才清除。
  - launchd 執行環境的 `PATH` 極簡，不載入 shell 設定（pyenv／conda 的 shims 皆不可用），plist 必須寫死已安裝 fastapi／uvicorn／PyYAML 的 Python 絕對路徑；使用者日後切換 Python 環境時，plist 會靜默失效，同樣只表現為連線失敗。
  - 任何一次 `install.sh` 重新部署（含只改 kunsu-inbox、未動沙盤）後，執行中的伺服器是舊版 Python 模組搭配新版掃描腳本的混版狀態——`app/kunsu_scan.py` 每次刷新以 subprocess 呼叫部署目錄內的 `kunsu-inbox/scripts/scan-*.sh`；掃描腳本輸出契約若有變動，可能誤判而非只是看到舊畫面。須手動 `launchctl kickstart -k` 才會一致。以 `install.sh --link` 部署時，部署副本即 repo 工作樹，任何 repo 內容變動（含切換分支）都會立即造成同樣的混版狀態，不經過 `install.sh`。登入自動啟動使伺服器存活整個登入期間，遇上混版的機率高於手動前景啟動。
  - `~/scripts/kunsu-dashboard.sh`（repo 外的 `nohup` 背景啟動腳本）已於 2026-10-01 由使用者決定刪除，其 `~/.local/state/kunsu-dashboard/` 日誌與 PID 檔一併移除，消除對第 1 項第 1 條的既有違反。本 ADR 生效前，沙盤回到 `start.sh` 手動前景啟動。
- 本專案首次出現 launchd 相關交付物（即使只是範本），日後其他提案可能援引本 ADR 主張「既然沙盤可以用 launchd，X 也可以」。緩解：沿用 ADR 010 Decision 第 3 項的比照條件——本修訂僅適用於 `skills/kunsu-dashboard/`，且僅限 `RunAtLoad` 單一鍵。
- **結構不變量**：Invariant 1 字面規則與 ADR 010 的五條範圍界定架構不變；本 ADR 只把第 3 條的「手動」放寬為「使用者親手安裝的登入啟動」，不構成對常駐服務的整體鬆綁。

## Alternatives considered

- **LaunchAgent 加 `KeepAlive`（崩潰自動重啟）**：可同時解決「崩潰後沒人發現」的問題，但目前沒有崩潰的實際回報，屬未發生痛點；且 `KeepAlive` 搭配不可恢復的錯誤（registry 損壞時伺服器其實不會崩潰、但 port 被佔用或依賴缺失會）會形成重啟迴圈，launchd 以約 10 秒間隔持續重試，`/tmp` 日誌在單次開機期間持續膨脹，而使用者在瀏覽器端只看到偶發的連線失敗。真正構成「自主重啟路徑」，與 ADR 010 第 3 條的原始精神衝突最大。不採用；若日後出現崩潰回報，另立 ADR 評估。
- **launchd `Sockets` 隨連線啟動（瀏覽器第一次連線才啟動 process）**：零常駐、保留「由使用者動作觸發」的語意，可完整保住 ADR 010 區隔表 (b) 的字面。但 uvicorn 須接手 launchd 交付的 socket，Python 標準函式庫無 `launch_activate_socket` 綁定，須以 ctypes 自行呼叫，實作與維護成本超出「開機忘了開」的痛點規模。不採用；為 Decision 第 0 項否決條件 1 的判定依據，試用期觸發重評時一併重新評估。
- **macOS「登入項目」搭配 `nohup` 腳本**：同樣達成登入啟動，但登入項目是 GUI 設定（系統設定 → 一般 → 登入項目），repo 無法以文字範本描述、也無法以 `consistency-check.sh` 或 grep 檢查設定內容，違反 ADR 010「條件須可由程式碼直接檢查」的要求。不採用。
- **shell 啟動檔（`config.fish`／`.zshrc`）偵測未運作就啟動**：開第一個終端機時才觸發，與「開機後直接開瀏覽器看」的情境不符；且每開一個 shell 都執行一次檢查，屬隱性副作用。不採用。
- **維持現狀（手動 `start.sh`）**：零改動、完全符合 ADR 010，但不解決「開機忘了開」的實際回饋。不採用。
- **日誌導向 `/dev/null`**：嚴守第 1 項第 1 條字面、不需補充定義，但 launchd 啟動失敗時完全不可見。使用者選擇以 `/tmp` 日誌保留診斷能力（2026-10-01）。不採用。
- **plist 範本同時列出 Codex 部署路徑（`~/.agents/skills/kunsu-dashboard`）**：兩個部署目錄的內容由同一次 `install.sh` 產出、完全相同，且 `install.sh` 恆部署 Claude Code 目標（Codex 目標僅在偵測到 `~/.codex/` 時額外部署），因此 `~/.claude/skills/` 路徑對任何安裝者皆存在。列出第二組路徑沒有服務到任何實際存在的安裝情境，反而可能誘使使用者兩份 plist 都安裝，造成登入時兩個伺服器搶同一 port、其一啟動失敗。不採用；SKILL.md 僅以一句話說明兩處為同一份程式碼。
