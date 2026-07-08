# 🏠 kunsu 知識庫

為多 repo AI 協作建立「軍師」（規劃協調中心）的 scaffolding 工具組的 Obsidian 著陸頁。把這篇加入 **Bookmarks**，每次開 vault 一鍵回到這裡。

> 下方標示 `dataview` 的區塊需要啟用社群外掛 **Dataview**（本 vault 已內附程式碼，首次開啟時於 Settings → Community plugins 啟用即可）。未啟用時會顯示為原始程式碼區塊，不影響其他連結。

---

## 入口

- [[CLAUDE|CLAUDE.md]] — 專案主入口與核心規範
- [[docs/README|📁 文件中心索引]]

## 文件分類導航

- [[docs/adr/2026-07-06-adr-candidate-001-pure-skill-no-injection|ADR 001 — 純 skill＋範本，不注入子 repo]]
- [[docs/adr/2026-07-06-adr-candidate-002-relay-automation-registry-inbox|ADR 002 — 傳令自動化：反向註冊表＋inbox]]
- [[docs/plans/2026-07-06-001-feat-planner-toolkit-skills-plan|實作計畫 — kunsu-init 與 kunsu-inbox skill 工具組]]
- [[docs/brainstorms/2026-07-06-planner-toolkit-requirements|種子需求 — 規劃中心 scaffolding 與傳令自動化]]

---

## 進行中計畫

```dataview
TABLE type AS 類型, date AS 日期
FROM "docs/plans"
WHERE status = "active"
SORT date DESC
```

## 架構決策（ADR）

```dataview
TABLE status AS 狀態, date AS 日期
FROM "docs/adr"
SORT date DESC
```

## 最近構想（brainstorms）

```dataview
TABLE title AS 標題, topic AS 主題, date AS 日期
FROM "docs/brainstorms"
WHERE date
SORT date DESC
LIMIT 10
```

---

## 使用提醒

- **別用 Obsidian 搬移／改名** CE plugin 管理的固定路徑（如 `docs/plans`、`docs/brainstorms`、`docs/solutions`、根目錄 `CONCEPTS.md`）—— CE 指令靠這些路徑自動發現文件，改名會失效。
- 新筆記預設落點建議設在 `docs/scratch/`（Settings → Files and links → Default location for new notes）。
- 文件之間用標準 Markdown 連結或 `[[wiki]]` 串接，Obsidian 的 Graph／Backlinks 都讀得到。
