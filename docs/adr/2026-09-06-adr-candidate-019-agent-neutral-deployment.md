---
title: ADR Candidate 019 — kunsu 通用化：adapter 為部署目標＋字面對應，Claude Code 是第一個 adapter
date: 2026-09-06
type: adr
status: accepted
---

# ADR 019：kunsu 同一份原始碼雙部署至 Claude Code 與 Codex——Invariant 3 擴張、ADR 009 第二種確認形態、ADR 001 Consequences 翻案

> 狀態：**Accepted**（2026-10-03 使用者審定。生效條件達成：codex-pilot 於審定同日單輪 25 項全數 PASS（codex-cli 0.154.0、gpt-5.5），此前八個 AE 已於第 3／5 輪分別成立、第九波遷移已依合併證據執行。審定同日落字：Invariant 3 字面、ADR 001／009 修訂註記、ADR 010 Decision 7 措辭。源自 [2026-09-06 需求文件](../brainstorms/2026-09-06-codex-agent-neutral-deployment-requirements.md)，該文件經 5-persona doc review 13 筆修正；實作計畫 [2026-09-06-001](../plans/2026-09-06-001-feat-codex-agent-neutral-deployment-plan.md) 經 4-persona review 14 筆修正。本 ADR 為計畫 U1，依 ADR 010／017 慣例先出 candidate、一輪 doc review（coherence／feasibility／adversarial 三 persona，13 筆修正全數套用）後才動載體。**生效條件**：Decision 6 的「相容」與 Consequences「首次以第二 agent 實證」以實作計畫 U8 試點通過為生效條件；試點證明 Codex 無法執行 handoff 流程（非 sandbox 設定問題）時，本 ADR 退回 candidate、Decision 6 重評）。

## Context

kunsu 的資料層（交接、回覆、上報、申請、todo 皆為 YAML frontmatter＋markdown；註冊表為純 JSON；「未 commit 即未處理」訊號是 git）與腳本層（十八支產檔、歸檔、掃描腳本與兩支 hook）從一開始就沒有依賴任何特定 AI coding agent。但工具組的**部署與指引**只認 Claude Code：Invariant 3 字面「部署至 `~/.claude/skills/`」、hook 掛載說明只寫 `~/.claude/settings.json`、七份 SKILL.md 以 Claude Code 工具名（AskUserQuestion、ListAgents、SendMessage、`$CLAUDE_SKILL_DIR`）與斜線呼叫形（`/handoff`）描述流程步驟。ADR 001 Consequences 當時明寫「無法服務不跑 Claude Code 的使用情境（接受——目前唯一使用者的工作流即 Claude Code）」。

2026-08-31 的外部計畫《Kunsu 通用 Agent 架構重構》提出 Core／Adapter 程式化重構——Agent Runtime interface（start／attach／status／stop）、registry live state store、capability detection——2026-09-01 評估屬過度設計：落實需建 orchestrator 或 daemon，違反 Invariant 1（純 skill＋範本＋膠水腳本），推翻 ADR 002／010／015 的手動掌控設計。

2026-09-06 對 Codex CLI 0.142.5 的查證（官方文件、`rust-v0.142.5` 原始碼、本機 `codex exec` 實測）改變了前提：

- hooks 支援 `PreToolUse`（JSON `permissionDecision: "deny"` 或 exit 2）與 `SessionStart`（stdout 注入 context），stdin 欄位 `tool_name: "Bash"`、`tool_input.command`、`source`、`cwd` 與 Claude Code 一致（實收確認）；hook 程序不受 sandbox（實測 read-only 下仍寫入家目錄）。
- skills 採同一套 `SKILL.md`（name／description frontmatter）格式，文件位置 `~/.agents/skills/`（`~/.codex/skills` 原始碼標 deprecated），目錄 symlink 追蹤，陌生 frontmatter 欄位靜默忽略；`$name` 顯式呼叫或依 description 隱式選用。
- `project_doc_fallback_filenames = ["CLAUDE.md"]` 使 AGENTS.md 缺席時讀軍師 CLAUDE.md；`project_doc_max_bytes` 預設 32 KiB 為專案鏈合計預算、超限靜默截尾（ebook 軍師 CLAUDE.md 已 34,581 bytes）。
- Codex 的阻塞式提問 `request_user_input` 預設只在 plan mode 可用（`[features] default_mode_request_user_input` 旗標可在 default mode 啟用，under development）；無跨 session 傳訊（ListAgents／SendMessage 無對應物）。
- 副官盤點：十八支腳本中只有 `session_hook.py`、`pretooluse_git_guard.py`、`kc.fish` 三支是換 agent 即整支失效的硬耦合，其中兩支 hook 契約 Codex 已相容；其餘十五支的 Claude 字面只剩 `~/.claude/*.json` 狀態檔路徑與 `CLAUDE.md || AGENTS.md` 專案根標記。

於是上游 idea「Codex 無 PreToolUse 等價攔截點、ADR 017／018 防線在 Codex 側退回提醒層」的前提不成立。真正沒有對應物的只剩跨 session 推播與 `kc.fish` 的啟動命名，兩者本就有降級路徑或不在賭注內。使用者定案：Codex 第一階段同時扮演接手方與軍師，最小成立版本為「軍師與子專案雙向都能經 handoff 文件溝通」。

## Decision（提案）

1. **Invariant 3 字面擴為「部署至各 agent 的 skill 目錄」**：本 ADR 所稱「adapter」指一個特定 agent 的部署目標（skill 目錄與 hook 設定檔）加上一組字面對應（各 SKILL 首節的 Agent 對應表），定義詳 Decision 2。部署目標：Claude Code `~/.claude/skills/`、Codex `~/.agents/skills/`（不用 deprecated 的 `~/.codex/skills`；兩目錄並存時只部署一處）。`~/.agents/skills/` 是 Agent Skills 開放規格的共用 user 目錄（本機已有第三方 skill），任何遵循該規格的 agent 部署後都會載入 kunsu——未列於對應表的 agent 依 Decision 3 的保守預設行為。開發與部署分離的精神零改動：原始碼仍只在本 repo 版控，經 `install.sh` 部署，不在任何部署目錄內開發。可由程式碼檢查的條件（比照 ADR 010 第 21 行）：`scripts/consistency-check.sh` D 項擴充為每個部署目標覆蓋全部 `skills/` 下的 skill。
2. **adapter＝部署目標＋字面對應，不是程式層**：讓 kunsu 在不同 agent 上可用的方式是一個部署目標（各 agent 的 skill 目錄與 hook 設定檔）加一組字面對應（SKILL.md 內文以能力名指稱，各 SKILL 一張「Agent 對應表」列能力→Claude Code 工具／Codex 對應），不建 Agent Runtime interface、不建 registry live state store。依據：ADR 001 Decision 1（交付物限定純 skill＋範本＋膠水腳本，零改動）；ADR 003 Alternatives 對 vendor 複製的否決（「兩份原始碼需人工同步」）——本 ADR 據此不另寫 Codex 薄殼，七份對應表為七份副本、由 consistency-check 機械比對逐字一致。Claude Code 是第一個 adapter，不是 kunsu 的內部假設；第三個 agent 只需再加一個部署目標與改對應表。
3. **ADR 009 修訂——確認 commit 的第二種實現形態**：ADR 009 Decision 1「AskUserQuestion 確認一次 → 執行」與 Consequences「headless／pipeline 情境 AskUserQuestion 不可用時退化為『不 commit＋提示』」，修訂為：阻塞式確認工具可用即用；不可用時依對應表「阻塞式確認」列的**能力類別**（不以 agent 名稱、不以「使用者是否在線」）判定——具備原生阻塞式工具的 agent（Claude Code）：工具不可用即為 headless／pipeline，一律視同取消（既有行為）；不具備者（Codex，除非開啟 `default_mode_request_user_input` 使工具可用）：agent 印出定型指令與訊息、附一句狀態宣告（index 已暫存待確認 commit，下一步只能同意或取消）、結束該回合，僅在**緊接的下一回合**收到使用者明確同意的文字才執行——該回合內容非明確同意（含改要求別事）即視同取消，index 暫存保留，之後若要 commit 須重新印出定型指令再問一次，不得把更早回合的懸置確認與後續任何肯定語連結；`codex exec` 無下一回合即等價取消；對應表未列的 agent 視同不具備，且不進入文字回合，只印定型指令後停止、推播整步跳過。**此形態屬規範層而非結構關卡**：AskUserQuestion 的阻塞由工具層強制，文字同意由 agent 判讀；「獲同意後 commit」與「未等同意逕行 commit」的產物同形（都是一筆 commit），事後偵測（歷史夾帶、`MISDECLARED_ARCHIVE_ADD`）只覆蓋 commit 內容形狀，對「同意缺席」零觀測——形狀正確的未授權 commit 不產生任何事件；此缺口的實害邊界由 ADR 009「絕不 push」界定為本地可逆（`git reset --soft HEAD~1`），裁決依據為使用者親身遭遇的回報而非統計檔。**條件式定性**（見 Decision 5）：真實路徑下每個可寫根的 `.git/` 唯讀，Codex TUI 基線與「僅列軍師路徑」的選用形之下，`git add`／`git commit` 皆須經 Codex sandbox 核准提示（預設 `approvals_reviewer` 為 user），該提示本身是工具層阻塞關卡、逕行 commit 可被看見並拒絕；「純規範層」與 `codex exec` 的印指令→無下一回合即取消流程，只在 `<軍師 repo>/.git` 被明列進 `writable_roots` 或 sandbox 為 danger-full-access 時成立。「使用者明確要求」的定義零改動，全域「不主動 commit」規則零改動；ADR 009 Decision 2 投遞端不對稱（子專案端回覆不 commit）零改動、Codex 接手方照用。ADR 002 Decision 5「產品取捨與驗收照舊 AskUserQuestion」的人工閘門不動，僅載體依 agent 對應。
4. **ADR 001 Consequences 翻案**：「無法服務不跑 Claude Code 的使用情境（接受——目前唯一使用者的工作流即 Claude Code）」一句翻案。比照 ADR 015 對 ADR 002 的兩層記法：（一）事實前提變更——使用者工作流已同時含 Codex（2026-09-06 定案兩端都要）；（二）機制變更——不是為第二 agent 另建工具鏈，而是同一份原始碼多一個部署目標與一組字面對應，ADR 001 Decision 1 零改動。本翻案**使 ADR 001 的 Claude Code 限制限縮於「指引與部署層的字面」**，其對編譯型工具與 MCP 的否決維持不變。
5. **sandbox 與 Invariant 2 的邊界**：Codex 模型經 shell 執行的腳本受 sandbox（workspace-write 下 cwd 外路徑與每個可寫根底下的 `.git/` 唯讀），影響三類寫入——接手方 reply／apply／report 寫軍師 repo、軍師端 `git mv`／`git add`／`git commit`、腳本層對 `~/.claude/*.json` 統計檔與 registry 的寫入（fail-open 靜默不記）；hook 程序不受 sandbox。處置三選一，本 ADR 定基線與界線：
   - **基線：TUI 逐次核准**——workspace-write 被擋時 Codex 跳核准提示改在 sandbox 外重跑，零設定、零 kunsu 指引登記（Codex 首次信任專案仍自寫 `[projects.*] trust_level`，屬 agent 自身簿記）；此核准提示同時是 Decision 3 所述的附帶結構關卡。`codex exec` 無核准提示，基線不適用，exec 使用者只能走試點形或選用形。
   - **試點：CLI 單次覆寫**——`-c sandbox_workspace_write.writable_roots=[...]` 只在該次呼叫生效、不寫 config；明列 `<repo>/.git` 可解除該根 `.git/` 唯讀，但同時移除上述核准關卡。
   - **選用：`writable_roots` 常設登記**——把軍師路徑（與 `~/.claude`）寫進 `~/.codex/config.toml`。Invariant 2 所稱「常設登記」的判準：限 kunsu 流程維護、消費、或掛載說明指引使用者寫入的登記；agent 自身簿記（Codex `[projects.*] trust_level`、Claude Code `~/.claude/projects/`）不在其列。`writable_roots` 由掛載說明指引寫入、且不隨 add-project／remove-project 生命週期同步（會 stale），落入前者——成為機器路徑第三處登記，字面牴觸 Invariant 2「常設登記只存在於兩處」；本 ADR **不開此例外**，只在掛載說明列為選用並註明張力，由使用者自行決定；列入 `<repo>/.git` 後，基線下每次 git 寫入觸發的 TUI 核准提示（Codex 側唯一附帶的結構性關卡）隨之消失，Decision 3 的規範層形態失去此附帶保護——選用前應知悉；`~/.claude` 狀態檔目錄不是機器路徑登記、不觸 Invariant 2，但決定 ADR 017／018 觀察期數據對 Codex 使用是否可見（不列則 Codex 側統計靜默缺漏，只有 hook 路徑會寫）。
6. **ADR 002 Decision 4 MCP 重啟訊號未觸發**：該訊號之一為「需讓無法執行 Claude hooks／skills 的 agent 型別化存取信箱」；Codex 的 hooks 契約已實測相容、skills 格式已查證相容（handoff 流程在 Codex 上的端到端可用性以 U8 試點為生效條件，見狀態 blockquote），本 ADR 引入第二 agent **不構成**該訊號，MCP 維持延後。ADR 015 Decision 2 推播降級（工具不可用整步跳過、hook 兜底）在 Codex 側直接生效，ADR 015 零改動。
7. **ADR 010 措辭附註**：`skills/kunsu-dashboard/SKILL.md` 自「刻意不使用觸發語慣例格式」改為「frontmatter 存在但兩 agent 各以原生旗標停用選用」——Claude Code `disable-model-invocation: true`／`user-invocable: false`，Codex `agents/openai.yaml` `policy.allow_implicit_invocation: false`。理由：Codex loader 對缺 frontmatter 的 SKILL.md 每次啟動記 warning，而 `session_hook.py` 需同樹存在 `kunsu-dashboard`。沙盤 app 與 `start.sh` 零改動，ADR 010 例外範圍界定五條零改動；此為「沙盤零改動」邊界的唯一、有限例外。
8. **ADR 014 Decision 6 機器層級設定擴及 `~/.codex/`**：`~/.codex/hooks.json`（hook 掛載，附加於既有陣列尾端；信任鍵含位置索引，清理壞條目須排在附加與信任之前）與 `~/.codex/config.toml`（`project_doc_max_bytes = 65536` 必要；`project_doc_fallback_filenames = ["CLAUDE.md"]` 降為選用——軍師 repo 改由 kunsu-init scaffold 內建 `AGENTS.md → CLAUDE.md` symlink 讓 Codex 原生讀到憲章，軍師 repo 是 kunsu 自己的產出、不觸 Invariant 2，全域 fallback 的「所有子專案也讀 CLAUDE.md」副作用與「軍師 repo 出現 AGENTS.md 即失效」脆弱點同時消失；三 live 軍師於第九波遷移補 symlink）與 `~/.claude/settings.json` 同屬機器層級，指向部署路徑，不進任何 git repo。Codex hook 指向 Codex 部署位置的腳本（各部署位置自足），不指回 Claude Code 部署位置。hooks.json 信任位置索引的事後漂移（第三方 plugin 安裝或移除改動前面條目）由 `scripts/consistency-check.sh` 新增 WARN 級檢查項偵測——比對 `~/.codex/config.toml` `hooks.state` 鍵中的群組索引與 hooks.json 內 kunsu 條目實際索引，不一致即 WARN（比照既有 live 軍師 WARN 級抽查讀取機器層級狀態的先例）。

## 邊界與威脅模型（顯式接受）

- **文字同意的不可觀察性**（Decision 3，於 `.git` 可寫的形態下）：Codex 側「獲同意後 commit」與「逕行 commit」產物同形，規範層無法自證，事後偵測對同意缺席零觀測；接受，實害邊界由「絕不 push」界定為本地可逆，裁決依據為使用者親身遭遇的回報（不以統計檔零事件推定零違規）。基線形態下 sandbox 核准提示為附帶結構關卡。
- **Codex hook 失效形狀**：未信任、清理前面條目使位置索引改變——兩支 hook 同時靜默略過、零訊號；此時 Codex 側統計只剩模型 shell 路徑，基線 sandbox 下該路徑對 `~/.claude/*.json` 又靜默失敗，疊加後 Codex 側對 ADR 017／018 觀察期零觀測，統計檔「零事件」不可讀為守門健康。掛錯路徑則不同：`python3 <不存在的檔案>` exit 2 且 stderr 非空，Codex 對 PreToolUse 視為 Blocked——與 Claude Code 同為 fail-closed 擋全部 Bash（以試點實測為準）。接受，掛載說明固定順序（清壞條目→尾端附加→TUI 信任）、掛後自檢、試點前置核對 `hooks.state` 索引、consistency-check 常設 WARN 偵測索引漂移。
- **統計數據對 Codex 側可能缺漏**（Decision 5）：未列 `~/.claude` 於 `writable_roots` 時 `total_runs`、基線、`MISDECLARED` 事件在 Codex 模型 shell 路徑不記；接受，掛載說明明寫，playbook 手動核對真實路徑 `total_runs` 是否遞增。
- **全域 project doc 設定的副作用**：`project_doc_fallback_filenames` 使 Codex 在所有子專案也讀 CLAUDE.md；`project_doc_max_bytes` 超限靜默截尾。接受，掛載說明明寫，consistency-check 可加 WARN 級大小門檻。
- **hook 狀態檔跨 agent 共用**：版號變動提示被先啟動的 agent 消耗一次；接受為小損失。
- **既有並發防護缺口**：三個狀態檔兩 agent 併寫，暴露機率上升；本 ADR 不處理，沿後續評估項。

## 開放問題

1. `GUARD_DENY` 事件是否加 `agent` 欄位以區分來源 agent（觀察期數據混流；commit 衍生事件天生無法歸因）——觸及腳本行為，規劃期裁決。
2. `default_mode_request_user_input` 成熟後，Codex 側是否改用原生阻塞式提問取代文字回合（R5「工具可用即用」已自動涵蓋，只差是否在掛載說明升為建議）。
3. Codex 軍師端 add-project 審核（核准寫 registry 走模型 shell 受 sandbox）待 Decision 5 處置定案後另批評估。
4. `/import`（Codex 自 Claude Code 匯入 skills 至 `~/.agents/skills/`）與 install.sh 雙部署的互動，待實測一次後於掛載說明補一句。

## Consequences

- **正面**：kunsu 的協議與腳本首次以第二 agent 實證 agent 無關；Codex 接手方與軍師端可用，且與 Claude Code 共用同一份原始碼、同一組 hook、同一套狀態檔；ADR 017 守門與 ADR 014 hook 在 Codex 側零改動即生效；「adapter＝部署目標＋字面對應」使第三 agent 的成本收斂為一個部署目標、一張對應表與一組 hook 掛載片段，前提是該 agent 的 hook payload 契約相容。
- **負面／限制**：七份對應表為七份副本（機械比對收口）；Codex 側確認 commit 在 `.git` 可寫的形態下自結構關卡降為規範層，本地可逆（絕不 push）承擔兜底；Codex 側統計數據完整性依賴使用者是否登記 `~/.claude` 為可寫；Invariant 3 與 ADR 001 字面各修訂一處、ADR 009 修訂一處、ADR 010 措辭一處，憲章副本同步成本由 consistency-check H 鏈與第九波遷移吸收；Codex 版本漂移（文件已領先 0.142.5）使掛載片段須隨版本重驗，「hook 程序不受 sandbox」為本版 hook runner 實作細節而非文件承諾，列為升版重驗項。

## Alternatives considered

- **Core／Adapter 程式化重構**（外部計畫原案）：Agent Runtime interface 與 live state store 需常駐程式，違反 Invariant 1，推翻 ADR 002／010／015 的手動掌控設計；且大半「agent-neutral」目標已天然成立。不採。
- **Codex 專屬薄殼 SKILL.md**：流程指引出現第二副本，done 六道查核、斷言層級紀律、矛盾回報全要複製或 Codex 側缺席，正是本 repo 已實證會漂移的形狀（ADR 003 vendor 複製否決同理）。不採。
- **抽 agent-neutral 協議規格文件＋兩薄殼**：等於三份載體，且使用者定案的賭注不含 spec，做了不驗證任何東西；等第三 agent 真的出現再評估。不採。
- **逐處括號對應（「能力（Claude Code：X；Codex：Y）」）**：第三 agent 到來時要改十七個以上分散編輯點，consistency-check 要逐點排除括號。不採為主體，改為內文能力名＋各 SKILL 一張對應表。
- **`writable_roots` 常設登記軍師路徑並開 Invariant 2 例外**：機器路徑第三處登記、新增軍師須同步維護；TUI 逐次核准零設定可用。不採為基線，列為選用（Decision 5）。
- **單一 `agent-map.md` 來源＋install.sh 部署時複製進各 skill 目錄**：repo 內副本歸零、M 項可省，但 SKILL.md 須改以「見同目錄對應表檔」指稱，agent 多一次讀檔——手動路徑觸及率教訓（v0.16.0）顯示多一跳即多一分失效機率，且部署後仍是七份複本只是生成時點不同。不採；七副本＋機械比對是「計算載體同步」的既定路線。
- **軍師 repo 內 `AGENTS.md → CLAUDE.md` symlink**（取代全域 `project_doc_fallback_filenames`）：只寫軍師自己的 repo、不觸 Invariant 2，全域副作用與 fallback 失效條件同時消失。**採納**（Decision 8），fallback 降為選用。
- **Codex 只當接手方**：使用者定案兩端都要；若日後改回，Codex 薄殼路線才值得重評。
