---
status: 未處理
date: 2026-09-28
source: 2026-09-28 線總表 code review residual
severity: low
---

# series 讀端強健化：引號值、YAML 型別值、CRLF

series 讀端強健化三項（皆 residual，目前無實害）：（1）總表 frontmatter 寫成 series: "線A"（帶引號）不會命中且被列為他線——骨架已印不加引號版本，可在 awk 取值後去成對引號；（2）series 值為 YAML 型別轉換值（yes／123／null／~）目前唯一消費端是本腳本文字比對，沙盤與 hook 不讀此欄，若日後沙盤依 series 聚合（B-2 視圖）須在讀端統一為字串；（3）CRLF 檔案在非 ugrep 環境下 grep -x 比對可能漏算，與既有查重同屬已接受限制。

## 相關檔案


## 待辦方向

