---
date: 2026-07-24
topic: handoff-redact-grill-prompts
---

# handoff redact 與 grill 議題硬化提示 — 需求

## Summary

在 `handoff` 與 kunsu 投遞 skill 補兩類**提示句**：(1) **redact** — 各建檔／投遞步驟提醒「投遞前檢查並移除敏感資訊（API key／密碼／PII／憑證）」；(2) **grill** — 產交接前確保議題想透（可用 grilling／brainstorm）。純文件指引、零依賴、不動任何機制、狀態機或不變量。改動限於 skill 文件與版號 patch，不出 ADR。

---

## Problem Frame

兩者皆源自 Matt Pocock 的 [mattpocock/skills](https://github.com/mattpocock/skills) 研究——其 `handoff` skill 明列「投遞前 redact 敏感資訊」，`grill-me`／`grilling` 是「產出前 relentless 一問一答硬化議題」的 pre-build stress test。

- **redact 缺口**：`skills/handoff/SKILL.md`（v0.8.0）目前無任何 redact 指引。kunsu 交接／回覆／申請／上報會被 commit 進軍師 repo、未來公開時更可能外流，跨 repo 場景比單機 handoff 更需要。與全域安全規範「絕不將測試憑證／機密寫入受版控檔案」對齊，但該規範未在 skill 操作步驟現身。
- **grill 缺口（小）**：軍師 `/handoff add` 前無結構化的「議題想透」提示。但 ce-brainstorm 的 Interaction Rules 已內建 grilling 精神（一問一答、每題帶推薦、事實自查決策才問、達成共識前不動手），故此處**不重造機制**，只補一句指向既有工具的提示。

kunsu 的 handoff 與 mattpocock handoff 是不同物種（派工單 vs 接力棒），本需求僅借鏡「概念」，不整包移植。

---

## Key Decisions

- **提示形態，非守門。** redact 與 grill 都採「一句提示」，不建自動機密掃描腳本、不建產交接前 checklist 機制。符合 handoff 純指令本質、kunsu Invariant 1（不建編譯工具）、kunsu「偵測提示不強制」哲學，並對稱 mattpocock 自身的提示形態。

- **redact 涵蓋全部投遞／交接產出。** 機密可能寫入的每個點都提示：handoff `add`／`reply`（通用層）＋ `kunsu-apply` ＋ `kunsu-report`。一句提示成本低、無盲點。

- **redact 放通用層。** redact 是普世安全實踐，寫進 handoff 通用步驟讓所有 handoff 使用者受益（不限 kunsu），kunsu 投遞經 handoff 時自然涵蓋；apply／report 為 kunsu 專屬 skill，各自補提示。

- **grill 承認 ce-brainstorm 已內建，僅一句提示。** 放通用 handoff `add`（產交接前想透對任何交接都適用）＋軍師範本工作流程，指向既有 grilling／brainstorm。

- **不出 ADR、版號 patch。** 純文件提示補強，不動機制／不變量／狀態機，直接改 skill 文件；handoff v0.8.0→v0.8.1。（對比 committed-orphan 那條線動狀態機語意故出 ADR 014，此處判斷不需。）

---

## Requirements

**redact 提示**

- R1. handoff `add` 建交接檔步驟加 redact 提示（通用層）。
- R2. handoff `reply` 建回覆檔步驟加 redact 提示（通用層）。
- R3. `kunsu-apply` 投遞步驟加 redact 提示。
- R4. `kunsu-report` 投遞步驟加 redact 提示。
- R5. redact 提示的敏感資訊清單：API key、密碼、PII、憑證（比照 mattpocock 與全域安全規範，開放補充）。
- R6. 形態為提示指引，非自動掃描守門——不新增掃描腳本、不阻斷投遞。

**grill 提示**

- R7. handoff `add` 加「產交接前確保議題想透（可用 grilling／brainstorm）」提示（通用層）。
- R8. kunsu-init 軍師範本工作流程加對應的產交接前議題硬化提示。

**一致性**

- R9. handoff skill 版號 patch（v0.8.0→v0.8.1）；不出 ADR、不改 CONCEPTS（redact／議題硬化非新領域概念）；多副本文字（若同一提示落於多處）以 grep 核查一致。

---

## Scope Boundaries

- **自動機密掃描守門（不做）** — shell 腳本掃 API key／私鑰 pattern 於投遞前警告。對「一句提示」等級補強過度，且會讓 handoff 通用原語變重。
- **更實質的 grill 產交接前檢查機制（不做）** — handoff add 內建提問／checklist 步驟。ce-brainstorm 已覆蓋 grilling 精神，重造無邊際價值。
- **redact 僅限 kunsu 語境（否決）** — 已選「全部投遞／交接產出」，redact 放通用層適用所有 handoff 使用者。

---

## Dependencies / Assumptions

- **假設：預防性需求。** 目前無「機密寫進交接被 commit」的實際事件記錄；動機為未來公開 kunsu 時的外流風險，與 committed-orphan 那條線同一 posture。
- **假設：提示句足以達成目的。** redact／grill 靠使用者（與執行的 Claude session）遵循提示，不強制、不掃描；接受「使用者無視提示仍可能寫入機密」的殘餘風險，換取零依賴與符合哲學。

---

## Sources / Research

- [mattpocock/skills](https://github.com/mattpocock/skills) — `skills/productivity/handoff/SKILL.md`（redact secrets 指引）、`skills/productivity/grilling/SKILL.md`（relentless interview primitive）、`skills/productivity/grill-me/SKILL.md`。
- `skills/handoff/SKILL.md`（v0.8.0）— 現況無 redact 指引，add／reply 建檔步驟為提示落點。
- `skills/kunsu-apply/SKILL.md`、`skills/kunsu-report/SKILL.md` — kunsu 投遞端提示落點。
- `skills/kunsu-init/assets/templates/` 軍師範本 — grill 提示落點。
- 全域安全規範（`~/.claude/rules/common/security.md`）— redact 對齊來源。
