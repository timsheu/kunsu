---
status: 未處理
date: 2026-10-02
source: code-review
severity: low
---

# 沙盤同名軍師目錄只有排序在前者可經 ?k= 開啟

看板與 archive 頁以 `?k=<軍師目錄名>` 選軍師（`_select_kunsu` 白名單比對），registry 中兩個軍師目錄同名時（例如兩處都叫 `ebook`）只有排序在前者能開啟，後者在看板／archive／全文頁皆不可達。

來源：PR #1 Tier 2 code review（correctness＋Codex 跨模型佐證），2026-10-02 使用者裁決暫不處理——三 live 軍師目錄名互異、無實際案例；避免現在把可讀目錄名改成雜湊 token。

## 相關檔案

- skills/kunsu-dashboard/app/board_routes.py（`_select_kunsu`、`_kunsu_list`）
- skills/kunsu-dashboard/app/board_html.py（`_nav`、`handoff_href`、`kunsu_label`）

## 待辦方向

- 出現同名軍師時：`?k=` 改為「目錄名-6 碼路徑雜湊」唯一 token（可沿用 `html_common.nav_anchor_id` 的雜湊方式），`_select_kunsu`／`_nav`／`handoff_href` 三處同步，目錄名僅供顯示；舊式純目錄名仍可解析為相容。
