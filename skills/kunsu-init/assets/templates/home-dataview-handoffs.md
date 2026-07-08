## 交接文件狀態

```dataview
TABLE from AS 來源, to AS 對象, status AS 狀態, date AS 日期
FROM "docs/handoffs"
WHERE status
SORT date DESC
```

## 使用提醒（軍師附加）

- 本 vault 只涵蓋規劃文件，不含任何程式碼；各子專案各自有獨立的專案。
- **別用 Obsidian 搬移／改名** CE plugin 管理的固定路徑（如 `docs/plans`、`docs/brainstorms`、`docs/solutions`、`docs/handoffs`）——CE 指令靠這些路徑自動發現文件，改名會失效。
- 回覆信箱目錄 `docs/handoffs/replies/` 是對方 session 的寫入範圍，本 vault 只讀取，不編輯其中任何檔案。
