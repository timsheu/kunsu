---
status: 未處理
date: 2026-09-28
source: 2026-09-28 線總表 simplify／code review
severity: low
---

# consistency-check H 鏈資料表化與查重 12 行窗口餘裕

簡化審查跳過的既有重構：scripts/consistency-check.sh H 鏈為單行 14+ 個 grep -q 的 AND 鏈（每波遷移加兩個子句），WARN 訊息枚舉需同步維護、每軍師重複開檔 grep。候選修法：改「必要子字串 × 檔案」資料表驅動迴圈，遷移只加一筆資料。屬既有鏈的重構、非本次 diff 範圍。另：查重 12 行窗口（sed -n '1,12p'）在 depends_on＋series 同時存在時只餘 1 行，再加第三個選填 frontmatter 欄位須連動放寬窗口常數。

## 相關檔案


## 待辦方向

