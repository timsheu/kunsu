## 上報狀態

```dataview
TABLE from AS 來源, created AS 建立日期, status AS 狀態, tags AS 標籤
FROM "docs/reports"
WHERE status
SORT created DESC
```

## 使用提醒（上報信箱）

- 上報信箱 `docs/reports/` 是子專案 session 以 `/kunsu-report` 主動上報的寫入範圍，本 vault 只讀取，不編輯其中任何檔案。
- **別用 Obsidian 搬移／改名** `docs/reports/` 下的檔案——歸檔需依協議四步驟由軍師 session 執行（Edit status → git add → git mv → 確認 commit），Obsidian 直接搬移會繞過版控順序、讓後續 git 狀態紊亂。
- 歸檔時依序：以 Edit 更新 `status: submitted` → `archived`，再 `git add`，再 `git mv` 至 `archive/`（untracked 檔案直接 `git mv` 會失敗，不可倒置順序），最後經 AskUserQuestion 確認後 commit 本次歸檔。
